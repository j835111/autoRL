from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from auto_rl.config import AgentConfig, ExperimentConfig, TrainingConfig
from auto_rl.experiment_management import (
    build_run_id,
    confidence_score,
    median_absolute_deviation,
    render_session_document,
)
from auto_rl.envs import GridGameEnv
from auto_rl.researcher import ResearchDecision, build_researcher
from auto_rl.researcher.llm_bridge import build_tuning_prompt
from auto_rl.schema import load_schema, validate_payload
from auto_rl.training import InnerAgent, build_agent, load_agent
from auto_rl.training.metrics import (
    BenchmarkSummary,
    CheckSummary,
    EpisodeSummary,
    EvaluationSummary,
    PhaseMetrics,
    TrainingSummary,
)


@dataclass
class CheckpointRecord:
    phase_index: int
    policy_path: str
    metrics_path: str
    success_rate: float
    avg_reward: float
    agent_config: AgentConfig
    training_config: TrainingConfig

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_index": self.phase_index,
            "policy_path": self.policy_path,
            "metrics_path": self.metrics_path,
            "success_rate": self.success_rate,
            "avg_reward": self.avg_reward,
            "agent_config": self.agent_config.to_dict(),
            "training_config": self.training_config.to_dict(),
        }


class AutoRLOrchestrator:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.output_dir = Path(config.training.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir = self.output_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.phase_log_path = self.output_dir / "phase_log.jsonl"
        self.metadata_path = self.output_dir / "experiment_metadata.json"
        self.experiment_journal_path = self.output_dir / "experiment_journal.jsonl"
        self.session_doc_path = self.output_dir / "experiment_session.md"
        self.phase_metrics_schema = load_schema(
            Path(__file__).resolve().parents[1] / "schemas" / "phase_metrics.schema.json"
        )

    def train(self) -> dict[str, Any]:
        self._prepare_output_dir()
        run_id = build_run_id(self.config.training.seed)
        started_at = datetime.now(UTC)
        started_clock = perf_counter()
        env = GridGameEnv(self.config.env, seed=self.config.training.seed)
        agent = build_agent(
            action_size=env.action_size,
            config=self.config.agent,
            seed=self.config.training.seed,
        )
        researcher = build_researcher(self.config.research)
        self._write_metadata(run_id=run_id, started_at=started_at)
        self._append_experiment_journal(
            {
                "event": "run_start",
                "run_id": run_id,
                "started_at": started_at.isoformat(),
                "objective": self.config.training.objective,
                "agent_config": self.config.agent.to_dict(),
                "training_config": self.config.training.to_dict(),
            }
        )
        self._write_session_doc(
            run_id,
            self._build_session_snapshot(
                history=[],
                best_checkpoint=None,
                rollbacks_applied=0,
                failed_checks=0,
            ),
            stop_reason=None,
        )

        history: list[PhaseMetrics] = []
        checkpoint_history: list[CheckpointRecord] = []
        best_checkpoint: CheckpointRecord | None = None
        stop_reason: str | None = None
        rollbacks_applied = 0
        failed_checks = 0
        last_completed_agent_config = AgentConfig.from_dict(self.config.agent.to_dict())
        last_completed_training_config = TrainingConfig.from_dict(self.config.training.to_dict())

        for phase_index in range(self.config.training.phases):
            runtime_stop_reason = self._runtime_budget_stop_reason(started_clock)
            if runtime_stop_reason:
                stop_reason = runtime_stop_reason
                break

            phase_agent_config = AgentConfig.from_dict(self.config.agent.to_dict())
            phase_training_config = TrainingConfig.from_dict(self.config.training.to_dict())
            agent.set_hyperparameters(self.config.agent, reset_epsilon=True)

            training_episodes = self._run_episodes(
                env=env,
                agent=agent,
                episodes=self.config.training.episodes_per_phase,
                training=True,
            )
            evaluation_episodes = self._run_episodes(
                env=env,
                agent=agent,
                episodes=self.config.training.evaluation_episodes,
                training=False,
            )

            phase_metrics = PhaseMetrics(
                phase_index=phase_index,
                training=TrainingSummary.from_episodes(training_episodes, final_epsilon=agent.epsilon),
                evaluation=EvaluationSummary.from_episodes(evaluation_episodes),
                learning_rate=self.config.agent.learning_rate,
                gamma=self.config.agent.gamma,
                epsilon_start=self.config.agent.epsilon_start,
                epsilon_decay=self.config.agent.epsilon_decay,
                episodes_per_phase=self.config.training.episodes_per_phase,
                q_table_size=agent.state_registry_size,
            )
            phase_metrics.benchmark = self._build_benchmark_summary(
                current=phase_metrics,
                history=history,
                best_checkpoint=best_checkpoint,
            )
            history.append(phase_metrics)

            metrics_path = self.output_dir / f"phase_{phase_index:02d}_metrics.json"
            checkpoint = self._save_checkpoint(phase_index, agent, env.action_labels, metrics_path, phase_metrics)
            checkpoint_history.append(checkpoint)

            phase_metrics.journal_event_id = f"{run_id}:phase:{phase_index}"
            phase_metrics.checks = self._run_phase_checks(phase_metrics, checkpoint.policy_path)

            checks_failed = not phase_metrics.checks.passed
            if checks_failed:
                failed_checks += 1
                phase_metrics.adjustments.append(
                    "Phase checks failed: keep current best only and avoid accepting this phase as deployable."
                )
            else:
                failed_checks = 0

            if not checks_failed and self._is_better_policy(phase_metrics, best_checkpoint):
                best_checkpoint = checkpoint
                agent.save(
                    self.output_dir / "best_policy.json",
                    env_config=self.config.env,
                    action_labels=env.action_labels,
                )

            prompt_path: str | None = None
            decision = ResearchDecision(agent=self.config.agent, training=self.config.training)

            if checks_failed:
                decision = ResearchDecision(
                    agent=phase_agent_config,
                    training=phase_training_config,
                    reasons=[
                        "Correctness checks failed for this phase.",
                        "Skip accepting benchmark gains until checks pass again.",
                    ],
                    source="system",
                    fallback_used=True,
                    rollback_requested=best_checkpoint is not None and best_checkpoint.phase_index != phase_index,
                )
            elif researcher is not None:
                prompt_text = build_tuning_prompt(history, self.config.agent, self.config.training)
                prompt_path = str(self._write_phase_prompt(phase_index, prompt_text))
                decision = researcher.analyze(
                    history=history,
                    agent_config=self.config.agent,
                    training_config=self.config.training,
                )
                phase_metrics.adjustments = list(decision.reasons)
            else:
                phase_metrics.adjustments = ["Research disabled: keep current configuration."]

            rollback_applied = False
            if decision.rollback_requested and best_checkpoint and best_checkpoint.phase_index != phase_index:
                agent = self._restore_checkpoint(best_checkpoint)
                self.config.agent = AgentConfig.from_dict(best_checkpoint.agent_config.to_dict())
                self.config.training = TrainingConfig.from_dict(best_checkpoint.training_config.to_dict())
                last_completed_agent_config = AgentConfig.from_dict(best_checkpoint.agent_config.to_dict())
                last_completed_training_config = TrainingConfig.from_dict(best_checkpoint.training_config.to_dict())
                rollback_applied = True
                rollbacks_applied += 1
                phase_metrics.adjustments.append(
                    f"Rollback applied to checkpoint from phase {best_checkpoint.phase_index}."
                )
            else:
                last_completed_agent_config = phase_agent_config
                last_completed_training_config = phase_training_config
                self.config.agent = decision.agent
                self.config.training = decision.training

            comparison = self._build_comparison(phase_metrics, best_checkpoint)
            comparison["rollback_applied"] = rollback_applied
            comparison_path = self.output_dir / f"phase_{phase_index:02d}_compare.json"

            self._write_json(metrics_path, phase_metrics.to_dict())
            self._write_json(comparison_path, comparison)
            self._append_phase_log(
                {
                    "run_id": run_id,
                    "journal_event_id": phase_metrics.journal_event_id,
                    "phase_index": phase_index,
                    "metrics_path": str(metrics_path),
                    "checkpoint_path": checkpoint.policy_path,
                    "comparison_path": str(comparison_path),
                    "prompt_path": prompt_path,
                    "research_source": decision.source,
                    "adjustments": phase_metrics.adjustments,
                    "validated_adjustments": decision.adjustments,
                    "fallback_used": decision.fallback_used,
                    "stop_requested": decision.stop_requested,
                    "rollback_requested": decision.rollback_requested,
                    "rollback_applied": rollback_applied,
                    "benchmark": phase_metrics.benchmark.to_dict(),
                    "checks": phase_metrics.checks.to_dict(),
                }
            )
            self._append_experiment_journal(
                {
                    "event": "phase_result",
                    "run_id": run_id,
                    "journal_event_id": phase_metrics.journal_event_id,
                    "phase_index": phase_index,
                    "benchmark": phase_metrics.benchmark.to_dict(),
                    "checks": phase_metrics.checks.to_dict(),
                    "metrics_path": str(metrics_path),
                    "checkpoint_path": checkpoint.policy_path,
                    "comparison_path": str(comparison_path),
                    "adjustments": phase_metrics.adjustments,
                    "research_source": decision.source,
                    "rollback_applied": rollback_applied,
                }
            )
            self._write_session_doc(
                run_id,
                self._build_session_snapshot(
                    history=history,
                    best_checkpoint=best_checkpoint,
                    rollbacks_applied=rollbacks_applied,
                    failed_checks=failed_checks,
                ),
                stop_reason=None,
            )

            checks_budget_reason = self._failed_checks_budget_stop_reason(failed_checks)
            if checks_budget_reason:
                stop_reason = checks_budget_reason
                break

            if decision.stop_requested:
                stop_reason = f"Researcher requested stop after phase {phase_index}."
                break

            threshold_reason = self._should_early_stop(history)
            if threshold_reason:
                stop_reason = f"Early stop after phase {phase_index}: {threshold_reason}"
                break

            rollback_budget_reason = self._rollback_budget_stop_reason(rollbacks_applied)
            if rollback_budget_reason:
                stop_reason = rollback_budget_reason
                break

        agent.save(
            self.output_dir / "final_policy.json",
            env_config=self.config.env,
            action_labels=env.action_labels,
        )

        best_phase = best_checkpoint.phase_index if best_checkpoint else -1
        best_eval_reward = best_checkpoint.avg_reward if best_checkpoint else float("-inf")
        best_eval_success_rate = best_checkpoint.success_rate if best_checkpoint else float("-inf")

        final_prompt = build_tuning_prompt(history, self.config.agent, self.config.training)
        summary = {
            "run_id": run_id,
            "objective": self.config.training.objective,
            "best_phase": best_phase,
            "best_eval_reward": best_eval_reward,
            "best_eval_success_rate": best_eval_success_rate,
            "final_agent_config": last_completed_agent_config.to_dict(),
            "final_training_config": last_completed_training_config.to_dict(),
            "suggested_next_agent_config": self.config.agent.to_dict(),
            "suggested_next_training_config": self.config.training.to_dict(),
            "history": [item.to_dict() for item in history],
            "checkpoints": [item.to_dict() for item in checkpoint_history],
            "stop_reason": stop_reason,
            "rollbacks_applied": rollbacks_applied,
            "failed_checks": failed_checks,
            "experiment_journal_path": str(self.experiment_journal_path),
            "session_doc_path": str(self.session_doc_path),
            "llm_tuning_prompt": final_prompt,
        }
        self._write_json(self.output_dir / "summary.json", summary)
        ExperimentConfig(
            env=self.config.env,
            agent=last_completed_agent_config,
            training=last_completed_training_config,
            research=self.config.research,
        ).save(self.output_dir / "resolved_config.json")
        self._write_session_doc(run_id, summary, stop_reason)
        self._append_experiment_journal(
            {
                "event": "run_end",
                "run_id": run_id,
                "ended_at": datetime.now(UTC).isoformat(),
                "stop_reason": stop_reason,
                "best_phase": best_phase,
                "best_eval_reward": best_eval_reward,
                "best_eval_success_rate": best_eval_success_rate,
                "rollbacks_applied": rollbacks_applied,
                "failed_checks": failed_checks,
            }
        )
        return summary

    def play(self, policy_path: str | Path, episodes: int = 3, render: bool = True) -> list[dict[str, Any]]:
        return self.play_saved_policy(
            policy_path,
            episodes=episodes,
            render=render,
            seed=self.config.training.seed,
        )

    @staticmethod
    def play_saved_policy(
        policy_path: str | Path,
        episodes: int = 3,
        render: bool = True,
        seed: int = 0,
    ) -> list[dict[str, Any]]:
        agent, env_config, action_labels = load_agent(policy_path, seed=seed)
        env = GridGameEnv(env_config, seed=seed)
        traces: list[dict[str, Any]] = []

        for episode_index in range(episodes):
            state = env.reset()
            done = False
            total_reward = 0.0
            steps = 0
            frames = [env.render()] if render else []
            success = False

            while not done:
                action = agent.greedy_action(state)
                result = env.step(action)
                state = result.state
                total_reward += result.reward
                steps += 1
                success = result.success
                done = result.done
                if render:
                    frames.append(f"Action: {action_labels[action]}\n{env.render()}")

            traces.append(
                {
                    "episode": episode_index,
                    "reward": total_reward,
                    "steps": steps,
                    "success": success,
                    "frames": frames,
                }
            )

        return traces

    def _prepare_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        managed_files = (
            self.output_dir / "best_policy.json",
            self.output_dir / "final_policy.json",
            self.output_dir / "summary.json",
            self.output_dir / "resolved_config.json",
            self.output_dir / "experiment_metadata.json",
            self.output_dir / "phase_log.jsonl",
            self.output_dir / "experiment_session.md",
        )
        for path in managed_files:
            if path.exists():
                path.unlink()

        for pattern in ("phase_*_metrics.json", "phase_*_compare.json", "phase_*_tuning_prompt.txt"):
            for path in self.output_dir.glob(pattern):
                path.unlink()

        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _run_episodes(
        self,
        env: GridGameEnv,
        agent: InnerAgent,
        episodes: int,
        training: bool,
    ) -> list[EpisodeSummary]:
        summaries: list[EpisodeSummary] = []
        epsilon_before_eval = agent.epsilon

        if not training:
            agent.epsilon = 0.0

        for _ in range(episodes):
            state = env.reset()
            done = False
            total_reward = 0.0
            total_td_error = 0.0
            steps = 0
            success = False
            hit_trap = False

            while not done:
                action = agent.select_action(state, explore=training)
                result = env.step(action)
                if training:
                    total_td_error += agent.update(
                        state=state,
                        action=action,
                        reward=result.reward,
                        next_state=result.state,
                        done=result.done,
                    )
                state = result.state
                total_reward += result.reward
                steps += 1
                success = result.success
                hit_trap = result.hit_trap
                done = result.done

            summaries.append(
                EpisodeSummary(
                    reward=total_reward,
                    steps=steps,
                    success=success,
                    hit_trap=hit_trap,
                    td_error=(total_td_error / steps) if steps else 0.0,
                )
            )

            if training:
                agent.end_episode()

        if not training:
            agent.epsilon = epsilon_before_eval

        return summaries

    def _save_checkpoint(
        self,
        phase_index: int,
        agent: InnerAgent,
        action_labels: list[str],
        metrics_path: Path,
        phase_metrics: PhaseMetrics,
    ) -> CheckpointRecord:
        policy_path = self.checkpoint_dir / f"phase_{phase_index:02d}_policy.json"
        agent.save(policy_path, env_config=self.config.env, action_labels=action_labels)
        checkpoint = CheckpointRecord(
            phase_index=phase_index,
            policy_path=str(policy_path),
            metrics_path=str(metrics_path),
            success_rate=phase_metrics.evaluation.success_rate,
            avg_reward=phase_metrics.evaluation.avg_reward,
            agent_config=AgentConfig.from_dict(self.config.agent.to_dict()),
            training_config=TrainingConfig.from_dict(self.config.training.to_dict()),
        )
        self._write_json(
            self.checkpoint_dir / f"phase_{phase_index:02d}_checkpoint.json",
            checkpoint.to_dict(),
        )
        return checkpoint

    def _restore_checkpoint(self, checkpoint: CheckpointRecord) -> InnerAgent:
        restored_agent, _, _ = load_agent(checkpoint.policy_path, seed=self.config.training.seed)
        return restored_agent

    def _write_phase_prompt(self, phase_index: int, prompt_text: str) -> Path:
        path = self.output_dir / f"phase_{phase_index:02d}_tuning_prompt.txt"
        path.write_text(prompt_text, encoding="utf-8")
        return path

    def _is_better_policy(self, phase_metrics: PhaseMetrics, best_checkpoint: CheckpointRecord | None) -> bool:
        if best_checkpoint is None:
            return True
        return (
            phase_metrics.evaluation.success_rate > best_checkpoint.success_rate
            or (
                phase_metrics.evaluation.success_rate == best_checkpoint.success_rate
                and phase_metrics.evaluation.avg_reward > best_checkpoint.avg_reward
            )
        )

    def _build_comparison(
        self,
        phase_metrics: PhaseMetrics,
        best_checkpoint: CheckpointRecord | None,
    ) -> dict[str, Any]:
        if best_checkpoint is None:
            return {
                "phase_index": phase_metrics.phase_index,
                "best_phase_index": phase_metrics.phase_index,
                "delta_success_rate": 0.0,
                "delta_avg_reward": 0.0,
                "is_best_so_far": True,
            }

        delta_success = phase_metrics.evaluation.success_rate - best_checkpoint.success_rate
        delta_reward = phase_metrics.evaluation.avg_reward - best_checkpoint.avg_reward
        return {
            "phase_index": phase_metrics.phase_index,
            "best_phase_index": best_checkpoint.phase_index,
            "delta_success_rate": delta_success,
            "delta_avg_reward": delta_reward,
            "is_best_so_far": (
                phase_metrics.phase_index == best_checkpoint.phase_index
                and delta_success == 0.0
                and delta_reward == 0.0
            ),
        }

    def _should_early_stop(self, history: list[PhaseMetrics]) -> str | None:
        patience = max(1, self.config.research.stop_patience)
        if len(history) < patience:
            return None

        recent = history[-patience:]
        if all(
            item.evaluation.success_rate >= self.config.research.stop_success_threshold
            and item.evaluation.avg_reward >= self.config.research.stop_reward_threshold
            for item in recent
        ):
            return (
                "evaluation reward and success rate stayed above the stop thresholds "
                f"for {patience} consecutive phases"
            )
        return None

    def _build_benchmark_summary(
        self,
        current: PhaseMetrics,
        history: list[PhaseMetrics],
        best_checkpoint: CheckpointRecord | None,
    ) -> BenchmarkSummary:
        previous = history[-1] if history else None
        reward_delta_previous = (
            current.evaluation.avg_reward - previous.evaluation.avg_reward if previous else 0.0
        )
        success_delta_previous = (
            current.evaluation.success_rate - previous.evaluation.success_rate if previous else 0.0
        )
        reward_delta_best = (
            current.evaluation.avg_reward - best_checkpoint.avg_reward if best_checkpoint else 0.0
        )
        success_delta_best = (
            current.evaluation.success_rate - best_checkpoint.success_rate if best_checkpoint else 0.0
        )
        reward_history = [item.evaluation.avg_reward for item in history] + [current.evaluation.avg_reward]
        noise_floor = median_absolute_deviation(reward_history)
        score = confidence_score(reward_delta_previous, noise_floor)
        passes_gate = len(reward_history) < 3 or score >= self.config.research.min_confidence_score
        return BenchmarkSummary(
            reward_delta_vs_previous=reward_delta_previous,
            success_delta_vs_previous=success_delta_previous,
            reward_delta_vs_best=reward_delta_best,
            success_delta_vs_best=success_delta_best,
            noise_floor=noise_floor,
            confidence_score=score,
            passes_confidence_gate=passes_gate,
        )

    def _run_phase_checks(self, phase_metrics: PhaseMetrics, policy_path: str | Path) -> CheckSummary:
        passed_checks: list[str] = []
        failed_checks: list[str] = []

        try:
            validate_payload(phase_metrics.to_dict(), self.phase_metrics_schema)
            passed_checks.append("phase_metrics_schema")
        except Exception as exc:
            failed_checks.append(f"phase_metrics_schema: {exc}")

        try:
            load_agent(policy_path, seed=self.config.training.seed)
            passed_checks.append("checkpoint_load")
        except Exception as exc:
            failed_checks.append(f"checkpoint_load: {exc}")

        try:
            traces = self.play_saved_policy(policy_path, episodes=1, render=False, seed=self.config.training.seed)
            if len(traces) != 1:
                raise ValueError("standalone play did not return exactly one trace")
            passed_checks.append("standalone_play_smoke")
        except Exception as exc:
            failed_checks.append(f"standalone_play_smoke: {exc}")

        return CheckSummary(
            passed=not failed_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
        )

    def _runtime_budget_stop_reason(self, started_clock: float) -> str | None:
        max_runtime_seconds = self.config.training.max_runtime_seconds
        if max_runtime_seconds is None:
            return None
        elapsed = perf_counter() - started_clock
        if elapsed >= max_runtime_seconds:
            return f"Runtime budget exceeded after {elapsed:.2f}s."
        return None

    def _rollback_budget_stop_reason(self, rollbacks_applied: int) -> str | None:
        if rollbacks_applied > self.config.research.max_rollbacks:
            return f"Rollback budget exhausted at {rollbacks_applied} rollbacks."
        return None

    def _failed_checks_budget_stop_reason(self, failed_checks: int) -> str | None:
        if failed_checks > self.config.research.max_failed_checks:
            return f"Correctness checks failed {failed_checks} consecutive phases."
        return None

    def _write_metadata(self, run_id: str, started_at: datetime) -> None:
        metadata = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "algorithm": self.config.agent.algorithm,
            "research_mode": self.config.research.mode if self.config.research.enabled else "disabled",
            "seed": self.config.training.seed,
            "output_dir": str(self.output_dir),
            "objective": self.config.training.objective,
        }
        self._write_json(self.metadata_path, metadata)

    def _append_phase_log(self, payload: dict[str, Any]) -> None:
        with self.phase_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _append_experiment_journal(self, payload: dict[str, Any]) -> None:
        with self.experiment_journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _build_session_snapshot(
        self,
        history: list[PhaseMetrics],
        best_checkpoint: CheckpointRecord | None,
        rollbacks_applied: int,
        failed_checks: int,
    ) -> dict[str, Any]:
        return {
            "best_phase": best_checkpoint.phase_index if best_checkpoint else -1,
            "best_eval_reward": best_checkpoint.avg_reward if best_checkpoint else 0.0,
            "best_eval_success_rate": best_checkpoint.success_rate if best_checkpoint else 0.0,
            "history": [item.to_dict() for item in history],
            "rollbacks_applied": rollbacks_applied,
            "failed_checks": failed_checks,
            "suggested_next_agent_config": self.config.agent.to_dict(),
            "suggested_next_training_config": self.config.training.to_dict(),
        }

    def _write_session_doc(self, run_id: str, summary: dict[str, Any], stop_reason: str | None) -> None:
        self.session_doc_path.write_text(
            render_session_document(
                run_id=run_id,
                objective=self.config.training.objective,
                output_dir=str(self.output_dir),
                journal_path=str(self.experiment_journal_path),
                summary=summary,
                stop_reason=stop_reason,
            ),
            encoding="utf-8",
        )

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

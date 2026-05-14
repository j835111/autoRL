from __future__ import annotations

from auto_rl.config import AgentConfig, ResearchConfig, TrainingConfig
from auto_rl.researcher.base import AutoResearcher, ResearchDecision
from auto_rl.researcher.validation import ResearcherAdjustmentValidator
from auto_rl.training.metrics import PhaseMetrics


class HeuristicAutoResearcher(AutoResearcher):
    def __init__(
        self,
        config: ResearchConfig,
        validator: ResearcherAdjustmentValidator | None = None,
    ) -> None:
        self.config = config
        self.validator = validator or ResearcherAdjustmentValidator()
        self._stagnation_count = 0
        self._regression_count = 0
        self._success_streak = 0

    def analyze(
        self,
        history: list[PhaseMetrics],
        agent_config: AgentConfig,
        training_config: TrainingConfig,
    ) -> ResearchDecision:
        if len(history) < 2:
            return self.validator.apply(
                payload={"rationale": ["Bootstrap phase: keep initial hyperparameters."]},
                agent_config=agent_config,
                training_config=training_config,
                source="heuristic",
            )

        previous = history[-2]
        current = history[-1]
        reward_delta = current.evaluation.avg_reward - previous.evaluation.avg_reward
        success_delta = current.evaluation.success_rate - previous.evaluation.success_rate
        payload: dict[str, float | int | bool | list[str]] = {"rationale": []}
        reasons = payload["rationale"]
        confidence_gate = current.benchmark.passes_confidence_gate if current.benchmark else True

        raw_improvement = (
            reward_delta > self.config.reward_improvement_threshold
            or success_delta > self.config.success_improvement_threshold
        )
        improved = raw_improvement and confidence_gate

        if improved:
            self._stagnation_count = 0
            self._regression_count = 0
            payload["learning_rate"] = min(
                self.config.max_learning_rate,
                agent_config.learning_rate * self.config.lr_growth_factor,
            )
            payload["epsilon_decay"] = max(
                self.config.min_epsilon_decay,
                agent_config.epsilon_decay * self.config.epsilon_decay_tighten,
            )
            payload["gamma"] = min(0.999, agent_config.gamma + self.config.gamma_step)
            reasons.append("Performance improved: slightly raise learning rate and tighten exploration decay.")
            reasons.append("Long-horizon behavior improved: increase gamma a little.")
        else:
            if raw_improvement and not confidence_gate:
                reasons.append(
                    "Improvement stayed within the estimated noise floor: keep changes conservative for now."
                )
            self._stagnation_count += 1
            reasons.append("Evaluation plateau detected.")

            if current.training.final_epsilon <= max(agent_config.epsilon_min + 0.02, 0.1):
                payload["epsilon_start"] = min(
                    self.config.max_epsilon_start,
                    agent_config.epsilon_start + self.config.epsilon_boost,
                )
                payload["epsilon_decay"] = min(
                    self.config.max_epsilon_decay,
                    agent_config.epsilon_decay * self.config.epsilon_decay_relax,
                )
                reasons.append("Exploration looks exhausted: boost epsilon_start and relax epsilon decay.")

            payload["learning_rate"] = max(
                self.config.min_learning_rate,
                agent_config.learning_rate * self.config.lr_decay_factor,
            )
            reasons.append("Reduce learning rate to stabilize value updates.")

            if self._stagnation_count >= self.config.plateau_patience:
                payload["episodes_per_phase"] = min(
                    self.config.max_episodes_per_phase,
                    int(training_config.episodes_per_phase * 1.15),
                )
                payload["gamma"] = max(0.85, agent_config.gamma - self.config.gamma_step)
                self._stagnation_count = 0
                reasons.append("Plateau persisted: allocate a longer phase and slightly shorten horizon.")

        payload["epsilon_min"] = max(self.config.epsilon_min_floor, agent_config.epsilon_min)

        if (
            current.evaluation.success_rate >= self.config.stop_success_threshold
            and current.evaluation.avg_reward >= self.config.stop_reward_threshold
        ):
            self._success_streak += 1
        else:
            self._success_streak = 0

        if self._success_streak >= self.config.stop_patience:
            payload["stop_training"] = True
            reasons.append("Success target held long enough: recommend stopping training.")
            self._success_streak = 0

        best_previous = max(
            history[:-1],
            key=lambda item: (item.evaluation.success_rate, item.evaluation.avg_reward),
            default=None,
        )
        if best_previous and (
            best_previous.evaluation.success_rate - current.evaluation.success_rate
            >= self.config.rollback_success_tolerance
            or best_previous.evaluation.avg_reward - current.evaluation.avg_reward
            >= self.config.rollback_reward_tolerance
        ):
            self._regression_count += 1
        else:
            self._regression_count = 0

        if self._regression_count >= self.config.rollback_patience:
            payload["rollback_to_best"] = True
            reasons.append("Current phase regressed enough from the best checkpoint: recommend rollback.")
            self._regression_count = 0

        try:
            return self.validator.apply(
                payload=payload,
                agent_config=agent_config,
                training_config=training_config,
                source="heuristic",
            )
        except Exception as exc:
            return self.validator.fallback(
                agent_config=agent_config,
                training_config=training_config,
                source="heuristic",
                reason=f"Heuristic payload failed validation: {exc}",
            )

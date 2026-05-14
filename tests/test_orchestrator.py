from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from auto_rl.config import AgentConfig, ExperimentConfig, TrainingConfig
from auto_rl.orchestrator import AutoRLOrchestrator
from auto_rl.researcher.base import ResearchDecision


class _IncrementResearcher:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, history, agent_config, training_config) -> ResearchDecision:  # type: ignore[no-untyped-def]
        del history
        self.calls += 1
        next_agent = AgentConfig.from_dict(agent_config.to_dict())
        next_agent.learning_rate += 0.1
        next_training = TrainingConfig.from_dict(training_config.to_dict())
        return ResearchDecision(
            agent=next_agent,
            training=next_training,
            reasons=[f"decision-{self.calls}"],
            source="test",
            adjustments={"learning_rate": next_agent.learning_rate},
        )


class OrchestratorSmokeTests(unittest.TestCase):
    def test_training_creates_artifacts_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "run"
            config = ExperimentConfig.load("configs/baseline.json")
            config.agent.algorithm = "q_learning"
            config.training.phases = 2
            config.training.episodes_per_phase = 25
            config.training.evaluation_episodes = 5
            config.training.output_dir = str(output_dir)

            summary = AutoRLOrchestrator(config).train()

            self.assertIn("history", summary)
            self.assertIn("run_id", summary)
            self.assertIn("objective", summary)
            self.assertTrue((output_dir / "best_policy.json").exists())
            self.assertTrue((output_dir / "final_policy.json").exists())
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "resolved_config.json").exists())
            self.assertTrue((output_dir / "experiment_metadata.json").exists())
            self.assertTrue((output_dir / "phase_log.jsonl").exists())
            self.assertTrue((output_dir / "experiment_journal.jsonl").exists())
            self.assertTrue((output_dir / "experiment_session.md").exists())
            self.assertTrue((output_dir / "phase_00_metrics.json").exists())
            self.assertTrue((output_dir / "phase_00_compare.json").exists())

            phase_metrics = json.loads((output_dir / "phase_00_metrics.json").read_text(encoding="utf-8"))
            phase_log = json.loads((output_dir / "phase_log.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("benchmark", phase_metrics)
            self.assertIn("checks", phase_metrics)
            self.assertIn("passed", phase_metrics["checks"])
            self.assertEqual(phase_log["run_id"], summary["run_id"])
            self.assertTrue(phase_log["journal_event_id"].endswith(":phase:0"))

    def test_resolved_config_matches_final_policy_phase_not_next_suggestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "run"
            config = ExperimentConfig.load("configs/baseline.json")
            config.agent.algorithm = "q_learning"
            config.training.phases = 2
            config.training.episodes_per_phase = 15
            config.training.evaluation_episodes = 3
            config.training.output_dir = str(output_dir)

            researcher = _IncrementResearcher()
            with patch("auto_rl.orchestrator.build_researcher", return_value=researcher):
                summary = AutoRLOrchestrator(config).train()

            resolved_config = json.loads((output_dir / "resolved_config.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(summary["final_agent_config"]["learning_rate"], 0.15)
            self.assertAlmostEqual(resolved_config["agent"]["learning_rate"], 0.15)
            self.assertAlmostEqual(summary["suggested_next_agent_config"]["learning_rate"], 0.25)

    def test_reusing_output_dir_clears_old_logs_and_phase_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "run"

            config = ExperimentConfig.load("configs/baseline.json")
            config.agent.algorithm = "q_learning"
            config.training.output_dir = str(output_dir)
            config.training.phases = 2
            config.training.episodes_per_phase = 15
            config.training.evaluation_episodes = 3
            AutoRLOrchestrator(config).train()

            config = ExperimentConfig.load("configs/baseline.json")
            config.agent.algorithm = "q_learning"
            config.training.output_dir = str(output_dir)
            config.training.phases = 1
            config.training.episodes_per_phase = 15
            config.training.evaluation_episodes = 3
            AutoRLOrchestrator(config).train()

            phase_log_lines = (output_dir / "phase_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
            journal_lines = (output_dir / "experiment_journal.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(phase_log_lines), 1)
            self.assertGreaterEqual(len(journal_lines), 4)
            self.assertTrue((output_dir / "phase_00_metrics.json").exists())
            self.assertFalse((output_dir / "phase_01_metrics.json").exists())

    def test_runtime_budget_and_session_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "run"
            config = ExperimentConfig.load("configs/baseline.json")
            config.agent.algorithm = "q_learning"
            config.training.output_dir = str(output_dir)
            config.training.max_runtime_seconds = 0

            summary = AutoRLOrchestrator(config).train()

            self.assertIn("Runtime budget exceeded", summary["stop_reason"])
            self.assertTrue((output_dir / "experiment_session.md").exists())
            session_doc = (output_dir / "experiment_session.md").read_text(encoding="utf-8")
            self.assertIn("Resume Hints", session_doc)

    def test_zero_budgets_allow_first_event_then_stop(self) -> None:
        config = ExperimentConfig.load("configs/baseline.json")
        orchestrator = AutoRLOrchestrator(config)
        orchestrator.config.research.max_rollbacks = 0
        orchestrator.config.research.max_failed_checks = 0

        self.assertIsNone(orchestrator._rollback_budget_stop_reason(0))
        self.assertIn("Rollback budget exhausted", orchestrator._rollback_budget_stop_reason(1) or "")
        self.assertIsNone(orchestrator._failed_checks_budget_stop_reason(0))
        self.assertIn(
            "Correctness checks failed",
            orchestrator._failed_checks_budget_stop_reason(1) or "",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path

from auto_rl.schema import SchemaValidationError, load_schema, validate_payload
from auto_rl.training.metrics import EvaluationSummary, PhaseMetrics, TrainingSummary


class PhaseMetricsSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_schema(Path("schemas/phase_metrics.schema.json"))

    def test_valid_phase_metrics_pass_schema_validation(self) -> None:
        payload = PhaseMetrics(
            phase_index=0,
            training=TrainingSummary(
                avg_reward=1.0,
                success_rate=0.5,
                avg_steps=10.0,
                mean_td_error=0.3,
                final_epsilon=0.2,
            ),
            evaluation=EvaluationSummary(
                avg_reward=2.0,
                success_rate=1.0,
                avg_steps=8.0,
            ),
            learning_rate=0.05,
            gamma=0.95,
            epsilon_start=1.0,
            epsilon_decay=0.99,
            episodes_per_phase=20,
            q_table_size=10,
            adjustments=["kept learning rate steady"],
        ).to_dict()

        validate_payload(payload, self.schema)

    def test_missing_required_field_fails_schema_validation(self) -> None:
        payload = {
            "phase_index": 0,
            "training": {
                "avg_reward": 1.0,
                "success_rate": 0.5,
                "avg_steps": 10.0,
                "mean_td_error": 0.3,
                "final_epsilon": 0.2,
            },
            "evaluation": {
                "avg_reward": 2.0,
                "success_rate": 1.0,
                "avg_steps": 8.0,
            },
            "learning_rate": 0.05,
            "gamma": 0.95,
            "epsilon_start": 1.0,
            "epsilon_decay": 0.99,
            "episodes_per_phase": 20,
            "q_table_size": 10,
        }

        with self.assertRaises(SchemaValidationError):
            validate_payload(payload, self.schema)


if __name__ == "__main__":
    unittest.main()

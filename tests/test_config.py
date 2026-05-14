from __future__ import annotations

import unittest

from auto_rl.config import ExperimentConfig


class ConfigLoadTests(unittest.TestCase):
    def test_baseline_config_loads_with_uv_ready_defaults(self) -> None:
        config = ExperimentConfig.load("configs/baseline.json")

        self.assertEqual(config.agent.algorithm, "dqn")
        self.assertEqual(config.agent.learning_rate, 0.05)
        self.assertEqual(config.training.episodes_per_phase, 220)
        self.assertEqual(config.research.mode, "heuristic")


if __name__ == "__main__":
    unittest.main()

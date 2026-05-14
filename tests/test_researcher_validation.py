from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auto_rl.config import AgentConfig, ResearchConfig, TrainingConfig
from auto_rl.researcher.llm import LLMAutoResearcher
from auto_rl.researcher.validation import ResearcherAdjustmentValidator
from auto_rl.schema import SchemaValidationError


class ResearcherValidationTests(unittest.TestCase):
    def test_validator_applies_valid_adjustments(self) -> None:
        validator = ResearcherAdjustmentValidator()
        agent_config = AgentConfig(algorithm="dqn")
        training_config = TrainingConfig()

        decision = validator.apply(
            payload={
                "learning_rate": 0.1,
                "episodes_per_phase": 200,
                "stop_training": True,
                "rationale": ["metric target reached"],
            },
            agent_config=agent_config,
            training_config=training_config,
            source="test",
        )

        self.assertEqual(decision.agent.learning_rate, 0.1)
        self.assertEqual(decision.training.episodes_per_phase, 200)
        self.assertTrue(decision.stop_requested)
        self.assertEqual(decision.source, "test")

    def test_validator_rejects_invalid_cross_field_values(self) -> None:
        validator = ResearcherAdjustmentValidator()

        with self.assertRaises(SchemaValidationError):
            validator.apply(
                payload={"epsilon_start": 0.1, "epsilon_min": 0.5, "rationale": ["bad payload"]},
                agent_config=AgentConfig(algorithm="dqn"),
                training_config=TrainingConfig(),
                source="test",
            )

    def test_llm_researcher_falls_back_on_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            response_path = Path(tmp_dir) / "llm.json"
            response_path.write_text(
                '{"epsilon_start": 0.1, "epsilon_min": 0.5, "rationale": ["bad"]}',
                encoding="utf-8",
            )
            researcher = LLMAutoResearcher(
                ResearchConfig(mode="llm", llm_response_path=str(response_path))
            )
            agent_config = AgentConfig(algorithm="dqn")
            training_config = TrainingConfig()

            decision = researcher.analyze([], agent_config, training_config)

            self.assertTrue(decision.fallback_used)
            self.assertEqual(decision.agent.learning_rate, agent_config.learning_rate)
            self.assertEqual(decision.training.episodes_per_phase, training_config.episodes_per_phase)


if __name__ == "__main__":
    unittest.main()

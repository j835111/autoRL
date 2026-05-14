from __future__ import annotations

from pathlib import Path

from auto_rl.config import AgentConfig, ResearchConfig, TrainingConfig
from auto_rl.researcher.base import AutoResearcher, ResearchDecision
from auto_rl.researcher.llm_bridge import build_tuning_prompt, parse_llm_adjustments
from auto_rl.researcher.validation import ResearcherAdjustmentValidator
from auto_rl.training.metrics import PhaseMetrics


class LLMAutoResearcher(AutoResearcher):
    def __init__(
        self,
        config: ResearchConfig,
        validator: ResearcherAdjustmentValidator | None = None,
    ) -> None:
        self.config = config
        self.validator = validator or ResearcherAdjustmentValidator()

    def analyze(
        self,
        history: list[PhaseMetrics],
        agent_config: AgentConfig,
        training_config: TrainingConfig,
    ) -> ResearchDecision:
        del history
        response_path = self.config.llm_response_path
        if not response_path:
            return self.validator.fallback(
                agent_config=agent_config,
                training_config=training_config,
                source="llm",
                reason="LLM mode is enabled but no llm_response_path is configured.",
            )

        try:
            raw_text = Path(response_path).read_text(encoding="utf-8")
        except OSError as exc:
            return self.validator.fallback(
                agent_config=agent_config,
                training_config=training_config,
                source="llm",
                reason=f"Failed to read LLM response from '{response_path}': {exc}",
            )

        try:
            payload = parse_llm_adjustments(raw_text)
        except Exception as exc:
            return self.validator.fallback(
                agent_config=agent_config,
                training_config=training_config,
                source="llm",
                reason=f"Failed to parse LLM adjustment payload: {exc}",
            )

        if "rationale" not in payload:
            payload["rationale"] = ["Applied validated LLM tuning payload."]

        try:
            return self.validator.apply(
                payload=payload,
                agent_config=agent_config,
                training_config=training_config,
                source="llm",
            )
        except Exception as exc:
            return self.validator.fallback(
                agent_config=agent_config,
                training_config=training_config,
                source="llm",
                reason=f"LLM payload failed validation: {exc}",
            )

    def build_prompt(
        self,
        history: list[PhaseMetrics],
        agent_config: AgentConfig,
        training_config: TrainingConfig,
    ) -> str:
        return build_tuning_prompt(history, agent_config, training_config)

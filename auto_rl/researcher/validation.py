from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from auto_rl.config import AgentConfig, TrainingConfig
from auto_rl.researcher.base import ResearchDecision
from auto_rl.schema import SchemaValidationError, load_schema, validate_payload

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "researcher_adjustments.schema.json"

_AGENT_FIELDS = {
    "learning_rate",
    "gamma",
    "epsilon_start",
    "epsilon_min",
    "epsilon_decay",
}
_TRAINING_FIELDS = {"episodes_per_phase"}
_CONTROL_FIELDS = {"rationale", "stop_training", "rollback_to_best"}


class ResearcherAdjustmentValidator:
    def __init__(self, schema_path: str | Path = _SCHEMA_PATH) -> None:
        self.schema = load_schema(schema_path)

    def validate(self, payload: dict[str, Any], agent_config: AgentConfig, training_config: TrainingConfig) -> None:
        validate_payload(payload, self.schema)
        epsilon_start = float(payload.get("epsilon_start", agent_config.epsilon_start))
        epsilon_min = float(payload.get("epsilon_min", agent_config.epsilon_min))
        if epsilon_min > epsilon_start:
            raise SchemaValidationError(["$.epsilon_min: must be <= epsilon_start"])

        learning_rate = float(payload.get("learning_rate", agent_config.learning_rate))
        if learning_rate <= 0.0:
            raise SchemaValidationError(["$.learning_rate: must stay > 0"])

        episodes_per_phase = int(payload.get("episodes_per_phase", training_config.episodes_per_phase))
        if episodes_per_phase < 1:
            raise SchemaValidationError(["$.episodes_per_phase: must stay >= 1"])

    def apply(
        self,
        payload: dict[str, Any],
        agent_config: AgentConfig,
        training_config: TrainingConfig,
        source: str,
    ) -> ResearchDecision:
        self.validate(payload, agent_config, training_config)

        next_agent = replace(agent_config)
        next_training = replace(training_config)

        for key in _AGENT_FIELDS:
            if key in payload:
                setattr(next_agent, key, payload[key])
        for key in _TRAINING_FIELDS:
            if key in payload:
                setattr(next_training, key, payload[key])

        reasons = list(payload.get("rationale", []))
        if not reasons:
            reasons = ["Validated researcher payload applied."]

        adjustments = {
            key: value
            for key, value in payload.items()
            if key not in _CONTROL_FIELDS
        }
        return ResearchDecision(
            agent=next_agent,
            training=next_training,
            reasons=reasons,
            source=source,
            adjustments=adjustments,
            stop_requested=bool(payload.get("stop_training", False)),
            rollback_requested=bool(payload.get("rollback_to_best", False)),
        )

    def fallback(
        self,
        agent_config: AgentConfig,
        training_config: TrainingConfig,
        source: str,
        reason: str,
    ) -> ResearchDecision:
        return ResearchDecision(
            agent=replace(agent_config),
            training=replace(training_config),
            reasons=[reason, "Fallback to the current validated configuration."],
            source=source,
            fallback_used=True,
        )

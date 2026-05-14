from __future__ import annotations

import json
from typing import Any

from auto_rl.config import AgentConfig, TrainingConfig
from auto_rl.training.metrics import PhaseMetrics


def build_tuning_prompt(
    history: list[PhaseMetrics],
    agent_config: AgentConfig,
    training_config: TrainingConfig,
) -> str:
    recent_history = [item.to_dict() for item in history[-3:]]
    return (
        "You are an RL auto-researcher. Review the recent phase reports and respond with JSON only. "
        "Do not wrap the JSON in markdown or prose. Keep the agent independently deployable. "
        "Return keys only when you want to change them. Allowed keys: "
        "learning_rate, gamma, epsilon_start, epsilon_min, epsilon_decay, episodes_per_phase, "
        "stop_training, rollback_to_best, rationale.\n\n"
        f"Current agent config:\n{json.dumps(agent_config.to_dict(), indent=2)}\n\n"
        f"Current training config:\n{json.dumps(training_config.to_dict(), indent=2)}\n\n"
        f"Recent phase reports:\n{json.dumps(recent_history, indent=2)}\n"
    )


def parse_llm_adjustments(raw_text: str) -> dict[str, Any]:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response does not contain a JSON object.")
    return json.loads(raw_text[start : end + 1])

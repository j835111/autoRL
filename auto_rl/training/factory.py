from __future__ import annotations

import json
from pathlib import Path

from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.training.base import InnerAgent
from auto_rl.training.dqn import DQNAgent
from auto_rl.training.q_learning import QLearningAgent


def build_agent(action_size: int, config: AgentConfig, seed: int = 0) -> InnerAgent:
    algorithm = config.algorithm.lower()
    if algorithm in {"q_learning", "tabular_q_learning"}:
        return QLearningAgent(action_size=action_size, config=config, seed=seed)
    if algorithm == "dqn":
        return DQNAgent(action_size=action_size, config=config, seed=seed)
    raise ValueError(f"Unsupported agent algorithm: {config.algorithm}")


def load_agent(path: str | Path, seed: int = 0) -> tuple[InnerAgent, EnvConfig, list[str]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    algorithm = str(payload.get("algorithm", "")).lower()
    if algorithm in {"tabular_q_learning", "q_learning"}:
        return QLearningAgent.from_payload(payload, seed=seed)
    if algorithm == "dqn":
        return DQNAgent.from_payload(payload, seed=seed)
    raise ValueError(f"Unsupported saved agent algorithm: {payload.get('algorithm')}")

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _as_tuple_pair(value: list[int] | tuple[int, int]) -> tuple[int, int]:
    return (int(value[0]), int(value[1]))


def _as_tuple_pairs(values: list[list[int]] | list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [_as_tuple_pair(item) for item in values]


@dataclass
class EnvConfig:
    width: int = 6
    height: int = 6
    start: tuple[int, int] = (0, 0)
    goal: tuple[int, int] = (5, 5)
    traps: list[tuple[int, int]] = field(default_factory=lambda: [(1, 2), (3, 4), (4, 1)])
    walls: list[tuple[int, int]] = field(default_factory=lambda: [(2, 1), (2, 2), (2, 3)])
    max_steps: int = 45
    step_penalty: float = -0.1
    goal_reward: float = 10.0
    trap_penalty: float = -5.0
    distance_reward_scale: float = 0.15

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnvConfig":
        payload = dict(data)
        payload["start"] = _as_tuple_pair(payload.get("start", (0, 0)))
        payload["goal"] = _as_tuple_pair(payload.get("goal", (5, 5)))
        payload["traps"] = _as_tuple_pairs(payload.get("traps", []))
        payload["walls"] = _as_tuple_pairs(payload.get("walls", []))
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["start"] = list(self.start)
        data["goal"] = list(self.goal)
        data["traps"] = [list(item) for item in self.traps]
        data["walls"] = [list(item) for item in self.walls]
        return data


@dataclass
class AgentConfig:
    algorithm: str = "dqn"
    learning_rate: float = 0.22
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_min: float = 0.05
    epsilon_decay: float = 0.985
    hidden_size: int = 32
    replay_capacity: int = 512
    batch_size: int = 16
    min_replay_size: int = 32
    target_sync_interval: int = 25

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingConfig:
    phases: int = 8
    episodes_per_phase: int = 180
    evaluation_episodes: int = 40
    seed: int = 7
    output_dir: str = "outputs/demo_run"
    objective: str = "Optimize evaluation reward and success rate while preserving correctness."
    max_runtime_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingConfig":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchConfig:
    enabled: bool = True
    mode: str = "heuristic"
    reward_improvement_threshold: float = 0.2
    success_improvement_threshold: float = 0.03
    plateau_patience: int = 2
    lr_decay_factor: float = 0.75
    lr_growth_factor: float = 1.05
    epsilon_boost: float = 0.15
    epsilon_min_floor: float = 0.03
    epsilon_decay_tighten: float = 0.985
    epsilon_decay_relax: float = 1.01
    gamma_step: float = 0.01
    max_learning_rate: float = 0.5
    min_learning_rate: float = 0.02
    max_epsilon_start: float = 1.0
    min_epsilon_decay: float = 0.9
    max_epsilon_decay: float = 0.999
    max_episodes_per_phase: int = 320
    rollback_patience: int = 2
    rollback_success_tolerance: float = 0.15
    rollback_reward_tolerance: float = 1.2
    stop_success_threshold: float = 0.95
    stop_reward_threshold: float = 8.0
    stop_patience: int = 2
    min_confidence_score: float = 1.0
    max_rollbacks: int = 3
    max_failed_checks: int = 2
    llm_response_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchConfig":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentConfig:
    env: EnvConfig = field(default_factory=EnvConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentConfig":
        return cls(
            env=EnvConfig.from_dict(data.get("env", {})),
            agent=AgentConfig.from_dict(data.get("agent", {})),
            training=TrainingConfig.from_dict(data.get("training", {})),
            research=ResearchConfig.from_dict(data.get("research", {})),
        )

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def save(self, path: str | Path) -> None:
        output = {
            "env": self.env.to_dict(),
            "agent": self.agent.to_dict(),
            "training": self.training.to_dict(),
            "research": self.research.to_dict(),
        }
        Path(path).write_text(json.dumps(output, indent=2), encoding="utf-8")

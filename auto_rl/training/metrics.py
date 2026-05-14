from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any


@dataclass
class EpisodeSummary:
    reward: float
    steps: int
    success: bool
    hit_trap: bool
    td_error: float


@dataclass
class TrainingSummary:
    avg_reward: float
    success_rate: float
    avg_steps: float
    mean_td_error: float
    final_epsilon: float

    @classmethod
    def from_episodes(cls, episodes: list[EpisodeSummary], final_epsilon: float) -> "TrainingSummary":
        return cls(
            avg_reward=mean([item.reward for item in episodes]) if episodes else 0.0,
            success_rate=mean([1.0 if item.success else 0.0 for item in episodes]) if episodes else 0.0,
            avg_steps=mean([item.steps for item in episodes]) if episodes else 0.0,
            mean_td_error=mean([item.td_error for item in episodes]) if episodes else 0.0,
            final_epsilon=final_epsilon,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationSummary:
    avg_reward: float
    success_rate: float
    avg_steps: float

    @classmethod
    def from_episodes(cls, episodes: list[EpisodeSummary]) -> "EvaluationSummary":
        return cls(
            avg_reward=mean([item.reward for item in episodes]) if episodes else 0.0,
            success_rate=mean([1.0 if item.success else 0.0 for item in episodes]) if episodes else 0.0,
            avg_steps=mean([item.steps for item in episodes]) if episodes else 0.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkSummary:
    reward_delta_vs_previous: float = 0.0
    success_delta_vs_previous: float = 0.0
    reward_delta_vs_best: float = 0.0
    success_delta_vs_best: float = 0.0
    noise_floor: float = 0.0
    confidence_score: float = 0.0
    passes_confidence_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckSummary:
    passed: bool = True
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PhaseMetrics:
    phase_index: int
    training: TrainingSummary
    evaluation: EvaluationSummary
    learning_rate: float
    gamma: float
    epsilon_start: float
    epsilon_decay: float
    episodes_per_phase: int
    q_table_size: int
    benchmark: BenchmarkSummary = field(default_factory=BenchmarkSummary)
    checks: CheckSummary = field(default_factory=CheckSummary)
    adjustments: list[str] = field(default_factory=list)
    journal_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["training"] = self.training.to_dict()
        payload["evaluation"] = self.evaluation.to_dict()
        payload["benchmark"] = self.benchmark.to_dict()
        payload["checks"] = self.checks.to_dict()
        if payload["journal_event_id"] is None:
            payload.pop("journal_event_id")
        return payload

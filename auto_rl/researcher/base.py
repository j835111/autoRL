from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from auto_rl.config import AgentConfig, TrainingConfig
from auto_rl.training.metrics import PhaseMetrics


@dataclass
class ResearchDecision:
    agent: AgentConfig
    training: TrainingConfig
    reasons: list[str] = field(default_factory=list)
    source: str = "heuristic"
    adjustments: dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False
    stop_requested: bool = False
    rollback_requested: bool = False


class AutoResearcher(ABC):
    @abstractmethod
    def analyze(
        self,
        history: list[PhaseMetrics],
        agent_config: AgentConfig,
        training_config: TrainingConfig,
    ) -> ResearchDecision:
        raise NotImplementedError

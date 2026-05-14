from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

Observation = Any


@dataclass(frozen=True)
class StepResult:
    state: Observation
    reward: float
    done: bool
    success: bool
    hit_trap: bool


class Environment(ABC):
    ACTIONS: tuple[str, ...]

    @property
    def action_size(self) -> int:
        return len(self.ACTIONS)

    @property
    def action_labels(self) -> list[str]:
        return list(self.ACTIONS)

    @abstractmethod
    def reset(self) -> Observation:
        raise NotImplementedError

    @abstractmethod
    def step(self, action: int) -> StepResult:
        raise NotImplementedError

    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.envs.base import Observation


class InnerAgent(ABC):
    algorithm: str

    def __init__(self, action_size: int, config: AgentConfig, seed: int = 0) -> None:
        self.action_size = action_size
        self.config = config
        self.seed = seed

    @abstractmethod
    def set_hyperparameters(self, config: AgentConfig, reset_epsilon: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def select_action(self, state: Observation, explore: bool = True) -> int:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        state: Observation,
        action: int,
        reward: float,
        next_state: Observation,
        done: bool,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def end_episode(self) -> None:
        raise NotImplementedError

    def greedy_action(self, state: Observation) -> int:
        return self.select_action(state, explore=False)

    @property
    @abstractmethod
    def epsilon(self) -> float:
        raise NotImplementedError

    @epsilon.setter
    @abstractmethod
    def epsilon(self, value: float) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def policy_size(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def state_registry_size(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str | Path, env_config: EnvConfig, action_labels: list[str]) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        seed: int = 0,
    ) -> tuple["InnerAgent", EnvConfig, list[str]]:
        raise NotImplementedError

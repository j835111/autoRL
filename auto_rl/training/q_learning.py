from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random
from typing import Any

from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.envs.base import Observation
from auto_rl.training.base import InnerAgent


@dataclass
class PolicySnapshot:
    algorithm: str
    action_labels: list[str]
    env_config: dict[str, Any]
    agent_config: dict[str, Any]
    agent_state: dict[str, Any]


class QLearningAgent(InnerAgent):
    algorithm = "tabular_q_learning"

    def __init__(self, action_size: int, config: AgentConfig, seed: int = 0) -> None:
        super().__init__(action_size=action_size, config=config, seed=seed)
        self.random = Random(seed)
        self.q_table: dict[str, list[float]] = {}
        self.set_hyperparameters(config, reset_epsilon=True)

    def set_hyperparameters(self, config: AgentConfig, reset_epsilon: bool = False) -> None:
        self.config = config
        self.learning_rate = config.learning_rate
        self.gamma = config.gamma
        self.epsilon_min = config.epsilon_min
        self.epsilon_decay = config.epsilon_decay
        if reset_epsilon or not hasattr(self, "epsilon"):
            self._epsilon = config.epsilon_start

    @property
    def epsilon(self) -> float:
        return self._epsilon

    @epsilon.setter
    def epsilon(self, value: float) -> None:
        self._epsilon = float(value)

    @property
    def policy_size(self) -> int:
        return sum(len(values) for values in self.q_table.values())

    @property
    def state_registry_size(self) -> int:
        return len(self.q_table)

    def ensure_state(self, state: Observation) -> str:
        state_key = str(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0 for _ in range(self.action_size)]
        return state_key

    def select_action(self, state: Observation, explore: bool = True) -> int:
        state_key = self.ensure_state(state)
        if explore and self.random.random() < self.epsilon:
            return self.random.randrange(self.action_size)

        values = self.q_table[state_key]
        best_value = max(values)
        best_actions = [index for index, value in enumerate(values) if value == best_value]
        return self.random.choice(best_actions)

    def update(self, state: Observation, action: int, reward: float, next_state: Observation, done: bool) -> float:
        state_key = self.ensure_state(state)
        next_state_key = self.ensure_state(next_state)

        target = reward
        if not done:
            target += self.gamma * max(self.q_table[next_state_key])

        current = self.q_table[state_key][action]
        td_error = target - current
        self.q_table[state_key][action] = current + self.learning_rate * td_error
        return abs(td_error)

    def end_episode(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: str | Path, env_config: EnvConfig, action_labels: list[str]) -> None:
        snapshot = PolicySnapshot(
            algorithm=self.algorithm,
            action_labels=action_labels,
            env_config=env_config.to_dict(),
            agent_config=asdict(self.config),
            agent_state={"q_table": self.q_table},
        )
        Path(path).write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        seed: int = 0,
    ) -> tuple["QLearningAgent", EnvConfig, list[str]]:
        env_config = EnvConfig.from_dict(payload["env_config"])
        agent_config = AgentConfig.from_dict(payload["agent_config"])
        action_labels = list(payload["action_labels"])
        agent = cls(action_size=len(action_labels), config=agent_config, seed=seed)
        raw_q_table = payload.get("agent_state", {}).get("q_table", payload.get("q_table", {}))
        agent.q_table = {
            str(state): [float(value) for value in values]
            for state, values in raw_q_table.items()
        }
        agent.epsilon = 0.0
        return agent, env_config, action_labels

    @classmethod
    def load(cls, path: str | Path, seed: int = 0) -> tuple["QLearningAgent", EnvConfig, list[str]]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_payload(payload, seed=seed)

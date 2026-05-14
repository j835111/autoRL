from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random
from typing import Any

from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.envs.base import Observation
from auto_rl.training.base import InnerAgent


@dataclass
class DQNPolicySnapshot:
    algorithm: str
    action_labels: list[str]
    env_config: dict[str, Any]
    agent_config: dict[str, Any]
    agent_state: dict[str, Any]


@dataclass(frozen=True)
class Transition:
    state: Observation
    action: int
    reward: float
    next_state: Observation
    done: bool


class DQNAgent(InnerAgent):
    algorithm = "dqn"

    def __init__(self, action_size: int, config: AgentConfig, seed: int = 0) -> None:
        super().__init__(action_size=action_size, config=config, seed=seed)
        self.random = Random(seed)
        self.replay_buffer: deque[Transition] = deque(maxlen=config.replay_capacity)
        self._seen_states: set[str] = set()
        self.input_size: int | None = None
        self.hidden_size = config.hidden_size
        self.optimizer_steps = 0
        self.online_network: dict[str, list[Any]] | None = None
        self.target_network: dict[str, list[Any]] | None = None
        self.set_hyperparameters(config, reset_epsilon=True)

    def set_hyperparameters(self, config: AgentConfig, reset_epsilon: bool = False) -> None:
        self.config = config
        self.hidden_size = config.hidden_size
        self.learning_rate = config.learning_rate
        self.gamma = config.gamma
        self.epsilon_min = config.epsilon_min
        self.epsilon_decay = config.epsilon_decay
        self.batch_size = config.batch_size
        self.min_replay_size = config.min_replay_size
        self.target_sync_interval = max(1, config.target_sync_interval)
        replay_items = list(self.replay_buffer) if hasattr(self, "replay_buffer") else []
        self.replay_buffer = deque(replay_items, maxlen=config.replay_capacity)
        if reset_epsilon or not hasattr(self, "_epsilon"):
            self._epsilon = config.epsilon_start

    @property
    def epsilon(self) -> float:
        return self._epsilon

    @epsilon.setter
    def epsilon(self, value: float) -> None:
        self._epsilon = float(value)

    @property
    def policy_size(self) -> int:
        if not self.online_network:
            return 0
        return (
            len(self.online_network["w1"]) * len(self.online_network["w1"][0])
            + len(self.online_network["b1"])
            + len(self.online_network["w2"]) * len(self.online_network["w2"][0])
            + len(self.online_network["b2"])
        )

    @property
    def state_registry_size(self) -> int:
        return len(self._seen_states)

    def select_action(self, state: Observation, explore: bool = True) -> int:
        features = self._encode_state(state)
        if explore and self.random.random() < self.epsilon:
            return self.random.randrange(self.action_size)
        q_values = self._forward(self.online_network, features)[2]
        best_value = max(q_values)
        best_actions = [index for index, value in enumerate(q_values) if value == best_value]
        return self.random.choice(best_actions)

    def update(self, state: Observation, action: int, reward: float, next_state: Observation, done: bool) -> float:
        self._encode_state(state)
        self._encode_state(next_state)
        self.replay_buffer.append(
            Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
            )
        )

        if len(self.replay_buffer) < self.min_replay_size:
            return 0.0

        batch_size = min(self.batch_size, len(self.replay_buffer))
        batch = self.random.sample(list(self.replay_buffer), batch_size)
        step_size = self.learning_rate / batch_size
        total_error = 0.0

        for transition in batch:
            state_features = self._encode_state(transition.state)
            next_features = self._encode_state(transition.next_state)
            hidden_linear, hidden_activation, q_values = self._forward(self.online_network, state_features)
            next_q_values = self._forward(self.target_network, next_features)[2]
            target_value = transition.reward
            if not transition.done:
                target_value += self.gamma * max(next_q_values)

            current_value = q_values[transition.action]
            td_error = target_value - current_value
            total_error += abs(td_error)
            self._apply_gradient(
                features=state_features,
                hidden_linear=hidden_linear,
                hidden_activation=hidden_activation,
                action=transition.action,
                td_error=td_error,
                step_size=step_size,
            )

        self.optimizer_steps += 1
        if self.optimizer_steps % self.target_sync_interval == 0:
            self.target_network = self._clone_network(self.online_network)

        return total_error / batch_size

    def end_episode(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: str | Path, env_config: EnvConfig, action_labels: list[str]) -> None:
        if self.online_network is None:
            raise ValueError("DQN model has not been initialized yet.")
        snapshot = DQNPolicySnapshot(
            algorithm=self.algorithm,
            action_labels=action_labels,
            env_config=env_config.to_dict(),
            agent_config=asdict(self.config),
            agent_state={
                "input_size": self.input_size,
                "online_network": self.online_network,
                "target_network": self.target_network,
                "optimizer_steps": self.optimizer_steps,
                "state_registry_size": len(self._seen_states),
                "seen_states": sorted(self._seen_states),
                "epsilon": self.epsilon,
                "replay_buffer": [asdict(item) for item in self.replay_buffer],
            },
        )
        Path(path).write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        seed: int = 0,
    ) -> tuple["DQNAgent", EnvConfig, list[str]]:
        env_config = EnvConfig.from_dict(payload["env_config"])
        agent_config = AgentConfig.from_dict(payload["agent_config"])
        action_labels = list(payload["action_labels"])
        agent = cls(action_size=len(action_labels), config=agent_config, seed=seed)
        agent_state = payload["agent_state"]
        agent.input_size = int(agent_state["input_size"])
        agent.online_network = cls._deserialize_network(agent_state["online_network"])
        target_network = agent_state.get("target_network") or agent_state["online_network"]
        agent.target_network = cls._deserialize_network(target_network)
        agent.optimizer_steps = int(agent_state.get("optimizer_steps", 0))
        seen_states = agent_state.get("seen_states")
        if seen_states is not None:
            agent._seen_states = {str(item) for item in seen_states}
        else:
            seen_count = int(agent_state.get("state_registry_size", 0))
            agent._seen_states = {f"loaded:{index}" for index in range(seen_count)}
        replay_items = [
            Transition(
                state=item["state"],
                action=int(item["action"]),
                reward=float(item["reward"]),
                next_state=item["next_state"],
                done=bool(item["done"]),
            )
            for item in agent_state.get("replay_buffer", [])
        ]
        agent.replay_buffer = deque(replay_items, maxlen=agent_config.replay_capacity)
        agent.epsilon = float(agent_state.get("epsilon", 0.0))
        return agent, env_config, action_labels

    def _encode_state(self, state: Observation) -> list[float]:
        features = _flatten_state(state)
        if not features:
            raise ValueError("State encoder produced an empty feature vector.")
        if self.input_size is None:
            self.input_size = len(features)
            self.online_network = self._initialize_network(self.input_size, self.hidden_size, self.action_size)
            self.target_network = self._clone_network(self.online_network)
        if len(features) != self.input_size:
            raise ValueError(
                f"DQN expected state vectors of size {self.input_size}, got {len(features)}."
            )
        self._seen_states.add(_state_signature(state))
        return features

    def _apply_gradient(
        self,
        features: list[float],
        hidden_linear: list[float],
        hidden_activation: list[float],
        action: int,
        td_error: float,
        step_size: float,
    ) -> None:
        network = self.online_network
        if network is None:
            raise ValueError("Online network is not initialized.")

        output_gradient = -td_error
        output_weights_before = list(network["w2"][action])

        for index, value in enumerate(hidden_activation):
            gradient = output_gradient * value
            network["w2"][action][index] -= step_size * gradient
        network["b2"][action] -= step_size * output_gradient

        for hidden_index, pre_activation in enumerate(hidden_linear):
            if pre_activation <= 0.0:
                continue
            hidden_gradient = output_gradient * output_weights_before[hidden_index]
            for feature_index, feature_value in enumerate(features):
                gradient = hidden_gradient * feature_value
                network["w1"][hidden_index][feature_index] -= step_size * gradient
            network["b1"][hidden_index] -= step_size * hidden_gradient

    def _forward(
        self,
        network: dict[str, list[Any]] | None,
        features: list[float],
    ) -> tuple[list[float], list[float], list[float]]:
        if network is None:
            raise ValueError("Network is not initialized.")

        hidden_linear = [
            sum(weight * feature for weight, feature in zip(row, features)) + bias
            for row, bias in zip(network["w1"], network["b1"])
        ]
        hidden_activation = [max(0.0, value) for value in hidden_linear]
        q_values = [
            sum(weight * hidden for weight, hidden in zip(row, hidden_activation)) + bias
            for row, bias in zip(network["w2"], network["b2"])
        ]
        return hidden_linear, hidden_activation, q_values

    def _initialize_network(self, input_size: int, hidden_size: int, output_size: int) -> dict[str, list[Any]]:
        first_scale = math.sqrt(2.0 / max(1, input_size))
        second_scale = math.sqrt(2.0 / max(1, hidden_size))
        return {
            "w1": [
                [self.random.uniform(-first_scale, first_scale) for _ in range(input_size)]
                for _ in range(hidden_size)
            ],
            "b1": [0.0 for _ in range(hidden_size)],
            "w2": [
                [self.random.uniform(-second_scale, second_scale) for _ in range(hidden_size)]
                for _ in range(output_size)
            ],
            "b2": [0.0 for _ in range(output_size)],
        }

    def _clone_network(self, network: dict[str, list[Any]] | None) -> dict[str, list[Any]]:
        if network is None:
            raise ValueError("Cannot clone an uninitialized network.")
        return self._deserialize_network(network)

    @staticmethod
    def _deserialize_network(network: dict[str, list[Any]]) -> dict[str, list[Any]]:
        return {
            "w1": [[float(value) for value in row] for row in network["w1"]],
            "b1": [float(value) for value in network["b1"]],
            "w2": [[float(value) for value in row] for row in network["w2"]],
            "b2": [float(value) for value in network["b2"]],
        }


def _flatten_state(state: Observation) -> list[float]:
    if isinstance(state, bool):
        return [1.0 if state else 0.0]
    if isinstance(state, (int, float)):
        return [float(state)]
    if isinstance(state, str):
        parts = [part.strip() for part in state.split(",")]
        try:
            return [float(part) for part in parts if part]
        except ValueError:
            if not state:
                return [0.0]
            return [float(ord(char)) / 255.0 for char in state]
    if isinstance(state, (list, tuple)):
        values: list[float] = []
        for item in state:
            values.extend(_flatten_state(item))
        return values
    if isinstance(state, dict):
        values: list[float] = []
        for key in sorted(state):
            values.extend(_flatten_state(state[key]))
        return values
    raise TypeError(f"Unsupported state type for DQN encoder: {type(state)!r}")


def _state_signature(state: Observation) -> str:
    if isinstance(state, dict):
        return json.dumps(state, sort_keys=True, ensure_ascii=True)
    if isinstance(state, (list, tuple)):
        return json.dumps(state, ensure_ascii=True)
    return str(state)

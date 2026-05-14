from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from auto_rl.envs.base import Environment, Observation, StepResult


@dataclass(frozen=True)
class AdapterStep:
    observation: Observation
    reward: float = 0.0
    done: bool = False
    success: bool = False
    failed: bool = False
    info: dict[str, Any] | None = None


class RealGameAdapter(Protocol):
    action_labels: Sequence[str]

    def reset(self) -> Observation:
        ...

    def step(self, action_label: str) -> AdapterStep:
        ...

    def render(self) -> str:
        ...


class RealGameEnvWrapper(Environment):
    def __init__(
        self,
        adapter: RealGameAdapter,
        reward_fn: Callable[[AdapterStep], float] | None = None,
        success_fn: Callable[[AdapterStep], bool] | None = None,
        failure_fn: Callable[[AdapterStep], bool] | None = None,
        observation_fn: Callable[[Observation], Observation] | None = None,
    ) -> None:
        self.adapter = adapter
        self.ACTIONS = tuple(adapter.action_labels)
        self._reward_fn = reward_fn or (lambda step: step.reward)
        self._success_fn = success_fn or (lambda step: step.success)
        self._failure_fn = failure_fn or (lambda step: step.failed)
        self._observation_fn = observation_fn or (lambda observation: observation)

    def reset(self) -> Observation:
        return self._observation_fn(self.adapter.reset())

    def step(self, action: int) -> StepResult:
        action_label = self.ACTIONS[action]
        adapter_step = self.adapter.step(action_label)
        success = self._success_fn(adapter_step)
        failed = self._failure_fn(adapter_step)
        return StepResult(
            state=self._observation_fn(adapter_step.observation),
            reward=self._reward_fn(adapter_step),
            done=adapter_step.done or success or failed,
            success=success,
            hit_trap=failed,
        )

    def render(self) -> str:
        return self.adapter.render()

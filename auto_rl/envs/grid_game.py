from __future__ import annotations

from auto_rl.config import EnvConfig
from auto_rl.envs.base import Environment, StepResult


class GridGameEnv(Environment):
    ACTIONS = ("up", "down", "left", "right")

    def __init__(self, config: EnvConfig, seed: int = 0) -> None:
        del seed
        self.config = config
        self.position = config.start
        self.steps_taken = 0
        self._traps = set(config.traps)
        self._walls = set(config.walls)

    def reset(self) -> str:
        self.position = self.config.start
        self.steps_taken = 0
        return self._state_key(self.position)

    def step(self, action: int) -> StepResult:
        self.steps_taken += 1
        before_distance = self._distance_to_goal(self.position)
        self.position = self._move(self.position, action)
        after_distance = self._distance_to_goal(self.position)

        reward = self.config.step_penalty
        reward += (before_distance - after_distance) * self.config.distance_reward_scale

        success = self.position == self.config.goal
        hit_trap = self.position in self._traps
        done = success or hit_trap or self.steps_taken >= self.config.max_steps

        if success:
            reward += self.config.goal_reward
        elif hit_trap:
            reward += self.config.trap_penalty

        return StepResult(
            state=self._state_key(self.position),
            reward=reward,
            done=done,
            success=success,
            hit_trap=hit_trap,
        )

    def render(self) -> str:
        rows: list[str] = []
        for y in range(self.config.height):
            cells: list[str] = []
            for x in range(self.config.width):
                pos = (x, y)
                if pos == self.position:
                    cells.append("A")
                elif pos == self.config.goal:
                    cells.append("G")
                elif pos in self._walls:
                    cells.append("#")
                elif pos in self._traps:
                    cells.append("X")
                else:
                    cells.append(".")
            rows.append(" ".join(cells))
        return "\n".join(rows)

    def _move(self, position: tuple[int, int], action: int) -> tuple[int, int]:
        x, y = position
        if action == 0:
            candidate = (x, y - 1)
        elif action == 1:
            candidate = (x, y + 1)
        elif action == 2:
            candidate = (x - 1, y)
        elif action == 3:
            candidate = (x + 1, y)
        else:
            raise ValueError(f"Unsupported action: {action}")

        if not self._within_bounds(candidate) or candidate in self._walls:
            return position
        return candidate

    def _within_bounds(self, position: tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.config.width and 0 <= y < self.config.height

    def _distance_to_goal(self, position: tuple[int, int]) -> int:
        return abs(position[0] - self.config.goal[0]) + abs(position[1] - self.config.goal[1])

    def _state_key(self, position: tuple[int, int]) -> str:
        return f"{position[0]},{position[1]}"

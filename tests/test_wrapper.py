from __future__ import annotations

import unittest

from auto_rl.envs import AdapterStep, RealGameEnvWrapper


class _FakeAdapter:
    action_labels = ("tap_left", "tap_right")

    def reset(self) -> dict[str, int]:
        return {"screen": 0}

    def step(self, action_label: str) -> AdapterStep:
        if action_label == "tap_right":
            return AdapterStep(observation={"screen": 1}, reward=2.0, done=True, success=True)
        return AdapterStep(observation={"screen": -1}, reward=-1.0, done=True, failed=True)

    def render(self) -> str:
        return "fake-screen"


class RealGameWrapperTests(unittest.TestCase):
    def test_wrapper_maps_adapter_actions_and_outcomes(self) -> None:
        env = RealGameEnvWrapper(adapter=_FakeAdapter())

        self.assertEqual(env.reset(), {"screen": 0})
        success_step = env.step(1)
        failure_step = env.step(0)

        self.assertEqual(env.action_size, 2)
        self.assertEqual(success_step.reward, 2.0)
        self.assertTrue(success_step.success)
        self.assertFalse(success_step.hit_trap)
        self.assertTrue(failure_step.hit_trap)
        self.assertEqual(env.render(), "fake-screen")


if __name__ == "__main__":
    unittest.main()

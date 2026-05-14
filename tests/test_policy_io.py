from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.training import DQNAgent, QLearningAgent, load_agent


class PolicyIOTests(unittest.TestCase):
    def test_q_learning_policy_round_trip(self) -> None:
        config = AgentConfig(algorithm="q_learning")
        agent = QLearningAgent(action_size=4, config=config, seed=3)
        agent.update("0,0", 3, 1.0, "1,0", False)
        agent.update("1,0", 1, 10.0, "1,1", True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "q_policy.json"
            agent.save(path, env_config=EnvConfig(), action_labels=["up", "down", "left", "right"])
            loaded_agent, loaded_env, action_labels = load_agent(path, seed=3)

            self.assertIsInstance(loaded_agent, QLearningAgent)
            self.assertEqual(action_labels, ["up", "down", "left", "right"])
            self.assertEqual(loaded_env.goal, EnvConfig().goal)
            self.assertEqual(loaded_agent.q_table, agent.q_table)

    def test_dqn_policy_round_trip(self) -> None:
        config = AgentConfig(
            algorithm="dqn",
            learning_rate=0.05,
            hidden_size=16,
            replay_capacity=64,
            batch_size=8,
            min_replay_size=8,
            target_sync_interval=4,
        )
        agent = DQNAgent(action_size=4, config=config, seed=4)

        for index in range(20):
            state = f"{index % 6},{(index // 6) % 6}"
            next_state = f"{(index + 1) % 6},{((index + 1) // 6) % 6}"
            agent.select_action(state)
            agent.update(
                state=state,
                action=index % 4,
                reward=10.0 if index % 5 == 0 else -0.1,
                next_state=next_state,
                done=index % 7 == 0,
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "dqn_policy.json"
            agent.save(path, env_config=EnvConfig(), action_labels=["up", "down", "left", "right"])
            loaded_agent, loaded_env, action_labels = load_agent(path, seed=4)

            self.assertIsInstance(loaded_agent, DQNAgent)
            self.assertEqual(action_labels, ["up", "down", "left", "right"])
            self.assertEqual(loaded_env.start, EnvConfig().start)
            self.assertGreater(loaded_agent.policy_size, 0)
            self.assertEqual(loaded_agent.policy_size, agent.policy_size)
            self.assertEqual(len(loaded_agent.replay_buffer), len(agent.replay_buffer))
            self.assertEqual(loaded_agent.optimizer_steps, agent.optimizer_steps)
            self.assertIn(loaded_agent.greedy_action("0,0"), range(4))


if __name__ == "__main__":
    unittest.main()

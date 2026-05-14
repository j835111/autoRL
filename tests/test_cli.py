from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from auto_rl.cli import main
from auto_rl.config import AgentConfig, EnvConfig
from auto_rl.training import QLearningAgent


class CLITests(unittest.TestCase):
    def test_play_runs_without_project_config(self) -> None:
        agent = QLearningAgent(action_size=4, config=AgentConfig(algorithm="q_learning"), seed=2)
        agent.update("0,0", 3, 0.5, "1,0", False)
        agent.update("1,0", 1, 10.0, "1,1", True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            policy_path = tmp_path / "policy.json"
            agent.save(policy_path, env_config=EnvConfig(), action_labels=["up", "down", "left", "right"])

            previous_cwd = Path.cwd()
            previous_argv = sys.argv
            stdout = io.StringIO()
            try:
                os.chdir(tmp_path)
                sys.argv = [
                    "auto-rl",
                    "play",
                    "--policy",
                    str(policy_path),
                    "--episodes",
                    "1",
                    "--quiet",
                ]
                with redirect_stdout(stdout):
                    main()
            finally:
                os.chdir(previous_cwd)
                sys.argv = previous_argv

            output = stdout.getvalue()
            self.assertIn("Episode 0:", output)
            self.assertIn("success=", output)


if __name__ == "__main__":
    unittest.main()

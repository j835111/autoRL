from __future__ import annotations

import argparse
from pathlib import Path

from auto_rl.config import ExperimentConfig
from auto_rl.orchestrator import AutoRLOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal RL + auto-research framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train the inner RL agent with an outer researcher loop")
    train_parser.add_argument("--config", default="configs/baseline.json", help="Path to experiment config JSON")

    play_parser = subparsers.add_parser("play", help="Run an already trained inner policy without the researcher")
    play_parser.add_argument("--policy", required=True, help="Path to saved policy JSON")
    play_parser.add_argument("--episodes", type=int, default=3, help="Number of episodes to run")
    play_parser.add_argument("--quiet", action="store_true", help="Hide frame-by-frame rendering")
    play_parser.add_argument("--seed", type=int, default=None, help="Optional seed used when loading the policy")
    play_parser.add_argument(
        "--config",
        default=None,
        help="Optional config path used only to source a default seed for play mode",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "train":
        config = ExperimentConfig.load(args.config)
        orchestrator = AutoRLOrchestrator(config)
        summary = orchestrator.train()
        print(f"Training complete. Best phase: {summary['best_phase']}")
        print(f"Best evaluation success rate: {summary['best_eval_success_rate']:.3f}")
        print(f"Best evaluation reward: {summary['best_eval_reward']:.3f}")
        if summary.get("stop_reason"):
            print(f"Stop reason: {summary['stop_reason']}")
        print(f"Artifacts saved under: {Path(config.training.output_dir).resolve()}")
        return

    if args.command == "play":
        seed = args.seed if args.seed is not None else 0
        if args.config is not None and args.seed is None:
            seed = ExperimentConfig.load(args.config).training.seed

        traces = AutoRLOrchestrator.play_saved_policy(
            args.policy,
            episodes=args.episodes,
            render=not args.quiet,
            seed=seed,
        )
        for trace in traces:
            print(
                f"Episode {trace['episode']}: reward={trace['reward']:.3f}, "
                f"steps={trace['steps']}, success={trace['success']}"
            )
            if not args.quiet:
                print("\n---\n".join(trace["frames"]))
                print()
        return

    raise ValueError(f"Unsupported command: {args.command}")

from __future__ import annotations

from datetime import UTC, datetime
from statistics import median
from typing import Any


def build_run_id(seed: int) -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}-seed{seed}"


def median_absolute_deviation(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0

    center = median(values)
    deviations = [abs(value - center) for value in values]
    return float(median(deviations))


def confidence_score(improvement: float, noise_floor: float) -> float:
    if noise_floor <= 0.0:
        if improvement == 0.0:
            return 0.0
        # Deterministic evaluation runs can have zero observed noise. Treat any
        # non-zero delta as overwhelmingly confident without emitting Infinity.
        return abs(improvement) / 1e-12
    return abs(improvement) / noise_floor


def render_session_document(
    *,
    run_id: str,
    objective: str,
    output_dir: str,
    journal_path: str,
    summary: dict[str, Any],
    stop_reason: str | None,
) -> str:
    recent_history = summary.get("history", [])[-3:]
    phase_count = len(summary.get("history", []))
    recent_lines = []
    for item in recent_history:
        benchmark = item.get("benchmark", {})
        checks = item.get("checks", {})
        recent_lines.append(
            "- "
            f"phase {item['phase_index']}: "
            f"eval_reward={item['evaluation']['avg_reward']:.3f}, "
            f"success={item['evaluation']['success_rate']:.3f}, "
            f"confidence={benchmark.get('confidence_score', 0.0):.3f}, "
            f"checks_passed={checks.get('passed', True)}"
        )
    if not recent_lines:
        recent_lines.append("- No completed phases yet.")

    return "\n".join(
        [
            "# AutoRL Session",
            "",
            f"- Run ID: `{run_id}`",
            f"- Objective: {objective}",
            f"- Output Dir: `{output_dir}`",
            f"- Journal: `{journal_path}`",
            f"- Best Phase: `{summary.get('best_phase', -1)}`",
            f"- Best Eval Reward: `{summary.get('best_eval_reward', 0.0):.3f}`",
            f"- Best Eval Success Rate: `{summary.get('best_eval_success_rate', 0.0):.3f}`",
            f"- Completed Phases: `{phase_count}`",
            f"- Rollbacks Applied: `{summary.get('rollbacks_applied', 0)}`",
            f"- Consecutive Failed Checks: `{summary.get('failed_checks', 0)}`",
            f"- Stop Reason: {stop_reason or 'None'}",
            "",
            "## Current Artifacts",
            "",
            "- `best_policy.json`",
            "- `final_policy.json`",
            "- `summary.json`",
            "- `resolved_config.json`",
            "- `experiment_journal.jsonl`",
            "",
            "## Recent Phases",
            "",
            *recent_lines,
            "",
            "## Resume Hints",
            "",
            "- Read `summary.json` for the last finalized result.",
            "- Read `experiment_journal.jsonl` for append-only history across runs.",
            "- Use `resolved_config.json` as the last config that actually produced `final_policy.json`.",
            "- Treat `suggested_next_*` in `summary.json` as the next hypothesis, not a completed result.",
        ]
    )

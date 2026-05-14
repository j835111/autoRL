# AutoRL Session

- Run ID: `20260331T120223769485Z-seed7`
- Objective: Optimize evaluation reward and success rate while preserving correctness.
- Output Dir: `outputs/demo_run`
- Journal: `outputs/demo_run/experiment_journal.jsonl`
- Best Phase: `3`
- Best Eval Reward: `10.500`
- Best Eval Success Rate: `1.000`
- Completed Phases: `5`
- Rollbacks Applied: `0`
- Consecutive Failed Checks: `0`
- Stop Reason: Researcher requested stop after phase 4.

## Current Artifacts

- `best_policy.json`
- `final_policy.json`
- `summary.json`
- `resolved_config.json`
- `experiment_journal.jsonl`

## Recent Phases

- phase 2: eval_reward=-3.750, success=0.000, confidence=0.000, checks_passed=True
- phase 3: eval_reward=10.500, success=1.000, confidence=38.000, checks_passed=True
- phase 4: eval_reward=10.500, success=1.000, confidence=0.000, checks_passed=True

## Resume Hints

- Read `summary.json` for the last finalized result.
- Read `experiment_journal.jsonl` for append-only history across runs.
- Use `resolved_config.json` as the last config that actually produced `final_policy.json`.
- Treat `suggested_next_*` in `summary.json` as the next hypothesis, not a completed result.
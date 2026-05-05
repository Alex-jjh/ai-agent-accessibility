#!/usr/bin/env python3.11
"""Stage 2 filter: identify base-solvable tasks from smoker results.

Reads per-case JSON records produced by the runner (under
`data/smoker-shard-{a,b}/<runId>/cases/*.json`) and applies the
solvability gate:

  1. Majority-vote success (>=2/3 reps, configurable)
  2. Answer consistency (all successful reps must emit the same
     `send_msg_to_user(...)` payload, up to light normalization)
  3. Step-budget ceiling: median successful step count <= maxSteps
     (drops tasks that squeak through at the step limit, which tend
     to be timeout-adjacent and brittle under any manipulation)
  4. No errored reps (harness/bridge errors → exclude; not a task
     property)

Outputs:
  - results/smoker/filter-summary.csv  (one row per task)
  - results/smoker/passing-tasks.json  ({app: [task_id, ...]})
  - config-manipulation-filtered.yaml  (ready-to-run config)

Run:
    python3.11 scripts/smoker/analyze-smoker.py \\
      --shard-a data/smoker-shard-a \\
      --shard-b data/smoker-shard-b

Then review `results/smoker/filter-summary.csv`, optionally tune the
`--min-success` / `--max-median-steps` thresholds, and re-run.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO / "results" / "smoker"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CaseSummary:
    app: str
    task_id: str
    attempt: int
    success: bool
    outcome: str  # success/partial_success/failure/timeout
    total_steps: int
    final_answer: str | None
    case_id: str


@dataclass
class TaskStats:
    app: str
    task_id: str
    reps: int = 0
    successes: int = 0
    timeouts: int = 0
    failures: int = 0
    errors: int = 0
    step_counts: list[int] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successes / self.reps if self.reps else 0.0

    @property
    def median_steps(self) -> float:
        return float(median(self.step_counts)) if self.step_counts else 0.0

    @property
    def answer_consistent(self) -> bool:
        """True if all SUCCESSFUL reps emitted the same normalized answer."""
        succ_answers = [
            _normalize_answer(a)
            for a, o in zip(self.answers, self.outcomes)
            if o == "success" and a is not None
        ]
        if len(succ_answers) < 2:
            return True  # can't assess drift with <2 successes
        return len(set(succ_answers)) == 1

    @property
    def unique_successful_answers(self) -> list[str]:
        seen: list[str] = []
        for a, o in zip(self.answers, self.outcomes):
            if o != "success" or a is None:
                continue
            norm = _normalize_answer(a)
            if norm not in seen:
                seen.append(norm)
        return seen


# ---------------------------------------------------------------------------
# Answer extraction
# ---------------------------------------------------------------------------

# Match send_msg_to_user("payload") — captures the first argument, letting
# inner quotes and parens through. Good enough for filter-stage comparison.
_ANSWER_RE = re.compile(r'send_msg_to_user\s*\(\s*["\']?(.*?)["\']?\s*\)\s*$', re.DOTALL)


def _extract_answer(action: str) -> str | None:
    m = _ANSWER_RE.search(action.strip())
    if not m:
        return None
    return m.group(1).strip()


def _normalize_answer(s: str) -> str:
    """Strip trivial formatting differences that shouldn't count as drift."""
    x = s.strip().lower()
    # collapse whitespace
    x = re.sub(r"\s+", " ", x)
    # strip leading $ and trailing punctuation
    x = x.strip(".,;:!? ")
    return x


def _find_final_answer(steps: list[dict]) -> str | None:
    """Walk steps backwards; return payload of last send_msg_to_user action."""
    for step in reversed(steps):
        action = step.get("action", "")
        if "send_msg_to_user" in action:
            return _extract_answer(action)
    return None


# ---------------------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------------------

def _iter_cases(shard_dir: Path):
    """Yield CaseSummary from every case JSON under shard_dir/*/cases/*.json."""
    for run_dir in sorted(shard_dir.glob("*")):
        cases_dir = run_dir / "cases"
        if not cases_dir.is_dir():
            continue
        for case_path in sorted(cases_dir.glob("*.json")):
            try:
                data = json.loads(case_path.read_text())
            except json.JSONDecodeError:
                print(f"  warn: malformed JSON {case_path}", file=sys.stderr)
                continue
            trace = data.get("trace", {}) or {}
            steps = trace.get("steps", []) or []
            yield CaseSummary(
                app=data.get("app", ""),
                task_id=str(data.get("taskId", "")),
                attempt=int(data.get("attempt", 0)),
                success=bool(trace.get("success", False)),
                outcome=trace.get("outcome", "failure"),
                total_steps=int(trace.get("totalSteps", len(steps))),
                final_answer=_find_final_answer(steps),
                case_id=data.get("caseId", ""),
            )


def aggregate(shard_dirs: list[Path]) -> dict[tuple[str, str], TaskStats]:
    by_task: dict[tuple[str, str], TaskStats] = {}
    for shard in shard_dirs:
        if not shard.exists():
            print(f"  warn: shard dir missing: {shard}", file=sys.stderr)
            continue
        for case in _iter_cases(shard):
            key = (case.app, case.task_id)
            stats = by_task.setdefault(key, TaskStats(app=case.app, task_id=case.task_id))
            stats.reps += 1
            stats.outcomes.append(case.outcome)
            stats.answers.append(case.final_answer or "")
            stats.step_counts.append(case.total_steps)
            if case.outcome == "success":
                stats.successes += 1
            elif case.outcome == "timeout":
                stats.timeouts += 1
            elif case.outcome == "failure":
                stats.failures += 1
            else:
                stats.errors += 1
    return by_task


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

@dataclass
class FilterConfig:
    min_successes: int = 2        # ≥2/3 = majority vote
    required_reps: int = 3
    max_median_steps: int = 25     # leave 5-step headroom below the 30 maxSteps
    require_answer_consistency: bool = True
    disallow_errors: bool = True


def classify(stats: TaskStats, cfg: FilterConfig) -> tuple[bool, str]:
    """Return (passes, reason). reason is '' if passes."""
    if stats.reps < cfg.required_reps:
        return False, f"incomplete_reps:{stats.reps}/{cfg.required_reps}"
    if cfg.disallow_errors and stats.errors > 0:
        return False, f"harness_errors:{stats.errors}"
    if stats.successes < cfg.min_successes:
        return False, f"insufficient_success:{stats.successes}/{stats.reps}"
    if cfg.require_answer_consistency and not stats.answer_consistent:
        return False, f"answer_drift:{len(stats.unique_successful_answers)}_unique"
    if stats.median_steps > cfg.max_median_steps:
        return False, f"step_budget:median={stats.median_steps:.0f}>{cfg.max_median_steps}"
    return True, ""


# ---------------------------------------------------------------------------
# Config emission
# ---------------------------------------------------------------------------

MANIPULATION_CONFIG_TEMPLATE = '''\
# Manipulation — Filtered Full AMT Experiment
# Auto-generated by scripts/smoker/analyze-smoker.py on {date}.
# Source: smoker runs with >= {min_succ}/{req_reps} base success
#         and no answer drift and median_steps <= {max_steps}.
#
# Matrix: {n_tasks} tasks × 26 operators × 3 reps × 2 models
#       = {n_cases:,} cases
# Estimated: ~$800-1,200, 3-5 days wall (parallel shards)
#
# To shard: duplicate this file, split `individualVariants` list across shards.

webarena:
  apps:
{apps_yaml}
  tasksPerApp:
{tasks_yaml}

scanner:
  wcagLevels: ["A", "AA"]
  stabilityIntervalMs: 2000
  stabilityTimeoutMs: 15000
  concurrency: 1

variants:
  levels: []
  scoreRanges:
    low:         {{ min: 0.0,  max: 0.25 }}
    medium-low:  {{ min: 0.25, max: 0.50 }}
    base:        {{ min: 0.40, max: 0.70 }}
    high:        {{ min: 0.75, max: 1.0  }}
  individualVariants:
    # All 26 AMT operators (L1-L13, ML1-ML3, H1-H8 including H5a/b/c)
    - ["L1"]
    - ["L2"]
    - ["L3"]
    - ["L4"]
    - ["L5"]
    - ["L6"]
    - ["L7"]
    - ["L8"]
    - ["L9"]
    - ["L10"]
    - ["L11"]
    - ["L12"]
    - ["L13"]
    - ["ML1"]
    - ["ML2"]
    - ["ML3"]
    - ["H1"]
    - ["H2"]
    - ["H3"]
    - ["H4"]
    - ["H5a"]
    - ["H5b"]
    - ["H5c"]
    - ["H6"]
    - ["H7"]
    - ["H8"]

runner:
  repetitions: 3
  maxSteps: 30
  concurrency: 1
  agentConfigs:
    - observationMode: "text-only"
      llmBackend: "claude-sonnet"
      maxSteps: 30
      retryCount: 3
      retryBackoffMs: 1000
      temperature: 0.0
    # Add the llama-4 agent as a separate shard config when running Stage 3
    # to keep per-shard budgets predictable.

recorder:
  waitAfterLoadMs: 10000
  concurrency: 1

output:
  dataDir: "./data/manipulation-v2"
  exportFormats: ["json", "csv"]
'''


APP_URL_BY_NAME = {
    "ecommerce": "http://10.0.1.50:7770",
    "ecommerce_admin": "http://10.0.1.50:7780",
    "reddit": "http://10.0.1.50:9999",
    "gitlab": "http://10.0.1.50:8023",
}


def emit_config(passing: dict[str, list[str]], out_path: Path) -> None:
    from datetime import date

    apps_yaml = "\n".join(
        f'    {app}:\n      url: "{APP_URL_BY_NAME[app]}"' for app in sorted(passing) if passing[app]
    )
    tasks_yaml_lines = []
    for app in sorted(passing):
        ids = passing[app]
        if not ids:
            continue
        # chunk to keep lines readable
        chunks = [ids[i : i + 15] for i in range(0, len(ids), 15)]
        joined = (",\n      ").join(", ".join(f'"{i}"' for i in c) for c in chunks)
        tasks_yaml_lines.append(f"    {app}: [\n      {joined}\n    ]")
    tasks_yaml = "\n".join(tasks_yaml_lines)

    n_tasks = sum(len(v) for v in passing.values())
    n_cases = n_tasks * 26 * 3 * 2  # 26 ops × 3 reps × 2 models (text-only claude + llama)

    out_path.write_text(
        MANIPULATION_CONFIG_TEMPLATE.format(
            date=date.today().isoformat(),
            min_succ=2,
            req_reps=3,
            max_steps=25,
            n_tasks=n_tasks,
            n_cases=n_cases,
            apps_yaml=apps_yaml,
            tasks_yaml=tasks_yaml,
        )
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-a", type=Path, default=REPO / "data" / "smoker-shard-a")
    ap.add_argument("--shard-b", type=Path, default=REPO / "data" / "smoker-shard-b")
    ap.add_argument("--min-success", type=int, default=2, help="min successful reps of 3 (default 2)")
    ap.add_argument("--max-median-steps", type=int, default=25)
    ap.add_argument("--no-answer-check", action="store_true")
    ap.add_argument(
        "--output-config",
        type=Path,
        default=REPO / "config-manipulation-filtered.yaml",
    )
    ap.add_argument("--summary-csv", type=Path, default=RESULTS_DIR / "filter-summary.csv")
    ap.add_argument("--passing-json", type=Path, default=RESULTS_DIR / "passing-tasks.json")
    args = ap.parse_args()

    cfg = FilterConfig(
        min_successes=args.min_success,
        max_median_steps=args.max_median_steps,
        require_answer_consistency=not args.no_answer_check,
    )

    print(f"Loading cases from:\n  {args.shard_a}\n  {args.shard_b}")
    by_task = aggregate([args.shard_a, args.shard_b])
    print(f"Aggregated {len(by_task)} tasks, {sum(s.reps for s in by_task.values())} cases.\n")

    # Classify
    passing: dict[str, list[str]] = defaultdict(list)
    rows = []
    drop_reasons: dict[str, int] = defaultdict(int)
    for (app, tid), stats in sorted(by_task.items(), key=lambda x: (x[0][0], int(x[0][1]))):
        ok, reason = classify(stats, cfg)
        if ok:
            passing[app].append(tid)
        else:
            drop_reasons[reason.split(":", 1)[0]] += 1
        rows.append({
            "app": app,
            "task_id": tid,
            "reps": stats.reps,
            "successes": stats.successes,
            "timeouts": stats.timeouts,
            "failures": stats.failures,
            "errors": stats.errors,
            "success_rate": f"{stats.success_rate:.2f}",
            "median_steps": f"{stats.median_steps:.1f}",
            "answer_consistent": stats.answer_consistent,
            "unique_successful_answers": len(stats.unique_successful_answers),
            "passes_filter": ok,
            "drop_reason": reason,
        })

    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_csv.open("w", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"Wrote {args.summary_csv}")

    args.passing_json.write_text(
        json.dumps({app: sorted(ids, key=int) for app, ids in passing.items()}, indent=2)
    )
    print(f"Wrote {args.passing_json}")

    emit_config(passing, args.output_config)
    print(f"Wrote {args.output_config}")

    # Summary
    n_passing = sum(len(v) for v in passing.values())
    print(f"\nFilter results (min_success={cfg.min_successes}/{cfg.required_reps}, "
          f"max_median_steps={cfg.max_median_steps}, "
          f"answer_check={cfg.require_answer_consistency}):")
    for app in sorted(passing):
        print(f"  {app:18} {len(passing[app]):>3} passing")
    print(f"  {'TOTAL':18} {n_passing:>3} passing / {len(by_task)} ({100*n_passing/max(len(by_task),1):.1f}%)")
    if drop_reasons:
        print("\nDrop reasons:")
        for r, n in sorted(drop_reasons.items(), key=lambda x: -x[1]):
            print(f"  {r:22} {n}")

    print(f"\nEstimated Stage 3 cases: {n_passing * 26 * 3 * 2:,} "
          f"({n_passing} tasks × 26 ops × 3 reps × 2 models)")


if __name__ == "__main__":
    main()

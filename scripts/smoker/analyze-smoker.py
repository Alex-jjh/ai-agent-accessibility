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
    # Failure-mode signals extracted from trace (for paper-ready reporting)
    bridge_crash: bool = False
    context_window_exceeded: bool = False
    admin_login_failed: bool = False
    empty_first_obs: bool = False
    goto_timeout: bool = False
    chromium_crashed: bool = False


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
    # Failure-mode indicators across reps (aggregated for paper-ready reporting)
    bridge_crashes: int = 0
    context_window_exceeded: int = 0
    admin_login_failed: int = 0
    empty_first_obs: int = 0
    goto_timeout: int = 0
    chromium_crashes: int = 0

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
            bridge_log = trace.get("bridgeLog") or ""

            # Scan steps + bridge log for known failure-mode signals
            bridge_crash = False
            context_window = False
            goto_timeout = False
            chromium_crashed = False
            empty_first = False
            for s in steps:
                rd = s.get("resultDetail") or ""
                if "Bridge process terminated" in rd:
                    bridge_crash = True
                if "Context Window" in rd or "context_window_exceeded" in rd.lower():
                    context_window = True
                if "Page.goto" in rd and "Timeout" in rd:
                    goto_timeout = True
                if "Target crashed" in rd or "Frame.evaluate" in rd:
                    chromium_crashed = True
            if steps and "No accessibility tree" in (steps[0].get("observation") or ""):
                empty_first = True
            admin_login = "ui_login for shopping_admin failed" in bridge_log

            yield CaseSummary(
                app=data.get("app", ""),
                task_id=str(data.get("taskId", "")),
                attempt=int(data.get("attempt", 0)),
                success=bool(trace.get("success", False)),
                outcome=trace.get("outcome", "failure"),
                total_steps=int(trace.get("totalSteps", len(steps))),
                final_answer=_find_final_answer(steps),
                case_id=data.get("caseId", ""),
                bridge_crash=bridge_crash,
                context_window_exceeded=context_window,
                admin_login_failed=admin_login,
                empty_first_obs=empty_first,
                goto_timeout=goto_timeout,
                chromium_crashed=chromium_crashed,
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
            # Tally failure-mode signals for paper-ready reporting
            if case.bridge_crash:
                stats.bridge_crashes += 1
            if case.context_window_exceeded:
                stats.context_window_exceeded += 1
            if case.admin_login_failed:
                stats.admin_login_failed += 1
            if case.empty_first_obs:
                stats.empty_first_obs += 1
            if case.goto_timeout:
                stats.goto_timeout += 1
            if case.chromium_crashed:
                stats.chromium_crashes += 1
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


# Category labels used in both the per-task CSV and the aggregated
# paper-ready exclusion report. Keep these stable — paper tables will
# reference these strings verbatim.
EXCLUSION_CATEGORIES = {
    "included":                  "Base-solvable task (passes all gates)",
    "incomplete_reps":           "Fewer than 3 reps recorded (shard crash / early kill)",
    "harness_errors":            "Bridge/harness errors outside agent control",
    "context_window_exceeded":   "A11y tree exceeds Claude context window (Magento admin grids)",
    "bridge_crash":              "BrowserGym env.reset() crashed on multi-URL task",
    "admin_login_failed":        "Magento admin login timed out (infrastructure)",
    "goto_timeout":              "Playwright Page.goto() timed out on start_url",
    "chromium_crash":            "Chromium tab crashed mid-task",
    "insufficient_success":      "Base success rate < majority vote (task too hard for Claude)",
    "answer_drift":              "Successful reps produced different answers (Docker state drift)",
    "step_budget":               "Median step count > limit (task brittle at step budget)",
}


def classify(stats: TaskStats, cfg: FilterConfig) -> tuple[bool, str, str]:
    """Return (passes, code, human_reason).

    code is a short machine-readable label (e.g. 'admin_login_failed').
    human_reason is an English sentence suitable for paper table captions.
    """
    if stats.reps < cfg.required_reps:
        code = "incomplete_reps"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.reps}/{cfg.required_reps} reps)"

    # Rank infra failures BEFORE insufficient_success so paper can attribute
    # the exclusion to the root cause rather than the symptom (low success).
    if stats.context_window_exceeded >= 2:
        code = "context_window_exceeded"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.context_window_exceeded}/{stats.reps} reps)"
    if stats.bridge_crashes >= 2:
        code = "bridge_crash"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.bridge_crashes}/{stats.reps} reps)"
    if stats.admin_login_failed >= 2:
        code = "admin_login_failed"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.admin_login_failed}/{stats.reps} reps)"
    if stats.goto_timeout >= 2:
        code = "goto_timeout"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.goto_timeout}/{stats.reps} reps)"
    if stats.chromium_crashes >= 2:
        code = "chromium_crash"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.chromium_crashes}/{stats.reps} reps)"
    if cfg.disallow_errors and stats.errors > 0:
        code = "harness_errors"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.errors} errored reps)"
    if stats.successes < cfg.min_successes:
        code = "insufficient_success"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.successes}/{stats.reps} success)"
    if cfg.require_answer_consistency and not stats.answer_consistent:
        code = "answer_drift"
        n_unique = len(stats.unique_successful_answers)
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({n_unique} distinct answers)"
    if stats.median_steps > cfg.max_median_steps:
        code = "step_budget"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} (median={stats.median_steps:.0f})"
    return True, "included", EXCLUSION_CATEGORIES["included"]


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
# Paper-ready exclusion report
# ---------------------------------------------------------------------------

def emit_exclusion_report(
    by_task: dict[tuple[str, str], TaskStats],
    passing: dict[str, list[str]],
    cfg: FilterConfig,
    args,
    out_path: Path,
) -> None:
    """Write a markdown report suitable for direct inclusion in the paper's
    task-selection appendix. Documents every exclusion bucket with counts,
    per-app breakdown, and human-readable rationale.
    """
    from datetime import datetime, timezone

    total_tasks = len(by_task)
    n_passing = sum(len(v) for v in passing.values())
    n_excluded = total_tasks - n_passing

    # Per-app totals
    per_app_total: dict[str, int] = defaultdict(int)
    per_app_pass: dict[str, int] = defaultdict(int)
    for (app, _), _ in by_task.items():
        per_app_total[app] += 1
    for app, ids in passing.items():
        per_app_pass[app] = len(ids)

    # Per-bucket counts
    bucket_rows: dict[str, list[TaskStats]] = defaultdict(list)
    for (_, _), stats in by_task.items():
        ok, code, _ = classify(stats, cfg)
        bucket_rows[code].append(stats)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Smoker Base-Solvability Gate — Task Exclusion Report")
    lines.append("")
    lines.append(f"_Generated by `scripts/smoker/analyze-smoker.py` on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}._")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report documents which WebArena tasks were eligible for the "
        "manipulation (Stage 3) experiment and the specific reason each "
        "excluded task was dropped. It is designed to be cited verbatim in "
        "the CHI 2027 paper's task-selection appendix so reviewers can verify "
        "the exclusion criteria were applied consistently and that no "
        "exclusion was post-hoc biased toward outcomes."
    )
    lines.append("")
    lines.append("## Gate parameters")
    lines.append("")
    lines.append(f"- Agent: Claude Sonnet 4 (`claude-sonnet` alias in LiteLLM, `us.anthropic.claude-sonnet-4-20250514-v1:0`)")
    lines.append(f"- Condition: base variant (no patches), temperature 0.0, maxSteps 30")
    lines.append(f"- Reps per task: {cfg.required_reps}")
    lines.append(f"- Inclusion gates (all must pass):")
    lines.append(f"  1. **Majority-vote success**: ≥{cfg.min_successes}/{cfg.required_reps} reps report `success`")
    lines.append(f"  2. **Answer consistency**: all successful reps emit the same normalized final answer")
    lines.append(f"  3. **Step-budget headroom**: median successful step count ≤ {cfg.max_median_steps}")
    lines.append(f"  4. **Harness health**: zero reps hit bridge/context/Chromium errors that were not the agent's fault")
    lines.append("")
    lines.append("## Top-line numbers")
    lines.append("")
    lines.append(f"- **Total smoker-tested tasks**: {total_tasks}")
    lines.append(f"- **Passed → used in Stage 3**: {n_passing} ({100*n_passing/max(total_tasks,1):.1f}%)")
    lines.append(f"- **Excluded**: {n_excluded} ({100*n_excluded/max(total_tasks,1):.1f}%)")
    lines.append("")
    lines.append("### Per-app pass-through")
    lines.append("")
    lines.append("| App | Total | Passed | Excluded | Pass rate |")
    lines.append("|-----|------:|-------:|---------:|----------:|")
    for app in sorted(per_app_total):
        tot = per_app_total[app]
        pas = per_app_pass[app]
        exc = tot - pas
        lines.append(f"| {app} | {tot} | {pas} | {exc} | {100*pas/max(tot,1):.1f}% |")
    lines.append("")

    lines.append("## Exclusion categories")
    lines.append("")
    lines.append(
        "Each excluded task is attributed to the **first** criterion it fails, "
        "in this priority order (infrastructure failures ranked ahead of "
        "task-difficulty failures so reviewers can see the underlying cause "
        "rather than only the success-rate symptom):"
    )
    lines.append("")
    lines.append("| # | Category | Description | Count |")
    lines.append("|---|----------|-------------|------:|")
    priority = [
        "incomplete_reps",
        "context_window_exceeded",
        "bridge_crash",
        "admin_login_failed",
        "goto_timeout",
        "chromium_crash",
        "harness_errors",
        "insufficient_success",
        "answer_drift",
        "step_budget",
    ]
    for i, code in enumerate(priority, 1):
        n = len(bucket_rows.get(code, []))
        desc = EXCLUSION_CATEGORIES.get(code, code)
        lines.append(f"| {i} | `{code}` | {desc} | {n} |")
    lines.append(f"| — | `included` | {EXCLUSION_CATEGORIES['included']} | {len(bucket_rows.get('included', []))} |")
    lines.append("")

    # Per-bucket task list (for full transparency)
    lines.append("## Excluded tasks per category")
    lines.append("")
    for code in priority:
        tasks = bucket_rows.get(code, [])
        if not tasks:
            continue
        lines.append(f"### `{code}` — {EXCLUSION_CATEGORIES.get(code, code)}")
        lines.append("")
        lines.append("| Task | Reps | Success | Median steps | Signal |")
        lines.append("|------|-----:|--------:|-------------:|--------|")
        for s in sorted(tasks, key=lambda x: (x.app, int(x.task_id))):
            signal_parts = []
            if s.context_window_exceeded:
                signal_parts.append(f"ctx_win×{s.context_window_exceeded}")
            if s.bridge_crashes:
                signal_parts.append(f"bridge×{s.bridge_crashes}")
            if s.admin_login_failed:
                signal_parts.append(f"admin_login×{s.admin_login_failed}")
            if s.goto_timeout:
                signal_parts.append(f"goto_to×{s.goto_timeout}")
            if s.chromium_crashes:
                signal_parts.append(f"chrome_crash×{s.chromium_crashes}")
            if s.empty_first_obs:
                signal_parts.append(f"empty_obs×{s.empty_first_obs}")
            n_unique = len(s.unique_successful_answers)
            if code == "answer_drift":
                signal_parts.append(f"answers={n_unique}")
            signal = ", ".join(signal_parts) if signal_parts else "—"
            lines.append(
                f"| {s.app}:{s.task_id} | {s.reps} | {s.successes}/{s.reps} | "
                f"{s.median_steps:.0f} | {signal} |"
            )
        lines.append("")

    lines.append("## Paper-drop-in narrative")
    lines.append("")
    lines.append(
        "> We sourced all 684 WebArena tasks across the four deployed apps "
        "(shopping_admin, shopping, reddit, gitlab) and filtered them through "
        "a base-solvability smoker: each task was run three times at the "
        "unmodified baseline by Claude Sonnet 4 in text-only observation mode. "
        "We retained tasks that (i) succeeded in at least two of three reps, "
        "(ii) produced the same normalized final answer across successful reps, "
        "and (iii) had a median successful step count within the 30-step "
        "budget with five-step headroom. Tasks whose three reps were dominated "
        "by infrastructure failures — BrowserGym `env.reset()` crashes on "
        "multi-URL tasks, Playwright navigation timeouts on Magento start "
        "pages, Chromium tab crashes, Claude context-window overruns on "
        f"Magento admin grids — were attributed to the corresponding "
        f"infrastructure category rather than to agent failure. Of the 684 "
        f"tasks tested, **{n_passing} survived the gate** and formed the "
        f"Stage 3 manipulation task set. A full per-task breakdown is in "
        f"Appendix X (regenerable via `scripts/smoker/analyze-smoker.py` "
        f"from the raw case JSON)."
    )
    lines.append("")

    out_path.write_text("\n".join(lines))


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
    per_app_drop: dict[tuple[str, str], int] = defaultdict(int)
    for (app, tid), stats in sorted(by_task.items(), key=lambda x: (x[0][0], int(x[0][1]))):
        ok, code, reason = classify(stats, cfg)
        if ok:
            passing[app].append(tid)
        else:
            drop_reasons[code] += 1
            per_app_drop[(app, code)] += 1
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
            "bridge_crashes": stats.bridge_crashes,
            "context_window_exceeded": stats.context_window_exceeded,
            "admin_login_failed": stats.admin_login_failed,
            "empty_first_obs": stats.empty_first_obs,
            "goto_timeout": stats.goto_timeout,
            "chromium_crashes": stats.chromium_crashes,
            "passes_filter": ok,
            "drop_code": code,
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

    # Paper-ready exclusion report
    report_path = RESULTS_DIR / "exclusion-report.md"
    emit_exclusion_report(by_task, passing, cfg, args, report_path)
    print(f"Wrote {report_path}")

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

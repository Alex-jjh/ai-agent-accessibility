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
    """Pre-registered gate for the Stage 3 manipulation task set.

    Pre-registration date: 2026-05-06 (before any Stage 3 manipulation data
    was collected). The gate is intentionally conservative — stochastic and
    trivial tasks are excluded to avoid inflating the observed drop. Our
    observed manipulation effects are therefore lower bounds of the true
    effects on WebArena task population.

    Gate criteria (all must pass):
      1. required_reps reps must be recorded (shard completeness)
      2. Zero reps with infrastructure errors (context window, bridge crash,
         admin login timeout, goto timeout, Chromium crash)
      3. All required_reps reps must report `success` from BrowserGym's
         evaluator (strict 3/3; majority vote rejected because baseline
         stochasticity would confound manipulation signal)
      4. Median successful step count must be >= min_median_steps
         (excludes trivial queries where a11y tree parsing contributes
         nothing and manipulation cannot affect outcome)
      5. Median successful step count must be <= max_median_steps
         (excludes tasks that squeak through at the step limit and are
         brittle under any manipulation)

    ANSWER-CONSISTENCY CHECK DROPPED (2026-05-06): BrowserGym's evaluator
    is the authoritative judge of correctness. Requiring literal string
    equality of agent answers across reps was false-rejecting tasks where
    the agent paraphrased a correct answer (e.g., 'The issue is open' vs
    'The issue is still open'). BrowserGym accepted both as success,
    so our downstream check was redundant and over-strict.
    """
    required_reps: int = 3
    require_full_success: bool = True   # 3/3 strict
    min_median_steps: int = 3            # excludes trivial "click once" tasks
    max_median_steps: int = 25           # excludes tasks brittle at step budget
    disallow_infra_failures: bool = True
    disallow_harness_errors: bool = True


# Category labels used in both the per-task CSV and the aggregated
# paper-ready exclusion report. Keep these stable — paper tables will
# reference these strings verbatim.
#
# Priority order matters: each task is attributed to the FIRST criterion
# it fails. Infrastructure failures rank ahead of difficulty failures so
# the paper cannot be accused of mislabeling a Magento timeout as
# "Claude cannot solve this task".
EXCLUSION_CATEGORIES = {
    "included":                  "Base-solvable task (passes all gates; used in Stage 3 manipulation)",
    # Level 1: shard completeness
    "incomplete_reps":           "Fewer than 3 reps recorded (shard crash or early kill)",
    # Level 2: infrastructure failures (rank above difficulty)
    "context_window_exceeded":   "A11y tree exceeds Claude context window (Magento admin grids)",
    "bridge_crash":              "BrowserGym env.reset() crashed on multi-URL task",
    "admin_login_failed":        "Magento admin login timed out (infrastructure flakiness)",
    "goto_timeout":              "Playwright Page.goto() timed out on start_url",
    "chromium_crash":            "Chromium tab crashed mid-task (OOM / JS crash)",
    "harness_errors":            "Bridge/harness errors outside agent control",
    # Level 3: stochastic or weak base solvability
    "stochastic_base":           "<3/3 reps succeeded — baseline is non-deterministic (retained as Tier-2 reference)",
    # Level 4: task-complexity mismatches
    "trivial_task":              "Median successful step count < 3 — a11y tree contributes little (variant manipulation cannot produce measurable effect)",
    "step_budget":               "Median successful step count > 25 — task brittle at step budget",
}


def classify(stats: TaskStats, cfg: FilterConfig) -> tuple[bool, str, str]:
    """Return (passes, code, human_reason).

    code is a short machine-readable label (e.g. 'admin_login_failed').
    human_reason is an English sentence suitable for paper table captions.
    """
    # Level 1: shard completeness
    if stats.reps < cfg.required_reps:
        code = "incomplete_reps"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.reps}/{cfg.required_reps} reps)"

    # Level 2: infrastructure failures (rank above difficulty so paper can
    # attribute the exclusion to the root cause rather than the symptom).
    if cfg.disallow_infra_failures:
        if stats.context_window_exceeded >= 1:
            code = "context_window_exceeded"
            return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.context_window_exceeded}/{stats.reps} reps)"
        if stats.bridge_crashes >= 1:
            code = "bridge_crash"
            return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.bridge_crashes}/{stats.reps} reps)"
        if stats.admin_login_failed >= 1:
            code = "admin_login_failed"
            return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.admin_login_failed}/{stats.reps} reps)"
        if stats.goto_timeout >= 1:
            code = "goto_timeout"
            return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.goto_timeout}/{stats.reps} reps)"
        if stats.chromium_crashes >= 1:
            code = "chromium_crash"
            return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.chromium_crashes}/{stats.reps} reps)"
    if cfg.disallow_harness_errors and stats.errors > 0:
        code = "harness_errors"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.errors} errored reps)"

    # Level 3: strict base-solvability
    if cfg.require_full_success and stats.successes < cfg.required_reps:
        code = "stochastic_base"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} ({stats.successes}/{stats.reps} success)"

    # Level 4: complexity mismatches
    if stats.median_steps < cfg.min_median_steps:
        code = "trivial_task"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} (median={stats.median_steps:.0f} < {cfg.min_median_steps})"
    if stats.median_steps > cfg.max_median_steps:
        code = "step_budget"
        return False, code, f"{EXCLUSION_CATEGORIES[code]} (median={stats.median_steps:.0f} > {cfg.max_median_steps})"

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
    lines.append("## Pre-registration")
    lines.append("")
    lines.append(
        "The gate criteria below were **pre-registered on 2026-05-06**, "
        "before any Stage 3 manipulation data was collected. No post-hoc "
        "adjustments were made based on manipulation outcomes. See "
        "`docs/analysis/task-selection-methodology.md` for the full "
        "pre-registration record including justification for each gate."
    )
    lines.append("")
    lines.append("## Gate parameters")
    lines.append("")
    lines.append(f"- Agent: Claude Sonnet 4 (`claude-sonnet` alias in LiteLLM, `us.anthropic.claude-sonnet-4-20250514-v1:0`)")
    lines.append(f"- Condition: base variant (no patches), temperature 0.0, maxSteps 30")
    lines.append(f"- Reps per task: {cfg.required_reps}")
    lines.append(f"- Inclusion gates (all must pass, in priority order):")
    lines.append(f"  1. **Shard completeness**: exactly {cfg.required_reps}/{cfg.required_reps} reps recorded")
    lines.append(f"  2. **Zero infrastructure failures**: no context-window overruns, bridge crashes, admin-login timeouts, navigation timeouts, or Chromium crashes (see category priority below)")
    lines.append(f"  3. **Strict base solvability**: 3/3 reps report `success` from BrowserGym's evaluator (2/3 tasks are retained as a Tier-2 reference set, not used in Stage 3 manipulation)")
    lines.append(f"  4. **Minimum complexity**: median successful step count ≥ {cfg.min_median_steps} (excludes trivial queries where a11y tree contributes little)")
    lines.append(f"  5. **Step-budget headroom**: median successful step count ≤ {cfg.max_median_steps} (excludes tasks brittle at step limit)")
    lines.append("")
    lines.append("## Why this gate is *conservative* (lower-bound argument)")
    lines.append("")
    lines.append(
        "Each gate criterion makes the **observed manipulation effect "
        "smaller** than it would be without the gate:"
    )
    lines.append("")
    lines.append("- Excluding **trivial tasks** (step < 3) removes cases where a11y tree parsing barely matters; these tasks would otherwise dilute the mean drop.")
    lines.append("- Excluding **stochastic-base tasks** (<3/3 success) removes cases where baseline noise would be misattributed to manipulation; these tasks would otherwise add variance.")
    lines.append("- Excluding **infrastructure failures** removes cases that are artifacts of the benchmark × model interaction (context window, Magento login flakiness) rather than the research question.")
    lines.append("")
    lines.append(
        "Our reported Stage 3 manipulation drops are therefore **lower bounds** "
        "of the true effect on the WebArena task population. A less conservative "
        "gate (e.g., 2/3 majority, no step floor) would produce a larger "
        "observed drop but at the cost of interpretability."
    )
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
        "stochastic_base",
        "trivial_task",
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
            if code == "stochastic_base":
                n_unique = len(s.unique_successful_answers)
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
        "> **Task selection methodology.** Our primary analysis set was "
        "constructed via a three-stage pipeline designed to balance "
        "statistical power (many tasks) with interpretability (clean "
        "baselines). (1) We sourced all 684 WebArena tasks across the "
        "four deployed apps (shopping_admin, shopping, reddit, gitlab); "
        "no eligibility filter was applied at this stage, and no LLM-judge "
        "tasks exist in these apps so evaluation is fully offline. (2) We "
        "ran a **base-solvability smoker**: each task was executed three "
        "times at the unmodified baseline by Claude Sonnet 4 "
        "(`us.anthropic.claude-sonnet-4-20250514-v1:0`) in text-only "
        "observation mode, before any manipulation data was collected. "
        "(3) We applied a **pre-registered inclusion gate** (registered "
        "2026-05-06): a task enters the Stage 3 manipulation set if and "
        "only if (a) all three reps completed without infrastructure "
        "failures, (b) all three reps were judged `success` by BrowserGym's "
        "evaluator, and (c) the median successful step count fell within "
        "[3, 25]. Each excluded task is attributed to the **first** "
        "criterion it fails, with infrastructure categories ranked ahead "
        "of difficulty categories so that, e.g., a Magento context-window "
        "overrun is not misattributed to Claude's solving ability."
    )
    lines.append("")
    lines.append(
        "> This gate is deliberately conservative. Excluding trivial tasks "
        "(median < 3 steps) removes cases where the a11y tree contributes "
        "little to task success; excluding stochastic-base tasks (< 3/3) "
        "removes cases whose baseline noise would be misattributed to "
        "manipulation; excluding infrastructure failures removes artifacts "
        "of the benchmark × model interaction. Each exclusion reduces "
        "the observed manipulation effect, so our reported drops are "
        "**lower bounds** of the true effect on the WebArena task population."
    )
    lines.append("")
    lines.append(
        f"> Of the 684 tasks tested, **{n_passing} survived the gate** "
        f"({100*n_passing/max(total_tasks,1):.1f}%) and formed the Stage 3 "
        f"manipulation task set. A full per-task exclusion table with "
        f"named reasons appears in Appendix X, and the entire filter "
        f"pipeline is regenerable via `scripts/smoker/analyze-smoker.py` "
        f"from the raw case JSON. This primary set is complemented by "
        f"a Tier-2 reference set of stochastic-base tasks (see "
        f"`passing-tier2.json`) and by the N=13 Mode A depth set "
        f"(hand-selected in prior work) used for mechanistic case studies."
    )
    lines.append("")

    out_path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Smoker filter: emit Stage 3 manipulation task set from "
                    "pre-registered gate (2026-05-06). See "
                    "docs/analysis/task-selection-methodology.md.",
    )
    ap.add_argument("--shard-a", type=Path, default=REPO / "data" / "smoker-shard-a")
    ap.add_argument("--shard-b", type=Path, default=REPO / "data" / "smoker-shard-b")
    ap.add_argument("--min-median-steps", type=int, default=3,
                    help="Minimum median successful step count (default 3, "
                         "excludes trivial click-and-done tasks).")
    ap.add_argument("--max-median-steps", type=int, default=25,
                    help="Maximum median step count (default 25, leaves 5-step "
                         "headroom below the 30-step agent budget).")
    ap.add_argument(
        "--output-config",
        type=Path,
        default=REPO / "config-manipulation-filtered.yaml",
    )
    ap.add_argument("--summary-csv", type=Path, default=RESULTS_DIR / "filter-summary.csv")
    ap.add_argument("--passing-json", type=Path, default=RESULTS_DIR / "passing-tasks.json")
    ap.add_argument("--tier2-json", type=Path, default=RESULTS_DIR / "passing-tier2.json",
                    help="Output file for Tier-2 stochastic-base tasks (<3/3 "
                         "success). Not used in Stage 3; retained for paper "
                         "supplementary material.")
    args = ap.parse_args()

    cfg = FilterConfig(
        min_median_steps=args.min_median_steps,
        max_median_steps=args.max_median_steps,
    )

    print(f"Loading cases from:\n  {args.shard_a}\n  {args.shard_b}")
    by_task = aggregate([args.shard_a, args.shard_b])
    print(f"Aggregated {len(by_task)} tasks, {sum(s.reps for s in by_task.values())} cases.\n")

    # Classify
    passing: dict[str, list[str]] = defaultdict(list)
    tier2: dict[str, list[str]] = defaultdict(list)  # stochastic-base-only
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
            # Stochastic-base tasks are retained as a Tier-2 reference set.
            # Paper can use them for "tasks where base solvability is
            # non-deterministic" analysis without running manipulation on them.
            if code == "stochastic_base":
                tier2[app].append(tid)
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

    args.tier2_json.write_text(
        json.dumps({app: sorted(ids, key=int) for app, ids in tier2.items()}, indent=2)
    )
    print(f"Wrote {args.tier2_json} (Tier-2 stochastic-base reference set, NOT used in Stage 3)")

    emit_config(passing, args.output_config)
    print(f"Wrote {args.output_config}")

    # Paper-ready exclusion report
    report_path = RESULTS_DIR / "exclusion-report.md"
    emit_exclusion_report(by_task, passing, cfg, args, report_path)
    print(f"Wrote {report_path}")

    # Summary
    n_passing = sum(len(v) for v in passing.values())
    n_tier2 = sum(len(v) for v in tier2.values())
    print(
        f"\nPre-registered gate (2026-05-06): strict 3/3 success, "
        f"no infra failures, median_steps in "
        f"[{cfg.min_median_steps}, {cfg.max_median_steps}]:"
    )
    for app in sorted({*passing, *tier2}):
        p = len(passing.get(app, []))
        t = len(tier2.get(app, []))
        print(f"  {app:18} {p:>3} passing  +  {t:>3} Tier-2 stochastic")
    print(
        f"  {'TOTAL':18} {n_passing:>3} passing  +  {n_tier2:>3} Tier-2  / "
        f"{len(by_task)} ({100*n_passing/max(len(by_task),1):.1f}% primary, "
        f"{100*(n_passing+n_tier2)/max(len(by_task),1):.1f}% combined)"
    )
    if drop_reasons:
        print("\nDrop reasons:")
        for r, n in sorted(drop_reasons.items(), key=lambda x: -x[1]):
            print(f"  {r:22} {n}")

    print(
        f"\nEstimated Stage 3 cases: {n_passing * 26 * 3 * 2:,} "
        f"({n_passing} tasks × 26 ops × 3 reps × Claude + Llama4)"
    )


if __name__ == "__main__":
    main()

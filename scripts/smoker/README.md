# Smoker Pipeline

> **Purpose**: Stage 1-2 of the 3-stage task expansion plan
> (smoker → filter → manipulate). Identifies which of WebArena's 684
> deployed-app tasks are base-solvable by the Claude Sonnet 4 text-only
> agent, yielding a clean task set for the Stage 3 full AMT experiment.
>
> Model alias `claude-sonnet` → `us.anthropic.claude-sonnet-4-20250514-v1:0`
> (see `litellm_config.yaml`).

## Pipeline

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ Stage 1: Smoker      │     │ Stage 2: Filter      │     │ Stage 3: Manipulate  │
│                      │     │                      │     │                      │
│ 684 tasks × 3 reps   │ ──> │ analyze-smoker.py    │ ──> │ ~300 tasks × 26 ops  │
│ base variant only    │     │ Pre-registered gate  │     │ × 3 reps × 2 models  │
│ text-only agent      │     │ (locked 2026-05-06)  │     │ ≈ 46,800 cases       │
│ Claude Sonnet 4      │     │ - 3/3 strict success │     │                      │
│ 2,052 cases, 2 days  │     │ - 0 infra failures   │     │ Paper §5.1-5.3       │
│                      │     │ - steps in [3, 25]   │     │ (breadth tier)       │
│                      │     │ 10-30 min            │     │                      │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
                                    │
                                    ├──→  passing-tasks.json    (primary set, Stage 3)
                                    ├──→  passing-tier2.json    (stochastic-base ref)
                                    └──→  exclusion-report.md   (paper-ready table)

Full methodology + pre-registration record:
  docs/analysis/task-selection-methodology.md
```

## Files

| File | Purpose |
|---|---|
| `generate-smoker-configs.py` | Generates `config-smoker-shard-{a,b}.yaml` from `test.raw.json` |
| `analyze-smoker.py` | Applies pre-registered gate, emits Stage 3 config + exclusion report + Tier-2 reference |
| `gate-quick.py` | Diagnostic: count tasks per bucket (3/3 consistent / drift / 2/3 / 1/3 / 0/3) |
| `gate-complexity.py` | Diagnostic: step-distribution of 3/3-passing set (used to justify min_median_steps=3) |
| `show-drift.py` | Diagnostic: show raw answers for 3/3-success-but-drift tasks |
| `smoker-task-ids.json` | Reference list of all 684 task IDs per app |
| `../../config-smoker-shard-a.yaml` | Generated — shopping_admin + shopping (374 tasks) |
| `../../config-smoker-shard-b.yaml` | Generated — reddit + gitlab (310 tasks) |
| `../../docs/smoker-docker-reset.md` | Docker reset strategy for the smoker run |
| `../../docs/analysis/task-selection-methodology.md` | **Pre-registration record + paper methodology** |

## Running

### 1. Regenerate configs (only if webarena package changed)

```bash
python3.11 scripts/smoker/generate-smoker-configs.py
```

### 2. Reset WebArena containers (critical — see docs/smoker-docker-reset.md)

```bash
# On the WebArena EC2
for c in shopping shopping_admin forum gitlab; do docker restart $c; done
sleep 60
for port in 7770 7780 9999 8023; do
  curl -sfI http://localhost:$port | head -1
done
```

### 3. Launch smoker shards

```bash
# On Platform EC2, account A
bash scripts/launchers/launch-smoker-shard-a.sh

# On Platform EC2, account B (parallel)
bash scripts/launchers/launch-smoker-shard-b.sh
```

Shard A finishes first (~20h) since shard B has more tasks but similar
rate — both roughly hit $150 each.

### 4. Download + analyze

```bash
# On local machine
bash scripts/data-pipeline/experiment-download.sh --latest smoker-shard-a
bash scripts/data-pipeline/experiment-download.sh --latest smoker-shard-b

python3.11 scripts/smoker/analyze-smoker.py
```

Outputs:

- `results/smoker/filter-summary.csv` — one row per task with stats + drop reason + failure-mode signals (bridge crashes, context-window exceeded, admin login failures, etc.)
- `results/smoker/passing-tasks.json` — final task list `{app: [task_id, ...]}`
- `results/smoker/exclusion-report.md` — **paper-ready** markdown report: per-category counts, per-task rationale, and a drop-in narrative paragraph for the task-selection appendix
- `config-manipulation-filtered.yaml` — ready-to-run Stage 3 config

### 5. Review the results

Open `results/smoker/exclusion-report.md` first — that's the
paper-ready narrative. Then `results/smoker/filter-summary.csv` for
per-task detail.

**Gate parameters are pre-registered and locked** (see
`docs/analysis/task-selection-methodology.md`). Do not adjust after
Stage 3 data has been collected. The defaults (`--min-median-steps 3`,
`--max-median-steps 25`, strict 3/3) are the pre-registered values.

If you need to run exploratory sensitivity analysis (e.g., "how would
the count change under a 2/3 majority gate?"), do this **separately**
as a paper robustness check, not as the primary gate:

```bash
# Exploratory only — paper reports the pre-registered default
python3.11 scripts/smoker/analyze-smoker.py \
    --min-median-steps 5 \
    --summary-csv /tmp/sensitivity.csv \
    --passing-json /tmp/sensitivity-pass.json \
    --output-config /tmp/sensitivity-config.yaml \
    --tier2-json /tmp/sensitivity-tier2.json
```

## Answer extraction

The filter reads each case's trace and walks steps backward to find
the last `send_msg_to_user(...)` action. Payload is extracted for the
per-task CSV columns. BrowserGym's evaluator judges success
independently of any answer normalization on our side; we do not
gate on answer-consistency (see methodology doc §5.3).

## What the filter catches

**Pre-registered gate (locked 2026-05-06).** Full methodology:
`docs/analysis/task-selection-methodology.md`.

Tasks are attributed to the **first** criterion they fail, in this
priority order (infrastructure ranked ahead of difficulty so the
paper cannot mislabel a Magento timeout as "Claude can't solve this"):

| Priority | Drop reason | Meaning | Typical cause |
|---|---|---|---|
| 1 | `incomplete_reps` | <3 reps in data | Shard crashed or early kill |
| 2 | `context_window_exceeded` | A11y tree exceeds Claude's context | Magento admin grid pages (Customers, Orders, Products) |
| 3 | `bridge_crash` | BrowserGym `env.reset()` crashed | Multi-URL task whose first URL times out |
| 4 | `admin_login_failed` | Magento admin login timed out | Magento admin login form flakiness |
| 5 | `goto_timeout` | `Page.goto` timed out on start_url | Slow-loading Magento product page |
| 6 | `chromium_crash` | Target crashed mid-task | Chromium tab OOM / JS crash |
| 7 | `harness_errors` | Any other bridge error | Transient infrastructure |
| 8 | `stochastic_base` | <3/3 reps succeeded | Non-deterministic baseline (retained as Tier-2 reference) |
| 9 | `trivial_task` | Median successful step count < 3 | Answer visible on landing page; a11y tree cannot matter |
| 10 | `step_budget` | Median successful step count > 25 | Task brittle at step limit |

**Answer-consistency check removed** — BrowserGym's evaluator is
authoritative; paraphrase variation was false-rejecting legitimate
tasks in pilot.

### Two outputs, two purposes

- `results/smoker/passing-tasks.json` — **Primary set** (Stage 3
  manipulation task set). Passes all gates above.
- `results/smoker/passing-tier2.json` — **Tier-2 reference set**
  (stochastic-base tasks, < 3/3). Retained for supplementary
  analysis; NOT run through Stage 3 manipulation.

### Conservative-gate argument

Each exclusion criterion **reduces** the observed manipulation drop:

- Removing trivial tasks removes 0-pp cases (manipulation cannot
  affect a task solved without navigation)
- Removing stochastic-base tasks removes baseline-noise cases
  (cannot distinguish manipulation from baseline variability)
- Removing infrastructure failures removes artifacts of
  benchmark × model interaction

Reported Stage 3 drops are therefore **lower bounds** of the true
effect on the WebArena task population.

Expected final yield: **~250-350 tasks** for Stage 3 primary set,
+ ~150-200 in Tier-2 reference. Depends on drop-rate distribution
from the live smoker; pre-completion estimate is wide because
Magento state drift and baseline stochasticity vary across accounts.


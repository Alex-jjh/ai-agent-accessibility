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
│ 684 tasks × 3 reps   │ ──> │ analyze-smoker.py    │ ──> │ ~80 tasks × 26 ops   │
│ base variant only    │     │ - majority vote ≥2/3 │     │ × 3 reps × 2 models  │
│ text-only agent      │     │ - answer consistent  │     │ ≈ 12,000 cases       │
│ Claude Sonnet 4      │     │ - median steps ≤ 25  │     │                      │
│ 2,052 cases, 2 days  │     │ - no harness errors  │     │ (separate roadmap    │
│                      │     │ 10-30 min            │     │  after Stage 2 done) │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `generate-smoker-configs.py` | Generates `config-smoker-shard-{a,b}.yaml` from `test.raw.json` |
| `analyze-smoker.py` | Applies filter gate, emits `config-manipulation-filtered.yaml` |
| `../smoker-task-ids.json` | Reference list of all 684 task IDs per app |
| `../../config-smoker-shard-a.yaml` | Generated — shopping_admin + shopping (374 tasks) |
| `../../config-smoker-shard-b.yaml` | Generated — reddit + gitlab (310 tasks) |
| `../../docs/smoker-docker-reset.md` | Docker reset strategy for the smoker run |

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

### 5. Review and tune

Open `results/smoker/filter-summary.csv`. Check the drop-reason
distribution. Common tuning knobs:

```bash
# Looser gate (1/3 success, keep more tasks)
python3.11 scripts/smoker/analyze-smoker.py --min-success 1

# Skip answer-consistency check (if drift false-positives dominate)
python3.11 scripts/smoker/analyze-smoker.py --no-answer-check

# Allow longer tasks
python3.11 scripts/smoker/analyze-smoker.py --max-median-steps 28
```

Default (`--min-success 2 --max-median-steps 25 --answer-check`) is the
tight gate from `docs/smoker-docker-reset.md`.

## What the filter catches

| Drop reason | Meaning | Typical cause |
|---|---|---|
| `context_window_exceeded` | A11y tree exceeds Claude's context | Magento admin grid pages (Customers, Orders, Products) |
| `bridge_crash` | BrowserGym `env.reset()` crashed | Multi-URL task whose first URL times out |
| `admin_login_failed` | Magento admin login timed out | Magento admin login form flakiness |
| `goto_timeout` | `Page.goto` timed out on start_url | Slow-loading Magento product page |
| `chromium_crash` | Target crashed mid-task | Chromium tab OOM / JS crash |
| `insufficient_success` | <2/3 reps succeeded | Task too hard for Claude base |
| `answer_drift` | Different literal answers across successful reps | DB state drift between reps |
| `step_budget` | Median steps > 25 | Task squeaks through at step limit — brittle |
| `harness_errors` | Any rep hit bridge/harness error | Transient network / process failure |
| `incomplete_reps` | <3 reps in data | Shard didn't complete; resume or re-run |

Infrastructure failures are ranked **ahead of** `insufficient_success`
so the paper's exclusion report attributes a dropped task to the root
cause (e.g., context-window overflow) rather than to the downstream
symptom (low success rate).

Expected final yield: **60-120 tasks** (literature suggests ~30-40%
base solvability for Claude Sonnet 4 on WebArena; the answer-consistency
gate and infra filters trim another ~10-20%).

## Answer extraction notes

The filter reads each case's trace and walks steps backward to find
the last `send_msg_to_user(...)` action. Payload is extracted and
normalized (lowercase, collapsed whitespace, stripped trailing
punctuation) before comparison. This catches agents that produce
semantically identical but literally different answers across reps.

If the filter flags a task for drift where the answers are actually
equivalent (e.g. `"25.99"` vs `"$25.99"`), tune the extraction by
editing `_normalize_answer()` in `analyze-smoker.py` rather than
manually overriding the drop.

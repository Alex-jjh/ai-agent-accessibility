# Experiment Data Schema — Three-Layer Architecture

## Design Principles

Following best practices from WebArena-Verified (structured evaluators), SWE-bench
(predictions + trajectories + results separation), and CHI open science guidelines
(deidentified data + metadata + code).

Three layers, each serving a different analysis need:

## Layer 1: `results/combined-experiment.csv` (~1,040 rows, ~50KB)

**Purpose**: Primary data source for all statistical analysis. One row per case.
Every table and figure in the paper is generated from this file.

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `case_id` | string | Unique identifier | `ecommerce:low:23:text-only:claude:0:1` |
| `experiment` | string | Source experiment | `pilot4-full`, `expansion-claude`, `expansion-llama4`, `expansion-som`, `expansion-cua` |
| `task_id` | int | WebArena task ID | `23` |
| `app` | string | WebArena application | `ecommerce`, `ecommerce_admin`, `reddit`, `gitlab` |
| `app_short` | string | Short app name | `ecom`, `admin`, `reddit`, `gitlab` |
| `variant` | string | Accessibility variant | `low`, `medium-low`, `base`, `high` |
| `variant_ordinal` | int | Variant as ordinal (for CLMM) | `0`, `1`, `2`, `3` |
| `agent_type` | string | Agent observation mode | `text-only`, `vision-only`, `cua` |
| `model` | string | LLM model | `claude-sonnet`, `llama4-maverick` |
| `model_family` | string | Model family (for grouping) | `anthropic`, `meta` |
| `rep` | int | Repetition number (1-5) | `3` |
| `success` | bool | Task completed correctly | `true`, `false` |
| `outcome` | string | Detailed outcome | `success`, `failure`, `timeout`, `partial_success` |
| `reward` | float | BrowserGym reward (0.0 or 1.0) | `1.0` |
| `total_steps` | int | Number of agent steps | `7` |
| `total_tokens` | int | Total LLM tokens consumed | `134522` |
| `duration_ms` | int | Wall-clock duration (ms) | `85000` |
| `final_answer` | string | Agent's submitted answer (truncated to 200 chars) | `Lily Potter` |
| `failure_type` | string | Auto-classified failure type (null if success) | `F_SIF`, `F_COF`, `F_REA`, `F_SOM_PHANTOM` |
| `failure_domain` | string | Failure domain | `a11y`, `model`, `platform`, `task`, `som` |
| `task_template` | int | WebArena template ID | `222` |
| `task_intent` | string | Task intent (truncated) | `Tell me the count of reviewers...` |
| `nav_depth` | string | Navigation depth category | `shallow`, `medium`, `deep` |
| `eval_type` | string | WebArena evaluation type | `string_match`, `exact_match` |
| `dom_changes` | int | Number of DOM changes applied by variant | `135` |
| `task_feasible` | bool | Is task feasible at this variant? | `true`, `false` |

### Derived columns (computed, not stored)

These are computed in analysis scripts, not in the CSV:
- `success_rate`: aggregate per cell (task × variant × agent)
- `token_inflation`: ratio vs base variant
- `a11y_gradient`: base_rate - low_rate per agent

### Notes

- `variant_ordinal`: low=0, medium-low=1, base=2, high=3 (for ordinal regression)
- `task_feasible`: annotated per task×variant based on trace analysis
  (e.g., ecom:23 low = infeasible because tabpanel ARIA broken)
- `failure_type`: uses the taxonomy from src/classifier/taxonomy/classify.ts
  plus SoM-specific types (F_SOM_PHANTOM, F_SOM_MISREAD, F_SOM_FILL, F_SOM_EXPLORE, F_SOM_NAV)
- `final_answer`: truncated to 200 chars to keep CSV manageable; full answer in Layer 2

---

## Layer 2: `results/trace-summaries.jsonl` (~1,040 lines, ~5MB)

**Purpose**: Per-case trace summaries for qualitative analysis. Supports failure
attribution, action sequence analysis, and token breakdown without needing full traces.

### Schema (one JSON object per line)

```json
{
  "case_id": "ecommerce:low:23:text-only:claude:0:1",
  "experiment": "pilot4-full",
  "task_id": 23,
  "variant": "low",
  "agent_type": "text-only",
  "model": "claude-sonnet",
  "rep": 1,
  "success": false,
  "outcome": "failure",
  "total_steps": 15,
  "total_tokens": 172000,
  "duration_ms": 120000,
  "final_answer": "the review content is not accessible on this page",
  "failure_type": "F_SIF",
  "action_sequence": ["click(557)", "click(1557)", "scroll(0,500)", "scroll(0,500)", "..."],
  "step_tokens": [8500, 12000, 15000, "..."],
  "step_durations_ms": [3200, 2800, 2500, "..."],
  "click_failures": 3,
  "fill_failures": 0,
  "goto_count": 1,
  "max_consecutive_click_failures": 2,
  "observation_sizes": [4500, 8200, 8200, "..."],
  "max_observation_size": 168657,
  "variant_dom_changes": 135,
  "variant_dom_hash_changed": true,
  "pages_visited": ["http://10.0.1.50:7770/zoe-product.html"],
  "error_messages": ["element is not visible", "Could not find element with bid 1557"]
}
```

### Notes

- `action_sequence`: list of action strings (truncated to first 30 steps)
- `step_tokens`: per-step token consumption
- `observation_sizes`: character count of each step's observation
- `pages_visited`: unique URLs visited during the trace
- `error_messages`: unique error messages encountered

---

## Layer 3: Raw Traces (existing JSON files, ~375MB)

**Purpose**: Complete trace data for deep-dive analysis. Contains full a11y tree
observations, agent reasoning text, and (for CUA) screenshot metadata.

**Location**: `data/` directories (synced via S3, not in git)
**Format**: One JSON file per case, existing format from BrowserGym bridge

---

## Task Metadata: `results/task-metadata.csv` (13-20 rows)

**Purpose**: Per-task metadata for joining with results.

| Column | Type | Description |
|--------|------|-------------|
| `task_id` | int | WebArena task ID |
| `app` | string | Application |
| `template_id` | int | WebArena template ID |
| `intent` | string | Full task intent text |
| `eval_type` | string | Evaluation type |
| `expected_answer` | string | Ground truth answer |
| `nav_depth` | string | shallow/medium/deep |
| `page_type` | string | Product page, admin grid, forum, etc. |
| `interaction_type` | string | read, search, filter, navigate |
| `low_feasible` | bool | Is task feasible at low variant? |
| `ml_feasible` | bool | Is task feasible at medium-low? |
| `selection_phase` | string | pilot4, expansion-phase1, expansion-phase2 |

---

## Experiment Metadata: `results/experiment-metadata.csv` (6 rows)

**Purpose**: Per-experiment metadata for provenance.

| Column | Type | Description |
|--------|------|-------------|
| `experiment` | string | Experiment name |
| `date` | string | Run date (ISO 8601) |
| `model_id` | string | Bedrock model ID |
| `agent_type` | string | Observation mode |
| `tasks` | string | Comma-separated task IDs |
| `variants` | string | Comma-separated variant names |
| `reps` | int | Repetitions per cell |
| `total_cases` | int | Total cases |
| `bridge_version` | string | Git commit hash of bridge code |
| `variant_script_hash` | string | SHA-256 of apply-low.js etc. |

---

## Statistical Analysis Outputs: `results/stats/`

Generated by analysis scripts, not manually created:

- `chi_square_tests.csv` — All pairwise χ² tests (low vs base, etc.)
- `effect_sizes.csv` — Cramér's V, odds ratios, confidence intervals
- `clmm_results.csv` — Cumulative Link Mixed Model output
- `token_analysis.csv` — Per-variant token statistics
- `failure_attribution.csv` — Failure type × variant × agent breakdown

---

## Directory Structure

```
results/
  combined-experiment.csv      # Layer 1: primary analysis data
  trace-summaries.jsonl        # Layer 2: per-case trace summaries
  task-metadata.csv            # Task-level metadata
  experiment-metadata.csv      # Experiment-level provenance
  stats/                       # Generated statistical outputs
    chi_square_tests.csv
    effect_sizes.csv
    clmm_results.csv
    token_analysis.csv
    failure_attribution.csv
data/                          # Layer 3: raw traces (S3, not git)
  pilot4-full/
  pilot4-cua/
  expansion-claude/
  expansion-llama4/
  expansion-som/
  expansion-cua/
```

## Reproducibility Contract

Given `results/combined-experiment.csv` + `analysis/*.py`, any researcher can:
1. Reproduce all tables and figures in the paper
2. Run additional statistical tests
3. Verify our claims without needing the 375MB raw traces

Given `results/trace-summaries.jsonl`, a researcher can additionally:
4. Verify failure classifications
5. Analyze action sequences and token patterns
6. Identify specific failure examples

Given `data/` (raw traces from S3/Zenodo), a researcher can additionally:
7. Read full agent observations and reasoning
8. Re-run failure classification with different criteria
9. Extract new features not in our summary

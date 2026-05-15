# Phase 1 — Composite Variant Study (N=1,040)

> **Purpose**: establish the causal relationship between accessibility
> degradation and agent failure, using composite variant bundles.
> **Status (2026-05-15)**: data frozen 2026-04-14. Used as motivator (§5.1)
> in the paper; superseded by Phase 6 Stage 3 as the primary breadth dataset.

## Design matrix

```
4 variants  ×  13 tasks  ×  5 reps  ×  4 agent-model cells  =  1,040 cases
```

| Dimension | Values |
|---|---|
| Variants | low, medium-low, base, high (composite operator bundles) |
| Tasks | 13 hand-selected from WebArena (4 apps, 11 templates, 5 shallow / 5 medium / 3 deep) |
| Reps | 5 per cell (LiteLLM @ temperature=0.0) |
| Agent × Model cells | Claude × {text-only, SoM, CUA} + Llama 4 × text-only |

**Variant composition** (paper Appendix `tab:low-ops`, `tab:ml-ops`, `tab:high-ops`):

| Variant | Operators applied | Source script |
|---|---|---|
| `low` | L1–L13 (all 13 Low operators) | `src/variants/patches/inject/apply-low.js` |
| `medium-low` | ML1–ML3 | `src/variants/patches/inject/apply-medium-low.js` |
| `base` | (no-op control) | (no patch) |
| `high` | H1–H8 + H5a/b/c | `src/variants/patches/inject/apply-high.js` |

## On-disk data (~383 MB total)

| Directory | Cases | Model × agent | Date |
|---|--:|---|---|
| `data/pilot4-full/` | 240 | Claude × text+SoM (6 tasks × 4 variants × 2 archs × 5 reps) | 2026-04-07 |
| `data/pilot4-cua/` | 120¹ | Claude × CUA (6 tasks × 4 variants × 5 reps) | 2026-04-08 |
| `data/expansion-claude/` | 140 | Claude × text-only (7 new tasks × 4 variants × 5 reps) | 2026-04-13 |
| `data/expansion-llama4/` | 260 | Llama 4 × text-only (13 tasks × 4 variants × 5 reps) | 2026-04-13 |
| `data/expansion-som/` | 140 | Claude × SoM (7 new tasks × 4 variants × 5 reps) | 2026-04-14 |
| `data/expansion-cua/` | 140 | Claude × CUA (7 new tasks × 4 variants × 5 reps) | 2026-04-14 |
| **Total** | **1,040** | | |

¹ Raw filesystem holds 121 files for `pilot4-cua` because `ecommerce_high_23`
has 6 attempts on disk (one was a hung-bridge retry from a different run UUID).
`analysis/lib/load.py:_select_largest_uuid` picks the UUID with the most files,
yielding 120 — matching `results/combined-experiment.csv` (1,040 rows).

### Per-experiment file layout

```
data/<experiment>/<run-uuid>/cases/<case>.json   # flat case JSON, full trace inline
data/<experiment>/track-a/runs/<uuid>/cases/<case>/
    trace-attempt-1.json                          # same trace, per-case dir layout
    scan-result.json                              # scanner Tier 1+2 metrics
data/<experiment>/exports/{experiment-data,failure-classifications,
                           scan-metrics,trace-summaries}.csv
data/<experiment>/<phase>.log                     # runner stdout
```

Both layouts are populated; **both are read by different downstream scripts**
(see `docs/data-inventory.md` §4 for the matrix).

## Derived artefacts (`results/`)

| File | Producer | Schema |
|---|---|---|
| `results/combined-experiment.csv` | `analysis/export_combined_data.py` | 1,040 rows × 26 columns (case_id, experiment, task_id, app, variant, agent_type, model, success, …) |
| `results/trace-summaries.jsonl` | same | 1,040 lines, one JSON object per case |
| `results/task-metadata.csv` | same | per-task: template id, intent, navigation depth |
| `results/experiment-metadata.csv` | same | per-run summary |
| `results/stats/{descriptive,gee_models,interaction_tests,primary_tests,…}.csv` | `analysis/run_statistics.py` | descriptive + Cochran-Armitage + GEE per agent-model |
| `results/bootstrap_decomposition.csv` | `analysis/bootstrap_decomposition.py` | text/CUA/semantic pathway CIs |
| `results/breslow_day_cross_model.txt` | `analysis/breslow_day.py` | OR homogeneity Claude vs Llama 4 |

## How to audit

```sh
# Quick check (CSV totals + per-variant rates)
make audit-composite

# Full re-export from raw JSON + verify
make export-data
make verify-numbers          # legacy alias, composite-only
```

Verifier asserts:
- `len(results/combined-experiment.csv) == 1040`
- per-experiment counts (240/120/140/260/140/140)
- Claude × text-only success rates per variant: low 38.5%, medium-low 100.0%, base 93.8%, high 89.2%
- Llama 4 × text-only: 36.9% / 61.5% / 70.8% / 75.4%
- CUA × Claude: 58.5% / 98.5% / 93.8% / 95.4%
- SoM × Claude: 4.6% / 27.7% / 27.7% / 32.3%

Tolerances: ±0.005 (rate fraction). Constants in `analysis/_constants.py:COMPOSITE_*`.

## Paper sections

- **§5.1 Composite Variant Effects** — main table (`tab:main-results`) and the
  narrative around the 55-pp Low collapse, asymmetric dose-response, and
  causal-decomposition figure (`figure5_causal_decomposition`).
- **§5.1 Token inflation** — Wilcoxon p < 1e-6, low ~97K vs base ~40K (`figure6_token_violin`).
- **§5.6 Failure-type distribution** — composite phase only.
- **§5.5 Vision agent findings / phantom bids** — SoM 27.7% baseline → 4.6% Low.

## Known caveats

- **Composite, not per-operator.** Cannot attribute the 55-pp drop to any
  single operator. Phase 4 (Mode A) and Phase 6 (Stage 3) decompose it.
- **CUA composite baseline is clean** (93.8%); Mode A CUA baseline is
  depressed (48.2%) due to task-architecture mismatch on 5 of 13 tasks.
  Paper uses **composite** CUA contrast for the primary decomposition.
- **No GT corrections applied.** Tasks 41/198/293 only entered the corpus
  with Mode A; composite phase predates the GT-correction protocol.

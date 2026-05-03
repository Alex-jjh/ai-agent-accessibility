# Analysis Engine (Module 6) — Python Statistical Analysis

Python-based statistical analysis for the AI Agent Accessibility Platform.
Consumes CSV exports produced by the TypeScript data export layer (Modules 1–5).

## Relationship with `scripts/amt/`

This directory and `scripts/amt/` serve different purposes:

| Concern | `analysis/` | `scripts/amt/` |
|---------|-------------|----------------|
| Statistical modeling (CLMM, GEE, GLMM) | ✅ primary | — |
| Cross-model tests (Breslow-Day, bootstrap) | ✅ primary | — |
| Visual equivalence analysis | ✅ primary | — |
| Python package with `requirements.txt` | ✅ yes | — |
| AMT operator TypeScript tooling | — | ✅ primary |
| AMT DOM audit (12-dim signatures) | — | ✅ primary |
| Ground truth corrections + paper audit | — | ✅ primary |
| Mode A / C.2 case-level analysis | — | ✅ primary |

Both are **git-tracked, paper-critical**. They call into each other:
- `scripts/amt/audit-operator.ts` uses `analysis/ssim_helper.py`
- Mode A + C.2 CSV outputs from `scripts/amt/` feed into `analysis/` for
  statistical modeling

## Directory Structure

```
analysis/
├── __init__.py              # Python package marker
├── README.md                # this file
├── requirements.txt         # statsmodels, pymer4, sklearn, shap, ...
├── Copy of FinalData.xlsx   # Griffith et al. raw data (ICPSR 183081)
├── models/                  # CLMM + Random Forest (reusable modeling)
│   ├── primary.py           #   CLMM/GEE for Req 13 (primary a11y effect)
│   ├── secondary.py         #   Random Forest + SHAP for Req 14
│   ├── test_primary.py
│   └── test_secondary.py
├── viz/                     # Paper-ready figure code
│   ├── figures.py
│   └── test_figures.py
├── archive/                 # Historical pilot + expansion scripts
│   └── (see archive/README.md)
│
├── <active analysis scripts — see taxonomy below>
```

## Active Script Taxonomy

### Paper-wide statistics
- `run_statistics.py` — Main statistical runner (orchestrates all tests on composite variants)
- `compute_primary_stats.py` — Primary (Fisher/chi²) + secondary (Cochran-Armitage) tests
- `glmm_analysis.py` — GLMM mixed-effects via statsmodels GEE + BinomialBayesMixedGLM
- `amt_statistics.py` — **AMT paper tests** (individual operators + composition + cross-model)
  - §5.1: Fisher's exact per operator, Holm-Bonferroni corrected
  - §5.3: Breslow-Day cross-model OR homogeneity
  - §5.4: Compositional additivity departure tests

### Cross-model replication
- `breslow_day.py` — Breslow-Day test for odds-ratio homogeneity (Claude vs Llama 4)
- `bootstrap_decomposition.py` — Bootstrap CIs for pathway decomposition + Holm-Bonferroni

### Causal decomposition & sensitivity
- `majority_vote_sensitivity.py` — Robustness check: aggregate 5 reps to majority vote
- `cua_failure_trace_validation.py` — Validates CUA low-variant failures against link→span signature

### Data export & verification
- `export_combined_data.py` — Reads all 7,284 traces → `results/combined-experiment.csv`
- `verify_all_data_points.py` — Asserts every number in `paper/key-numbers.md` against CSV
- `paper_consistency_audit.py` — Scans paper/*.tex for numerical claims
- `generate_results_tables.py` — Generate LaTeX tables from CSV

### Metrics & helpers
- `semantic_density.py` — Novel metric: interactive_nodes / total_a11y_tokens
- `test_semantic_density.py` — Unit tests
- `ssim_helper.py` — Structural Similarity Index via scikit-image (subprocess-callable)

### Visual equivalence (Phase 7)
- `visual_equivalence_analysis.py` — SSIM/pHash/MAD analysis per-URL, per-patch
- `visual_equivalence_gallery.py` — Human review HTML generator

### Human baseline (A11y-CUA + Griffith)
- `griffith_triangulation.py` — Derives per-participant metrics from Griffith et al. (2022)

## Setup

```bash
cd analysis
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running from the repo root (via Makefile)

```bash
make verify-numbers   # run verify_all_data_points.py
make export-data      # re-export combined CSV
make run-stats        # full statistical analysis
make all              # all three in sequence
```

## CLMM Implementation: Decision Tree

Track A requires a mixed-effects model with an ordinal predictor
(`a11y_variant_level`: Low / Medium-Low / Base / High) and binary or ordinal
outcome (`agent_success`). The ideal model is a Cumulative Link Mixed Model
(CLMM) with random intercepts for app and LLM backend.

Three implementation paths are available, in order of preference:

### Path 1 — `pymer4` (preferred)

`pymer4` is a Python wrapper around R's `lme4` package via `rpy2`.

**Pros:** Full mixed-effects logistic regression with ordinal coding; R formula
syntax (`success ~ variant + (1|app) + (1|llm_backend)`); well-tested.

**Cons:** Requires R + `lme4` R package.

```bash
pip install pymer4
python -c "from pymer4.models import Lmer; print('pymer4 OK')"
```

### Path 2 — `statsmodels` GEE fallback

If `pymer4` fails, use `statsmodels.GEE` with ordinal contrast coding.

**Pros:** Pure Python.
**Cons:** Population-averaged (not subject-specific). Must disclose in paper.

### Path 3 — R + `ordinal::clmm()` via `rpy2` (last resort)

Only if reviewers require true CLMM with ordinal DV.

## Key Design Decisions

- **Primary IVs are criterion-level feature vectors**, not Composite_Score
  (which is supplementary for interpretability only).
- **Sensitivity analysis** fits models with Tier 1 only, Tier 2 only, and
  composite to assess robustness.
- **Vision agent is a control condition.** Interaction tests check whether
  Text-Only shows a11y gradient while Vision shows null gradient — strongest
  evidence for A11y Tree as the causal mechanism.
- **Post-hoc power analysis** runs after pilot (20 sites) to determine if
  N=50 is sufficient for Track B.

## Input Data

| File | Contents |
|------|----------|
| `results/combined-experiment.csv` | One row per case: app, variant, agent, outcome |
| `results/amt/*.csv` | AMT signature matrices (from `scripts/amt/`) |
| `data/<experiment>/cases/*.json` | Raw case JSON (primary source of truth) |

## Requirements Traceability

| Component | Requirements |
|-----------|-------------|
| `models/primary.py` | 13.1, 13.2, 13.3, 13.4, 13.5, 8.6 |
| `models/secondary.py` | 14.1, 14.2, 14.3, 14.4 |
| `viz/figures.py` | 13.3, 14.2, 14.4 |

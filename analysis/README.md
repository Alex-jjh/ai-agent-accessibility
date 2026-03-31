# Analysis Engine (Module 6)

Python-based statistical analysis for the AI Agent Accessibility Platform.
Consumes CSV exports produced by the TypeScript data export layer (Modules 1–5).

## Directory Structure

```
analysis/
├── __init__.py
├── requirements.txt
├── README.md
├── models/
│   ├── __init__.py
│   ├── primary.py      # CLMM + GEE for primary research question (Req 13)
│   └── secondary.py    # Random Forest + SHAP for secondary question (Req 14)
└── viz/
    ├── __init__.py
    └── figures.py       # Paper-ready figures for CHI/ASSETS submission
```

## Setup

```bash
cd analysis
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## CLMM Implementation: Decision Tree

Track A requires a mixed-effects model with an ordinal predictor
(`a11y_variant_level`: Low / Medium-Low / Base / High) and binary or ordinal
outcome (`agent_success`). The ideal model is a Cumulative Link Mixed Model
(CLMM) with random intercepts for app and LLM backend.

Three implementation paths are available, in order of preference:

### Path 1 — `pymer4` (preferred)

`pymer4` is a Python wrapper around R's `lme4` package. It provides
`Lmer`/`Lm` classes that call R under the hood via `rpy2`.

**Pros:** Full mixed-effects logistic regression with ordinal coding; familiar
R formula syntax (`success ~ variant + (1|app) + (1|llm_backend)`); well-tested
in published research.

**Cons:** Requires a working R installation and the `lme4` R package. Install
can fail on systems without R.

**Install check:**

```bash
pip install pymer4
python -c "from pymer4.models import Lmer; print('pymer4 OK')"
```

If this succeeds, use `pymer4` for Track A CLMM.

### Path 2 — `statsmodels` GEE fallback

If `pymer4` installation fails (no R runtime available), fall back to
`statsmodels.genmod.generalized_estimating_equations.GEE` with ordinal contrast
coding for the variant predictor.

**Pros:** Pure Python, no R dependency; GEE handles correlated observations
(repeated measures within apps/backends) via exchangeable or independent
working correlation structures.

**Cons:** GEE is a population-averaged model, not a subject-specific
mixed-effects model. It estimates marginal effects rather than conditional
effects. This distinction must be acknowledged in the paper:

> "We used GEE with logit link and exchangeable working correlation as a
> fallback for CLMM, because the R runtime was unavailable. GEE estimates
> population-averaged effects; conditional (subject-specific) effect sizes
> may differ. We coded the ordinal variant predictor using polynomial
> contrasts to preserve the ordered nature of accessibility levels."

**Implementation:** Use `statsmodels.genmod.generalized_estimating_equations.GEE`
with `family=Binomial()`, `cov_struct=Exchangeable()`, and polynomial contrast
coding for the 4-level ordinal predictor.

### Path 3 — R + `ordinal` package + `rpy2` (last resort)

If `pymer4` is insufficient for the paper's statistical claims (e.g., the
reviewers require a true CLMM with ordinal DV for three-level outcome
failure/partial/success), install R directly and use the `ordinal` R package
via `rpy2`.

**Pros:** True CLMM via `ordinal::clmm()` — the gold standard for ordinal
mixed-effects regression.

**Cons:** Heaviest dependency footprint (full R installation + R packages +
`rpy2` bridge). More complex to set up and maintain.

**Install:**

```bash
# Install R (platform-specific)
# Then:
pip install rpy2
Rscript -e 'install.packages("ordinal")'
python -c "import rpy2.robjects as ro; ro.r('library(ordinal)'); print('R+ordinal OK')"
```

Only pursue this path if Path 1 fails AND the paper requires ordinal DV
modeling that GEE cannot provide.

## Key Design Decisions

- **Primary IVs are criterion-level feature vectors**, not Composite_Score.
  The composite is supplementary for interpretability reporting only.
- **Sensitivity analysis** fits models with Tier 1 only, Tier 2 only, and
  the supplementary composite to assess robustness.
- **Vision agent is a control condition.** The `interaction_effect()` test
  checks whether Text-Only agents show a strong a11y gradient while Vision
  agents show a weak/null gradient — the strongest evidence for the A11y Tree
  as the causal mechanism.
- **Post-hoc power analysis** runs after the pilot (20 sites) to determine
  if N=50 is sufficient for Track B's target effect size.

## Input Data

The Analysis Engine reads CSV files exported by the TypeScript platform:

| File | Contents |
|------|----------|
| `experiment-data.csv` | One row per test case: app, variant, agent config, outcome |
| `scan-metrics.csv` | Tier 1 + Tier 2 metrics per scan |
| `failure-classifications.csv` | Auto-classified failure types with confidence |
| `trace-summaries.csv` | Aggregated action trace statistics |

## Requirements Traceability

| Component | Requirements |
|-----------|-------------|
| `models/primary.py` | 13.1, 13.2, 13.3, 13.4, 13.5, 8.6 |
| `models/secondary.py` | 14.1, 14.2, 14.3, 14.4 |
| `viz/figures.py` | 13.3, 14.2, 14.4 |

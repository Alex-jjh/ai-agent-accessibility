# Reproducibility Statement

> Companion to the paper *Same Barrier, Different Signatures*. This document
> describes the exact steps to reproduce every numerical claim in §4–§5 of
> the paper from raw case JSON files.

## TL;DR

```sh
cd ai-agent-accessibility
make setup           # one-time: venv + deps
# obtain raw data — 14,768 case JSONs + 9,408 PNGs (via DOI archive when published)
make verify-all      # → 100/100 PASS, results/key-numbers.json
make audit-paper     # → 28/28 PASS, ~3 seconds
```

If both commands report PASS, every paper number in §4 + §5 has been
re-derived from raw data and matches the manuscript.

## Hardware / software environment

The findings reproduce on:

- **OS**: macOS 14+ (development); Linux x86-64 (data collection on AWS)
- **Python**: 3.11.x (specified in `analysis/requirements.txt`)
- **Node.js**: ≥ 18 (for the TS scanner / variants / runner modules; not
  required for re-deriving paper numbers)
- **Statistics**: scipy 1.13+, statsmodels 0.14+, pandas 2.0+ (versions
  pinned in `analysis/requirements.txt`)
- **Disk**: ~16 GB for full repo + raw data; ~30 MB for paper-supplementary/
- **Memory**: 8 GB sufficient (no large in-memory aggregates)
- **Wall time**: `make verify-all` finishes in ~30 seconds on a 2023 MacBook Air.

## Step-by-step

### 1. Setup

```sh
git clone <repo>     # or unzip the archived tarball
cd ai-agent-accessibility
make setup           # creates analysis/.venv and pip installs requirements
```

### 2. Obtain raw data

The `data/` directory (~10 GB, 14,768 case JSONs + 9,408 PNGs) is excluded
from the repository for size. Three options to obtain it:

- **Camera-ready archive** (preferred): DOI to be assigned at acceptance.
- **`data.zip`** (~2.9 GB, full snapshot): currently lives on the authors'
  Google Drive; will move to the DOI archive at camera-ready.
- **Subset reproduction**: the four primary CSV exports under `results/`
  (`combined-experiment.csv`, `stage3/per-operator-stage3.csv`, etc.) suffice
  to verify §5 success rates without re-loading raw JSONs. `make verify-all`
  uses these CSVs where it can.

### 3. Verify

```sh
make verify-all      # primary V&V — 100 assertions across 7 stages
```

Expected output:
```
Total: 100 passed, 0 failed across 7 stages
Detail: results/key-numbers.json
```

`make audit-paper` (delegates to `scripts/amt/audit-paper-numbers.py`)
does the **same** work without depending on the V&V framework — useful
as an independent cross-check:

```
AUDIT COMPLETE: 28 passed, 0 failed
```

### 4. Per-stage reproduction

Each phase is independently verifiable:

```sh
make audit-composite      # Phase 1 — N=1,040 composite study
make audit-mode-a         # Phase 2 — N=4,056 Mode A depth
make audit-c2             # Phase 3 — N=2,184 C.2 composition
make audit-dom            # Phase 4 — 26 ops × 12-dim DOM matrix
make audit-smoker         # Phase 5 — task-funnel gate (684 → 48)
make audit-stage3         # Phase 6 — N=7,488 Stage 3 breadth (★ primary)
make audit-stage4b        # Phase 6 — 9,408 SSIM captures
```

### 5. Heavy-weight statistics

For the publication-ready statistics tables and reports:

```sh
python3 analysis/run_statistics.py     # composite descriptive + GEE
python3 analysis/amt_statistics.py     # Mode A + C.2 inferential
python3 analysis/stage3_statistics.py  # Stage 3 inferential
```

Outputs land in `results/{stats,amt,stage3}/`.

### 6. Build supplementary bundle

```sh
bash scripts/maintenance/build-supplementary.sh
```

Outputs land in `paper-supplementary/`.

## What each statistical method underwrites

| Paper claim | Method | Script | Output |
|---|---|---|---|
| Composite Low collapse Z=9.83 | Chi-square Low-vs-rest | `phase1_composite._low_vs_rest_z` | key-numbers.json |
| Cochran-Armitage trend Z=6.635 | CA trend test | `phase1_composite._cochran_armitage_z` | key-numbers.json |
| Token inflation p ≈ 1.3e-4 | Mann-Whitney U | `phase1_composite._wilcoxon_token_log10_p` | key-numbers.json |
| Per-operator Fisher (Holm-corrected) | scipy.fisher_exact + multipletests | `amt_statistics`, `stage3_statistics` | results/{amt,stage3}/per-operator-*.csv |
| Bootstrap pathway CIs (B=2000) | task-level resampling | `bootstrap_decomposition.py` | results/bootstrap_decomposition.csv |
| Breslow-Day cross-model | OR homogeneity test | `lib/stats.breslow_day` | results/breslow_day_cross_model.txt |
| GEE composite β=−1.56 | exchangeable-correlation GEE | `glmm_analysis.py` | results/glmm_model_comparison.csv |
| GEE Mode A β<0 (sign + sig) | same | `amt_statistics.test_gee_mode_a` | key-numbers.json |
| Spearman ρ=0.426 | rank correlation | `phase4._compute_dom_behavior_spearman` | key-numbers.json |
| 15/28 super-additive | binomial test | `amt_statistics.test_compositional_interaction` | key-numbers.json |
| Majority-vote Z=4.005 | per-cell aggregation + chi-square | `majority_vote_sensitivity.py` | results/majority_vote_sensitivity.csv |
| Stage 4b SSIM medians | scikit-image structural_similarity | `scripts/stage3/ssim-analysis.py` | results/stage3/visual-equiv/ssim-per-operator.csv |

12 distinct methods. All except Jonckheere-Terpstra (computed but not
quoted in the paper) and BinomialBayesMixedGLM (computed but not quoted)
have direct verifier assertions.

## Known limitations to reproducibility

- **LLM non-determinism at temperature 0.0**. Bedrock provider-side
  variability creates between-rep variance in 23.1% of composite cells.
  Paper's primary findings preserve under majority-vote aggregation
  (results/majority_vote_sensitivity.csv).
- **Bedrock 429 rate-limit retries**. 36/3,744 Stage 3 Claude cases hit
  a 429; all absorbed by 4-retry loop. Confound localized to L5
  (Spearman ρ=−0.010 across operators); see results/stage3/rate-limit-audit-claude.md.
- **Docker state drift**. Magento + GitLab data drifts under repeated
  agent interactions. Three Mode A tasks (41, 198, 293) corrected
  post-hoc via `analysis/_constants.py:GT_CORRECTIONS`; corrections are
  conservative (accept both old and new ground truth). Stage 3 excluded
  state-mutation tasks via Gate 5 to eliminate this confound class.
- **Two paper claims overstated and corrected** (commits `6198841` paper
  + `1c62f50` ai-agent-accessibility):
  - Wilcoxon token-inflation p was `<10⁻⁶`, now correctly reports
    `≈ 1.3 × 10⁻⁴` per-case Mann-Whitney.
  - Mode A 7-gate convergence was `10/13`, now correctly `5/13` (the 8
    failures are exactly the tasks Mode A's own docs flag as controls).

## Build provenance

This statement was last updated 2026-05-15 against:
- `make verify-all` → 100/100 PASS
- `make audit-paper` → 28/28 PASS
- `pre-archival-2026-05-14` and `pre-vv-2026-05-15` git tags as rollback anchors.

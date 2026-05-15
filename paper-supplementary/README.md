# Paper Supplementary Materials

> Reviewer-facing bundle of derived analysis outputs. All files here are
> **derived** from raw case JSONs in `data/` (excluded for size). Regenerate
> at any time with `bash scripts/maintenance/build-supplementary.sh`.

This bundle accompanies the paper *Same Barrier, Different Signatures: How
Web Accessibility Manipulation Reveals Agent Adaptation and Structural
Criticality* (CHI 2027 submission).

## What's here

### Statistics reports (Markdown)
| File | Source | Paper § |
|---|---|---|
| `statistics-composite.md` | `analysis/run_statistics.py` | §5.1 (Phase 1, N=1,040) |
| `statistics-mode-a-c2.md` | `analysis/amt_statistics.py` | §5.2–§5.4 (Phase 2 + Phase 3) |
| `statistics-stage3.md` | `analysis/stage3_statistics.py` | §5.1–§5.3 (Phase 6 ★ primary) |
| `signature-alignment-report.md` | `analysis/amt_statistics.py` | §5.2 alignment |
| `exclusion-narrative.md` | smoker filter pipeline | §4 task funnel (684 → 48) |

### Per-case / per-operator CSVs
| File | Schema | Paper § |
|---|---|---|
| `per-case-composite.csv` | 1,040 rows × 26 cols (case_id, app, variant, agent, model, success, ...) | §5.1 |
| `per-operator-stage3.csv` | 26 ops × Fisher exact + Wilson CI + drop_pp + p_holm | §5.1 (Stage 3) |
| `dom-signature-matrix.csv` | 26 ops × 12 DOM signature dims | §5.2 + appendix tab:dom-sig |
| `behavioral-signature-matrix.csv` | 26 ops × success rates per (agent, model) | §5.1 |
| `signature-alignment.csv` | 26 ops × DOM-vs-behavior alignment classification | §5.2 |
| `bootstrap-decomposition.csv` | functional / semantic pathway pp + 95% CI (B=2,000) | §5.1 |
| `breslow-day-cross-model.txt` | per-op OR homogeneity Claude vs Llama 4 | §5.3 |
| `glmm-model-comparison.csv` | 4 GEE models (M0–M4) on composite data | §5.1 footnote |
| `majority-vote-sensitivity.csv` | 5-rep → majority-vote aggregation, 208 cells | Appendix § Majority-Vote |
| `ssim-per-operator.csv` | 26 ops × SSIM mean / median / p10–p90 | §4.117 + §5.3 |
| `smoker-passing-tasks.json` | 48 task IDs, grouped by app | §4 task funnel |

### Audit & reproducibility
| File | Contents |
|---|---|
| `key-numbers.json` | Machine-readable output of `make verify-all` (100/100 PASS as of build date) |
| `reproducibility-statement.md` | Full reproducibility instructions (hardware, software, steps) |
| `MANIFEST.txt` | Auto-generated build timestamp + file inventory |

## How to regenerate

```sh
# From repo root, after running the upstream analysis pipeline:
make verify-all                                  # → results/key-numbers.json
python3 analysis/run_statistics.py               # → results/stats/*
python3 analysis/amt_statistics.py               # → results/amt/*
python3 analysis/stage3_statistics.py            # → results/stage3/*
bash scripts/maintenance/build-supplementary.sh  # → paper-supplementary/*
```

Or in one step:

```sh
make pre-submit
```

## What's NOT here

- **Raw case JSONs** — 14,768 files, ~10 GB. Available on request; will be
  uploaded to Zenodo / OSF for camera-ready (DOI placeholder).
- **Stage 4b 9,408 PNGs** — too large; available via the same archive.
- **Paper PDF** — built separately by the authors via `latexmk`.
- **Figures (F1–F11, etc.)** — separate supplementary figure package.

## Known paper-vs-data discrepancies

See `../docs/by-stage/audit-2026-05-15.md` §F. Briefly:
1. Wilcoxon token-inflation `p<10⁻⁶` in v1 paper drafts → corrected
   2026-05-15 to `p ≈ 1.3 × 10⁻⁴` per-case (paper now reports exact value).
2. Mode A GEE β values (paper §5.1 footnote) — direction + significance
   reproduce, exact β differs (1.35 vs 1.95). Documented in `_constants.py`.

All other paper claims trace to `key-numbers.json` and pass `make verify-all`.

## Contact

See parent paper for author contact information.

# Statistical Methods Inventory — AMT Paper

> Single reference for all statistical tests used across the three experimental
> phases. Each entry lists: what it tests, where it's implemented, what data
> it reads, and where the result appears in the paper.

---

## Phase 1: Composite Variant Study (N=1,040)

| Test | H₀ | Script | Data | Paper §  |
|------|-----|--------|------|----------|
| **Binary Low-vs-rest** (Fisher exact) | Low rate = rest rate | `compute_primary_stats.py` | `results/combined-experiment.csv` | §5.1 primary |
| **Cochran-Armitage trend** | No ordinal trend across 4 variants | `compute_primary_stats.py` | same | §5.1 secondary |
| **Jonckheere-Terpstra** | No ordered alternative | `compute_primary_stats.py` | same | §5.1 tertiary |
| **GEE (4 models)** | Variant effect = 0 after task clustering | `glmm_analysis.py` | same | §5.1 footnote |
| **Bootstrap decomposition** (B=2,000) | Pathway CIs for text-only vs CUA drop | `bootstrap_decomposition.py` | same | §5.1 decomposition |
| **Breslow-Day** (Claude vs Llama 4) | OR homogeneous across models | `breslow_day.py` | same | §5.4 cross-model |
| **Majority-vote sensitivity** | Findings robust to rep aggregation | `majority_vote_sensitivity.py` | same | Appendix A |
| **Wilcoxon rank-sum** | Token distributions equal across variants | `compute_primary_stats.py` | same | §5.1 token inflation |
| **Holm-Bonferroni** | Multiple comparison correction (8 secondary tests) | `compute_primary_stats.py` | same | §4 |

---

## Phase 2: Individual Operator Study (N=4,056)

| Test | H₀ | Script | Data | Paper § |
|------|-----|--------|------|---------|
| **Fisher exact per operator** (26 tests, Holm-Bonferroni) | Operator rate = H-baseline rate | `amt_statistics.py` | `data/mode-a-shard-{a,b}/` | §5.2 |
| **Wilson 95% CI** per operator | — | `amt_statistics.py` | same | §5.2 |
| **Odds ratio + Woolf logit CI** per operator | — | `amt_statistics.py` | same | §5.2 |
| **GEE destructive indicator** (L1/L5 vs rest) | Destructive effect = 0 after task clustering | `amt_statistics.py` | same | §5.2 footnote |
| **GEE Low-family indicator** (all L vs H) | Low-family effect = 0 after task clustering | `amt_statistics.py` | same | §5.2 footnote |
| **Majority-vote sensitivity** (3 reps → 1 vote) | L1/L5/L12 significance robust to aggregation | `amt_statistics.py` | same | §5.2 footnote |
| **Breslow-Day per operator** (Claude vs Llama 4) | Per-operator OR homogeneous across models | `amt_statistics.py` | `data/mode-a-llama4-textonly/` | §5.4 |
| **Mantel-Haenszel common OR** | — | `amt_statistics.py` | same | §5.4 |
| **Cohen's h** per operator | Effect size for cross-model comparison | `amt_statistics.py` | same | §5.4 |
| **Spearman rank correlation** (DOM magnitude vs behavioral drop) | No correlation between DOM change and agent impact | `amt_statistics.py` | `results/amt/dom_signature_matrix.csv` + behavioral | §5.3 |

---

## Phase 3: Compositional Study (N=2,188)

| Test | H₀ | Script | Data | Paper § |
|------|-----|--------|------|---------|
| **Fisher exact per pair** (28 pairs vs H-baseline) | Pair rate = H-baseline rate | `amt_statistics.py` | `data/c2-composition-shard-{a,b}/` | §5.5 |
| **Interaction term** (observed − expected additive drop) | — | `amt_statistics.py` | same | §5.5 |
| **Binomial test** (super vs sub count) | p(super) = p(sub) = 0.5 | `amt_statistics.py` | same | §5.5 |

---

## Cross-Study Triangulation

| Test | H₀ | Script | Data | Paper § |
|------|-----|--------|------|---------|
| **Griffith re-analysis** (N=320 blind users) | — | `griffith_triangulation.py` | `analysis/Copy of FinalData.xlsx` | §5.6 |
| **Variance decomposition** (site vs participant) | — | `griffith_triangulation.py` | same | §5.6 |
| **Bootstrap CI** on per-participant time ratio (B=10,000) | — | `griffith_triangulation.py` | same | §5.6 |

---

## DOM Signature Audit

| Analysis | Script | Data | Paper § |
|----------|--------|------|---------|
| **12-dim DOM signature** (26 ops × 39 samples) | `scripts/amt/amt-signature-analysis.py` | `data/archive/amt-dom-signatures/` | §3.2, §5.3 |
| **Behavioral signature** (26 ops × 3 agents × 2 models) | same | `data/mode-a-shard-{a,b}/` | §3.3, §5.2 |
| **Signature alignment classification** (4 categories) | same | both above | §3.4, §5.3 |

---

## Reproducibility

| Tool | What it checks | Script |
|------|---------------|--------|
| **Paper numbers audit** (28 checks) | Every quantitative claim in §4-§5 | `scripts/amt/audit-paper-numbers.py` |
| **GT corrections** | 3 Docker-drift tasks (41, 198, 293) | inline in all scripts |

---

## Summary: Test Count by Phase

| Phase | Tests | Corrections | Key result |
|-------|-------|-------------|------------|
| Composite (N=1,040) | 9 distinct tests | Holm-Bonferroni (8 secondary) | Low-vs-rest Z=9.83, p<10⁻¹⁹ |
| Individual (N=4,056) | 10 distinct tests | Holm-Bonferroni (26 operators) | L1 p<0.001, L5 p=0.001 |
| Compositional (N=2,188) | 3 distinct tests | — | 15/28 super-additive, p=0.019 |
| Triangulation | 3 analyses | — | Site explains 66.1% of variance |
| **Total** | **25 distinct statistical procedures** | | |

---

## Dependencies

All analyses require: `numpy`, `scipy`, `pandas`.
GEE models additionally require: `statsmodels`.
Griffith triangulation requires: `openpyxl`.

Run all analyses:
```bash
python3 analysis/amt_statistics.py          # Phase 2 + 3 (Fisher, GEE, MV, Breslow-Day, composition)
python3 analysis/compute_primary_stats.py   # Phase 1 (Low-vs-rest, C-A, J-T)
python3 analysis/glmm_analysis.py           # Phase 1 GEE models
python3 analysis/bootstrap_decomposition.py # Phase 1 pathway CIs
python3 analysis/majority_vote_sensitivity.py # Phase 1 MV sensitivity
python3 analysis/breslow_day.py             # Phase 1 cross-model
python3 analysis/griffith_triangulation.py  # Triangulation
python3 scripts/amt/audit-paper-numbers.py  # Reproducibility audit (28 checks)
```

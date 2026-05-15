# Phase 6 — Stage 3 Breadth (N=7,488) ★ PRIMARY DATASET

> **Purpose**: replicate Mode A per-operator findings at 48-task scale with
> two model families. This is the **primary dataset** for paper §5.1–§5.3.
> Mode A (Phase 2) becomes the depth complement.
> **Status (2026-05-15)**: data frozen 2026-05-10 (Claude) / 2026-05-09
> (Llama). Both shards 100% completion, 0 hard infrastructure confounds.

## Design matrix

```
48 tasks  ×  26 ops  ×  3 reps  ×  2 models  =  7,488 cases
```

| Dimension | Values |
|---|---|
| Tasks | 48 surviving the Phase 5 smoker gate (pre-registered) |
| Operators | L1–L13, ML1–ML3, H1–H8 + H5a/b/c (the 26 AMT operators) |
| Reps | 3 |
| Models | Claude Sonnet 4 + Llama 4 Maverick |
| Agent | text-only only (no SoM, no CUA — Mode A's data on those is sufficient) |

Per (model, operator) cell: 48 × 3 = 144 observations.
Per (model, operator) cell vs Mode A: 13 × 3 = 39. **Stage 3 has 3.7× more
observations per cell**, raising statistical power above 99% for a 20-pp drop
detection.

## On-disk data (~5.1 GB total)

| Directory | Cases | Model | Date |
|---|--:|---|---|
| `data/stage3-claude/` | 3,744 | Claude Sonnet 4 | 2026-05-10 |
| `data/stage3-llama/` | 3,744 | Llama 4 Maverick | 2026-05-09 |
| **Total** | **7,488** | | |

### File layout (per-case directory, NOT flat JSON)

Stage 3 uses a different on-disk layout than Mode A — each case is its own
directory with separated trace + scan-result files:

```
data/stage3-<model>/<run-uuid>/cases/<case-dirname>/
    trace-attempt-1.json    # full agent trace
    trace-attempt-N.json    # if retried (rate-limit, etc.) — keep highest-numbered
    scan-result.json        # accessibility scanner Tier 1+2

# Mirror layout (same data) under track-a/runs:
data/stage3-<model>/track-a/runs/<run-uuid>/cases/<case-dirname>/...
```

Case dirname format:
```
<app>_individual_<task-id>_<container-index>_<attempt>_<op-id>
e.g. ecommerce_admin_individual_187_0_1_H1
     gitlab_individual_312_0_2_L11
```

`analysis/lib/load.py:load_cases_stage3` parses this format and reads the
**highest-numbered** trace-attempt as the final result.

## Derived artefacts

| File | Producer | Contents |
|---|---|---|
| `results/stage3/per-operator-stage3.csv` | `analysis/stage3_statistics.py` | per-op rate, n, drop_pp, p, OR, p_holm, significant — Claude only |
| `results/stage3/statistics_report.md` | same | full report (Fisher exact + Holm-Bonferroni + GEE + cross-model) |
| `results/stage3/{claude,llama}-download-audit.md` | manual | post-collection audit (89.5% / 67.4% overall + per-op + per-task) |
| `results/stage3/sanity-{claude,llama}.txt` | `scripts/stage3/sanity-check.py` | completeness, outcome distribution, vs Mode A baseline |
| `results/stage3/pathological-{claude,llama}.txt` | `scripts/stage3/flag-pathological-tasks.py` | tasks where H-ops collapse <30% (suspect environment) |
| `results/stage3/rate-limit-audit-{claude,llama}.md` | `scripts/amt/audit-rate-limit-confound.py` | Bedrock 429 retry impact analysis |
| `results/stage3/visual-equiv/` | (Phase 6 Stage 4b — see separate doc) | SSIM derivations |

## Headline numbers (paper §5.1–§5.3)

### Overall success rates
- **Claude overall**: 89.5%
- **Llama 4 overall**: 67.4%
- **H-baseline Claude**: 91.9% (pooled across H-ops)

### Per-operator drops vs H-baseline (Claude, breadth set)
After Holm-Bonferroni correction across 26 tests:

| Operator | Rate | Drop pp | p_holm | Significant |
|---|--:|--:|--:|---|
| L1 (landmark→div) | 63.9% | −28.0 | <0.001 | ✓ |
| L9 (table flatten) | 79.2% | −12.7 | <0.001 | ✓ |
| L5 (Shadow DOM) | 80.6% | −11.3 | <0.001 | ✓ |
| L12 (duplicate IDs) | 84.0% | −7.8 | 0.041 | ✓ marginal |
| (22 others) | 88–100% | ±3 | NS | — |

### Cross-model: L11 adaptive recovery gap (paper §5.3 spine)

| L11 vs H-baseline | Claude | Llama 4 | Gap |
|---|--:|--:|--:|
| Breadth (Stage 3, 48 tasks) | +2.3 pp | −14.1 pp | 16.4 pp |
| Depth (Mode A, 13 tasks) | +1.5 pp | −14.6 pp | 16.1 pp |

Both datasets agree: Claude adapts (URL-construction fallback), Llama 4 persists.

### Sanity vs Mode A
- Bottom-5 Claude operators in Mode A (L1, L12, L5, L9, ML1): **5/5 overlap**
  with Stage 3 bottom-5
- Llama 4: 4/5 overlap (ML2 swaps in for L2)

## How to audit

```sh
make audit-stage3
# python -m analysis.stages.phase6_stage3
```

Verifier asserts:
- per-model case count = 3,744
- 26 operators present in both Claude and Llama
- Claude overall rate ≈ 89.5% (±0.5pp)
- Llama 4 overall rate ≈ 67.4% (±0.5pp)
- Claude H-baseline ≈ 91.9%
- L1, L9, L5, L12 drops within ±1.5pp of paper claim
- L11 gap reproduced (Claude +2.3, Llama −14.1)

## Paper sections

- **§5.1 Per-operator behavioural signatures** — `figure F4_behavioral_drop`
  (per-op ranking on Stage 3 data); the 4 significant operators after
  Holm-Bonferroni.
- **§5.3 Cross-model replication** — Stage 3 + Breslow-Day; the +33.4pp
  L11 model gap (Claude 89.6% vs Llama 56.2% on L11 raw rate, not
  H-baseline-relative).
- **§5.2 Signature alignment** — Stage 3 drops paired with DOM signatures
  (Phase 4) in `figure6_alignment_scatter`.
- **§4 Sample size justification** — 48 × 3 = 144 obs/op gives >99% power
  at 20-pp.

## Known caveats

- **Llama 4 capability floor**: 8 of 48 tasks show near-zero Llama success
  across all operators (including H-ops). Indicates capability limit, not
  operator effect. Tasks retained in primary analysis; documented in §6
  Limitations.
- **Rate-limit retries (Bedrock 429)**: 36/3,744 (1.0%) Claude cases hit a
  429; all absorbed by 4-retry loop. Spearman ρ across operators = −0.010,
  p = 0.963 — confound is localised (concentrated in L5: 13/36) and not
  systemic. Pre-drafted limitation language in `claude-download-audit.md
  §4.3`.
- **No SoM/CUA in Stage 3**: cost-benefit favours scaling text-only. SoM
  (Mode A baseline 27.7%) and Mode A CUA (baseline 48.2%) too noisy for
  48-task expansion to be informative. Composite-phase CUA (93.8% baseline)
  retains the clean architecture contrast.
- **Tasks 41/198/293 GT corrections still apply** uniformly via
  `apply_gt_corrections` (per Mode A protocol).

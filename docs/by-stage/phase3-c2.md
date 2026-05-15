# Phase 3 — C.2 Compositional Study (N=2,184)

> **Purpose**: test whether pairs of individual operators interact
> additively, super-additively, or sub-additively. Resolves the apparent
> paradox that most individual operators are benign yet composite Low
> produces a 55-pp collapse.
> **Status (2026-05-15)**: data frozen 2026-05-02. Used in §5.4.

## Design matrix

```
28 operator pairs  ×  13 tasks  ×  2 archs (text + CUA)  ×  3 reps  =  2,184
```

| Dimension | Values |
|---|---|
| Pairs | C(8,2) = 28 from the top-8 operators by mechanism diversity: L1, L2, L4, L5, L6, L9, L11, L12 |
| Pair order | Canonical H → ML → L (by ID); reproducible. Non-commutativity flagged in operator spec. |
| Tasks | same 13 as Phase 1/2 |
| Reps | 3 |
| Models | Claude × {text-only, CUA} only (no Llama 4 — budget) |

⚠ **The paper §4.122 and several pre-2026-05-15 docs miscompute this product**:
`28 × 13 × 2 × 3 = 2,184`, **not 2,188**. The on-disk N has always been 2,184;
the typo originated in §4.122 and propagated to abstract/§5.4/handoffs/steering.
Phase 3 of `_constants.py` carries this rationale; verifier asserts 2,184.

## On-disk data (~709 MB total)

| Directory | Cases | Description | Date |
|---|--:|---|---|
| `data/c2-composition-shard-a/` | 1,092 | first 14 pairs (sharded by pair-id) | 2026-05-02 |
| `data/c2-composition-shard-b/` | 1,092 | other 14 pairs | 2026-05-02 |
| **Total** | **2,184** | | |

Per-experiment dual layout same as Phase 1.

## Derived artefacts

| File | Producer |
|---|---|
| `results/amt/statistics_report.md` § "Composition" | `analysis/amt_statistics.py:test_compositional_interaction` |
| Paper figure `F8_composition` | `figures/generate_F8_composition.py` |

Categorisation per pair:
```
Δ_interaction = drop(A+B) − [drop(A) + drop(B)]
  super-additive: Δ > +5pp
  additive:       |Δ| ≤ 5pp
  sub-additive:   Δ < −5pp
```

Headline counts (paper §5.4):
- 15/28 super-additive
- 9/28 additive
- 4/28 sub-additive
- Binomial test on symmetric additivity: p = 0.019

## How to audit

```sh
make audit-c2
```

Verifier asserts:
- total cases = 2,184 (NOT 2,188)
- each shard = 1,092
- per-arch split text-only / cua = 1,092 each

## Paper sections

- **§5.4 Compositional Interactions (N=2,184)** — `figure F8_composition`,
  the named interaction patterns:
  - **L11 amplifier**: zero individual effect (+2.3pp breadth, +1.5pp depth)
    but +24.1pp interaction with L6 (largest in the 28-pair grid)
  - **L6 latent damage**: 100% individual success, super-additive with L1, L4, L9
  - **L5 ceiling**: sub-additive (perception-action gap saturates)

## Known caveats

- **Pair design is convenience, not factorial**. Top-8 operators chosen by
  mechanism diversity, not by individual significance. Different selection
  could yield different pair distribution.
- **No Llama 4 composition data**. Cross-model interaction patterns
  unknown — future work flagged in §7.
- **Canonical pair order matters for non-commutative pairs** (e.g. H4+L1
  both target `<nav>`; documented in operator spec).
- **Ground-truth corrections applied** identically to Mode A.

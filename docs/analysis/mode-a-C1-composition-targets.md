# C.1 Compositional Study — Top-8 Operator Selection

**Date**: 2026-05-01
**Selected operators**: L1, L2, L4, L5, L6, L9, L11, L12
**Pairwise combinations**: C(8,2) = 28
**Total cases**: 3,276 (28 × 13 tasks × 3 agents × 3 reps)
**Split**: Shard A (14 pairs, 1,638 cases) + Shard B (14 pairs, 1,638 cases)

---

## Selection Rationale

Operators selected for **mechanism diversity**, not just drop magnitude.
The goal is to test whether pairwise effects are additive, super-additive,
or sub-additive — which requires operators with distinct failure mechanisms.

| # | Op | Mechanism | Claude drop | Llama drop | Why selected |
|---|-----|-----------|-------------|------------|-------------|
| 1 | **L1** | Structural: landmark→div | -40.0pp | -32.6pp | Strongest individual effect, must-include |
| 2 | **L5** | Structural: Shadow DOM isolation | -22.1pp | -22.3pp | Second strongest, independent mechanism |
| 3 | **L11** | Functional: link→span (delete href) | -1.5pp | -14.6pp | Core of composite low; Llama 4 #3 |
| 4 | **L2** | Semantic: remove all ARIA+role | -4.1pp | -4.4pp | Overlaps with L1 → test sub-additivity |
| 5 | **L6** | Semantic: heading→div | 0.0pp | -4.4pp | Zero Claude effect → test "null + X" |
| 6 | **L9** | Semantic: table structure (thead→div) | -4.1pp | -4.4pp | Task-specific (admin tables only) |
| 7 | **L12** | Semantic: duplicate IDs | -14.4pp | -6.9pp | Vue.js effect on task 293 (real) |
| 8 | **L4** | Functional: remove keyboard handlers | -4.1pp | -6.9pp | Pure functional, no semantic overlap |

## Predicted Interactions (28 pairs)

### High-confidence predictions

| Pair | Prediction | Rationale |
|------|-----------|-----------|
| **L1+L11** | **Super-additive** | Composite low's core: landmark loss + link deletion = navigation collapse. Individual drops sum to ~41.5pp but composite low drops ~70pp. |
| **L1+L5** | **Super-additive** | Both structural: landmark loss makes page flat, Shadow DOM makes buttons unclickable. Compound isolation. |
| **L1+L2** | **Sub-additive** | L1 removes landmark elements (which carry ARIA). L2 removes ARIA from remaining elements. Overlap on landmark-associated ARIA. |
| **L5+L11** | **Additive** | Independent mechanisms: Shadow DOM wraps buttons, link→span converts links. No DOM overlap. |
| **L6+L9** | **Null** | Both weak individually. Heading removal + table structure removal on different page regions. |

### Exploratory predictions

| Pair | Prediction | Rationale |
|------|-----------|-----------|
| L1+L6 | Additive or null | L6 has zero Claude effect. If L1+L6 > L1 alone, headings compensate for landmark loss. |
| L1+L9 | Additive | Navigation (L1) + content structure (L9) are independent page regions. |
| L5+L12 | Unknown | Shadow DOM + duplicate IDs. May interact on Vue.js components. |
| L11+L12 | Unknown | Link deletion + ID duplication. Both affect GitLab Vue.js. |
| L4+L5 | Additive | Keyboard handlers + Shadow DOM. Double interaction barrier. |

## Shard Assignment

**Shard A** (14 pairs): All L1× (7) + all L2× excl L1 (6) + L4×L5 (1)
- Contains all L1 pairs → the most informative combinations
- Config: `config-c2-composition-shard-a.yaml`

**Shard B** (14 pairs): L4×{L6,L9,L11,L12} + L5×{L6,L9,L11,L12} + L6×{L9,L11,L12} + L9×{L11,L12} + L11×L12
- Contains the "weaker" pairs → exploratory
- Config: `config-c2-composition-shard-b.yaml`

## Cost Estimate

- 3,276 cases × ~$0.30/case = ~$980
- Wall time: ~3-4 days per shard (parallel = 3-4 days total)
- Requires 2 burner accounts with Bedrock access

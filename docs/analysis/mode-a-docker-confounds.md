# Docker State Confounds — Comprehensive Audit

> **STATUS (2026-05-15)**: Frozen audit from 2026-05-02. C.2 = "2,188" is a
> +4 typo; actual N is 2,184. Confound conclusions unchanged.

**Date**: 2026-05-02
**Scope**: Mode A (3,042 cases), Llama 4 (1,014 cases), C.2 (2,184 cases)

---

## 1. Summary of All Docker Confounds

| Experiment | Task | Shard | Issue | Impact | Mitigation |
|-----------|------|-------|-------|--------|------------|
| Mode A | 41, 198, 293 | Both | GT drift (search terms, orders, GitLab URL) | Both shards 0% | GT correction applied |
| Mode A | 4 | A only | Magento statistics stale ("Last updated Jun 2023") | Shard A task 4 failures inflated | Documented in analysis |
| Llama 4 | 4 | — | Same Docker as Mode A Shard B, statistics stale | Task 4 = 0% all operators | Excluded from operator ranking |
| Llama 4 | 41 | — | GT drift (same as Mode A) | Corrected with "abdomin" | GT correction applied |
| **C.2** | **41** | **B only** | **Search terms page non-functional** | **All 14 Shard B pairs +3 false negatives** | **Exclude task 41 from Shard B** |

---

## 2. C.2 Task 41 Confound (NEW — discovered 2026-05-02)

### Evidence

- Shard A (account 190...): task 41 = **42/42 (100%)** — all answer "hollister" ✅
- Shard B (account 275...): task 41 = **0/42 (0%)** — all answer "top selling products Jan 2023" ❌

### Root Cause

Shard B's Docker instance (account 275201671198) ran Mode A Shard B (1,404 cases) +
Llama 4 (1,014 cases) + C.2 Shard B (1,092 cases) = **3,510 total cases** before C.2
completed. The cumulative agent interactions with the Magento admin panel corrupted
the search terms functionality — the admin search terms page no longer returns data,
causing the agent to fall back to echoing the task description.

Shard A's Docker (account 190777959793) ran Mode A Shard A (1,638 cases) + C.2 Shard A
(1,092 cases) = **2,730 cases**. Its search terms page still works correctly.

### Impact on C.2 Results

Every Shard B pair has 3 false negatives from task 41 (out of 39 text-only cases per pair).
This inflates the observed drop by ~7.7pp for all 14 Shard B pairs.

**Affected pairs**: L4+L6, L4+L9, L4+L11, L4+L12, L5+L6, L5+L9, L5+L11, L5+L12,
L6+L9, L6+L11, L6+L12, L9+L11, L9+L12, L11+L12

**Unaffected pairs**: All L1× pairs (Shard A), all L2× pairs (Shard A)

### Corrected Interaction Effects (excluding task 41 from Shard B)

| Pair | Original Interaction | Corrected (excl task 41) | Still super-additive? |
|------|---------------------|--------------------------|----------------------|
| L6+L11 | +24.1pp | ~+18pp | ✅ Yes |
| L9+L11 | +19.0pp | ~+13pp | ✅ Yes |
| L4+L6 | +13.8pp | ~+8pp | ✅ Yes (borderline) |
| L5+L11 | +11.2pp | ~+5pp | ⚠️ Borderline |
| L4+L11 | +11.3pp | ~+5pp | ⚠️ Borderline |
| L6+L9 | +13.8pp | ~+8pp | ✅ Yes |

### Recommendation for Paper

1. Report C.2 results **excluding task 41 from Shard B** (conservative)
2. Note in §6 Limitations that WebArena Docker state is mutable and
   ground truth was verified post-hoc
3. Core findings (L11 amplifier, L6 latent damage, L5 ceiling) remain
   valid even with conservative correction

---

## 3. Mode A Cross-Shard Comparison

Mode A shows **no significant Docker confound** between shards:
- Maximum cross-shard difference: 13pp (task 67) — within expected operator effect range
- Task 41/198/293: both shards 0% (consistent GT drift, corrected)
- Task 4: Shard A 81% vs Shard B 72% — 9pp difference, within noise

The Mode A shard split is by **operator** (Shard A = H1-H8, ML1-3, L1;
Shard B = L2-L13), not by task. Both shards run all 13 tasks. The small
per-task differences are attributable to operator effects, not Docker state.

---

## 4. Lessons Learned

1. **WebArena Docker is NOT stateless**: Agent actions accumulate in the database.
   After 3,000+ cases, Magento admin functionality degrades.

2. **Cross-shard comparison is essential**: Running the same tasks on both shards
   allows detection of Docker state issues (task 41 in C.2 was caught this way).

3. **GT correction is necessary but not sufficient**: Some failures (like task 41
   Shard B's "top selling products Jan 2023") are not correctable because the
   answer is not a valid search term — it's a navigation failure symptom.

4. **For future experiments**: Verify ground truth for ALL tasks on each Docker
   instance BEFORE running experiments. Consider implementing `WA_FULL_RESET`
   between experiment batches.

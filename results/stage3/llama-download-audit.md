# Stage 3 Llama — Download + Sanity Audit

**Generated**: 2026-05-09 (CST evening)
**Source**: `data/stage3-llama/` downloaded from
`s3://a11y-platform-data-20260505084053926000000001/experiments/stage3-llama-20260509-111619.tar.gz`
**Archive**: 289 MB; 12,297 files

## TL;DR

✅ **Data is clean and complete.** 3,744/3,744 cases, every (task,op) × 3 reps.
🟢 **Rate-limit confound: acceptable** — 25 cases saw 429 retries, all absorbed, no per-op correlation.
⚠️ **Four tasks near-zero success across all operators** — these are **Llama-4 capability limits**,
not infra drift or operator effects. Consistent with Mode A's documented "model capability floor".

## §1. Completeness

- case files on disk: **3,744**
- expected: 48 tasks × 26 ops × 3 reps = **3,744**  ✅
- per-app breakdown matches expectation exactly
- all 26 operators present
- all 1,248 (task, op) cells have 3 reps

## §2. Outcome distribution

| Outcome          | Cases | %     |
|------------------|------:|------:|
| success          |  2,522 | 67.4% |
| partial_success  |    727 | 19.4% |
| failure          |    331 |  8.8% |
| timeout          |    164 |  4.4% |

**Overall success: 67.4%** — aligns with Mode A Llama 4 reference (71.8%).

## §3. Ordering verification vs Mode A

Bottom-5 (most destructive) operators:
- **Stage 3 Llama**: `L1, L9, L5, L11, ML2`
- **Mode A Llama ref**: `L1, L11, L2, L5, L9`
- Overlap: **4/5** — L1, L5, L9, L11 all in both ✓

Key patterns preserved:
- **L1 Landmark Paradox**: 45.8% (lowest) — matches Mode A finding
- **L5 Shadow DOM**: 56.2% — destructive as expected
- **L11 adaptive recovery gap**: 56.2% — Llama brittle, just as Mode A documented
- **H-ops cluster**: 67-73% range, no strong separation among enhancements
- **L3 top-performing L-op**: 75.0% — Llama handles aria removal gracefully

## §4. Rate-limit confound: 🟢 acceptable

(See `rate-limit-audit-llama.md` for full detail.)

- 0 hard confounds (4-retry loop absorbed every 429)
- 25 cases (0.7%) saw ≥1 429 retry
- No within-op χ² significance
- Spearman ρ between retry rate and success rate: non-significant

## §5. Pathological tasks (investigation required)

8 tasks have H-operator mean success < 30%. The H-family consists of
**enhancements**, so they should preserve or improve baseline. When H collapses,
the task is fragile in the environment for a reason unrelated to operator
semantics.

| Task | L-mean | ML-mean | H-mean | Overall |
|---|---:|---:|---:|---:|
| gitlab:316          |  0.0% |  0.0% |  0.0% |  0.0% |
| ecommerce_admin:1   |  2.6% |  0.0% |  0.0% |  1.3% |
| ecommerce_admin:187 | 10.3% |  0.0% |  0.0% |  5.1% |
| ecommerce:230       |  7.7% | 11.1% |  3.3% |  6.4% |
| gitlab:788          |  5.1% |  0.0% | 20.0% | 10.3% |
| gitlab:314          |  7.7% |  0.0% | 23.3% | 12.8% |
| ecommerce:47        | 25.6% |  0.0% | 26.7% | 23.1% |
| ecommerce:26        | 33.3% |  0.0% | 20.0% | 24.4% |

### Diagnosis

**gitlab:316** (0/78): agent (Llama 4) repeatedly starts the run then issues
`goto("https://github.com/facebook/react")` — an external URL — and drops out
of WebArena. The task asks for contributor ranking on a React-repo mirror in
the internal GitLab. Llama 4 hallucinates to public GitHub instead.

**ecommerce_admin:1** (1/78, exact_match="Sprite"): Magento admin
bestsellers report, Q1 2022 filter. Llama 4 times out at 30 steps on most
operator runs; best attempts produce partial_success with wrong-answer
"Luma" (the theme name) instead of "Sprite" (the bestselling brand).

These are **Llama-4-specific navigation/capability failures**, not Docker
drift or operator-level effects. They parallel Mode A's
"model capability floor" phenomenon (e.g., Mode A admin:4 was 5% for Llama
vs 95% for Claude).

### Why these passed the Stage 3 gate

The gate is defined in `docs/analysis/task-selection-methodology.md`: the
smoker ran **Claude** at base variant and selected tasks where Claude passes
3/3. Llama 4 was never gated. This is by design — the paper frames breadth
analysis as per-model, not joint — but means ~17% of tasks (8/48) will
contribute near-zero success across all Llama operators, flattening
Llama-4 operator contrasts on those tasks.

### Options for paper

1. **Keep all 48 tasks** — document the Llama-capability-floor tasks as
   Llama's intrinsic limit, not an operator effect (same framing as Mode A
   admin:4 analysis). Operator contrasts are still computable on the other
   40 tasks.
2. **Two-set analysis** — report Llama full-48 as "all" and Llama-40
   (excluding the 8 flagged) as "capable-subset". Both are legitimate.
3. **Per-task per-operator heatmap** — visualize which (task, op) cells are
   affected most. The flagged tasks will appear as horizontal near-zero
   bands regardless of operator, which is itself an interpretable visual.

**No action needed right now.** Data is valid; the pattern was expected based
on Mode A. Wait for Claude to complete, then do the joint analysis.

## §6. Performance distribution

| Metric | p50 | p90 | max |
|---|---:|---:|---:|
| Duration (sec) | 33.1 | 89.7 | 363.3 |
| Steps | 5 | 12 | 30 |
| Tokens | 70,907 | 272,792 | 2,414,474 |

Median case completes in 33s with 5 steps. No suspicious outliers.
The 2.4M-token max is consistent with Mode A observations on Magento admin
grid pages (same executor truncation safety net applies).

## §7. Verdict

🟢 **Data is ready for primary analysis.** Proceed with:
1. Wait for Claude to complete (~05-11 01-06 CST per latest rate estimate)
2. Run `scripts/stage3/sanity-check.py` + `flag-pathological-tasks.py` on
   Claude too
3. Then joint per-op contrasts + cross-model comparison

The 8 low-capability-floor tasks should be documented in §6 Limitations
but do not need pre-analysis exclusion.

---

**Regenerate this audit**:

```bash
python3.11 scripts/stage3/sanity-check.py --data-dir data/stage3-llama --label Llama
python3.11 scripts/stage3/flag-pathological-tasks.py --data-dir data/stage3-llama --label Llama
python3.11 scripts/amt/audit-rate-limit-confound.py \
    --data-dir data/stage3-llama \
    --log-file data/stage3-llama/stage3.log \
    --label "Stage 3 Llama" \
    --out results/stage3/rate-limit-audit-llama.md
```

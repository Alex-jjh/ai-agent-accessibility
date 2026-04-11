# Pilot 3b — Text-Only Agent Analysis

## 1. Data Separation and Validation

Pilot 3b ran 240 total cases: 120 text-only (configIndex=0, observationMode=text-only) and 120 vision-only (configIndex=1, observationMode=vision-only). All 120 vision-only cases failed immediately with a LiteLLM "Invalid model name claude-sonnet-vision" error (1 step, 0 tokens, F_UNK classification). These are excluded from all analysis below.

The 120 text-only cases use the same design as Pilot 3a:
- 6 tasks × 4 variants × 5 reps = 120 cases
- Tasks: admin:4, ecom:23, ecom:24, ecom:26, reddit:29, reddit:67
- Variants: low, medium-low, base, high
- Agent: claude-sonnet (text-only, a11y tree)

All 120 text-only cases executed successfully (no infrastructure failures, no crashes).

---

## 2. Text-Only Results: Pilot 3b vs Pilot 3a

### 2.1 Overall Success Rate

| Pilot | Pass | Total | Rate |
|-------|------|-------|------|
| 3b    | 86   | 120   | 71.7% |
| 3a    | 87   | 120   | 72.5% |
| **Δ** |      |       | **−0.8pp** |

The overall success rates are nearly identical (within 1 percentage point), indicating strong macro-level reproducibility.

### 2.2 Per-Variant Success Rates

| Variant     | 3b Pass/Total | 3b Rate | 3a Pass/Total | 3a Rate | Δ |
|-------------|---------------|---------|---------------|---------|---|
| low         | 13/30         | 43.3%   | 6/30          | 20.0%   | +23.3pp |
| medium-low  | 21/30         | 70.0%   | 26/30         | 86.7%   | −16.7pp |
| base        | 28/30         | 93.3%   | 27/30         | 90.0%   | +3.3pp |
| high        | 24/30         | 80.0%   | 28/30         | 93.3%   | −13.3pp |

Key observations:
- **Base variant** is highly stable: 93.3% (3b) vs 90.0% (3a), Δ = +3.3pp
- **Low variant** improved substantially: 43.3% (3b) vs 20.0% (3a), Δ = +23.3pp
- **Medium-low** dropped: 70.0% (3b) vs 86.7% (3a), Δ = −16.7pp
- **High** dropped: 80.0% (3b) vs 93.3% (3a), Δ = −13.3pp

The low variant improvement is the most notable change. This is driven by ecom:23 (0/5→3/5), ecom:24 (2/5→3/5), ecom:26 (0/5→2/5), and reddit:29 (2/5→3/5). The high variant regression is driven by admin:4 (4/5→2/5) and reddit:67 (5/5→4/5).

### 2.3 Task × Variant Matrix

| Task      | low (3b/3a) | ml (3b/3a) | base (3b/3a) | high (3b/3a) | Total (3b/3a) |
|-----------|-------------|------------|--------------|--------------|---------------|
| admin:4   | 0/5 · 0/5   | 2/5 · 4/5  | 5/5 · 5/5    | 2/5 · 4/5    | 9/20 · 13/20  |
| ecom:23   | 3/5 · 0/5   | 5/5 · 5/5  | 5/5 · 5/5    | 5/5 · 5/5    | 18/20 · 15/20 |
| ecom:24   | 3/5 · 2/5   | 5/5 · 5/5  | 5/5 · 5/5    | 5/5 · 5/5    | 18/20 · 17/20 |
| ecom:26   | 2/5 · 0/5   | 5/5 · 5/5  | 5/5 · 5/5    | 5/5 · 5/5    | 17/20 · 15/20 |
| reddit:29 | 3/5 · 2/5   | 1/5 · 2/5  | 3/5 · 2/5    | 3/5 · 4/5    | 10/20 · 10/20 |
| reddit:67 | 2/5 · 2/5   | 3/5 · 5/5  | 5/5 · 5/5    | 4/5 · 5/5    | 14/20 · 17/20 |

Stable cells (identical 3a↔3b):
- admin:4 low (0/5 = 0/5), ecom:23 ml/base/high (5/5 = 5/5), ecom:24 ml/base/high (5/5 = 5/5), ecom:26 ml/base/high (5/5 = 5/5), reddit:29 low (≈), reddit:67 low (2/5 = 2/5), reddit:67 base (5/5 = 5/5)

Unstable cells (≥2 case difference):
- **ecom:23 low**: 0/5 → 3/5 (+3 cases) — agent now sometimes succeeds despite low a11y
- **ecom:26 low**: 0/5 → 2/5 (+2 cases) — same pattern
- **admin:4 ml**: 4/5 → 2/5 (−2 cases) — regression
- **admin:4 high**: 4/5 → 2/5 (−2 cases) — regression
- **reddit:67 ml**: 5/5 → 3/5 (−2 cases) — regression

---

## 3. Statistical Tests

### 3.1 Chi-Square: Low vs Base

| Group | Pass | Fail | Rate |
|-------|------|------|------|
| Low   | 13   | 17   | 43.3% |
| Base  | 28   | 2    | 93.3% |

χ²(1) = 17.33, p ≈ 0.000031 — **Highly significant** (p < 0.001)

The accessibility gradient between low and base variants is strongly preserved in Pilot 3b.

### 3.2 Chi-Square: Low vs Medium-Low

| Group      | Pass | Fail | Rate |
|------------|------|------|------|
| Low        | 13   | 17   | 43.3% |
| Medium-Low | 21   | 9    | 70.0% |

χ²(1) = 4.34, p ≈ 0.037 — **Significant** (p < 0.05)

The distinction between low and medium-low is statistically significant, supporting the hypothesis that pseudo-compliance (medium-low) provides measurably better agent performance than severe a11y degradation (low).

### 3.3 Monotonic Gradient

| Variant     | Rate  |
|-------------|-------|
| low         | 43.3% |
| medium-low  | 70.0% |
| base        | 93.3% |
| high        | 80.0% |

**Monotonic: NO** — The gradient breaks at base→high (93.3% → 80.0%).

In Pilot 3a, the gradient was: 20.0% → 86.7% → 90.0% → 93.3% (monotonic ✓).

The 3b break is driven by admin:4 high (2/5 vs 4/5 in 3a) and reddit:67 high (4/5 vs 5/5). The admin:4 task is inherently noisy (complex multi-step Magento admin navigation), and the high variant regression there accounts for most of the gradient break.

If we exclude admin:4 (the noisiest task):
- low: 13/25 (52.0%), ml: 19/25 (76.0%), base: 23/25 (92.0%), high: 22/25 (88.0%)
- Still not perfectly monotonic, but the break is smaller (92→88%).

---

## 4. Token and Step Analysis

### 4.1 Average Tokens by Variant

| Variant     | 3b Avg Tokens | 3a Avg Tokens | Δ |
|-------------|---------------|---------------|---|
| low         | 150,361       | 181,877       | −17.3% |
| medium-low  | 65,901        | 78,128        | −15.6% |
| base        | 73,087        | 62,648        | +16.7% |
| high        | 73,440        | 63,790        | +15.1% |

Overall average: 3b = 90,697 tokens, 3a = 96,611 tokens (−6.1%)

The low variant uses ~2× more tokens than other variants in both pilots, consistent with the agent struggling and retrying more with degraded accessibility.

### 4.2 Average Steps by Variant

| Variant     | 3b Avg Steps | 3a Avg Steps |
|-------------|--------------|--------------|
| low         | 11.2         | 7.9          |
| medium-low  | 4.4          | 4.8          |
| base        | 4.7          | 4.8          |
| high        | 4.7          | 4.5          |

The low variant takes more steps in 3b (11.2 vs 7.9), partly because more low-variant cases now run longer before succeeding (3b has more low-variant successes). Medium-low, base, and high are stable across pilots.

### 4.3 Average Duration by Variant (3b only)

| Variant     | Avg Duration (s) |
|-------------|-----------------|
| low         | 99.0            |
| medium-low  | 51.4            |
| base        | 51.5            |
| high        | 54.0            |

Low variant cases take ~2× longer, consistent with the token and step patterns.

---

## 5. Failure Analysis

### 5.1 Failure Count

Total text-only failures: **34/120** (28.3%)
- Pilot 3a had 33/120 failures (27.5%)
- Nearly identical failure rates

### 5.2 Failure Type Distribution

| Type    | Count | Description |
|---------|-------|-------------|
| F_AMB   | 14    | Ambiguous task interpretation (agent confused about answer) |
| F_UNK   | 14    | Unknown/unclassified failure |
| timeout | 3     | Agent hit 30-step limit (all admin:4 low) |
| F_COF   | 2     | Context overflow (token limit exceeded) |
| F_ENF   | 1     | Element not found (accessibility-related) |

F_AMB dominates among classified failures — the agent navigates correctly but misinterprets what to report (especially on reddit:29 where it reports "0" instead of "1" for comment counts).

### 5.3 Failures by Task

| Task      | Failures | Rate | Primary Failure Modes |
|-----------|----------|------|-----------------------|
| admin:4   | 11/20    | 55%  | timeout (low), F_UNK (ml/high), F_COF |
| reddit:29 | 10/20    | 50%  | F_AMB (answer confusion), F_UNK |
| reddit:67 | 6/20     | 30%  | F_AMB, F_COF |
| ecom:26   | 3/20     | 15%  | F_UNK (low variant review access) |
| ecom:23   | 2/20     | 10%  | F_UNK (low variant) |
| ecom:24   | 2/20     | 10%  | F_UNK (low variant) |

The same two tasks (admin:4 and reddit:29) account for 62% of all failures in both pilots. These are the hardest tasks regardless of variant.

### 5.4 Failures by Variant

| Variant     | Failures | Rate |
|-------------|----------|------|
| low         | 17/30    | 57%  |
| medium-low  | 9/30     | 30%  |
| base        | 2/30     | 7%   |
| high        | 6/30     | 20%  |

The failure gradient (57% → 30% → 7% → 20%) mirrors the success gradient. The high variant's 20% failure rate (vs 7% for base) is the anomaly discussed in Section 3.3.

---

## 6. Reproducibility Assessment

### 6.1 Case-Level Agreement

Comparing the same 120 case slots (task × variant × rep) between Pilot 3a and 3b:

| Metric | Count | Rate |
|--------|-------|------|
| Total matching cases | 120 | — |
| **Agreement** | **89** | **74.2%** |
| Both pass | 71 | 59.2% |
| Both fail | 18 | 15.0% |
| Only 3a pass | 16 | 13.3% |
| Only 3b pass | 15 | 12.5% |

**Cohen's κ = 0.358** (fair agreement)

The relatively low kappa is expected for a stochastic LLM agent. The key insight: disagreements are roughly symmetric (16 cases 3a-only vs 15 cases 3b-only), meaning there's no systematic directional shift — just random variation.

### 6.2 Per-Task Agreement

| Task      | Agreement | Rate | 3a-only | 3b-only |
|-----------|-----------|------|---------|---------|
| ecom:26   | 18/20     | 90%  | 0       | 2       |
| ecom:23   | 17/20     | 85%  | 0       | 3       |
| ecom:24   | 17/20     | 85%  | 1       | 2       |
| admin:4   | 16/20     | 80%  | 4       | 0       |
| reddit:67 | 13/20     | 65%  | 5       | 2       |
| reddit:29 | 8/20      | 40%  | 6       | 6       |

**Most reproducible**: ecom:26 (90%), ecom:23 (85%), ecom:24 (85%) — these are simpler review-search tasks with deterministic answers.

**Least reproducible**: reddit:29 (40%) — this task involves counting comments on a specific user's post, and the agent frequently confuses the count. The 6-vs-6 split shows pure stochastic variance with no directional bias.

**admin:4** shows a directional shift: 4 cases passed in 3a but failed in 3b, 0 went the other direction. This suggests the admin task may have become slightly harder (possibly due to Magento state differences between runs).

### 6.3 Task×Variant Cells with Disagreements

12 out of 24 task×variant cells (50%) have at least one case disagreement. The cells with the most instability:

| Cell | Agreement | Pattern |
|------|-----------|---------|
| ecom:23 low | 2/5 | 3 cases flipped fail→pass (3b improvement) |
| admin:4 high | 3/5 | 2 cases flipped pass→fail (3b regression) |
| admin:4 ml | 3/5 | 2 cases flipped pass→fail (3b regression) |
| reddit:29 (all variants) | 2/5 each | High variance in both directions |
| reddit:67 low | 1/5 | 2 flipped each direction (pure noise) |

### 6.4 Reproducibility Summary

**What's reproducible:**
1. Overall success rate: 71.7% ≈ 72.5% (Δ < 1pp)
2. The core accessibility gradient: low << base is highly significant in both pilots
3. Easy tasks stay easy: ecom:23/24/26 at base/ml/high are 5/5 in both pilots
4. Hard tasks stay hard: admin:4 low is 0/5 in both pilots
5. Failure concentration: same two tasks (admin:4, reddit:29) dominate failures

**What's NOT reproducible:**
1. Exact per-variant rates: low jumped +23pp, high dropped −13pp
2. Individual case outcomes: only 74% agreement (κ = 0.36)
3. Monotonic gradient: preserved in 3a but broken in 3b
4. reddit:29 outcomes: essentially random (40% agreement)

**Interpretation**: The macro-level findings (overall rate, gradient significance, task difficulty ranking) are reproducible. The micro-level findings (exact variant rates, individual case outcomes) show substantial stochastic variation inherent to LLM agent evaluation. This is consistent with the literature on LLM evaluation reproducibility — 5 reps per cell is sufficient to detect large effects but insufficient to precisely estimate rates for individual cells.

---

## 7. Key Conclusions

1. **Pilot 3b replicates the core finding**: accessibility degradation significantly reduces agent success (low 43.3% vs base 93.3%, p < 0.001).

2. **The medium-low distinction holds**: pseudo-compliance (70.0%) is significantly better than severe degradation (43.3%, p = 0.037) but worse than baseline (93.3%).

3. **Overall rate is stable**: 71.7% vs 72.5% — the aggregate is highly reproducible even though individual cases vary.

4. **The monotonic gradient is fragile**: it held in 3a but broke in 3b due to high-variant regression on admin:4. This suggests the high→base distinction may not be robust with n=5 reps.

5. **reddit:29 is the noisiest task**: 40% case-level agreement, suggesting this task's outcome is dominated by stochastic factors rather than accessibility variant effects.

6. **Low variant improved in 3b**: the +23pp jump in low-variant success (especially ecom:23/24/26) suggests the agent may have found alternative navigation strategies that partially bypass a11y degradation. This warrants trace-level investigation.

7. **Recommendation for future pilots**: increase reps to ≥10 per cell for more stable per-variant estimates, or accept that the primary contrast (low vs base) is the robust finding while finer gradient distinctions require larger samples.

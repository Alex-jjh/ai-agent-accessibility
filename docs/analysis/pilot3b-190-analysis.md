# Pilot 3b Analysis (190/240 Cases)

**Run:** fb6d0b8b-a7c3-44d8-922d-e94963795a12
**Total traces loaded:** 190
**Agent types:** configIndex=0 (text-only, a11y tree), configIndex=1 (vision-only, SoM screenshot)
**Expected:** 240 cases (6 tasks × 4 variants × 2 agents × 5 reps)
**Completed:** 190 of 240

---

## 1. Data Inventory

**Total trace files found:** 190

**Text-only (configIndex=0):** 97
**Vision-only (configIndex=1):** 93

### Traces per Variant × Agent Type

| Variant | Text-Only | Vision-Only | Total |
|---------|-----------|-------------|-------|
| low | 26 | 27 | 53 |
| medium-low | 24 | 21 | 45 |
| base | 26 | 22 | 48 |
| high | 21 | 23 | 44 |
| **Total** | **97** | **93** | **190** |

### Traces per Task × Variant × Agent Type

| Task | Variant | Text-Only | Vision-Only |
|------|---------|-----------|-------------|
| ecommerce:23 | low | 5 | 5 |
| ecommerce:23 | medium-low | 4 | 3 |
| ecommerce:23 | base | 3 | 3 |
| ecommerce:23 | high | 4 | 4 |
| ecommerce:24 | low | 4 | 5 |
| ecommerce:24 | medium-low | 5 | 3 |
| ecommerce:24 | base | 5 | 5 |
| ecommerce:24 | high | 3 | 5 |
| ecommerce:26 | low | 4 | 5 |
| ecommerce:26 | medium-low | 5 | 5 |
| ecommerce:26 | base | 5 | 5 |
| ecommerce:26 | high | 4 | 4 |
| ecommerce_admin:4 | low | 5 | 5 |
| ecommerce_admin:4 | medium-low | 4 | 3 |
| ecommerce_admin:4 | base | 4 | 4 |
| ecommerce_admin:4 | high | 5 | 3 |
| reddit:29 | low | 5 | 5 |
| reddit:29 | medium-low | 2 | 3 |
| reddit:29 | base | 4 | 2 |
| reddit:29 | high | 3 | 3 |
| reddit:67 | low | 3 | 2 |
| reddit:67 | medium-low | 4 | 4 |
| reddit:67 | base | 5 | 3 |
| reddit:67 | high | 2 | 4 |

### Missing Cases (50 of 240)

**Expected:** 240 cases
**Found:** 190 cases
**Missing:** 50 cases

| Site:Task | Variant | Config | Missing Reps |
|-----------|---------|--------|--------------|
| ecommerce:23 | base | config=0 | [1, 3] |
| ecommerce:23 | base | config=1 | [1, 4] |
| ecommerce:23 | high | config=0 | [1] |
| ecommerce:23 | high | config=1 | [4] |
| ecommerce:23 | medium-low | config=0 | [1] |
| ecommerce:23 | medium-low | config=1 | [1, 4] |
| ecommerce:24 | high | config=0 | [1, 3] |
| ecommerce:24 | low | config=0 | [1] |
| ecommerce:24 | medium-low | config=1 | [1, 4] |
| ecommerce:26 | high | config=0 | [3] |
| ecommerce:26 | high | config=1 | [3] |
| ecommerce:26 | low | config=0 | [5] |
| ecommerce_admin:4 | base | config=0 | [5] |
| ecommerce_admin:4 | base | config=1 | [4] |
| ecommerce_admin:4 | high | config=1 | [2, 3] |
| ecommerce_admin:4 | medium-low | config=0 | [4] |
| ecommerce_admin:4 | medium-low | config=1 | [2, 4] |
| reddit:29 | base | config=0 | [2] |
| reddit:29 | base | config=1 | [3, 4, 5] |
| reddit:29 | high | config=0 | [1, 3] |
| reddit:29 | high | config=1 | [4, 5] |
| reddit:29 | medium-low | config=0 | [1, 2, 5] |
| reddit:29 | medium-low | config=1 | [3, 4] |
| reddit:67 | base | config=1 | [1, 2] |
| reddit:67 | high | config=0 | [1, 2, 4] |
| reddit:67 | high | config=1 | [1] |
| reddit:67 | low | config=0 | [2, 5] |
| reddit:67 | low | config=1 | [1, 2, 3] |
| reddit:67 | medium-low | config=0 | [3] |
| reddit:67 | medium-low | config=1 | [5] |

## 2. Text-Only Results (Comparison with Pilot 3a)

**Total text-only traces:** 97

### Per-Variant Success Rates

| Variant | Success | Total | Rate | Pilot 3a Rate |
|---------|---------|-------|------|---------------|
| low | 13 | 26 | 50.0% | 20.0% |
| medium-low | 21 | 24 | 87.5% | 86.7% |
| base | 22 | 26 | 84.6% | 90.0% |
| high | 20 | 21 | 95.2% | 93.3% |
| **Overall** | **76** | **97** | **78.4%** | **72.5%** |

### Per-Task × Per-Variant Success Matrix (Text-Only)

| Task | low | medium-low | base | high |
|------|-----|------------|------|------|
| ecommerce:23 | 4/5 (80%) | 4/4 (100%) | 3/3 (100%) | 4/4 (100%) |
| ecommerce:24 | 3/4 (75%) | 5/5 (100%) | 5/5 (100%) | 3/3 (100%) |
| ecommerce:26 | 0/4 (0%) | 5/5 (100%) | 5/5 (100%) | 4/4 (100%) |
| ecommerce_admin:4 | 0/5 (0%) | 4/4 (100%) | 3/4 (75%) | 5/5 (100%) |
| reddit:29 | 3/5 (60%) | 1/2 (50%) | 4/4 (100%) | 3/3 (100%) |
| reddit:67 | 3/3 (100%) | 2/4 (50%) | 2/5 (40%) | 1/2 (50%) |

### Chi-Square Test: Low vs Base (Text-Only)

- Low: 13/26 success (50.0%)
- Base: 22/26 success (84.6%)
- χ² = 7.08, p = 0.007799, Cramér's V = 0.369
- Fisher's exact p = 0.016701
- **Significant:** YES (p < 0.05)

### Comparison with Pilot 3a

| Variant | Pilot 3a | Pilot 3b (text-only) | Δ |
|---------|----------|---------------------|---|
| low | 20.0% | 50.0% | +30.0pp |
| medium-low | 86.7% | 87.5% | +0.8pp |
| base | 90.0% | 84.6% | -5.4pp |
| high | 93.3% | 95.2% | +1.9pp |

### Variant Gradient (Text-Only)

- Base - Low gap: 34.6pp
- High - Low range: 45.2pp
- Low → Medium-Low step: 37.5pp
- Low→ML as fraction of total: 83%

## 3. Vision-Only Results

**Total vision-only traces:** 93

### Per-Variant Success Rates (Vision-Only)

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 0 | 27 | 0.0% |
| medium-low | 7 | 21 | 33.3% |
| base | 7 | 22 | 31.8% |
| high | 7 | 23 | 30.4% |
| **Overall** | **21** | **93** | **22.6%** |

### Per-Task × Per-Variant Success Matrix (Vision-Only)

| Task | low | medium-low | base | high |
|------|-----|------------|------|------|
| ecommerce:23 | 0/5 (0%) | 0/3 (0%) | 0/3 (0%) | 0/4 (0%) |
| ecommerce:24 | 0/5 (0%) | 3/3 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce:26 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/4 (0%) |
| ecommerce_admin:4 | 0/5 (0%) | 0/3 (0%) | 0/4 (0%) | 0/3 (0%) |
| reddit:29 | 0/5 (0%) | 0/3 (0%) | 0/2 (0%) | 0/3 (0%) |
| reddit:67 | 0/2 (0%) | 4/4 (100%) | 2/3 (67%) | 2/4 (50%) |

### Variant Gradient Analysis (Vision-Only)

- Base - Low gap: 31.8pp
- High - Low range: 30.4pp
- **Interpretation:** Moderate gradient → some visual impact from DOM changes

### Chi-Square Test: Low vs Base (Vision-Only)

- Low: 0/27 (0.0%)
- Base: 7/22 (31.8%)
- χ² = 10.02, p = 0.001546, Cramér's V = 0.452
- Fisher's exact p = 0.001985
- **Significant:** YES

## 4. Text-Only vs Vision-Only Comparison (Causal Inference)

### Side-by-Side Per-Variant Comparison

| Variant | Text-Only | Vision-Only | Δ (Text - Vision) |
|---------|-----------|-------------|-------------------|
| low | 50.0% | 0.0% | +50.0pp |
| medium-low | 87.5% | 33.3% | +54.2pp |
| base | 84.6% | 31.8% | +52.8pp |
| high | 95.2% | 30.4% | +64.8pp |

### Critical Interaction Test

**Question:** Does text-only show a stronger variant gradient than vision-only?

- Text-only gradient (base - low): 34.6pp
- Vision-only gradient (base - low): 31.8pp
- **Interaction effect:** 2.8pp

### Causal Interpretation

⚠️ **MIXED EVIDENCE:** Both agents show variant gradients. DOM mutations may have visual side effects that affect vision-only agent too.
- Text gradient: 34.6pp
- Vision gradient: 31.8pp
- But interaction still 2.8pp → text-only more affected

### Per-Task Interaction Effects

| Task | Text(base) | Text(low) | Text Δ | Vision(base) | Vision(low) | Vision Δ | Interaction |
|------|-----------|----------|--------|-------------|------------|---------|-------------|
| ecommerce:23 | 100% | 80% | +20pp | 0% | 0% | +0pp | +20pp |
| ecommerce:24 | 100% | 75% | +25pp | 100% | 0% | +100pp | -75pp |
| ecommerce:26 | 100% | 0% | +100pp | 0% | 0% | +0pp | +100pp |
| ecommerce_admin:4 | 75% | 0% | +75pp | 0% | 0% | +0pp | +75pp |
| reddit:29 | 100% | 60% | +40pp | 0% | 0% | +0pp | +40pp |
| reddit:67 | 40% | 100% | -60pp | 67% | 0% | +67pp | -127pp |

## 5. Token and Step Analysis

### Average Tokens by Agent Type × Variant

| Variant | Text-Only Avg | Text-Only Med | Vision-Only Avg | Vision-Only Med |
|---------|--------------|---------------|-----------------|-----------------|
| low | 175,372 | 103,711 | 80,455 | 90,261 |
| medium-low | 71,794 | 42,281 | 46,245 | 32,329 |
| base | 134,454 | 44,020 | 33,866 | 32,437 |
| high | 96,056 | 44,110 | 38,039 | 30,417 |

### Average Steps by Agent Type × Variant

| Variant | Text-Only Avg | Text-Only Med | Vision-Only Avg | Vision-Only Med |
|---------|--------------|---------------|-----------------|-----------------|
| low | 11.8 | 8.0 | 22.6 | 30.0 |
| medium-low | 4.1 | 3.0 | 12.6 | 10.0 |
| base | 5.1 | 3.0 | 10.7 | 10.0 |
| high | 4.6 | 3.0 | 12.5 | 10.0 |

### Average Duration (seconds) by Agent Type × Variant

| Variant | Text-Only Avg | Vision-Only Avg |
|---------|--------------|-----------------|
| low | 106.9s | 184.9s |
| medium-low | 68.9s | 121.7s |
| base | 63.5s | 101.7s |
| high | 57.7s | 116.1s |

### Overall Token Comparison

- Text-only: avg=121,605, median=68,008, min=9,905, max=617,418
- Vision-only: avg=51,219, median=34,147, min=1,829, max=154,506
- Vision/Text token ratio: 0.42x

### Token Usage: Success vs Failure

| Agent | Outcome | Avg Tokens | Avg Steps | Count |
|-------|---------|-----------|-----------|-------|
| text-only | Success | 81,780 | 4.9 | 76 |
| text-only | Failure | 265,736 | 12.5 | 21 |
| vision-only | Success | 35,802 | 10.9 | 21 |
| vision-only | Failure | 55,716 | 16.2 | 72 |

## 6. Failure Analysis

### Text-Only Failures

**Total failures:** 21

**By outcome type:**

| Outcome | Count |
|---------|-------|
| failure | 10 |
| partial_success | 7 |
| timeout | 4 |

**By variant:**

| Variant | Failures |
|---------|----------|
| low | 13 |
| medium-low | 3 |
| base | 4 |
| high | 1 |

**By task:**

| Task | Failures |
|------|----------|
| ecommerce_admin:4 | 6 |
| reddit:67 | 6 |
| ecommerce:26 | 4 |
| reddit:29 | 3 |
| ecommerce:23 | 1 |
| ecommerce:24 | 1 |

**Hit step limit (≥29 steps):** 4/21

### Vision-Only Failures

**Total failures:** 72

**By outcome type:**

| Outcome | Count |
|---------|-------|
| partial_success | 35 |
| timeout | 24 |
| failure | 13 |

**By variant:**

| Variant | Failures |
|---------|----------|
| low | 27 |
| medium-low | 14 |
| base | 15 |
| high | 16 |

**By task:**

| Task | Failures |
|------|----------|
| ecommerce:26 | 19 |
| ecommerce_admin:4 | 15 |
| ecommerce:23 | 15 |
| reddit:29 | 13 |
| ecommerce:24 | 5 |
| reddit:67 | 5 |

**Hit step limit (≥29 steps):** 26/72

### Comparative Failure Patterns

| Metric | Text-Only | Vision-Only |
|--------|-----------|-------------|
| Total failures | 21 | 72 |
| Hit step limit | 4 | 26 |
| Low variant failures | 13 | 27 |
| Base variant failures | 4 | 15 |

### Detailed Low-Variant Failures

#### Text-Only Low Failures

- `ecommerce_admin_low_4_0_1`: outcome=timeout, steps=30
- `ecommerce_admin_low_4_0_2`: outcome=timeout, steps=30
- `ecommerce_admin_low_4_0_3`: outcome=partial_success, steps=25
- `ecommerce_admin_low_4_0_4`: outcome=timeout, steps=30
- `ecommerce_admin_low_4_0_5`: outcome=timeout, steps=30
- `ecommerce_low_23_0_2`: outcome=failure, steps=5
- `ecommerce_low_24_0_4`: outcome=partial_success, steps=9
- `ecommerce_low_26_0_1`: outcome=failure, steps=6
- `ecommerce_low_26_0_2`: outcome=failure, steps=6
- `ecommerce_low_26_0_3`: outcome=partial_success, steps=6
- `ecommerce_low_26_0_4`: outcome=failure, steps=6
- `reddit_low_29_0_4`: outcome=partial_success, steps=10
- `reddit_low_29_0_5`: outcome=partial_success, steps=5

#### Vision-Only Low Failures

- `ecommerce_admin_low_4_1_1`: outcome=failure, steps=4
- `ecommerce_admin_low_4_1_2`: outcome=partial_success, steps=6
- `ecommerce_admin_low_4_1_3`: outcome=failure, steps=3
- `ecommerce_admin_low_4_1_4`: outcome=failure, steps=7
- `ecommerce_admin_low_4_1_5`: outcome=partial_success, steps=8
- `ecommerce_low_23_1_1`: outcome=timeout, steps=30
- `ecommerce_low_23_1_2`: outcome=timeout, steps=30
- `ecommerce_low_23_1_3`: outcome=timeout, steps=30
- `ecommerce_low_23_1_4`: outcome=partial_success, steps=30
- `ecommerce_low_23_1_5`: outcome=partial_success, steps=10
- `ecommerce_low_24_1_1`: outcome=timeout, steps=30
- `ecommerce_low_24_1_2`: outcome=timeout, steps=30
- `ecommerce_low_24_1_3`: outcome=timeout, steps=30
- `ecommerce_low_24_1_4`: outcome=timeout, steps=30
- `ecommerce_low_24_1_5`: outcome=timeout, steps=30
- `ecommerce_low_26_1_1`: outcome=partial_success, steps=10
- `ecommerce_low_26_1_2`: outcome=timeout, steps=30
- `ecommerce_low_26_1_3`: outcome=partial_success, steps=11
- `ecommerce_low_26_1_4`: outcome=partial_success, steps=11
- `ecommerce_low_26_1_5`: outcome=timeout, steps=30
- `reddit_low_29_1_1`: outcome=timeout, steps=30
- `reddit_low_29_1_2`: outcome=timeout, steps=30
- `reddit_low_29_1_3`: outcome=timeout, steps=30
- `reddit_low_29_1_4`: outcome=timeout, steps=30
- `reddit_low_29_1_5`: outcome=timeout, steps=30
- `reddit_low_67_1_4`: outcome=timeout, steps=30
- `reddit_low_67_1_5`: outcome=timeout, steps=30

## 7. Deep Interpretation and Causal Analysis

### Vision-Only Success is Task-Specific, Not Variant-Specific

The vision-only agent shows a striking pattern: success is concentrated in exactly 2 of 6 tasks (task 24 and task 67), and ONLY at non-low variants:

| Task | low | ml | base | high | Pattern |
|------|-----|-----|------|------|---------|
| ecommerce:23 | 0/5 | 0/3 | 0/3 | 0/4 | ❌ All fail |
| ecommerce:24 | 0/5 | 3/3 | 5/5 | 5/5 | ⚠️ Low=0%, others succeed |
| ecommerce:26 | 0/5 | 0/5 | 0/5 | 0/4 | ❌ All fail |
| ecommerce_admin:4 | 0/5 | 0/3 | 0/4 | 0/3 | ❌ All fail |
| reddit:29 | 0/5 | 0/3 | 0/2 | 0/3 | ❌ All fail |
| reddit:67 | 0/2 | 4/4 | 2/3 | 2/4 | ⚠️ Low=0%, others succeed |

### The 0% Low-Variant Vision-Only Pattern

**Critical observation:** Vision-only achieves 0/27 (0%) at low variant across ALL tasks.

This is unexpected if vision-only were truly unaffected by DOM mutations. Two possible explanations:

1. **Low variant DOM mutations have visual side effects** — the low variant patches (removing labels, breaking ARIA, converting links to spans) may change the visual rendering enough that SoM overlay labels shift or disappear, making the vision agent unable to identify correct click targets.

2. **SoM overlay depends on DOM structure** — Set-of-Mark overlays are generated from the DOM's interactive elements. If low variant removes interactive semantics (e.g., link→span), those elements may lose their SoM bid labels entirely, making them invisible to the vision-only agent.

**Implication:** The vision-only agent is NOT a pure visual control — it's affected by DOM mutations through the SoM overlay generation pipeline. The SoM bids are derived from the a11y tree / DOM interactive elements, so low variant mutations that remove interactive semantics also remove SoM labels.

### Revised Causal Model

```
Low variant DOM mutations
    ├── Path A: Degrade a11y tree → text-only agent fails (CONFIRMED)
    └── Path B: Remove interactive elements → SoM labels disappear → vision-only agent fails (NEW)
```

Both agents are affected by low variant, but through DIFFERENT mechanisms:
- Text-only: degraded semantic information in a11y tree text
- Vision-only: missing SoM bid labels on de-semanticized elements

### Effective Control Comparison: Non-Low Variants

Since low variant affects both agents (through different paths), the meaningful comparison is at non-low variants where SoM labels are intact:

| Agent | Non-Low Success | Rate |
|-------|----------------|------|
| Text-only | 63/71 | 88.7% |
| Vision-only | 21/66 | 31.8% |
| **Gap** | | **56.9pp** |

Text-only dramatically outperforms vision-only at non-low variants (88.7% vs 31.8%), confirming that the a11y tree provides substantial task-relevant information beyond what visual screenshots offer.

### Summary of Key Findings

1. **Text-only replicates Pilot 3a gradient:** low=50% → ml=87.5% → base=84.6% → high=95.2% (χ²=7.08, p=0.008 for low vs base)
2. **Vision-only has 0% success at low variant** (0/27), likely because SoM overlay depends on DOM interactive elements that low variant removes
3. **Vision-only overall success is 22.6%** (21/93), concentrated in tasks 24 and 67 only
4. **The interaction test is confounded** by SoM's DOM dependency — both agents are affected by low variant through different mechanisms
5. **Text-only >> vision-only at non-low variants** (88.7% vs 31.8%), confirming a11y tree's informational advantage
6. **Vision-only failures are predominantly timeouts** (17/27 at low, 24/72 overall), suggesting the agent gets stuck without proper SoM labels
7. **Text-only low failures concentrate in admin:4 and ecommerce:26** — the same tasks identified in Pilot 3a as token inflation / content invisibility pathways

### Implications for Experimental Design

The SoM overlay's dependence on DOM interactive elements means the vision-only agent is NOT a pure visual control as originally intended. For future experiments:

- **Alternative control:** Use raw screenshots without SoM overlay (pure pixel-level vision)
- **Or:** Use a fixed SoM overlay generated from the BASE variant DOM, applied to all variants
- **The current data still supports** the core finding that a11y tree quality affects text-only agent performance (low vs base: p=0.008)
- **New finding:** SoM-based vision agents are ALSO affected by DOM semantic quality, which is itself a novel contribution

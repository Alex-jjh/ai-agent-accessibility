# Pilot 4 Full Analysis (240/240 Cases)

**Run ID:** f4929214-3d48-443b-a859-dd013a737d50
**Total traces:** 240
**Design:** 6 tasks × 4 variants × 2 agents × 5 reps = 240
**Variant injection:** Plan D (context.route + deferred patch + MutationObserver)
**Date:** 2026-04-07
---

## 1. Data Inventory

**Total traces:** 240

**Text-only:** 120
**Vision-only:** 120

### Traces per Variant × Agent

| Variant | Text-Only | Vision-Only | Total |
|---------|-----------|-------------|-------|
| low | 30 | 30 | 60 |
| medium-low | 30 | 30 | 60 |
| base | 30 | 30 | 60 |
| high | 30 | 30 | 60 |

### Traces per Task × Variant

| Task | Variant | Text | Vision |
|------|---------|------|--------|
| ecommerce:23 | low | 5 | 5 |
| ecommerce:23 | medium-low | 5 | 5 |
| ecommerce:23 | base | 5 | 5 |
| ecommerce:23 | high | 5 | 5 |
| ecommerce:24 | low | 5 | 5 |
| ecommerce:24 | medium-low | 5 | 5 |
| ecommerce:24 | base | 5 | 5 |
| ecommerce:24 | high | 5 | 5 |
| ecommerce:26 | low | 5 | 5 |
| ecommerce:26 | medium-low | 5 | 5 |
| ecommerce:26 | base | 5 | 5 |
| ecommerce:26 | high | 5 | 5 |
| ecommerce_admin:4 | low | 5 | 5 |
| ecommerce_admin:4 | medium-low | 5 | 5 |
| ecommerce_admin:4 | base | 5 | 5 |
| ecommerce_admin:4 | high | 5 | 5 |
| reddit:29 | low | 5 | 5 |
| reddit:29 | medium-low | 5 | 5 |
| reddit:29 | base | 5 | 5 |
| reddit:29 | high | 5 | 5 |
| reddit:67 | low | 5 | 5 |
| reddit:67 | medium-low | 5 | 5 |
| reddit:67 | base | 5 | 5 |
| reddit:67 | high | 5 | 5 |

**Expected:** 240 | **Found:** 240 | **Missing:** 0

## 2. Text-Only Results (n=120)

### Per-Variant Success Rates

| Variant | Success | Total | Rate | Pilot 3a |
|---------|---------|-------|------|----------|
| low | 7 | 30 | 23.3% | 20.0% |
| medium-low | 30 | 30 | 100.0% | 86.7% |
| base | 26 | 30 | 86.7% | 90.0% |
| high | 23 | 30 | 76.7% | 93.3% |
| **Overall** | **86** | **120** | **71.7%** | **72.5%** |

### Task × Variant Matrix

| Task | low | med-low | base | high |
|------|-----|---------|------|------|
| ecommerce:23 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce:24 | 1/5 (20%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce:26 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce_admin:4 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) |
| reddit:29 | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 3/5 (60%) |
| reddit:67 | 2/5 (40%) | 5/5 (100%) | 1/5 (20%) | 1/5 (20%) |

### Chi-Square: Low vs Base

- Low: 7/30 (23.3%)
- Base: 26/30 (86.7%)
- χ² = 24.31, p = 0.000001, Cramér's V = 0.637
- Fisher's exact p = 0.000001
- **Significant:** YES

### Variant Gradient

- Base - Low gap: 63.3pp
- High - Low range: 53.3pp
- Low → Medium-Low step: 76.7pp
- Step fraction: 144%

## 3. Vision-Only Results (n=120)

### Per-Variant Success Rates

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 0 | 30 | 0.0% |
| medium-low | 7 | 30 | 23.3% |
| base | 6 | 30 | 20.0% |
| high | 9 | 30 | 30.0% |
| **Overall** | **22** | **120** | **18.3%** |

### Task × Variant Matrix

| Task | low | med-low | base | high |
|------|-----|---------|------|------|
| ecommerce:23 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |
| ecommerce:24 | 0/5 (0%) | 3/5 (60%) | 2/5 (40%) | 5/5 (100%) |
| ecommerce:26 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |
| ecommerce_admin:4 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |
| reddit:29 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |
| reddit:67 | 0/5 (0%) | 4/5 (80%) | 4/5 (80%) | 4/5 (80%) |

### Chi-Square: Low vs Base

- Low: 0/30 (0.0%)
- Base: 6/30 (20.0%)
- χ² = 6.67, p = 0.009823, V = 0.333
- **Significant:** YES


## 4. Text-Only vs Vision-Only (Causal Inference)

### Side-by-Side

| Variant | Text-Only | Vision-Only | Δ |
|---------|-----------|-------------|---|
| low | 23.3% | 0.0% | +23.3pp |
| medium-low | 100.0% | 23.3% | +76.7pp |
| base | 86.7% | 20.0% | +66.7pp |
| high | 76.7% | 30.0% | +46.7pp |

### Interaction Test

- Text gradient (base-low): 63.3pp
- Vision gradient (base-low): 20.0pp
- **Interaction:** 43.3pp

⚠️ **MIXED:** Both show gradient. Text=63.3pp, Vision=20.0pp

### Per-Task Interaction

| Task | T(base) | T(low) | TΔ | V(base) | V(low) | VΔ | Inter |
|------|---------|--------|-----|---------|--------|-----|-------|
| ecommerce:23 | 100% | 0% | +100pp | 0% | 0% | +0pp | +100pp |
| ecommerce:24 | 100% | 20% | +80pp | 40% | 0% | +40pp | +40pp |
| ecommerce:26 | 100% | 0% | +100pp | 0% | 0% | +0pp | +100pp |
| ecommerce_admin:4 | 100% | 0% | +100pp | 0% | 0% | +0pp | +100pp |
| reddit:29 | 100% | 80% | +20pp | 0% | 0% | +0pp | +20pp |
| reddit:67 | 20% | 40% | -20pp | 80% | 0% | +80pp | -100pp |

## 5. Token & Step Analysis

### Avg Tokens by Agent × Variant

| Variant | Text Avg | Text Med | Vision Avg | Vision Med |
|---------|----------|----------|------------|------------|
| low | 172,002 | 113,743 | 50,585 | 51,621 |
| medium-low | 93,996 | 42,763 | 34,283 | 34,350 |
| base | 134,833 | 43,988 | 28,486 | 20,384 |
| high | 149,809 | 44,318 | 36,131 | 25,468 |

### ISSUE-BR-4 Check: High vs Base Token Inflation

**text-only:** high avg=149,809, base avg=134,833, Δ=+14,976 (+11.1%)
**vision-only:** high avg=36,131, base avg=28,486, Δ=+7,645 (+26.8%)

### Avg Steps by Agent × Variant

| Variant | Text Avg | Vision Avg |
|---------|----------|------------|
| low | 10.9 | 16.1 |
| medium-low | 4.8 | 11.1 |
| base | 4.9 | 9.3 |
| high | 5.1 | 11.0 |

### Outcome Breakdown

| Outcome | Text-Only | Vision-Only |
|---------|-----------|-------------|
| success | 86 | 22 |
| failure | 21 | 54 |
| timeout | 3 | 4 |
| partial_success | 10 | 40 |

## 6. Failure Analysis

### Text-Only Failures (n=34)

| Outcome | Count |
|---------|-------|
| failure | 21 |
| partial_success | 10 |
| timeout | 3 |

| Variant | Failures |
|---------|----------|
| low | 23 |
| medium-low | 0 |
| base | 4 |
| high | 7 |

| Task | Failures |
|------|----------|
| reddit:67 | 11 |
| ecommerce_admin:4 | 6 |
| ecommerce:23 | 5 |
| ecommerce:26 | 5 |
| ecommerce:24 | 4 |
| reddit:29 | 3 |

**Hit step limit (≥29):** 3/34

### Vision-Only Failures (n=98)

| Outcome | Count |
|---------|-------|
| failure | 54 |
| partial_success | 40 |
| timeout | 4 |

| Variant | Failures |
|---------|----------|
| low | 30 |
| medium-low | 23 |
| base | 24 |
| high | 21 |

| Task | Failures |
|------|----------|
| ecommerce_admin:4 | 20 |
| ecommerce:23 | 20 |
| ecommerce:26 | 20 |
| reddit:29 | 20 |
| ecommerce:24 | 10 |
| reddit:67 | 8 |

**Hit step limit (≥29):** 4/98

## 7. Plan D Verification

### ecom:23 low text-only: 0/5

- `ecommerce_low_23_0_1`: success=False, tablist=False, tabpanel=False
- `ecommerce_low_23_0_2`: success=False, tablist=False, tabpanel=False
- `ecommerce_low_23_0_3`: success=False, tablist=False, tabpanel=False
- `ecommerce_low_23_0_4`: success=False, tablist=False, tabpanel=False
- `ecommerce_low_23_0_5`: success=False, tablist=False, tabpanel=False

### All Low Text-Only Results

| Task | Success | Total | Rate |
|------|---------|-------|------|
| ecommerce:23 | 0 | 5 | 0% |
| ecommerce:24 | 1 | 5 | 20% |
| ecommerce:26 | 0 | 5 | 0% |
| ecommerce_admin:4 | 0 | 5 | 0% |
| reddit:29 | 4 | 5 | 80% |
| reddit:67 | 2 | 5 | 40% |

### Goto Escape Check (low variant)

- `ecommerce_admin_low_4_0_1` step 4: goto("http://10.0.1.49:7780/admin/admin/reports/")
- `ecommerce_admin_low_4_0_2` step 3: goto("http://10.0.1.49:7780/admin/admin/reports/")
- `ecommerce_admin_low_4_0_3` step 3: goto("http://10.0.1.49:7780/admin/admin/reports/")
- `ecommerce_admin_low_4_0_4` step 3: goto("http://10.0.1.49:7780/admin/admin/reports/")
- `ecommerce_admin_low_4_0_5` step 3: goto("http://10.0.1.49:7780/admin/admin/reports/")
- `ecommerce_low_23_0_1` step 5: goto("http://10.0.1.49:7770/3-pack-samsung-galaxy-s6-screen-protector-nearpow-te
- `ecommerce_low_23_0_2` step 5: goto("http://10.0.1.49:7770/3-pack-samsung-galaxy-s6-screen-protector-nearpow-te
- `ecommerce_low_23_0_3` step 5: goto("http://10.0.1.49:7770/3-pack-samsung-galaxy-s6-screen-protector-nearpow-te
- `ecommerce_low_23_0_5` step 5: goto("http://10.0.1.49:7770/3-pack-samsung-galaxy-s6-screen-protector-nearpow-te
- `ecommerce_low_24_0_1` step 4: goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5
- `ecommerce_low_24_0_2` step 7: goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5
- `ecommerce_low_24_0_3` step 4: goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5
- `ecommerce_low_24_0_4` step 6: goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5
- `ecommerce_low_24_0_5` step 4: goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5
- `ecommerce_low_26_0_1` step 4: goto("http://10.0.1.49:7770/epson-workforce-wf-3620-wifi-direct-all-in-one-color
- `ecommerce_low_26_0_2` step 4: goto("http://10.0.1.49:7770/epson-workforce-wf-3620-wifi-direct-all-in-one-color
- `ecommerce_low_26_0_3` step 4: goto("http://10.0.1.49:7770/epson-workforce-wf-3620-wifi-direct-all-in-one-color
- `ecommerce_low_26_0_4` step 4: goto("http://10.0.1.49:7770/epson-workforce-wf-3620-wifi-direct-all-in-one-color
- `ecommerce_low_26_0_5` step 4: goto("http://10.0.1.49:7770/epson-workforce-wf-3620-wifi-direct-all-in-one-color
- `reddit_low_29_0_1` step 3: goto("http://10.0.1.49:9999/f/DIY")
- `reddit_low_29_0_2` step 3: goto("http://10.0.1.49:9999/f/DIY")
- `reddit_low_29_0_3` step 3: goto("http://10.0.1.49:9999/f/DIY")
- `reddit_low_29_0_4` step 3: goto("http://10.0.1.49:9999/user/Maoman1")
- `reddit_low_29_0_5` step 3: goto("http://10.0.1.49:9999/f/DIY")
- `reddit_low_29_1_2` step 15: goto("http://10.0.1.49:9999/")
- `reddit_low_67_0_1` step 2: goto("http://10.0.1.49:9999/forums")
- `reddit_low_67_0_2` step 2: goto("http://10.0.1.49:9999/forums")
- `reddit_low_67_0_3` step 5: goto("http://10.0.1.49:9999/f/books")
- `reddit_low_67_0_4` step 2: goto("http://10.0.1.49:9999/forums")
- `reddit_low_67_0_5` step 2: goto("http://10.0.1.49:9999/forums")
- `reddit_low_67_1_2` step 17: goto("http://10.0.1.49:9999/f/books")
- `reddit_low_67_1_3` step 20: goto("http://10.0.1.49:9999/r/books")
- `reddit_low_67_1_5` step 17: goto("http://10.0.1.49:9999/r/books")

⚠️ 33 traces with goto() in low variant

## 8. Deep Interpretation

### Non-Low Variant Comparison

| Agent | Success | Rate |
|-------|---------|------|
| Text-only | 79/90 | 87.8% |
| Vision-only | 22/90 | 24.4% |
| **Gap** | | **63.3pp** |

### Comparison with Pilot 3a

| Variant | Pilot 3a | Pilot 4 | Δ |
|---------|----------|---------|---|
| low | 20.0% | 23.3% | +3.3pp |
| medium-low | 86.7% | 100.0% | +13.3pp |
| base | 90.0% | 86.7% | -3.3pp |
| high | 93.3% | 76.7% | -16.6pp |

### Key Findings

1. **Text-only gradient:** low=23.3% → ml=100.0% → base=86.7% → high=76.7%
2. **Step function:** low→ml jump = 76.7pp (144% of total)
3. **Vision-only overall:** 22/120
4. **Interaction effect:** 43.3pp (text gradient 63.3pp vs vision 20.0pp)
5. **Non-low gap:** text 87.8% vs vision 24.4% = 63.3pp advantage

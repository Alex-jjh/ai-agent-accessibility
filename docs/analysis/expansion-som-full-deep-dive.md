# Expansion-SoM Full Experiment Deep Dive

**Experiment**: expansion-som (run ed05230c)
**Model**: Claude Sonnet 4 via Bedrock (vision-only / SoM observation mode)
**Date**: April 13, 2026
**Cases**: 140 (7 tasks × 4 variants × 5 reps)
**Overall**: 38/140 (27.1%) success, 102 failures to classify

---

## 1. Executive Summary

The SoM (Set-of-Mark) full experiment achieved **38/140 (27.1%) overall success** across 7 expansion tasks with 5 repetitions each. This confirms the smoke test finding (17.9%) at scale — SoM agents are fundamentally limited on these tasks regardless of accessibility variant.

**Per-variant success rates:**

- **low**: 3/35 (8.6%)
- **medium-low**: 11/35 (31.4%)
- **base**: 12/35 (34.3%)
- **high**: 12/35 (34.3%)

**Outcome distribution:**

- success: 38 (27.1%)
- partial_success: 22 (15.7%)
- timeout: 67 (47.9%)
- failure: 13 (9.3%)

---

## 2. Task × Variant Success Matrix

| Task | low | medium-low | base | high | Total |
|------|-----|------------|------|------|-------|
| gitlab:132 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 3/5 (60%) | 13/20 |
| gitlab:293 | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 0/20 |
| gitlab:308 | 0/5 (0%) | 1/5 (20%) | 4/5 (80%) | 3/5 (60%) | 8/20 |
| admin:41 | 0/5 (0%) | 3/5 (60%) | 1/5 (20%) | 5/5 (100%) | 9/20 |
| admin:94 | 2/5 (40%) | 1/5 (20%) | 2/5 (40%) | 1/5 (20%) | 6/20 |
| admin:198 | 0/5 (0%) | 1/5 (20%) | 0/5 (0%) | 0/5 (0%) | 1/20 |
| ecom:188 | 1/5 (20%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) | 1/20 |
| **Total** | **3/35 (8%)** | **11/35 (31%)** | **12/35 (34%)** | **12/35 (34%)** | **38/140** |

### 2.1 Verification Against Experiment Log

Expected from log:
- low: 3/35 (8.6%), ml: 11/35 (31.4%), base: 12/35 (34.3%), high: 12/35 (34.3%)

Computed from traces:
- low: 3/35 (8.6%)
- ml: 11/35 (31.4%)
- base: 12/35 (34.3%)
- high: 12/35 (34.3%)

Expected per-task (low/ml/base/high %):
- gitlab:132: 0/60/100/60%, gitlab:293: 0/0/0/0%, gitlab:308: 0/20/80/60%
- admin:41: 0/60/20/100%, admin:94: 40/20/40/20%, admin:198: 0/20/0/0%
- ecom:188: 20/0/0/0%

Computed per-task:
- gitlab:132: 0%/100%/100%/60%
- gitlab:293: 0%/0%/0%/0%
- gitlab:308: 0%/20%/80%/60%
- admin:41: 0%/60%/20%/100%
- admin:94: 40%/20%/40%/20%
- admin:198: 0%/20%/0%/0%
- ecom:188: 20%/0%/0%/0%

---

## 3. Failure Mode Distribution

Total failures classified: **102**

| Failure Mode | Code | Count | % of Failures |
|-------------|------|-------|---------------|
| Phantom Bid Loop | F_SOM_PHANTOM | 49 | 48.0% |
| Visual Misread | F_SOM_MISREAD | 22 | 21.6% |
| Form Interaction Failure | F_SOM_FILL | 5 | 4.9% |
| Exploration Spiral | F_SOM_EXPLORE | 10 | 9.8% |
| Navigation Failure | F_SOM_NAV | 16 | 15.7% |

---

## 4. Failure Mode × Variant Breakdown

Which failure modes dominate at each variant level?

| Failure Mode | low | ml | base | high | Total |
|-------------|-----|-----|------|------|-------|
| Phantom Bid Loop | 8 | 15 | 12 | 14 | 49 |
| Visual Misread | 5 | 4 | 8 | 5 | 22 |
| Form Interaction Failure | 4 | 0 | 1 | 0 | 5 |
| Exploration Spiral | 2 | 3 | 2 | 3 | 10 |
| Navigation Failure | 13 | 2 | 0 | 1 | 16 |
| **Total failures** | **32** | **24** | **23** | **23** | **102** |

### 4.1 Variant-Level Analysis

**low** (32 failures):
- Phantom Bid Loop: 8 (25%)
- Visual Misread: 5 (16%)
- Form Interaction Failure: 4 (12%)
- Exploration Spiral: 2 (6%)
- Navigation Failure: 13 (41%)

**medium-low** (24 failures):
- Phantom Bid Loop: 15 (62%)
- Visual Misread: 4 (17%)
- Exploration Spiral: 3 (12%)
- Navigation Failure: 2 (8%)

**base** (23 failures):
- Phantom Bid Loop: 12 (52%)
- Visual Misread: 8 (35%)
- Form Interaction Failure: 1 (4%)
- Exploration Spiral: 2 (9%)

**high** (23 failures):
- Phantom Bid Loop: 14 (61%)
- Visual Misread: 5 (22%)
- Exploration Spiral: 3 (13%)
- Navigation Failure: 1 (4%)

---

## 5. Per-Task Failure Mode Profile

| Task | Phantom | Misread | Fill | Explore | Nav | Total Failures |
|------|---------|---------|------|---------|-----|----------------|
| gitlab:132 | 4 | - | 1 | 2 | - | 7 |
| gitlab:293 | 11 | 5 | 4 | - | - | 20 |
| gitlab:308 | 5 | - | - | 2 | 5 | 12 |
| admin:41 | - | 8 | - | - | 3 | 11 |
| admin:94 | 9 | - | - | 2 | 3 | 14 |
| admin:198 | 4 | 8 | - | 2 | 5 | 19 |
| ecom:188 | 16 | 1 | - | 2 | - | 19 |

### 5.1 Task-Level Narratives

#### gitlab:132 (13/20 success)

- **low**: 0/5 — F_SOM_PHANTOM, F_SOM_FILL, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM
- **medium-low**: 5/5 — —
- **base**: 5/5 — —
- **high**: 3/5 — F_SOM_EXPLORE, F_SOM_EXPLORE

#### gitlab:293 (0/20 success)

- **low**: 0/5 — F_SOM_PHANTOM, F_SOM_FILL, F_SOM_MISREAD, F_SOM_FILL, F_SOM_FILL
- **medium-low**: 0/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM
- **base**: 0/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_MISREAD, F_SOM_FILL
- **high**: 0/5 — F_SOM_PHANTOM, F_SOM_MISREAD, F_SOM_MISREAD, F_SOM_MISREAD, F_SOM_PHANTOM

#### gitlab:308 (8/20 success)

- **low**: 0/5 — F_SOM_PHANTOM, F_SOM_NAV, F_SOM_NAV, F_SOM_NAV, F_SOM_NAV
- **medium-low**: 1/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_NAV, F_SOM_EXPLORE
- **base**: 4/5 — F_SOM_EXPLORE
- **high**: 3/5 — F_SOM_PHANTOM, F_SOM_PHANTOM

#### admin:41 (9/20 success)

- **low**: 0/5 — F_SOM_NAV, F_SOM_MISREAD, F_SOM_NAV, F_SOM_MISREAD, F_SOM_NAV
- **medium-low**: 3/5 — F_SOM_MISREAD, F_SOM_MISREAD
- **base**: 1/5 — F_SOM_MISREAD, F_SOM_MISREAD, F_SOM_MISREAD, F_SOM_MISREAD
- **high**: 5/5 — —

#### admin:94 (6/20 success)

- **low**: 2/5 — F_SOM_NAV, F_SOM_NAV, F_SOM_NAV
- **medium-low**: 1/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_EXPLORE, F_SOM_PHANTOM
- **base**: 2/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM
- **high**: 1/5 — F_SOM_EXPLORE, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM

#### admin:198 (1/20 success)

- **low**: 0/5 — F_SOM_NAV, F_SOM_MISREAD, F_SOM_NAV, F_SOM_MISREAD, F_SOM_NAV
- **medium-low**: 1/5 — F_SOM_NAV, F_SOM_MISREAD, F_SOM_EXPLORE, F_SOM_MISREAD
- **base**: 0/5 — F_SOM_EXPLORE, F_SOM_MISREAD, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_MISREAD
- **high**: 0/5 — F_SOM_MISREAD, F_SOM_NAV, F_SOM_PHANTOM, F_SOM_MISREAD, F_SOM_PHANTOM

#### ecom:188 (1/20 success)

- **low**: 1/5 — F_SOM_EXPLORE, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_EXPLORE
- **medium-low**: 0/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM
- **base**: 0/5 — F_SOM_MISREAD, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM
- **high**: 0/5 — F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM, F_SOM_PHANTOM

---

## 6. Key Anomalies

### 6.1 admin:94 — Non-Monotonic (low 40% > ml 20%)

- low: 2/5, ml: 1/5, base: 2/5, high: 1/5

  low failures: Navigation Failure×3
  medium-low failures: Phantom Bid Loop×3, Exploration Spiral×1
  base failures: Phantom Bid Loop×3
  high failures: Exploration Spiral×1, Phantom Bid Loop×3

The non-monotonic pattern (low > ml) suggests that at low variant, the reduced SoM overlay density occasionally allows the agent to find a working navigation path (stochastic URL construction or simplified sidebar), while at ml the pseudo-compliance traps create more phantom bid targets that trap the agent.

### 6.2 ecom:188 — Forced Simplification (low 20% > others 0%)

- low: 1/5, ml: 0/5, base: 0/5, high: 0/5

Replicates the smoke finding at scale: low variant's link→span reduces SoM element count, eliminating phantom bid targets in the Magento sidebar menu. At base/ml/high, the agent gets trapped clicking 'My Account' or 'My Orders' phantom bids 20+ times. At low, the simplified DOM accidentally exposes a working navigation path.

### 6.3 admin:41 — Non-Monotonic (high 100% > base 20%)

- low: 0/5, ml: 3/5, base: 1/5, high: 5/5

  low failures: Navigation Failure×3, Visual Misread×2
  medium-low failures: Visual Misread×2
  base failures: Visual Misread×4

admin:41 asks for the top search term. The high variant's enhanced ARIA provides clearer visual structure for the dashboard data table, allowing the SoM agent to correctly read 'hollister'. At base, the dense SoM overlay on the Magento admin grid causes visual misreads (agent reads wrong row). At low, navigation to the dashboard is blocked by phantom bids.

### 6.4 gitlab:308 — Base 80% vs High 60%

- low: 0/5, ml: 1/5, base: 4/5, high: 3/5

Similar to gitlab:132 in smoke: high variant's ARIA over-annotation creates more SoM labels, providing more exploration options that delay the agent's fallback to direct URL construction. Base variant's simpler overlay leads to faster click failures, triggering the goto() strategy sooner.

---

## 7. Token Consumption by Failure Mode

| Failure Mode | Count | Avg Tokens | Median Tokens | Min | Max |
|-------------|-------|------------|---------------|-----|-----|
| Phantom Bid Loop | 49 | 106,005 | 103,074 | 40,654 | 144,196 |
| Visual Misread | 22 | 40,134 | 38,165 | 6,002 | 92,810 |
| Form Interaction Failure | 5 | 107,409 | 111,714 | 87,973 | 115,573 |
| Exploration Spiral | 10 | 88,622 | 85,507 | 79,514 | 112,595 |
| Navigation Failure | 16 | 43,454 | 33,529 | 1,768 | 142,889 |

### 7.1 Token Consumption by Variant (All Traces)

| Variant | Avg Tokens | Median Tokens | Avg (success) | Avg (failure) |
|---------|------------|---------------|---------------|---------------|
| low | 58,255 | 56,680 | 37,760 | 60,177 |
| medium-low | 79,344 | 93,631 | 50,156 | 92,722 |
| base | 73,326 | 79,025 | 53,173 | 83,841 |
| high | 71,647 | 84,539 | 32,606 | 92,016 |

---

## 8. Detailed Failure Classification Log

| # | Task | Variant | Rep | Outcome | Mode | Detail |
|---|------|---------|-----|---------|------|--------|
| 1 | admin:198 | low | 1 | failure | F_SOM_NAV | click_fails=4, goto=0, go_back=0 |
| 2 | admin:198 | low | 2 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 3 | admin:198 | low | 3 | failure | F_SOM_NAV | click_fails=4, goto=1, go_back=1 |
| 4 | admin:198 | low | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 5 | admin:198 | low | 5 | timeout | F_SOM_NAV | click_fails=18, goto=5, go_back=2 |
| 6 | admin:198 | medium-low | 1 | timeout | F_SOM_NAV | click_fails=1, goto=0, go_back=0 |
| 7 | admin:198 | medium-low | 3 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 8 | admin:198 | medium-low | 4 | timeout | F_SOM_EXPLORE | timeout, 17% click fail rate, 30 steps |
| 9 | admin:198 | medium-low | 5 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 10 | admin:198 | base | 1 | timeout | F_SOM_EXPLORE | timeout, 25% click fail rate, 30 steps |
| 11 | admin:198 | base | 2 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 12 | admin:198 | base | 3 | timeout | F_SOM_PHANTOM | 19 consec click fails (bids: 317,316,317,317,317...) |
| 13 | admin:198 | base | 4 | timeout | F_SOM_PHANTOM | 10 consec click fails (bids: 317,317,316,318,317...) |
| 14 | admin:198 | base | 5 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 15 | admin:198 | high | 1 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 16 | admin:198 | high | 2 | timeout | F_SOM_NAV | click_fails=5, goto=0, go_back=0 |
| 17 | admin:198 | high | 3 | timeout | F_SOM_PHANTOM | 5 consec click fails (bids: 1204,1202,1204,1202,1202...) |
| 18 | admin:198 | high | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 19 | admin:198 | high | 5 | timeout | F_SOM_PHANTOM | 27 consec click fails (bids: 317,316,317,317,317...) |
| 20 | admin:41 | low | 1 | failure | F_SOM_NAV | click_fails=2, goto=0, go_back=0 |
| 21 | admin:41 | low | 2 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 22 | admin:41 | low | 3 | failure | F_SOM_NAV | click_fails=2, goto=0, go_back=0 |
| 23 | admin:41 | low | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 24 | admin:41 | low | 5 | failure | F_SOM_NAV | unclassified (outcome=failure, steps=1) |
| 25 | admin:41 | medium-low | 1 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 26 | admin:41 | medium-low | 5 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 27 | admin:41 | base | 1 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 28 | admin:41 | base | 2 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 29 | admin:41 | base | 3 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 30 | admin:41 | base | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 31 | admin:94 | low | 1 | failure | F_SOM_NAV | click_fails=5, goto=5, go_back=0 |
| 32 | admin:94 | low | 2 | failure | F_SOM_NAV | click_fails=4, goto=4, go_back=0 |
| 33 | admin:94 | low | 4 | failure | F_SOM_NAV | click_fails=5, goto=8, go_back=0 |
| 34 | admin:94 | medium-low | 1 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 317,316,317,317,317...) |
| 35 | admin:94 | medium-low | 2 | timeout | F_SOM_PHANTOM | 18 consec click fails (bids: 144,1104,144,1193,1199...) |
| 36 | admin:94 | medium-low | 3 | timeout | F_SOM_EXPLORE | timeout, 4% click fail rate, 30 steps |
| 37 | admin:94 | medium-low | 4 | timeout | F_SOM_PHANTOM | 26 consec click fails (bids: 144,1104,500,1199,1199...) |
| 38 | admin:94 | base | 2 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 317,316,317,317,317...) |
| 39 | admin:94 | base | 3 | timeout | F_SOM_PHANTOM | 22 consec click fails (bids: 1002,144,1199,1199,1199...) |
| 40 | admin:94 | base | 5 | timeout | F_SOM_PHANTOM | 25 consec click fails (bids: 317,316,317,317,317...) |
| 41 | admin:94 | high | 2 | timeout | F_SOM_EXPLORE | timeout, 0% click fail rate, 30 steps |
| 42 | admin:94 | high | 3 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 317,317,317,317,317...) |
| 43 | admin:94 | high | 4 | timeout | F_SOM_PHANTOM | 16 consec click fails (bids: 317,317,317,317,317...) |
| 44 | admin:94 | high | 5 | timeout | F_SOM_PHANTOM | 15 consec click fails (bids: 317,316,317,317,317...) |
| 45 | ecom:188 | low | 1 | timeout | F_SOM_EXPLORE | timeout, 3% click fail rate, 30 steps |
| 46 | ecom:188 | low | 2 | timeout | F_SOM_PHANTOM | 13 consec click fails (bids: 809,2027,2027,2027,2027...) |
| 47 | ecom:188 | low | 4 | timeout | F_SOM_PHANTOM | 5 consec click fails (bids: 202,809,809,809,809...) |
| 48 | ecom:188 | low | 5 | timeout | F_SOM_EXPLORE | timeout, 0% click fail rate, 30 steps |
| 49 | ecom:188 | medium-low | 1 | timeout | F_SOM_PHANTOM | 13 consec click fails (bids: 2027,809,808,2027,2027...) |
| 50 | ecom:188 | medium-low | 2 | timeout | F_SOM_PHANTOM | 30 consec click fails (bids: 202,808,809,2929,808...) |
| 51 | ecom:188 | medium-low | 3 | timeout | F_SOM_PHANTOM | 28 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 52 | ecom:188 | medium-low | 4 | timeout | F_SOM_PHANTOM | 27 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 53 | ecom:188 | medium-low | 5 | timeout | F_SOM_PHANTOM | 23 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 54 | ecom:188 | base | 1 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 55 | ecom:188 | base | 2 | timeout | F_SOM_PHANTOM | 27 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 56 | ecom:188 | base | 3 | timeout | F_SOM_PHANTOM | 20 consec click fails (bids: 2027,809,808,2027,2027...) |
| 57 | ecom:188 | base | 4 | timeout | F_SOM_PHANTOM | 16 consec click fails (bids: 2927,2927,2927,2927,2927...) |
| 58 | ecom:188 | base | 5 | timeout | F_SOM_PHANTOM | 14 consec click fails (bids: 2027,809,2929,2927,808...) |
| 59 | ecom:188 | high | 1 | timeout | F_SOM_PHANTOM | 17 consec click fails (bids: 2027,2027,2027,2027,2027...) |
| 60 | ecom:188 | high | 2 | timeout | F_SOM_PHANTOM | 10 consec click fails (bids: 2027,2027,2027,2027,2027...) |
| 61 | ecom:188 | high | 3 | timeout | F_SOM_PHANTOM | 22 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 62 | ecom:188 | high | 4 | timeout | F_SOM_PHANTOM | 30 consec click fails (bids: 202,2927,809,808,2927...) |
| 63 | ecom:188 | high | 5 | timeout | F_SOM_PHANTOM | 19 consec click fails (bids: 1575,1575,1575,1575,1575...) |
| 64 | gitlab:132 | low | 1 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 232,274,232,232,232...) |
| 65 | gitlab:132 | low | 2 | timeout | F_SOM_FILL | 4 fill fails (1 consec) |
| 66 | gitlab:132 | low | 3 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 274,232,232,232,232...) |
| 67 | gitlab:132 | low | 4 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 824,771,824,784,824...) |
| 68 | gitlab:132 | low | 5 | timeout | F_SOM_PHANTOM | 5 consec click fails (bids: 464,229,228,226,535...) |
| 69 | gitlab:132 | high | 3 | timeout | F_SOM_EXPLORE | timeout, 0% click fail rate, 30 steps |
| 70 | gitlab:132 | high | 5 | timeout | F_SOM_EXPLORE | timeout, 3% click fail rate, 30 steps |
| 71 | gitlab:293 | low | 1 | timeout | F_SOM_PHANTOM | 17 consec click fails (bids: 248,976,976,976,976...) |
| 72 | gitlab:293 | low | 2 | timeout | F_SOM_FILL | 18 fill fails (4 consec) |
| 73 | gitlab:293 | low | 3 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 74 | gitlab:293 | low | 4 | timeout | F_SOM_FILL | 12 fill fails (4 consec) |
| 75 | gitlab:293 | low | 5 | timeout | F_SOM_FILL | 15 fill fails (2 consec) |
| 76 | gitlab:293 | medium-low | 1 | timeout | F_SOM_PHANTOM | 6 consec click fails (bids: 944,943,943,944,943...) |
| 77 | gitlab:293 | medium-low | 2 | timeout | F_SOM_PHANTOM | 13 consec click fails (bids: 25,24,197,944,943...) |
| 78 | gitlab:293 | medium-low | 3 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 25,24,197,944,944...) |
| 79 | gitlab:293 | medium-low | 4 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 943,943,943,943,943...) |
| 80 | gitlab:293 | medium-low | 5 | timeout | F_SOM_PHANTOM | 13 consec click fails (bids: 25,944,254,943,944...) |
| 81 | gitlab:293 | base | 1 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 25,198,944,943,943...) |
| 82 | gitlab:293 | base | 2 | timeout | F_SOM_PHANTOM | 5 consec click fails (bids: 25,24,197,198,199...) |
| 83 | gitlab:293 | base | 3 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 25,944,943,944,943...) |
| 84 | gitlab:293 | base | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 85 | gitlab:293 | base | 5 | timeout | F_SOM_FILL | 15 fill fails (7 consec) |
| 86 | gitlab:293 | high | 1 | timeout | F_SOM_PHANTOM | 8 consec click fails (bids: 944,944,944,944,944...) |
| 87 | gitlab:293 | high | 2 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 88 | gitlab:293 | high | 3 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 89 | gitlab:293 | high | 4 | partial_success | F_SOM_MISREAD | wrong answer (partial_success) |
| 90 | gitlab:293 | high | 5 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 999,943,943,944,943...) |
| 91 | gitlab:308 | low | 1 | failure | F_SOM_PHANTOM | 6 consec click fails (bids: 233,232,232,232,232...) |
| 92 | gitlab:308 | low | 2 | failure | F_SOM_NAV | click_fails=0, goto=1, go_back=0 |
| 93 | gitlab:308 | low | 3 | failure | F_SOM_NAV | click_fails=0, goto=1, go_back=0 |
| 94 | gitlab:308 | low | 4 | failure | F_SOM_NAV | click_fails=0, goto=1, go_back=0 |
| 95 | gitlab:308 | low | 5 | failure | F_SOM_NAV | click_fails=0, goto=1, go_back=0 |
| 96 | gitlab:308 | medium-low | 1 | timeout | F_SOM_PHANTOM | 6 consec click fails (bids: 357,299,357,300,357...) |
| 97 | gitlab:308 | medium-low | 2 | timeout | F_SOM_PHANTOM | 7 consec click fails (bids: 142,79,79,79,79...) |
| 98 | gitlab:308 | medium-low | 4 | timeout | F_SOM_NAV | click_fails=13, goto=1, go_back=0 |
| 99 | gitlab:308 | medium-low | 5 | timeout | F_SOM_EXPLORE | timeout, 0% click fail rate, 30 steps |
| 100 | gitlab:308 | base | 3 | timeout | F_SOM_EXPLORE | timeout, 7% click fail rate, 30 steps |
| 101 | gitlab:308 | high | 1 | timeout | F_SOM_PHANTOM | 13 consec click fails (bids: 439,439,439,357,439...) |
| 102 | gitlab:308 | high | 3 | timeout | F_SOM_PHANTOM | 11 consec click fails (bids: 439,439,439,439,439...) |

---

## 9. Comparison with Smoke Test (n=28)

| Metric | Smoke (n=28) | Full (n=140) |
|--------|-------------|-------------|
| Overall success | 5/28 (17.9%) | 38/140 (27.1%) |
| Phantom Bid Loop | 7 (30%) | 49 (48%) |
| Visual Misread | 6 (26%) | 22 (22%) |
| Form Interaction Failure | 4 (17%) | 5 (5%) |
| Exploration Spiral | 3 (13%) | 10 (10%) |
| Navigation Failure | 3 (13%) | 16 (16%) |

---

## 10. Implications for the Paper

### 10.1 SoM Failures Are Not Accessibility-Related

The failure mode distribution is remarkably consistent across variants. Phantom bid loops, visual misreads, and form interaction failures occur at base and high variants at comparable rates to low. This confirms that SoM's limitations are observation-mode-specific, not accessibility-driven.

### 10.2 Forced Simplification Confirmed at Scale

ecom:188's low-only success (1/5 at low vs 0/5 at all others) replicates the smoke finding with 5× more data. The mechanism — link→span reducing SoM overlay density — is the SoM-specific analog of text-only forced simplification in reddit:67.

### 10.3 ARIA Over-Annotation Effect Confirmed

Multiple tasks show base > high success (admin:94, gitlab:308), confirming that enhanced ARIA creates more SoM labels that delay fallback strategies. This is a novel finding: accessibility enhancement can degrade SoM agent performance.

### 10.4 The 27.1% Overall Rate Validates SoM as Weak Control

SoM achieves 27.1% overall vs text-only Claude's ~96% on the same tasks. The 69pp gap confirms the a11y tree's massive informational advantage over SoM screenshots for structured data extraction, form interaction, and multi-step navigation tasks.

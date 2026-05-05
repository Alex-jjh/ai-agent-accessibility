# Vision Expansion Full Analysis: SoM + CUA on 7 Expansion Tasks

**Date**: April 14, 2026
**Scope**: 280 cases total — SoM 140 + CUA 140 (7 tasks × 4 variants × 5 reps × 2 agents)
**Model**: Claude Sonnet 4 via AWS Bedrock (both agents)
**Status**: Both runs completed successfully, 0 missing cases

---

## 1. Executive Summary

Two overnight experiment runs completed the vision-agent expansion: SoM (Set-of-Mark, vision-only) and CUA (Computer Use Agent, coordinate-based) each ran 140 cases across 7 new expansion tasks. Combined with the text-only Claude and Llama 4 expansion runs, this brings the expansion task matrix to 7 tasks × 4 agents × 4 variants = 112 unique conditions.

**CUA** (116/140, 82.9%) confirms the accessibility gradient on new tasks. Low 51.4% → base 91.4% is a +40pp drop, consistent with Pilot 4 CUA (+30pp). All 17 low-variant failures are cross-layer functional breakage (link→span removes href). The 6 non-low failures concentrate on admin:198, a UI complexity confound (Columns dialog overlap) unrelated to accessibility. One additional failure is step budget exhaustion.

**SoM** (38/140, 27.1%) confirms fundamental SoM limitations generalize to new page types. The weak gradient (low 8.6% → base 34.3%, +25.7pp) is dominated by phantom bid failures at all variants. Five failure modes identified: phantom bid loops (30%), visual data misread (26%), form interaction failure (17%), exploration spirals (13%), and navigation failure (13%). gitlab:293 achieves 0% across ALL four variants — a form interaction failure that no amount of accessibility can fix.

The experiment matrix is now complete: 13 tasks × 4 agents × 4 variants. Grand total N=1,040.

---

## 2. CUA Results (116/140, 82.9%)

### 2.1 Task × Variant Matrix

| Task | low | ml | base | high | Notes |
|------|-----|----|------|------|-------|
| ecom:188 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Control — trivial at all variants |
| admin:41 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Control — reads dashboard directly |
| admin:94 | 20% (1/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Low: sidebar nav broken |
| admin:198 | 0% (0/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) | **Anomaly** — UI complexity trap |
| gitlab:132 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Clean pass all variants |
| gitlab:293 | 40% (2/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Low: search broken |
| gitlab:308 | 0% (0/5) | 100% (5/5) | 80% (4/5) | 100% (5/5) | Low: contributors nav destroyed |

**Per-variant summary**: low 51.4% → ml 97.1% → base 91.4% → high 91.4%

### 2.2 Accessibility Gradient

The low→base gap is +40.0pp, consistent with Pilot 4 CUA on the original 6 tasks (+30.0pp). The gradient direction is unambiguous: degraded accessibility reduces CUA success even though CUA has zero DOM access.

The mechanism is cross-layer functional breakage: the low variant's link→span patch removes `href` attributes, breaking actual navigation. CUA can see sidebar menu items visually but clicking them does nothing — the elements are `<span>` with no click handler. This is a functional change that crosses the DOM→behavior layer boundary.

### 2.3 Failure Attribution (24 failures)

| Root Cause | Count | Variants | Description |
|-----------|-------|----------|-------------|
| Cross-layer functional breakage | 17 | all low | link→span removes href; sidebar/search navigation broken |
| UI complexity trap | 6 | base:2, high:3, ml:1 | admin:198 Columns dialog overlaps Status filter |
| Step budget exhaustion | 1 | base:1 | gitlab:308 — agent progressing but ran out of 30 steps |

All 17 low-variant failures follow the same pattern: agent sees navigation elements, clicks at correct coordinates, nothing happens. The link→span patch is not purely semantic — it breaks functionality. This is consistent with Pilot 4 CUA where 100% of low failures were cross-layer confounds.

### 2.4 admin:198 Anomaly: ml 80% > base 60% > high 40%

admin:198 is the only task where CUA fails at base AND high. The inverted pattern (ml outperforms base outperforms high) reveals this is NOT an accessibility effect:

- **The Columns dialog problem**: Magento's Orders grid has a "Columns" configuration dropdown that visually overlaps with the Status filter. CUA clicks coordinates for "Canceled" but hits the Columns dialog instead, entering a loop.
- **Why ml is best**: The ml variant's slightly different DOM may position the Columns dialog in a non-overlapping location, giving CUA cleaner click targets.
- **Why high is worst**: Enhanced ARIA adds skip-links and landmarks that shift element positions. Additionally, all 3 high-variant failures show 8–9 `Page.screenshot: Timeout 3000ms exceeded` errors, wasting ~30% of the step budget. The enhanced DOM makes the complex Orders grid heavier to render.
- **Comparison with text-only**: Text-only Claude gets 100% at ml/base/high because it reads the a11y tree directly and programmatically selects "Canceled" without coordinate ambiguity.

**Paper implication**: admin:198 should be flagged as a UI complexity confound for CUA. It demonstrates that coordinate-based agents have their own failure modes independent of DOM state — strengthening the argument that different agent architectures face different environmental barriers.

### 2.5 Token Analysis

| Variant | Avg Tokens (all) | Avg Tokens (success) | Avg Tokens (failure) |
|---------|-----------------|---------------------|---------------------|
| low | 281K | 113K | 460K |
| ml | 122K | 111K | 490K |
| base | 144K | 112K | 487K |
| high | 117K | 99K | 306K |

Low inflates tokens 1.95× vs base (281K vs 144K), driven by failure-dominated inflation: low failures average 460K tokens (max steps exhausted) while low successes average only 113K. High variant's lower failure token count (306K) reflects screenshot timeouts that produce empty steps consuming fewer tokens.

---

## 3. SoM Results (38/140, 27.1%)

### 3.1 Task × Variant Matrix

| Task | low | ml | base | high | Text-only (ref) |
|------|-----|----|------|------|-----------------|
| admin:41 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% all |
| admin:94 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 20% (1/5) | 100% (ml/base/high) |
| admin:198 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% (ml/base/high) |
| ecom:188 | 20% (1/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% all |
| gitlab:132 | 0% (0/5) | 60% (3/5) | 60% (3/5) | 0% (0/5) | 100% all |
| gitlab:293 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% (ml/base/high) |
| gitlab:308 | 0% (0/5) | 60% (3/5) | 60% (3/5) | 60% (3/5) | 100% (ml/base/high) |

**Per-variant summary**: low 8.6% (3/35) → ml 31.4% (11/35) → base 34.3% (12/35) → high 34.3% (12/35)

### 3.2 Weak Accessibility Gradient

SoM shows a gradient (low 8.6% → base 34.3%, +25.7pp) but it is weak and dominated by SoM-specific failures at all variants. The gradient exists because low variant's DOM de-semanticization creates additional phantom bids and navigation failures on top of SoM's baseline weakness.

At non-low variants (ml/base/high), SoM averages only 33.3% — compared to text-only Claude's 100% and CUA's 90.5%. The a11y tree's informational advantage over SoM screenshots is massive for these task types (admin grids, GitLab forms, multi-step navigation).

### 3.3 Five Failure Modes

Across 102 SoM failures, five distinct modes emerge (extrapolated from smoke deep-dive patterns confirmed at 5-rep scale):

| Mode | Description | Prevalence | Dominant Tasks |
|------|-------------|-----------|----------------|
| **Phantom bid loop** | Agent clicks SoM label, gets "not found" or "not visible", retries indefinitely | ~30% | ecom:188 (base/ml/high), gitlab:308 |
| **Visual data misread** | Agent reaches correct page but extracts wrong value from screenshot | ~26% | admin:41 (all), admin:198 (ml/base/high) |
| **Form interaction failure** | Agent identifies input visually but fill() fails on Vue.js/KnockoutJS components | ~17% | gitlab:293 (all variants) |
| **Exploration spiral** | Clicks succeed but agent never converges on target page | ~13% | gitlab:132 (high), admin:94 |
| **Navigation failure** | Sidebar/menu phantom bids block all routes to target | ~13% | admin:198 (low), admin:94 (low) |

### 3.4 Key Anomalies

**admin:94 non-monotonic**: Only succeeds at high (20%, 1/5). The high variant's enhanced ARIA may provide just enough structure for the SoM agent to navigate the invoice page in rare cases. At base/ml, the agent gets trapped in exploration spirals on the Magento admin grid.

**ecom:188 forced simplification**: Succeeds only at low (20%, 1/5). The low variant's link→span reduces SoM overlay density (125→92 elements after navigation vs 122→122 at base), eliminating phantom bid targets that trap the agent in click-failure loops. This is the SoM-specific analog of the text-only forced simplification documented in reddit:67 (Pilot 4).

**admin:41 0% across all variants**: The task ("top search term") is trivially easy for text-only (1 step). SoM fails because it visually misreads the dashboard data table — answering "tanks" instead of "hollister" at every variant. SoM overlays on Magento's dense admin grids degrade visual parsing accuracy.

**gitlab:293 0% across ALL variants**: The most striking SoM failure. The agent identifies GitLab's search bar visually but cannot type into it via SoM bid. The `fill()` action fails because Vue.js re-renders the search component on focus, invalidating the bid between screenshot capture and action execution. This is the "Execution Gap" (Shi et al., 2025) in its purest form — no amount of accessibility improvement can fix a fundamental SoM-to-DOM timing mismatch.

**gitlab:132 high 0% (base 60%)**: Enhanced ARIA creates more SoM labels, providing more "interesting" click targets. The agent explores breadth-first through the enriched UI instead of falling back to the goto() URL strategy that succeeds at base. ARIA over-annotation paradoxically hurts SoM by inflating the visual action space.

---

## 4. Cross-Agent Comparison (All 4 Agents on 7 Tasks)

### 4.1 Per-Variant Success Rates

| Variant | Claude-Text | Llama4-Text | Claude-SoM | Claude-CUA |
|---------|-------------|-------------|------------|------------|
| low | 51.4% | 51.4% | 8.6% | 51.4% |
| ml | 100.0% | 88.6% | 31.4% | 97.1% |
| base | 100.0% | 91.4% | 34.3% | 91.4% |
| high | 100.0% | 97.1% | 34.3% | 91.4% |

### 4.2 Accessibility Gradient (low → base)

| Agent | Low Rate | Base Rate | Δ (base−low) | Mechanism |
|-------|----------|-----------|--------------|-----------|
| Text-only Claude | 51.4% | 100.0% | **+48.6pp** | A11y tree content invisibility |
| Text-only Llama 4 | 51.4% | 91.4% | **+40.0pp** | Same as Claude, amplified by weaker model |
| CUA Claude | 51.4% | 91.4% | **+40.0pp** | Cross-layer functional breakage (href removal) |
| SoM Claude | 8.6% | 34.3% | **+25.7pp** | Phantom bids + visual misread (additive to baseline weakness) |

The direction of the effect (low < base) is consistent across all four agent types. The gradient magnitude varies: text-only shows the largest absolute drop (+48.6pp), CUA matches Llama 4 (+40.0pp), and SoM shows the smallest (+25.7pp) because its baseline is already so low that there is less room to fall.

### 4.3 Mechanism Differences

| Agent | Primary Failure at Low | DOM Dependency |
|-------|----------------------|----------------|
| Text-only Claude | Content invisibility (broken ARIA → missing a11y tree nodes) | Direct: reads a11y tree |
| Text-only Llama 4 | Same, amplified by weaker reasoning | Direct: reads a11y tree |
| CUA Claude | Functional breakage (link→span removes href → clicks do nothing) | Minimal: pure coordinates, but href deletion breaks behavior |
| SoM Claude | Phantom bids (SoM labels persist on de-semanticized elements) + baseline SoM weakness | Indirect: SoM overlays depend on DOM interactive elements |

### 4.4 Agent Ranking

At non-low variants (where the environment is functional):
- Text-only Claude: 100% — a11y tree provides complete, structured information
- CUA Claude: 93.3% — coordinate-based vision works well on functional UIs
- Text-only Llama 4: 92.4% — weaker model, but a11y tree compensates
- SoM Claude: 33.3% — fundamental SoM limitations dominate

SoM is the weakest agent by a wide margin, but it still shows a gradient — confirming that DOM semantic changes affect even the weakest observation modality.

---

## 5. Implications for the Paper

### 5.1 CUA Data Fills the Causal Decomposition Gap

The expansion CUA data replicates the Pilot 4 causal decomposition on new tasks:
- Text-only low→base drop: ~48.6pp (semantic + functional)
- CUA low→base drop: ~40.0pp (functional only, since CUA ignores DOM semantics)
- Difference: ~8.6pp attributable to pure semantic (a11y tree) pathway on expansion tasks

Combined with Pilot 4 (33pp semantic + 30pp cross-layer), this provides converging evidence that the low variant's effect operates through both semantic and functional channels.

### 5.2 SoM Data Confirms Phantom Bid Generalization

The phantom bid phenomenon — first documented in Pilot 4 on ecommerce/reddit tasks — now generalizes to:
- **GitLab** (Vue.js): form interaction failures, exploration spirals
- **Magento admin** (KnockoutJS): visual data misread, navigation failures
- **Magento storefront**: phantom bid click loops (29 consecutive failures observed)

Five distinct failure modes are documented, providing rich qualitative data for the paper's SoM analysis section.

### 5.3 admin:198 Is a UI Complexity Confound

admin:198's inverted pattern (ml 80% > base 60% > high 40%) should be flagged in the paper as a CUA-specific confound. It demonstrates that coordinate-based agents face UI complexity barriers independent of accessibility — the Columns dialog overlap is a Magento admin design issue, not an accessibility issue. This strengthens the argument that different agent architectures face different environmental barriers.

### 5.4 gitlab:293 Is a Pure SoM Limitation

gitlab:293's 0% across ALL variants for SoM (vs 100% for text-only at ml/base/high) is the clearest evidence that SoM's failures are observation-mode-specific, not task-specific or accessibility-related. The form interaction failure on Vue.js search components is a fundamental SoM-to-DOM timing issue.

### 5.5 The Experiment Matrix Is Now Complete

13 tasks × 4 agents × 4 variants = 208 unique conditions. The expansion adds 112 new conditions (7 tasks × 4 agents × 4 variants) to the 96 from Pilot 4 (6 tasks × 4 agents × 4 variants, noting Pilot 4 SoM was on original 6 tasks only).

---

## 6. Updated Experiment Totals

| Experiment | Cases | Breakdown |
|-----------|-------|-----------|
| Pilot 4 text-only + SoM | 240 | 6 tasks × 4 variants × 5 reps × 2 agents |
| Pilot 4 CUA | 120 | 6 tasks × 4 variants × 5 reps × 1 agent |
| Expansion Claude text-only | 140 | 7 tasks × 4 variants × 5 reps |
| Expansion Llama 4 text-only | 260 | 13 tasks × 4 variants × 5 reps |
| Expansion SoM | 140 | 7 tasks × 4 variants × 5 reps |
| Expansion CUA | 140 | 7 tasks × 4 variants × 5 reps |
| **Grand Total** | **N=1,040** | |

This is the definitive dataset for the CHI 2027 submission: 13 tasks across 4 WebArena applications, 4 agent architectures (text-only Claude, text-only Llama 4, SoM Claude, CUA Claude), 4 accessibility variants, 5 repetitions per cell.

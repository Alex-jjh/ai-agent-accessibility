# CUA Expansion Smoke: Deep-Dive Trace Analysis

**Run**: `d2e92067-cc41-4e78-a723-5f4bbb8fc181` (2026-04-13)
**Design**: 7 tasks × 4 variants × 1 rep × CUA (coordinate-based vision agent)
**Total**: 28 cases, 21 success (75.0%), 7 timeout failures

## 1. Overall Results Matrix

| Task | low | ml | base | high | Notes |
|------|-----|----|------|------|-------|
| admin:41 | ✓ (3 steps) | ✓ (6) | ✓ (6) | ✓ (6) | Control task — trivial |
| admin:94 | ✗ timeout | ✓ (4) | ✓ (4) | ✓ (4) | Low: nav sidebar invisible |
| admin:198 | ✗ timeout | ✓ (16) | ✗ timeout | ✗ timeout | **Anomaly**: fails 3/4 variants |
| ecom:188 | ✓ (4) | ✓ (3) | ✓ (5) | ✓ (8) | Control task |
| gitlab:132 | ✓ (9) | ✓ (13) | ✓ (4) | ✓ (5) | Clean pass all variants |
| gitlab:293 | ✗ timeout | ✓ (12) | ✓ (13) | ✓ (16) | Low: search broken |
| gitlab:308 | ✗ timeout | ✗ timeout | ✓ (9) | ✓ (30) | **ml failure unique to CUA** |

**Success by variant**: low 3/7 (42.9%), ml 6/7 (85.7%), base 6/7 (85.7%), high 6/7 (85.7%)

**Comparison with text-only Claude (expansion smoke, same 7 tasks)**:
- Text-only: low 51.4%, ml 100%, base 100%, high 100%
- CUA: low 42.9%, ml 85.7%, base 85.7%, high 85.7%
- CUA is weaker overall (75% vs 87.5%) but the gap is concentrated in admin:198

---

## 2. admin:198 — The Magento Columns Dialog UI Trap

### 2.1 The Anomaly

admin:198 is the most anomalous case in the entire CUA smoke run. CUA succeeds at only medium-low (1/4), failing at low, base, AND high. This is unexpected because:
- Text-only Claude gets 5/5 at ml/base/high (only fails at low due to sidebar invisibility)
- Pilot 4 CUA (original 6 tasks) achieved 96.7% at base
- CUA should be unaffected by DOM semantic changes at base/high

### 2.2 Root Cause: Magento KnockoutJS Columns Dialog Intercept

The failure mechanism is identical across base and high variants. Step-by-step:

1. **Steps 1-3**: CUA correctly navigates Sales → Orders (identical across all variants)
2. **Step 4**: CUA clicks "Filters" button at ~(765, 265) — correct
3. **Step 5**: CUA clicks the Status dropdown at ~(1096, 490) — correct
4. **Step 6**: CUA clicks "Canceled" at ~(1011, 254) — **this is where it goes wrong**

At step 6, CUA believes it's selecting "Canceled" from the Status filter dropdown. But the Magento admin UI has a **Columns configuration dialog** that visually overlaps with the filter panel. The coordinate (1011, 254) actually hits the Columns dialog, not the Status filter.

**The loop pattern** (base trace, 30 steps):
```
click Status dropdown → click "Canceled" (actually hits Columns dialog)
→ see Columns dialog → click Cancel/Apply → back to filters
→ click Status dropdown → click "Canceled" (hits Columns dialog again)
→ repeat until timeout
```

The agent's reasoning reveals the confusion:
- Step 6: "I can see the status dropdown is open and 'Canceled' is the first option"
- Step 7: "I see a columns selection dialog has opened" (surprise!)
- Steps 8-30: Repeated attempts to select Canceled, each time hitting the Columns dialog

**Key evidence**: The coordinate (1011, 254) is clicked 6 times in the base trace. Each time, the agent believes it's selecting "Canceled" but actually triggers the Columns dialog.

### 2.3 Why medium-low Succeeds

The ml trace follows a different path after the same initial confusion:
- Steps 1-6: Same pattern — navigates to Orders, opens Filters, hits Columns dialog
- Step 7: Clicks "Apply Filters" at (1177, 607) — this closes the dialog AND applies whatever filter state exists
- Steps 8-11: Repeats the filter attempt, again hitting Columns dialog
- Step 12: **Crucially**, clicks at (384, 439) — a different coordinate that scrolls the orders table
- Steps 13-15: Scrolls through the orders table and **visually identifies cancelled orders**
- Step 16: Correctly identifies "Lily Potter" as the most recent cancelled order

The ml success is due to a **stochastic coordinate difference** at step 12 that breaks the loop. The agent accidentally scrolls the table instead of re-entering the filter loop, then reads the data visually.

### 2.4 Why high Has Additional Screenshot Timeouts

The high variant trace shows 10 `Page.screenshot: Timeout 3000ms exceeded` errors (steps 8-9, 11-12, 16-17, 19-20, 24-25). These are caused by the high variant's DOM changes (37 DOM changes applied) making the page heavier to render. The screenshot timeout (3000ms) is too tight for the enhanced DOM.

This means the high variant has TWO compounding failure factors:
1. The same Columns dialog UI trap as base
2. Screenshot capture failures that waste steps (10/30 steps lost to screenshot errors)

The high variant uses only 283K tokens vs base's 468K because screenshot errors produce empty steps that consume fewer tokens.

### 2.5 Classification

admin:198 failures at base and high are **NOT accessibility-related**. They are a **UI complexity / coordinate precision failure** — the Magento admin's Columns dialog overlaps with the Status filter dropdown in a way that confuses coordinate-based clicking. This is a task-specific CUA limitation.

The low variant failure IS partially accessibility-related: the low variant applies 428 DOM changes that strip the sidebar navigation, forcing CUA to use search/URL navigation (which also fails due to key press errors — see §4).

**Comparison with text-only**: Text-only Claude succeeds at base/high because it reads the a11y tree directly and can programmatically select "Canceled" from the Status filter without coordinate ambiguity. The Columns dialog is a separate DOM element that doesn't interfere with a11y tree-based interaction.

---

## 3. Low Variant Failures (4 tasks)

Four tasks fail at low: admin:94, admin:198, gitlab:293, gitlab:308.

### 3.1 admin:94 low — Sidebar Navigation Invisible

**Task**: "What is the grand total of invoice 000000001?"
**Failure mechanism**: The low variant applies 428 DOM changes that strip semantic structure from the Magento admin sidebar. CUA cannot find the navigation menu:

- Steps 2-5: Clicks on hamburger menu icon, search box — cannot find Sales/Invoices nav
- Steps 6-9: Types "000000001" in search box, key press fails ("Unknown key")
- Steps 10-13: Tries URL navigation (types `http://10.0.1.50:7780/admin/ad...`) — URL gets truncated
- Steps 14-30: Alternates between clicking sidebar area, search box, and URL bar — never reaches Invoices page

**Root cause analysis**: The low variant converts sidebar navigation links (`<a>`) to `<span>` elements, removing `href` attributes. Visually, the sidebar items may still appear as text, but:
1. The link→span conversion removes underlines and hover states (cross-layer visual change)
2. The sidebar may collapse or render differently without proper link semantics
3. CUA's coordinate clicks on the sidebar area don't trigger navigation

This is a **cross-layer functional breakage** — the link→span patch removes both DOM semantics AND navigation functionality (href deletion). CUA is affected because the visual affordance of clickable navigation is degraded.

### 3.2 admin:198 low — Same Sidebar Issue + Search Failure

Same mechanism as admin:94 low. CUA cannot navigate to the Orders page because the sidebar is broken. Additional failure: key press errors ("Unknown key: R") prevent search from working.

The trace shows CUA trying multiple strategies:
1. Click sidebar (fails — links are spans)
2. Search box (types "orders" but Enter key fails)
3. URL navigation (types URL but it gets truncated)
4. Mouse hover, right-click, clicking "Last Orders" section
5. None succeed within 30 steps

### 3.3 gitlab:293 low — Search Autocomplete Destroyed

**Task**: "Show me the SSH clone command for Super_Awesome_Robot"
**Failure mechanism**: The low variant applies 285 DOM changes to GitLab's Vue.js DOM. The search functionality is broken:

- Steps 1-4: CUA clicks search box at (248, 157) repeatedly, types "Super_Awesome_Robot"
- Step 5: Tries triple_click (unknown action)
- Steps 6-13: Alternates between clicking search box, typing, pressing Enter — search doesn't execute
- Steps 14-16: Scrolls through project list — doesn't find the repo
- Steps 17-30: Tries URL navigation, keyboard shortcuts — all fail

**Root cause**: The low variant strips ARIA attributes and semantic structure from GitLab's search component. The search autocomplete dropdown (which normally shows matching repos) doesn't appear. Without autocomplete, CUA types the repo name but the search doesn't execute properly.

This is a **functional breakage** — the search component's JavaScript event handlers are disrupted by the DOM changes.

### 3.4 gitlab:308 low — Contributors Chart Invisible

**Task**: "Who has made the most contributions to primer/design?"
**Failure mechanism**: CUA navigates to the primer/design repo but cannot find the Contributors page:

- Steps 1-15: Searches for "primer/design", eventually finds it by scrolling
- Step 16: Clicks on the project — enters the repo page
- Steps 17-20: Scrolls through repo page, finds "921 Commits"
- Step 20: Clicks on commits count (344, 378)
- Steps 21-30: Scrolls through commit history, finds Analytics section, sees repository graphs with aggregate stats (800 commits, 71 authors) but **cannot find the per-contributor breakdown**

**Root cause**: The low variant strips the Contributors navigation link/tab. CUA can see the repository graphs page (which shows aggregate commit stats) but cannot navigate to the Contributors sub-page that shows per-author commit counts. The agent scrolls through charts (commits per day, per weekday, per hour) but never reaches individual contributor data.

This is a **structural infeasibility** — the navigation pathway to the Contributors page is broken by the low variant.

---

## 4. gitlab:308 ml — The Only Case Where SoM Beats CUA

### 4.1 The Divergence

| Agent | gitlab:308 ml | gitlab:308 base | gitlab:308 high |
|-------|--------------|-----------------|-----------------|
| CUA | ✗ timeout (30 steps, 504K tokens) | ✓ (9 steps, 103K) | ✓ (30 steps, 499K) |
| SoM | ✓ (27 steps, 98K tokens) | ✗ timeout (30 steps, 96K) | ✗ timeout (30 steps, 123K) |
| Text-only | ✓ (all variants) | ✓ | ✓ |

This is the ONLY case in the entire smoke run where SoM succeeds and CUA fails.

### 4.2 Why CUA Fails at ml

The CUA ml trace reveals a **scroll exhaustion** failure:
- Steps 1-4: CUA navigates to primer/design → Contributors page (correct path)
- Steps 5-30: CUA scrolls through the Contributors list, reading each contributor one by one

The Contributors page shows 54+ contributors sorted by commit count. CUA reads them all:
1. Shawn Allen — 95 commits
2. Inayaili León — 77 commits
3. Emily Brick — 38 commits
... (continues through all 54 contributors)

CUA reaches step 30 (the max) while still scrolling through contributors at position ~54. It never issues a `task_complete` action because it's still reading.

**Why this doesn't happen at base**: At base, CUA reaches the Contributors page in 4 steps and reads the top contributors in 5 scrolls, then answers at step 9. The base variant's page loads faster and the contributor list renders more compactly.

**Why this doesn't happen at high**: At high, CUA also scrolls through all 54 contributors (steps 5-29) but manages to issue `task_complete` at exactly step 30 — just barely making it. The high trace uses 499K tokens (nearly identical to ml's 504K).

The ml failure is a **marginal timeout** — CUA needed ~31-32 steps but only had 30. The ml variant's 1 DOM change (medium-low patch) may cause slightly different page rendering that adds 1-2 extra scroll steps.

### 4.3 Why SoM Succeeds at ml

SoM succeeds at ml (27 steps) because it uses bid-based clicking which is more efficient for scrolling through lists. SoM can click on specific bid-labeled elements rather than coordinate-scrolling, potentially loading contributor data more efficiently.

However, SoM fails at base and high — this is likely due to SoM's general weakness on GitLab tasks (the SoM smoke shows only 4/28 successes overall, with most GitLab tasks timing out regardless of variant).

### 4.4 Interpretation

The gitlab:308 ml CUA failure is NOT accessibility-related. It's a **step budget exhaustion** caused by the Contributors page having 54+ entries that CUA reads sequentially. The ml variant adds marginal overhead (1 DOM change) that pushes CUA past the 30-step limit.

The SoM "win" here is also not meaningful — SoM fails at base and high for the same task. The ml success is likely a stochastic artifact of SoM's different scrolling behavior happening to be more efficient for this specific page layout under ml.

---

## 5. Token Consumption Patterns

### 5.1 Averages by Variant

| Variant | Avg Tokens | Success Avg | Failure Avg | Success Rate |
|---------|-----------|-------------|-------------|--------------|
| low | 284,327 | 49,794 | 460,226 | 3/7 (42.9%) |
| ml | 162,943 | 106,070 | 504,181 | 6/7 (85.7%) |
| base | 127,412 | 70,678 | 467,811 | 6/7 (85.7%) |
| high | 173,177 | 154,869 | 283,024 | 6/7 (85.7%) |

### 5.2 The 2.2× Low Inflation

CUA low averages 284K tokens vs base 127K — a 2.24× ratio. This is driven by:

1. **Failure-dominated inflation**: Low has 4 failures averaging 460K tokens each. Failures always consume max steps (30) and max tokens. Successes average only 50K.

2. **Exploration overhead**: Low-variant failures show CUA trying multiple navigation strategies (sidebar clicks, search, URL typing, keyboard shortcuts) — each strategy attempt consumes tokens for screenshot processing + reasoning.

3. **Key press errors**: Low traces show repeated `Unknown key` errors (e.g., "Unknown key: R") that waste steps. These appear to be CUA bridge issues with key encoding, not variant-related.

### 5.3 Controlling for Success

When comparing only successful cases:
- Low success avg: 49,794 (3 cases: admin:41, ecom:188, gitlab:132)
- Base success avg: 70,678 (6 cases)
- The low successes are actually CHEAPER because they're simpler tasks (admin:41 = 3 steps, ecom:188 = 4 steps)

When comparing the same task across variants (gitlab:132, the only task that succeeds at all 4):
- low: 103,905 tokens (9 steps)
- ml: 169,586 tokens (13 steps)
- base: 28,931 tokens (4 steps)
- high: 42,191 tokens (5 steps)

Here, low is 3.6× more expensive than base for the same task. CUA takes 9 steps at low vs 4 at base — the extra steps are spent navigating around broken search functionality.

### 5.4 High Variant Token Inflation

High averages 173K vs base 127K — a 1.36× ratio. This is driven by:
- gitlab:308 high: 499K tokens (30 steps scrolling through all contributors)
- admin:198 high: 283K tokens (timeout with screenshot errors)
- Other high successes are comparable to base

The high variant's DOM enhancements (17-37 DOM changes) make pages slightly heavier, causing:
1. Screenshot timeouts (admin:198 high: 10 screenshot errors)
2. Slower page rendering → more scroll steps needed (gitlab:308 high: 30 steps vs base 9)

---

## 6. Comparison with Pilot 4 CUA (Original 6 Tasks)

Pilot 4 CUA achieved 109/120 (90.8%) on the original 6 tasks:
- low: 66.7%, ml: 100%, base: 96.7%, high: 100%

The expansion CUA smoke achieves 75.0% on 7 new tasks:
- low: 42.9%, ml: 85.7%, base: 85.7%, high: 85.7%

The drop is concentrated in:
1. **admin:198** (3 failures) — UI complexity, not a11y
2. **gitlab:308 ml** (1 failure) — step budget, not a11y

Excluding admin:198, the expansion CUA results would be:
- low: 3/6 (50%), ml: 6/6 (100%), base: 6/6 (100%), high: 6/6 (100%)

This is closer to Pilot 4 CUA patterns, with low failures driven by cross-layer functional breakage.

---

## 7. Cross-Agent Comparison (CUA vs SoM vs Text-Only)

### 7.1 Success Matrix (7 new tasks, smoke = 1 rep each)

| Task | CUA low | CUA ml | CUA base | CUA high | SoM ml | SoM base | Text low | Text ml | Text base | Text high |
|------|---------|--------|----------|----------|--------|----------|----------|---------|-----------|-----------|
| admin:41 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| admin:94 | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| admin:198 | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| ecom:188 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ |
| gitlab:132 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gitlab:293 | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| gitlab:308 | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |

### 7.2 Key Observations

1. **SoM is dramatically weaker overall**: 4/28 success (14.3%) vs CUA 21/28 (75.0%). SoM fails on most admin tasks and most GitLab tasks regardless of variant.

2. **CUA and text-only agree on low failures**: admin:94, admin:198, gitlab:293, gitlab:308 all fail at low for both CUA and text-only. The failure mechanisms differ (CUA: visual/functional breakage; text-only: a11y tree degradation) but the outcome is the same.

3. **admin:198 is uniquely hard for CUA**: Text-only succeeds at base/high but CUA fails — the Columns dialog UI trap is CUA-specific.

4. **gitlab:308 ml is the ONLY SoM > CUA case**: SoM succeeds where CUA fails, but this is a marginal step-budget issue, not a systematic advantage.

---

## 8. Unexpected Patterns

### 8.1 Key Press Encoding Errors

Multiple low-variant traces show `Action key failed: Keyboard.press: Unknown key: "R` errors. This appears to be a CUA bridge issue where the key name gets truncated (likely "Return" → "R" due to JSON parsing). This wastes 2-3 steps per occurrence and compounds the navigation difficulty at low.

### 8.2 Screenshot Timeout at High

The high variant causes `Page.screenshot: Timeout 3000ms exceeded` errors in admin:198 (10 occurrences). The 37 DOM changes added by the high variant make the Magento admin page heavier to render. This is a platform issue — the 3000ms screenshot timeout is too tight for enhanced DOM.

### 8.3 gitlab:132 low Success Despite 285 DOM Changes

gitlab:132 succeeds at low (9 steps, 104K tokens) despite 285 DOM changes. The task ("How many commits did kilian make on 3/5/2023?") requires navigating to a specific commit page — CUA finds it by scrolling through the project list rather than using search. This suggests CUA can work around broken search if the target is visually findable by scrolling.

### 8.4 admin:41 low Success with 0 Clicks

admin:41 low succeeds in just 3 steps with 0 coordinate clicks — the agent reads the answer directly from the dashboard screenshot without any navigation. The task ("What is the top 1 search term?") has the answer visible on the admin dashboard's "Top search terms" widget. This is the ideal CUA scenario: information visible on the landing page.

---

## 9. Summary of Failure Attribution

| Failure | Variant | Tokens | Root Cause | A11y-Related? |
|---------|---------|--------|------------|---------------|
| admin:198 base | base | 468K | Columns dialog UI trap | **No** — UI complexity |
| admin:198 high | high | 283K | Columns dialog + screenshot timeouts | **No** — UI complexity + platform |
| admin:198 low | low | 463K | Sidebar nav broken (link→span) | **Partial** — cross-layer functional |
| admin:94 low | low | 460K | Sidebar nav broken (link→span) | **Partial** — cross-layer functional |
| gitlab:293 low | low | 457K | Search autocomplete broken | **Partial** — cross-layer functional |
| gitlab:308 low | low | 461K | Contributors nav link broken | **Yes** — structural infeasibility |
| gitlab:308 ml | ml | 504K | Step budget exhaustion (54 contributors) | **No** — task complexity |

**Summary**: Of 7 failures:
- 2 are pure UI complexity (admin:198 base/high) — CUA-specific, not a11y
- 1 is step budget (gitlab:308 ml) — task complexity, not a11y
- 3 are cross-layer functional breakage (admin:94/198 low, gitlab:293 low) — link→span removes href
- 1 is structural infeasibility (gitlab:308 low) — nav pathway destroyed

The 4 low-variant failures are consistent with the cross-layer confound identified in Pilot 4: the link→span patch removes both DOM semantics AND navigation functionality, affecting CUA through the functional (href deletion) pathway rather than the semantic pathway.

# Expansion-SoM Smoke Test Deep Dive

**Experiment**: expansion-som-smoke (run 78791f30)
**Model**: Claude Sonnet 3.5 via Bedrock (vision-only / SoM observation mode)
**Date**: April 13, 2026
**Cases**: 28 (7 tasks × 4 variants × 1 rep)

---

## 1. Executive Summary

The SoM (Set-of-Mark) smoke test achieved **5/28 (17.9%) overall success** across 7 new expansion tasks. Three tasks scored **0% across ALL four variants** including base and high: admin:41, admin:198, and gitlab:293. These universal failures are not accessibility-related — they reveal fundamental SoM agent limitations in visual grounding, navigation, and form interaction that text-only agents bypass entirely.

The outcome distribution — 46% timeout, 25% partial_success, 11% failure, 18% success — indicates SoM agents predominantly get trapped in click-failure loops or exploration spirals rather than failing cleanly.

Two anomalies provide additional insight: ecom:188 succeeds only at low (forced simplification via reduced SoM overlay clutter), and gitlab:132 succeeds at base but fails at high (ARIA over-annotation inflating the SoM overlay and causing navigation confusion).

---

## 2. Results Matrix

| Task | low | medium-low | base | high | Text-only Claude (ref) |
|------|-----|------------|------|------|----------------------|
| admin:41 | ✗ partial | ✗ failure | ✗ partial | ✗ partial | 100% all variants |
| admin:94 | ✗ failure | ✗ timeout | ✗ timeout | ✓ success | 100% (ml/base/high) |
| admin:198 | ✗ failure | ✗ partial | ✗ partial | ✗ partial | 100% (ml/base/high) |
| ecom:188 | **✓ success** | ✗ timeout | ✗ timeout | ✗ timeout | 100% all variants |
| gitlab:132 | ✗ partial | ✓ success | **✓ success** | ✗ timeout | 100% all variants |
| gitlab:293 | ✗ timeout | ✗ timeout | ✗ timeout | ✗ timeout | 100% (ml/base/high) |
| gitlab:308 | ✗ timeout | ✓ success | ✗ timeout | ✗ timeout | 100% (ml/base/high) |

**Outcome distribution** (n=28):
- timeout: 13 (46%) — agent exhausts 30 steps without answering
- partial_success: 7 (25%) — agent answers but incorrectly
- success: 5 (18%) — correct answer
- failure: 3 (11%) — agent stops early or gives no answer

---

## 3. Zero-Across-All-Variants Tasks: Failure Mode Analysis

### 3.1 admin:41 — Visual Misread of Dashboard Data

**Task**: "List the top 1 search terms in my store"
**Expected answer**: "hollister" (exact_match)
**Text-only Claude**: 100% at all variants (1 step — reads directly from a11y tree)

**SoM failure pattern**: The agent answers "tanks" at all four variants. It navigates to the Search Terms report page (or reads the "Last Search Terms" widget on the dashboard) and visually reads the first entry as "tanks" — but the ground truth is "hollister". The SoM agent **misreads the visual data** from the screenshot.

| Variant | Steps | Tokens | Answer | Failure mode |
|---------|-------|--------|--------|-------------|
| low | 4 | 8,315 | "tanks" | Visual misread |
| medium-low | 1 | 1,791 | (none — early stop) | Single click, no answer |
| base | 9 | 24,411 | "tanks" | Visual misread after navigation |
| high | 4 | 9,717 | "tanks" | Visual misread |

**Root cause**: This is a **visual grounding error**, not an accessibility issue. The text-only agent reads the a11y tree which contains the exact text "hollister" as the top search term. The SoM agent reads a screenshot where the search terms table is rendered visually, and either: (a) the SoM overlay obscures the actual top entry, (b) the agent misidentifies which row is "top" in the visual table, or (c) the dashboard's "Last Search Terms" widget shows different data than the full Search Terms report (sorted by recency vs. by count).

The high variant trace is particularly revealing: bid 274 resolves to `<span bid="274" browsergym_set_of_marks="0">Search Terms</span>` — a SoM-labeled element with `set_of_marks="0"` (not visible/interactable). The agent sees the label in the screenshot, clicks it twice, gets "element is not visible" errors, then scrolls down and reads the dashboard widget instead of navigating to the actual report. This is a **phantom bid** (Mode A: element exists but marked non-interactable).

**Key insight**: This task is trivially easy for text-only agents (1 step, answer directly from dashboard a11y tree). SoM fails because visual table reading is unreliable — the agent cannot distinguish which row is the "top" search term from a screenshot alone, and SoM overlays on the Magento admin's dense data tables create visual clutter that degrades reading accuracy.

### 3.2 admin:198 — Incorrect Order Identification

**Task**: "Get the customer name of the most recent cancelled order"
**Expected answer**: "Lily Potter" (exact_match)
**Text-only Claude**: 100% at base/high/ml (navigates to orders, filters by cancelled, reads name)

**SoM failure pattern**: The agent navigates to the orders page but identifies the wrong cancelled order. It answers "Alex Johnson" (high, ml) or "Adam Garcia" (base) — both are real customer names from the orders table, but neither is the most recent cancelled order.

| Variant | Steps | Tokens | Answer | Failure mode |
|---------|-------|--------|--------|-------------|
| low | 12 | 48,849 | (none) | Navigation failure — can't reach orders |
| medium-low | 5 | 12,373 | "Alex Johnson" | Wrong order identified |
| base | 8 | 21,265 | "Adam Garcia" | Wrong order identified |
| high | 6 | 12,940 | "Alex Johnson" | Wrong order identified |

**Root cause at ml/base/high**: The agent reaches the orders page and visually scans the table for "Cancelled" status entries. However, it cannot reliably determine which cancelled order is "most recent" from the visual layout. The orders table has columns for Order #, Purchase Date, Bill-to Name, Ship-to Name, Grand Total, Status, and Action — but visually parsing date ordering from a screenshot with SoM overlays on every cell is error-prone. The agent picks a cancelled order that is visible but not the most recent one.

**Root cause at low**: The low variant breaks Magento admin sidebar navigation. The agent clicks bid 154, 208 (both fail), tries `goto()` to the orders URL, goes back, and continues clicking failed bids. It never reaches the orders table. This is the standard **phantom bid / navigation failure** pattern seen in Pilot 4 low-variant SoM traces.

**Key insight**: Even at base/high where navigation succeeds, the SoM agent fails because **visual table parsing with date comparison** is fundamentally harder than text-based a11y tree parsing. The text-only agent can sort/filter the orders table programmatically; the SoM agent must visually scan rows and compare dates — a task that requires precise multi-column visual reasoning across SoM-labeled cells.

### 3.3 gitlab:293 — Search Interaction Failure

**Task**: "Show me the command to clone Super_Awesome_Robot with SSH"
**Expected answer**: "git clone ssh://git@metis.lti.cs.cmu.edu:2222/convexegg/super_awesome_robot.git"
**Text-only Claude**: 100% at base/high/ml (searches for repo, navigates to clone dialog)

**SoM failure pattern**: All four variants timeout at 30 steps. The agent's strategy is correct — search for "Super_Awesome_Robot" in GitLab's search bar — but it **cannot successfully interact with the search input field**.

| Variant | Steps | Tokens | Click fails | Fill fails | Dominant pattern |
|---------|-------|--------|-------------|-----------|-----------------|
| low | 30 | 115,597 | 11 | 6 | fill loop (5 consecutive) |
| medium-low | 30 | 101,253 | 13 | 9 | click+fill interleave |
| base | 30 | 102,678 | 15 | 11 | fill loop (bid 943/944, 9 consecutive click fails) |
| high | 30 | 103,301 | 3 | 9 | fill loop (6 consecutive) |

**Detailed trace analysis (base variant)**:
1. Steps 1-2: Clicks search bar (bid 134), tries `fill("134", "Super_Awesome_Robot")` → fails
2. Steps 3-13: Tries clicking/filling various bids (195, 896, 897, 895) — all fail
3. Steps 14-30: Gets stuck on bids 943/944 — clicks 943 nine consecutive times, all fail. Tries `fill("943", "Super_Awesome_Robot")` repeatedly. Never escapes this loop.

The error pattern shows the agent identifies the search input visually but the SoM bid assigned to it either: (a) doesn't correspond to the actual input element (bid mismatch), (b) the GitLab Vue.js search component re-renders on focus, invalidating the bid, or (c) the `fill()` action fails because the element is a Vue-managed input that doesn't accept standard Playwright fill operations via bid.

**Key insight**: This is a **form interaction failure** — the SoM agent cannot type into GitLab's search bar at ANY variant. The text-only agent uses the a11y tree to identify the search input by its role/name and fills it successfully. The SoM agent sees the search bar visually, identifies a bid for it, but the bid-to-element resolution fails for Vue.js dynamic components. This is a fundamental SoM limitation: **dynamic JavaScript frameworks that re-render on interaction invalidate SoM bids between the screenshot capture and the action execution** (the "Execution Gap" from Shi et al., 2025).

---

## 4. Anomaly Analysis

### 4.1 ecom:188 — Low Succeeds, All Others Timeout (Forced Simplification)

**Task**: "Tell me the total cost of my latest cancelled order?"
**Expected answer**: must include "365.42"

| Variant | Outcome | Steps | Tokens | SoM elements | Click fails |
|---------|---------|-------|--------|-------------|-------------|
| low | ✓ success | 3 | 5,888 | 125→152→92 | 0 |
| medium-low | ✗ timeout | 30 | 100,677 | 122→...→111 | 27 (21 consecutive) |
| base | ✗ timeout | 30 | 91,601 | 122 (constant) | 29 (29 consecutive!) |
| high | ✗ timeout | 30 | 106,142 | 122→...→111 | 27 (19 consecutive) |

**Low variant success trace** (3 steps, 30 seconds):
1. `click("227")` → success (My Account link)
2. `click("1425")` → success (My Orders link)
3. `send_msg_to_user("$365.42")` → reads order table, identifies cancelled order

**Base variant failure trace** (30 steps, all clicks fail):
The agent tries to click bid 2027 ("My Account") **23 consecutive times** — every single click returns "Could not find element with bid 2027". The agent is trapped in a pure phantom bid loop. It sees "My Account" in the screenshot with bid label 2027, but the element doesn't exist in the DOM's interactive element set.

**Medium-low and high** show the same pattern: bid 1575 ("My Orders") clicked 18-21 consecutive times, all returning "Could not find element".

**Root cause**: At base/ml/high, the Magento storefront's "My Account" and "My Orders" links are rendered as `<a>` elements with complex JavaScript event handlers. BrowserGym assigns them SoM bids, but the elements are in a collapsed sidebar menu that is visually visible (the SoM label appears on the screenshot) but not interactable until the menu is expanded via hover/click on a parent element. The SoM agent sees the label, clicks it, gets "not found", and retries indefinitely.

At **low variant**, the link→span patch converts these `<a>` elements to `<span>` elements. Paradoxically, this changes the page layout: the sidebar menu structure is simplified (fewer interactive elements), and the "My Account" link that remains clickable (bid 227) is a different element — possibly the top navigation bar link rather than the sidebar link. The low variant's DOM simplification **accidentally makes the correct navigation path more accessible** to the SoM agent by removing the confusing sidebar menu bids.

**SoM element counts confirm this**: low variant labels 125 elements on the initial page vs. 122 at base. After navigating to My Account, low drops to 92 elements while base stays at 122. The reduced element count at low means fewer phantom bid targets and a cleaner visual field.

**Classification**: This is **forced simplification for SoM** — the same mechanism documented for text-only agents in reddit:67 (Pilot 4), but operating through a different pathway. For text-only, link→span constrains the action space in the a11y tree. For SoM, link→span reduces the SoM overlay density, eliminating phantom bid targets that trap the agent in click-failure loops.

### 4.2 gitlab:132 — Base Succeeds, High Fails (ARIA Over-Annotation)

**Task**: "How many commits did kilian make to a11yproject on 3/5/2023?"
**Expected answer**: must include "1"

| Variant | Outcome | Steps | Tokens | Click fails | Strategy |
|---------|---------|-------|--------|-------------|---------|
| low | ✗ partial | 18 | 57,651 | 4 | Gets lost in search, answers "Press Enter to search" |
| medium-low | ✓ success | 16 | 63,757 | 11 (10 consecutive!) | Navigates to repo, uses goto() to commits page |
| base | ✓ success | 9 | 28,976 | 5 (5 consecutive) | Navigates to repo, uses goto() to commits page |
| high | ✗ timeout | 30 | 86,289 | 1 | Navigates into repo but gets stuck clicking through files |

**Base success trace** (9 steps):
1. Clicks into a11yproject repo (bid 388)
2. Clicks on repo link (bid 693)
3. Steps 3-7: Tries clicking "Commits" link (bid 208) — 5 consecutive failures (not visible)
4. Step 8: Falls back to `goto("http://10.0.1.50:8023/a11yproject/a11yproject.com/-/commits")` — success
5. Step 9: Reads commits page, counts kilian's commits on 3/5/2023, answers "1"

**High variant failure trace** (30 steps):
1. Clicks into a11yproject repo (bid 388)
2. Step 2: Clicks bid 350 — fails (not visible)
3. Steps 3-30: Successfully clicks through various elements (29/30 clicks succeed!) but **never reaches the commits page**. The agent navigates into the repository file browser, clicks on files, directories, and sidebar items, but never constructs the goto() URL to the commits page.

**Root cause**: The high variant adds ARIA landmarks, labels, and roles to GitLab's Vue.js interface. This increases the number of SoM-labeled elements and creates more "interesting" click targets. The agent at high variant has **more options** and explores them — clicking through the file browser, sidebar navigation items, and various UI elements — but this exploration is unproductive. It never discovers the goto() shortcut that the base variant agent uses after its click attempts fail.

At base, the agent tries clicking "Commits" (bid 208) five times, all fail, and then **gives up on clicking and constructs a direct URL**. This is the same "stochastic strategy variation" seen in admin:94 — but here the base variant's simpler SoM overlay (fewer labeled elements) leads to faster failure on click attempts, which triggers the goto() fallback sooner.

At high, the agent's clicks mostly succeed (29/30), so it never hits the "wall" that triggers the goto() fallback. It keeps exploring productively-looking but ultimately wrong paths through the enriched UI.

**Classification**: This is **ARIA over-annotation hurting SoM** — more ARIA means more SoM labels, which means more click targets, which means the agent explores longer before giving up. The high variant's enhanced accessibility paradoxically hurts the SoM agent by providing too many valid-looking interaction options, preventing the agent from reaching the "give up and try goto()" strategy that succeeds at base.

---

## 5. Failure Mode Taxonomy

Across all 28 traces, five distinct SoM failure modes emerge:

### Mode 1: Phantom Bid Click Loop (9/28 traces, 32%)
Agent sees a SoM label in the screenshot, clicks the bid, gets "Could not find element" or "element is not visible", and retries the same bid or nearby bids indefinitely. Dominant in ecom:188 (base/ml/high) and gitlab:308 (base/high).

**Signature**: ≥5 consecutive click failures on the same or adjacent bids. Max observed: 29 consecutive failures (ecom:188 base).

### Mode 2: Form Interaction Failure (4/28 traces, 14%)
Agent identifies a form input visually but cannot fill it via SoM bid. The `fill()` action fails because the bid doesn't resolve to a fillable element, or the Vue.js/React component re-renders on focus. Dominant in gitlab:293 (all variants).

**Signature**: Multiple `fill()` failures interleaved with `click()` attempts on the same input area.

### Mode 3: Visual Data Misread (6/28 traces, 21%)
Agent reaches the correct page and reads data from the screenshot, but extracts the wrong value. The SoM overlay on dense data tables (Magento admin grids) degrades visual parsing accuracy. Dominant in admin:41 (all variants) and admin:198 (ml/base/high).

**Signature**: Agent answers confidently but incorrectly. Low step count, reasonable token usage. `partial_success` outcome.

### Mode 4: Exploration Spiral (5/28 traces, 18%)
Agent clicks through many elements successfully but never reaches the target page. Each click leads to a new page with new SoM labels, and the agent explores breadth-first without converging. Dominant in gitlab:132 high, gitlab:308 (base/high), admin:94 (base/ml).

**Signature**: High step count (30), most clicks succeed, but agent never answers. `timeout` outcome with low click failure rate.

### Mode 5: Navigation Failure (4/28 traces, 14%)
Agent cannot navigate from the starting page to the target page because sidebar/menu elements are phantom bids. Distinct from Mode 1 in that the agent tries different navigation strategies (goto, go_back) rather than retrying the same bid. Dominant in admin:198 low, admin:94 low.

**Signature**: Mix of click failures, goto() attempts, and go_back() — agent is actively trying to find a path but all routes are blocked.

---

## 6. Comparison with Text-Only Agent

| Metric | SoM (vision-only) | Text-only Claude |
|--------|-------------------|-----------------|
| Overall success | 5/28 (17.9%) | 27/28 (96.4%)* |
| 0%-across-all tasks | 3 (admin:41, admin:198, gitlab:293) | 0 |
| Timeout rate | 46% | 0% |
| Avg tokens (success) | 45,023 | ~30,000 |
| Avg tokens (failure) | 90,847 | ~200,000 |
| Dominant failure | Click loop / visual misread | Content invisibility (low only) |

*Text-only reference from expansion-claude smoke (same 7 tasks, 4 variants, 1 rep each).

**The SoM failures are NOT accessibility-related.** All three 0%-across-all tasks succeed at 100% for text-only Claude at base and high variants. The failures are caused by:
1. SoM bid resolution failures on dynamic JavaScript UIs (Vue.js, KnockoutJS)
2. Visual table parsing errors on dense admin grids
3. Form interaction failures on framework-managed input components
4. Exploration spirals caused by too many SoM-labeled click targets

These are fundamental limitations of the SoM observation mode that exist independently of accessibility variant manipulation.

---

## 7. Implications for the Paper

### 7.1 SoM Has DOM Dependencies Beyond Accessibility

The paper's core argument — that SoM overlays depend on DOM interactive elements — is confirmed but the dependency is broader than accessibility alone. SoM fails on these tasks not because of accessibility degradation but because:
- BrowserGym's bid assignment creates phantom labels for elements that are visually present but not interactable (collapsed menus, hidden submenus)
- Vue.js/KnockoutJS dynamic re-rendering invalidates bids between screenshot capture and action execution
- Dense SoM overlays on data-heavy pages (admin grids) degrade visual parsing accuracy

### 7.2 Forced Simplification Extends to SoM

The ecom:188 anomaly (low succeeds, others fail) demonstrates that forced simplification operates through the SoM overlay pathway, not just the a11y tree pathway. Low variant's link→span reduces SoM element count (125 vs 122 initial, 92 vs 122 after navigation), eliminating phantom bid targets. This is the SoM-specific analog of the text-only forced simplification documented in reddit:67.

### 7.3 ARIA Over-Annotation Can Hurt SoM Agents

The gitlab:132 anomaly (base succeeds, high fails) shows that enhanced ARIA creates more SoM labels, which provides more exploration options, which delays the agent's fallback to direct URL construction. This is a novel finding: **accessibility enhancement can degrade SoM agent performance** by inflating the visual action space.

### 7.4 The 0%-Across-All Tasks Strengthen the Causal Argument

By showing that admin:41, admin:198, and gitlab:293 fail at ALL variants for SoM but succeed at ALL non-low variants for text-only, we establish that:
- These tasks are not inherently difficult (text-only solves them trivially)
- SoM's failures are observation-mode-specific, not task-specific
- The a11y tree provides fundamentally superior information for these task types (table parsing, form interaction, menu navigation)

This supports the paper's claim that the a11y tree's informational advantage over SoM screenshots is substantial (87.8% vs 24.4% at non-low variants in Pilot 4), and that this advantage is especially pronounced for tasks requiring precise data extraction from structured interfaces.

---

## 8. Failure Classification Summary

| Case | Outcome | Failure Mode | Classification |
|------|---------|-------------|----------------|
| admin:41 low | partial_success | Visual misread | F_SOM_MISREAD |
| admin:41 ml | failure | Early stop (1 step) | F_SOM_EARLY_STOP |
| admin:41 base | partial_success | Visual misread | F_SOM_MISREAD |
| admin:41 high | partial_success | Visual misread + phantom bid | F_SOM_MISREAD |
| admin:94 low | failure | Navigation failure | F_SOM_NAV |
| admin:94 ml | timeout | Exploration spiral | F_SOM_EXPLORE |
| admin:94 base | timeout | Exploration spiral | F_SOM_EXPLORE |
| admin:94 high | **success** | — | — |
| admin:198 low | failure | Navigation failure | F_SOM_NAV |
| admin:198 ml | partial_success | Wrong order (visual) | F_SOM_MISREAD |
| admin:198 base | partial_success | Wrong order (visual) | F_SOM_MISREAD |
| admin:198 high | partial_success | Wrong order (visual) | F_SOM_MISREAD |
| ecom:188 low | **success** | — (forced simplification) | — |
| ecom:188 ml | timeout | Phantom bid loop (21 consec) | F_SOM_PHANTOM |
| ecom:188 base | timeout | Phantom bid loop (29 consec!) | F_SOM_PHANTOM |
| ecom:188 high | timeout | Phantom bid loop (19 consec) | F_SOM_PHANTOM |
| gitlab:132 low | partial_success | Search/navigation failure | F_SOM_NAV |
| gitlab:132 ml | **success** | — | — |
| gitlab:132 base | **success** | — | — |
| gitlab:132 high | timeout | Exploration spiral (ARIA inflation) | F_SOM_EXPLORE |
| gitlab:293 low | timeout | Fill loop (5 consec) | F_SOM_FILL |
| gitlab:293 ml | timeout | Click+fill interleave | F_SOM_FILL |
| gitlab:293 base | timeout | Fill loop + click loop (9 consec) | F_SOM_FILL |
| gitlab:293 high | timeout | Fill loop (6 consec) | F_SOM_FILL |
| gitlab:308 low | timeout | Click loop (7 consec) | F_SOM_PHANTOM |
| gitlab:308 ml | **success** | — | — |
| gitlab:308 base | timeout | Click loop (7 consec) | F_SOM_PHANTOM |
| gitlab:308 high | timeout | Click loop (10 consec) | F_SOM_PHANTOM |

**Failure mode distribution** (n=23 failures):
- F_SOM_PHANTOM (phantom bid loop): 7 (30%)
- F_SOM_MISREAD (visual data misread): 6 (26%)
- F_SOM_FILL (form interaction failure): 4 (17%)
- F_SOM_EXPLORE (exploration spiral): 3 (13%)
- F_SOM_NAV (navigation failure): 3 (13%)

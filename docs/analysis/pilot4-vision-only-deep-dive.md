# Pilot 4 Vision-Only Agent Deep Dive

**Date:** 2026-04-08
**Data source:** Pilot 4 full run (f4929214), 120 vision-only traces
**Method:** Trace-level reading of 15+ individual traces across all 4 investigations

---

## Executive Summary

The vision-only agent (screenshot + SoM overlay, no a11y tree) achieves 18.3% overall (22/120), concentrated in exactly 2 of 6 tasks. Trace analysis reveals three distinct failure mechanisms and confirms the causal role of DOM semantics in SoM label generation.

---

## 1. Low Variant 0% — The Phantom Label Effect

**Finding:** Vision-only at low variant is 0/30 (0.0%), replicating Pilot 3b.

**Mechanism — Two distinct failure modes discovered:**

### Mode A: "Phantom Labels" (ecommerce tasks)
The low variant mutates DOM elements (link→span, removing interactive roles), but the SoM overlay is generated from the DOM's interactive element set. When low variant removes interactivity, SoM labels are still rendered on the screenshot at positions where elements *used to be* interactive, but the underlying DOM elements are now non-interactive `<span>` elements with `browsergym_set_of_marks="0"`.

**Trace evidence — `ecommerce_admin_low_4_1_1`:**
- Agent sees label "615" in screenshot, reasons about "Bestsellers section (label 615)"
- Clicks `click("615")` → resolves to `<span bid="615" browsergym_set_of_marks="0">Notifications</span>`
- Fails: "element is not visible" — the span exists but is not visible/interactive
- Agent tries label "545" → same result: `<ul bid="545" browsergym_set_of_marks="0">` — not visible
- Pattern repeats for all 4 steps until timeout

**Trace evidence — `ecommerce_low_24_1_1`:**
- Agent sees label "404" in screenshot → resolves to `<span bid="404">Makeup Palettes</span>` — not visible
- Agent sees label "1657" for Reviews tab → `ValueError: Could not find element with bid "1657"` — element doesn't exist
- Agent sees label "1658" → resolves to `<div bid="1658" data-role="content" id="modal-content...>` — not visible
- Stuck in loop: can see labels in screenshot but every click fails

### Mode B: "Vanished Elements" (reddit tasks)
On reddit (Postmill), the low variant removes interactive roles more aggressively. SoM labels that the agent sees in the screenshot correspond to element IDs that *do not exist at all* in the DOM.

**Trace evidence — `reddit_low_67_1_1`:**
- Agent sees "Forums" in navigation, identifies label "52" and "229" from screenshot
- Clicks `click("52")` → `ValueError: Could not find element with bid "52"` — element doesn't exist
- Clicks `click("229")` → `ValueError: Could not find element with bid "229"` — element doesn't exist
- Agent repeats click("229") for **25 consecutive steps**, never finding the element
- Total: 26 steps, all failures, 77K tokens burned

**Trace evidence — `reddit_low_29_1_1`:**
- Step 3: `click("139")` → `ValueError: Could not find element with bid "139"`
- Step 4: `click("138")` → `ValueError: Could not find element with bid "138"`
- Agent eventually finds some working elements (235, 236) but gets stuck clicking them repeatedly without navigation

**Key insight:** The two modes differ by site architecture:
- **Magento (ecommerce):** Low variant makes elements non-visible but keeps them in DOM → "element is not visible" errors
- **Postmill (reddit):** Low variant removes elements entirely from interactive set → "Could not find element" errors

Both modes produce 0% success because the agent cannot interact with any navigation elements.

---

## 2. Success Concentrated in 2 Tasks — Task Solvability Analysis

### Why ecommerce:24 succeeds (10/20 overall)

**Task:** "Find reviewers who mention price being unfair" on a product page with 2 reviews.

**Success mechanism — `ecommerce_high_24_1_1` (6 steps, success):**
1. Agent starts on product page, tries clicking review link → fails (not visible)
2. Falls back to `scroll(0, 500)` twice to find "Reviews (2)" tab
3. Clicks tab `click("1558")` → succeeds
4. Reads reviews visually from screenshot, sees both are positive
5. Sends answer: "No reviewers mention price being unfair"

**Why this works:** Task 24 has only 2 reviews, all visible on one screen after scrolling. The answer is a simple "no" — the agent just needs to read visible text. No multi-page navigation, no complex interaction chains.

**Success mechanism — `ecommerce_medium-low_24_1_1` (5 steps, success):**
- Same pattern: scroll down, click Reviews tab, read visible text, answer "no"
- The tab click `click("1558")` works at medium-low and above

### Why reddit:67 succeeds (12/20 overall)

**Task:** "Find book recommendations in top 10 posts of /f/books forum"

**Success mechanism — `reddit_base_67_1_1` (8 steps, success):**
1. Starts on /forums page, clicks "43" → success
2. Scrolls down 3 times to find "books" forum in list
3. Clicks "542" to enter /f/books → success
4. Reads post titles visually from screenshot
5. Scrolls once more to see all top 10 posts
6. Identifies book titles from post titles (visual text reading)
7. Sends answer listing 4 book titles

**Why this works:** The task requires reading post *titles* which are large, visible text. The agent doesn't need to click into individual posts or navigate complex UI. The forum list and post titles are all readable from screenshots.

### Why ecommerce:23 always fails (0/20)

**Task:** "Find reviewers who mention 'good fingerprint resistant'" on a product with 12 reviews across 2 pages.

**Failure mechanism — `ecommerce_base_23_1_1` (7 steps, partial_success):**
- Agent scrolls through reviews, reads some visible text
- Finds mentions of fingerprint resistance in product description (not reviews)
- Cannot click pagination to page 2 (element "615" not visible)
- Gives incomplete/wrong answer based on partial review reading

**Failure mechanism — `ecommerce_low_23_1_1` (18 steps, failure):**
- Agent scrolls up and down repeatedly trying to find reviews section
- Reviews tab click fails, pagination fails
- Never reaches the actual review content
- Bridge timeout at 120s

**Why this always fails:** 12 reviews across 2 pages requires pagination interaction. The pagination element (bid "615") is consistently "not visible" across ALL variants — this is a Magento UI issue where the pagination `<li>` element has `browsergym_set_of_marks="0"` and is not interactable. Even at high variant, the agent cannot paginate.

### Why ecommerce:26 always fails (0/20)

**Task:** "Find reviewers who complain about customer service" on a product with 12 reviews across 2 pages.

**Failure mechanism — `ecommerce_high_26_1_1` (13 steps, partial_success):**
- Agent successfully scrolls through page 1 reviews, finds 2 relevant reviewers
- Tries to click page 2 pagination → `click("615")` fails: "element is not visible"
- Gives partial answer (only page 1 reviewers) → marked as failure by evaluator

**Why this always fails:** Same pagination problem as ecom:23. The task requires reading ALL reviews across multiple pages, but pagination is broken for the vision-only agent.

### Why reddit:29 always fails (0/20)

**Task:** "Find latest post on DIY, check user's comments for downvote ratio"

**Failure mechanism — `reddit_high_29_1_1` (18 steps, failure):**
- Agent navigates to /f/DIY successfully
- Identifies first post by "Sorkill" correctly
- Tries to click username "Sorkill" to visit profile → clicks elements 235, 236, 223, 224, 234, 237 repeatedly
- None of these clicks navigate to the user profile page
- Agent is stuck on the same page for 15+ steps, clicking different elements
- Bridge timeout at 120s

**Why this always fails:** The task requires multi-step navigation: forum → post → user profile → comments tab → count votes. The vision-only agent cannot reliably navigate between pages because clicking SoM labels on link text often fails to trigger navigation.

### Why ecommerce_admin:4 always fails (0/20)

**Task:** "Find the most viewed product in the admin reports"

The admin backend has a complex sidebar menu with nested navigation. The vision-only agent cannot navigate the admin menu structure — SoM labels on menu items either resolve to non-visible elements or fail to trigger the correct navigation. All 20 traces show the agent stuck on the dashboard page, unable to reach the Reports section.

---

## 3. Task Solvability Summary

| Task | Vision Success | Mechanism |
|------|---------------|-----------|
| ecommerce:23 | 0/20 (0%) | Pagination broken (bid "615" not visible) |
| ecommerce:24 | 10/20 (50%) | Simple task: scroll + read 2 reviews |
| ecommerce:26 | 0/20 (0%) | Pagination broken (same as 23) |
| ecommerce_admin:4 | 0/20 (0%) | Admin menu navigation impossible |
| reddit:29 | 0/20 (0%) | Multi-step navigation fails |
| reddit:67 | 12/20 (60%) | Simple task: read post titles from list |

**Pattern:** Vision-only succeeds ONLY on tasks requiring simple visual reading (scroll + read visible text). Any task requiring multi-step navigation or interaction with specific UI widgets fails.

---

## 4. The Variant Gradient in Vision-Only

| Variant | Success | Rate |
|---------|---------|------|
| low | 0/30 | 0.0% |
| medium-low | 7/30 | 23.3% |
| base | 6/30 | 20.0% |
| high | 9/30 | 30.0% |

The gradient (0% → 23% → 20% → 30%) is driven entirely by ecom:24 and reddit:67:
- **ecom:24:** low=0, ml=3, base=2, high=5 — high variant's enhanced ARIA makes tab clicks work more reliably
- **reddit:67:** low=0, ml=4, base=4, high=4 — flat at non-low (SoM labels work once interactive roles are present)

The low→non-low jump (0% → ~24%) is because low variant removes interactive semantics that SoM labels depend on. This is NOT a visual change — it's a DOM semantic change affecting SoM label generation.

---

## 5. Causal Interpretation

The vision-only agent was designed as a control condition: since DOM mutations change semantics but not visual appearance, vision-only should be unaffected by variant level. **This expectation was wrong.**

**Revised understanding:** SoM (Set-of-Marks) overlay labels are generated from the DOM's interactive element set. When low variant removes interactive roles (link→span, button→div), those elements lose their SoM labels. The vision-only agent sees a screenshot with fewer/broken labels, making interaction impossible.

**Two causal pathways confirmed:**
```
Low variant DOM mutations
    ├── Path A: Degrade a11y tree → text-only agent fails (CONFIRMED, 23.3% vs 86.7%)
    └── Path B: Remove interactive elements → SoM labels broken → vision-only fails (CONFIRMED, 0% vs 20%)
```

Both agents are affected by low variant, but through DIFFERENT mechanisms:
- Text-only: degraded semantic information in a11y tree text
- Vision-only: missing/broken SoM bid labels on de-semanticized elements

**For the paper:** The vision-only control condition does not provide a clean "visual-only" baseline because SoM depends on DOM semantics. However, this is itself a novel finding: even "visual" AI agents are indirectly dependent on DOM accessibility through their element identification pipeline.

---

## 6. Implications

1. **Vision-only is NOT a pure visual control** — SoM labels depend on DOM interactive elements
2. **The meaningful comparison is text-only vs vision-only at non-low variants** where SoM labels are intact: text=87.8% vs vision=24.4% (63.3pp gap)
3. **This gap confirms a11y tree's informational advantage** — even with working SoM labels, the a11y tree provides substantially more task-relevant information than screenshots
4. **Future work:** Use raw screenshots without SoM overlay for a true visual-only control, or use a fixed SoM overlay generated from base variant DOM applied to all variants
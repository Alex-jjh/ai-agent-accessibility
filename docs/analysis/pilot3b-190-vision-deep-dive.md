# Pilot 3b-190 Vision-Only Deep Dive Analysis

**Run:** `fb6d0b8b-a7c3-44d8-922d-e94963795a12`
**Agent config:** `configIndex=1` → vision-only (screenshot only, no a11y tree)
**Date:** 2026-04-06

---

## Task A: Vision Low 0/27 Failure Mechanism Classification

### Summary Table

| Trace | Task | Category | Steps | Classification | Any Click Succeeded? |
|-------|------|----------|-------|----------------|---------------------|
| ecommerce_low_23_1_1 | 23 | ecommerce | 30 (truncated) | **SoM_PRESENT_CLICK_FAIL** | Yes (step 1: bid 1421, step 16: bid 1551, step 24: bid 1551) but never reached reviews content |
| ecommerce_low_23_1_2 | 23 | ecommerce | 30 (truncated) | **SoM_PRESENT_CLICK_FAIL** | Yes (step 1: bid 1421) but then stuck on bid 1651 forever |
| ecommerce_low_24_1_1 | 24 | ecommerce | 30 (truncated) | **SoM_PRESENT_CLICK_FAIL** | Yes (step 3: scroll, step 20: bid 1557, step 21: scroll) but never read review text |
| ecommerce_low_24_1_2 | 24 | ecommerce | 30 | **SoM_PRESENT_CLICK_FAIL** | Only scrolls succeeded; all click attempts failed |
| reddit_low_29_1_1 | 29 | reddit | 30 | **SoM_MISSING** / **TIMEOUT_LOOP** | Yes (step 23: bid 31) but then stuck on bid 229 loop |
| reddit_low_29_1_2 | 29 | reddit | 30 | **SoM_MISSING** / **TIMEOUT_LOOP** | Yes (step 7: bid 31, step 24: bid 31, step 26: bid 35) but stuck on bid 229 loop |

### Detailed Trace Analysis

#### 1. `ecommerce_low_23_1_1` — SoM_PRESENT_CLICK_FAIL

**Task:** Find reviewers who mention "good fingerprint resistant" for a Samsung Galaxy S6 screen protector.

**Step-by-step:**
- **Step 1:** Agent clicks bid `1421` → **success**. This is the "12 Reviews" link area.
- **Steps 2-5:** Agent scrolls down looking for reviews content. Sees product features ("Anti-Oil", "Oleophobic screen coating magically resists oils and reduces annoying fingerprints") but cannot find actual customer review text.
- **Steps 6-14:** Agent repeatedly tries to click bid `1651` (the "Reviews (12)" tab it sees in the SoM overlay). **Every attempt fails with `ValueError: Could not find element with bid "1651"`**. The agent also tries bid `1652` which resolves to a `<div data-role="content" id="modal-content...>` that is **not visible**.
- **Step 16:** Agent tries bid `1551` → **success**. This appears to activate the Reviews tab.
- **Steps 17-27:** Agent scrolls up and down repeatedly looking for actual review text content. It sees product description text about fingerprint resistance but **never finds the individual customer reviews**. The reviews content is not rendering visually or the agent cannot read it from the screenshot.

**Agent reasoning quotes:**
- Step 6: *"I can see the product page with the 'Reviews (12)' tab visible... Let me click on the Reviews tab"*
- Step 12: *"The previous attempts failed, but I can also see element ID 1652 near the Reviews tab. Let me try clicking on that instead."*
- Step 15: *"Since the URL already shows #reviews, the reviews section might already be loaded. Let me scroll down"*

**Classification: SoM_PRESENT_CLICK_FAIL** — Agent sees SoM labels in screenshot, references specific bid numbers (1651, 1652), but the bids either don't exist in the DOM or resolve to invisible elements. The low variant's DOM mutations likely removed or hid the interactive tab elements while the SoM overlay still renders labels at those positions.

---

#### 2. `ecommerce_low_23_1_2` — SoM_PRESENT_CLICK_FAIL

**Task:** Same as above (task 23, attempt 2).

**Step-by-step:**
- **Step 1:** Agent clicks bid `1421` → **success**.
- **Steps 2-5:** Scrolls, sees product features.
- **Steps 6-26:** Agent is **completely stuck** trying bid `1651` repeatedly. Every single attempt returns `ValueError: Could not find element with bid "1651"`. Agent also tries `1652` (steps 16, 23, 26) which resolves to invisible `<div data-role="content" id="modal-content...>`.
- **Steps 27-29:** Agent scrolls and tries more bids but never breaks out of the loop.

**Agent reasoning quotes:**
- Step 6: *"I can see the Reviews (12) tab which will show me the actual customer reviews"*
- Step 16: *"Since element ID 1651 is not working, let me try clicking on element ID 1652 which appears to be associated with the Reviews section"*

**Classification: SoM_PRESENT_CLICK_FAIL** — Pure bid hallucination loop. Agent sees "1651" in the SoM overlay on the screenshot but this bid does not exist in the actual DOM. The low variant has broken the tab element's DOM structure.

---

#### 3. `ecommerce_low_24_1_1` — SoM_PRESENT_CLICK_FAIL

**Task:** Find reviewers who mention price being unfair for Haflinger slippers.

**Step-by-step:**
- **Step 1:** Agent clicks bid `404` → **failure** (resolves to `<span>Makeup Palettes</span>`, not visible — a menu item, not the reviews link).
- **Step 2:** Agent clicks bid `883` → **failure** (resolves to `<li>`, not visible).
- **Step 3:** Scrolls down 500px → success.
- **Steps 4-17:** Agent sees "Reviews (2)" tab in screenshot. Repeatedly tries bids `1657` and `1658`:
  - `1657`: **ValueError: Could not find element** (does not exist in DOM)
  - `1658`: Resolves to `<div data-role="content" id="modal-content...>` — **not visible**
- **Step 18:** Scrolls down 300px.
- **Step 19:** Tries bid `1568` → resolves to `<legend>`, not visible.
- **Step 20:** Tries bid `1557` → **success!** Reviews tab activates.
- **Steps 21-30:** Agent scrolls up and down trying to read review content but **cannot see the actual review text** in the screenshot. Gets stuck scrolling.

**Agent reasoning quotes:**
- Step 4: *"I can see 'Reviews (2)' tab at the bottom of the page. I need to click on it"*
- Step 7: *"Let me try clicking on the 'Reviews (2)' tab which appears to be element 1657"*
- Step 20: *"I successfully clicked on the 'Reviews (2)' tab and can now see the reviews section"*
- Step 22: *"I can see the product information and details, but I need to scroll back up to find the actual customer reviews"*

**Classification: SoM_PRESENT_CLICK_FAIL** — Agent sees SoM labels, references them, but most bids are phantoms. Even after successfully clicking the Reviews tab (step 20), the agent **cannot read the review text from the screenshot** — the reviews content may be below the fold or the vision model cannot parse the text from the rendered page.

---

#### 4. `ecommerce_low_24_1_2` — SoM_PRESENT_CLICK_FAIL

**Task:** Same as above (task 24, attempt 2).

**Step-by-step:**
- **Step 1:** Agent clicks bid `404` → **failure** (same "Makeup Palettes" span, not visible).
- **Step 2:** Agent clicks bid `884` → **failure** (resolves to `<span id="ui-id-162">`, not visible).
- **Step 3:** Scrolls down → success.
- **Steps 4-21:** Agent is **completely stuck** alternating between bids `1657` (doesn't exist) and `1658` (invisible modal div). 18 consecutive failed click attempts with no variation in strategy.

**Agent reasoning quotes:**
- Step 4: *"I can see 'Reviews (2)' tab at the bottom of the page. I need to click on this tab"*
- Step 8: *"The element with label 1658 seems to be the tab content area, but I need to click on the actual tab header"*

**Classification: SoM_PRESENT_CLICK_FAIL** — Identical pattern to 24_1_1 but agent never discovers the working bid (1557). The low variant's DOM mutations make the tab header element invisible/removed while the SoM overlay still shows a label at that screen position.

---

#### 5. `reddit_low_29_1_1` — SoM_MISSING + TIMEOUT_LOOP

**Task:** Find the DIY forum, identify latest post, analyze comments.

**Step-by-step:**
- **Steps 1-22:** Agent is stuck on the homepage trying to click "Forums" navigation. Repeatedly tries bid `229` — **every attempt returns `ValueError: Could not find element with bid "229"`**. Also tries bids `52`, `230` — all fail.
- **Step 23:** Agent tries bid `31` → **success!** Navigates somewhere.
- **Step 24:** Back to trying bid `229` → fails.
- **Steps 25-26:** Scrolls.
- **Steps 27-30:** Back to bid `229` loop → all fail.

**Agent reasoning quotes:**
- Step 1: *"I can see 'Forums' in the navigation, so let me click on that to see available forums"*
- Step 8: *"I can see 'Forums' in the top navigation bar with a different label number"*
- Step 11: *"Looking at the screenshot, I can see 'Forums' in the top navigation bar with a different label number than 229"*
- Step 23: *"I can see 'Forums' in the top navigation bar with label 31"* → finally works

**Classification: SoM_MISSING + TIMEOUT_LOOP** — The agent sees "Forums" text in the screenshot and the SoM overlay shows label `229` near it, but bid 229 does not exist in the DOM. The low variant has converted the `<a>` link to a `<span>` (F42 operator), removing it from the interactive element set. The agent is stuck in a 30-step loop trying the same phantom bid. When it accidentally tries bid `31` (step 23), it succeeds — but then immediately reverts to trying `229` and gets stuck again.

---

#### 6. `reddit_low_29_1_2` — SoM_MISSING + TIMEOUT_LOOP

**Task:** Same as above (task 29, attempt 2).

**Step-by-step:**
- **Steps 1-6:** Agent tries bids `52`, `229`, `230` — all fail with `ValueError`.
- **Step 7:** Tries bid `31` → **success!** Navigates to headphones forum.
- **Steps 8-23:** Agent is stuck trying bid `229` to navigate to "Forums" list. 16 consecutive failures.
- **Step 24:** Tries bid `31` again → **success!** But still on headphones forum.
- **Step 25:** Tries bid `229` → fails.
- **Step 26:** Tries bid `35` → **success!** Navigates somewhere.
- **Steps 27-30:** Back to bid `229` loop → all fail.

**Agent reasoning quotes:**
- Step 2: *"I can see 'Forums' in the navigation menu at the top. This should take me to a list of all forums"*
- Step 8: *"I'm now on a forums page showing posts in the 'headphones' forum. I need to find the DIY forum specifically"*
- Step 24: *"I can see element 31 near the 'Forums' text in the navigation bar"*

**Classification: SoM_MISSING + TIMEOUT_LOOP** — Same pattern as 29_1_1. Agent sees "Forums" label in screenshot, hallucinates bid `229` from the SoM overlay, but this bid doesn't exist. Occasionally stumbles onto working bids (`31`, `35`) but cannot navigate to the DIY forum because the primary navigation element has been destroyed by the low variant.

---

### Failure Mechanism Summary

| Classification | Count | Description |
|---------------|-------|-------------|
| **SoM_PRESENT_CLICK_FAIL** | 4/6 | Agent sees SoM labels, references specific bid numbers, but bids either don't exist in DOM or resolve to invisible elements. Low variant DOM mutations (F42: link→span, F55: focus blur) break interactive elements while SoM overlay still renders labels at those screen positions. |
| **SoM_MISSING + TIMEOUT_LOOP** | 2/6 | Agent sees text labels in screenshot but the SoM bid numbers it reads are phantoms. Gets stuck in 20+ step loops trying the same non-existent bid. Occasionally finds working bids by accident but cannot sustain navigation. |

**Root cause:** The SoM overlay renders bid labels based on DOM element positions, but the low variant's accessibility mutations (removing `role`, converting `<a>` to `<span>`, adding `aria-hidden`) make elements non-interactive or invisible to Playwright's locator system. The vision-only agent sees the label in the screenshot but the underlying element cannot be clicked.

---

## Task B: ecom:24 Vision Gradient — low 0/5 vs non-low 13/13

### The Cleanest Gradient

Task 24 ("find reviewers who mention price being unfair" for Haflinger slippers) shows a perfect vision gradient:
- **Low:** 0/5 (all fail)
- **Medium-low, Base, High:** 13/13 (all succeed)

### Trace Comparison

#### `ecommerce_low_24_1_1` (FAILURE — 30 steps, timeout)

1. **Step 1:** Clicks bid `404` → fails (resolves to "Makeup Palettes" span, not visible)
2. **Step 2:** Clicks bid `883` → fails (invisible `<li>`)
3. **Step 3:** Scrolls down 500px
4. **Steps 4-17:** Sees "Reviews (2)" tab. Alternates between:
   - bid `1657` → `ValueError: Could not find element` (phantom)
   - bid `1658` → resolves to `<div data-role="content" id="modal-content...>` (invisible)
5. **Step 20:** Finally clicks bid `1557` → success (Reviews tab opens)
6. **Steps 21-30:** Scrolls up/down but **cannot read review text from screenshot**. Never answers.

**Divergence point:** The agent reaches the Reviews tab at step 20 but then cannot extract the review content visually. It scrolls repeatedly but never sees reviewer names or review text.

#### `ecommerce_base_24_1_1` (SUCCESS — 5 steps)

1. **Step 1:** Clicks bid `853` → fails (same invisible menu item pattern)
2. **Step 2:** Scrolls down 500px
3. **Step 3:** Scrolls down 500px more
4. **Step 4:** Sees "Reviews (2)" tab, clicks bid `1557` → **success!**
5. **Step 5:** Agent **immediately reads both reviews**:
   - *"First review by 'Wonderful!' - Rating: 5 stars, says 'Nothing.....everyday use.'"*
   - *"Second review by 'Joe' - 'Die Haflinger sind wie beschrieben und erwartet sehr gut'"*
   - Concludes: *"Neither review mentions anything about the price being unfair"*
   - Sends answer → **success**

#### `ecommerce_high_24_1_1` (SUCCESS — 8 steps)

1. **Steps 1-2:** Clicks bids `853`, `892` → both fail (invisible elements)
2. **Steps 3-6:** Scrolls down, then back up
3. **Step 7:** Clicks bid `1422` → **success!** (different bid than base's `1557`)
4. **Step 8:** Agent reads both reviews:
   - *"First review by 'Wonderful!' - Rating: 5 stars, says 'Nothing.....everyday use.'"*
   - *"Second review by 'Joe' - 'Die Haflinger sind wie beschrieben und erwartet sehr gut'"*
   - Sends answer → **success**

### Exact Divergence Point Analysis

| Aspect | Low | Base | High |
|--------|-----|------|------|
| First successful click on Reviews tab | Step 20 (bid 1557) | Step 4 (bid 1557) | Step 7 (bid 1422) |
| Steps wasted on phantom bids | 16 steps (bids 1657, 1658) | 1 step (bid 853) | 2 steps (bids 853, 892) |
| Could read review text after tab opened? | **NO** — scrolled 10+ steps, never saw text | **YES** — immediately read both reviews | **YES** — immediately read both reviews |
| Total steps | 30 (timeout) | 5 | 8 |

### Critical Finding: The Divergence Is NOT About Finding the Tab

The low trace actually finds and clicks the Reviews tab (step 20, bid 1557 — same bid as base!). The divergence happens **after** the tab opens:

- **Base/High:** After clicking the Reviews tab, the review content (reviewer names, star ratings, review text) renders visually and the agent reads it from the screenshot in a single step.
- **Low:** After clicking the Reviews tab, the agent **cannot see the review content**. It scrolls up and down for 10 steps saying things like *"I need to scroll back up to find the actual customer reviews"* and *"I can see product details but I need to find the actual customer reviews"*.

**Hypothesis:** The low variant's DOM mutations affect the review content rendering. Possible mechanisms:
1. `aria-hidden="true"` on review container → CSS may hide it
2. `display:none` or `visibility:hidden` applied by mutation
3. Review text nodes converted to non-visible elements
4. The review content is present in DOM but not rendered visually, so the screenshot shows blank space where reviews should be

### Does Base Show SoM Labels That Low Doesn't?

**No — both see the same SoM labels.** Both low and base traces reference the same bid numbers (1557 for the Reviews tab). The difference is:
1. **Low wastes more steps** on phantom bids (1657, 1658) before finding 1557
2. **Low cannot read review content** even after successfully opening the Reviews tab

The SoM overlay is identical across variants (it's rendered from the DOM). The issue is that the low variant's mutations make the review *content* invisible/unreadable in the screenshot, not that the SoM labels are different.

---

## Task C: ecom:26 vision 0/19 vs ecom:24 vision non-low 13/13

### Task Descriptions

- **Task 24:** "List reviewers who mention price being unfair" → Haflinger slippers, 2 reviews, single page
- **Task 26:** "List reviewers who complain about customer service" → Epson printer, 12 reviews, **2 pages**

### `ecommerce_base_26_1_1` (FAILURE — 11 steps, partial_success)

1. **Step 1:** Clicks bid `1421` → **success** (reviews link works immediately!)
2. **Steps 2-8:** Agent scrolls through reviews, **successfully reads multiple reviews**:
   - Sees "JellyfishGoldfish" review ("Decent ink gobbler")
   - Sees "Shirey II" and "Roxanne Brandon Coffey" reviews
   - **Finds "Pich in Vegas"** — customer service complaint: *"Called customer service, and through very broken English was told there was no way to change their arbitrary 2-sided default"*
   - **Finds "AmyRemyR"** — customer service complaint: *"Her technical support is CLEARLY not customer support"*
3. **Step 9:** Agent sees pagination "1 2" and tries to click page 2 (bid `615`) → **failure** (invisible `<li>`)
4. **Step 10:** Tries bid `615` again → **failure**
5. **Step 11:** Agent gives up on page 2 and sends answer: *"Pich in Vegas, AmyRemyR"*

**Result:** `partial_success` / `F_REA` (failure confidence 0.7) — Agent found 2 of the reviewers but **could not access page 2** of reviews to find additional complainers.

### `ecommerce_base_24_1_1` (SUCCESS — 5 steps)

As analyzed above: Agent clicks Reviews tab, immediately reads both reviews (only 2, single page), sends correct answer.

### Comparison

| Aspect | Task 24 (base, success) | Task 26 (base, failure) |
|--------|------------------------|------------------------|
| Product | Haflinger slippers | Epson printer |
| Total reviews | 2 | 12 |
| Review pages | 1 | **2** |
| Reviews visible on page 1 | All 2 | ~8 of 12 |
| Agent could read review text? | Yes | Yes |
| Agent found relevant reviewers? | Yes (none exist → correct "no") | **Partial** (found 2, missed page 2) |
| Pagination required? | No | **Yes** |
| Pagination click worked? | N/A | **No** (bid 615 → invisible `<li>`) |

### Why Task 26 Always Fails for Vision

1. **Pagination is the blocker.** Task 26 has 12 reviews across 2 pages. The agent successfully reads page 1 reviews and correctly identifies customer service complaints. But it **cannot click the page 2 pagination link** — the bid resolves to an invisible `<li>` element.

2. **The answer requires completeness.** Even though the agent found 2 correct reviewers (Pich in Vegas, AmyRemyR), the evaluation likely requires finding ALL reviewers who complain about customer service, including those on page 2. The `partial_success` outcome with `F_REA` classification confirms this.

3. **Task 24 succeeds because it's simpler.** Only 2 reviews, single page, and the correct answer is "no one mentions unfair pricing" — the agent just needs to read 2 short reviews and confirm absence. No pagination needed.

4. **This is NOT a variant-specific issue.** Task 26 fails at base level too (0/19 across all vision variants). The pagination click failure affects all variants equally because it's a structural page interaction issue, not an accessibility mutation issue.

### Is Task 26 Harder Because Reviews Require More Navigation?

**Yes, definitively.** The failure mechanism is:
- **Task 24:** 2 reviews, 1 page → read all, answer → done
- **Task 26:** 12 reviews, 2 pages → read page 1 (works), click page 2 (fails) → incomplete answer → fail

The vision-only agent can read review text from screenshots (proven by task 26 step 4-5 where it quotes specific review content). The bottleneck is **interactive pagination** — clicking page navigation elements that the SoM overlay labels but that resolve to invisible DOM elements.

---

## Cross-Cutting Findings

### 1. The SoM Bid Hallucination Problem

Across all 6 low traces, the dominant failure pattern is the agent reading SoM label numbers from the screenshot that don't correspond to clickable DOM elements:

| Phantom Bid | Actual Element | Traces Affected |
|-------------|---------------|-----------------|
| `1651` | Does not exist in DOM | ecom_low_23_1_1, ecom_low_23_1_2 |
| `1657` | Does not exist in DOM | ecom_low_24_1_1, ecom_low_24_1_2 |
| `1658` | `<div data-role="content" id="modal-content">` (invisible) | ecom_low_24_1_1, ecom_low_24_1_2 |
| `229` | Does not exist in DOM | reddit_low_29_1_1, reddit_low_29_1_2 |
| `52` | Does not exist in DOM | reddit_low_29_1_1, reddit_low_29_1_2 |

The low variant's DOM mutations (F42: `<a>` → `<span>`, F77: duplicate IDs, F55: focus blur) remove elements from the interactive set. The SoM overlay may still render labels at those screen positions based on the pre-mutation DOM snapshot, creating a mismatch between what the agent sees and what it can click.

### 2. Vision-Only Agent CAN Read Text From Screenshots

Contrary to what might be expected, the vision-only agent demonstrates strong text reading ability:
- Task 26 base: Agent reads and quotes specific review content ("Called customer service, and through very broken English...")
- Task 24 base/high: Agent reads both reviews and correctly identifies reviewer names and content
- Task 23 low: Agent reads product feature text ("Oleophobic screen coating magically resists oils and reduces annoying fingerprints")

The failure is not in text comprehension but in **element interaction** — finding and clicking the right DOM elements.

### 3. Low Variant Creates a Double Failure Mode

For ecommerce tasks, the low variant causes TWO distinct failures:
1. **Navigation failure:** Agent wastes 15-20 steps clicking phantom bids before finding a working one
2. **Content invisibility:** Even after navigating to the right section, review content may not render visually due to DOM mutations

This explains why low is 0/27 while base/high succeed — base/high agents find working bids faster AND can see the content after navigation.

### 4. Task 26 Is a Vision-Universal Failure

Task 26 fails across ALL vision variants (0/19) because pagination is broken for the vision-only agent regardless of accessibility level. This is a **task complexity confound**, not an accessibility gradient signal. Task 26 should be excluded from vision-only gradient analysis or analyzed separately as a pagination-dependent task.

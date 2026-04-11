# Pilot 3b-190 Trace Deep Dive

Run: `fb6d0b8b-a7c3-44d8-922d-e94963795a12`
Date: 2026-04-06
Analyst: Kiro (automated trace analysis)

---

## Investigation 1: ecom:23 low text-only — 4/5 success (variant escape?)

### Summary

**Verdict: CONFIRMED VARIANT ESCAPE via goto() reload.**

All 4 successes follow the same pattern: agent cannot see reviews in degraded DOM → uses goto() to reload the page → variant patches are cleared → reviews become visible → agent finds Rachel and T. Gannon.

### Per-Rep Breakdown

| Rep | Success | Steps | goto() | After goto: links | tabpanel | Rachel | Gannon | Final answer |
|-----|---------|-------|--------|-------------------|----------|--------|--------|-------------|
| 1   | ✅ YES  | 9     | Step 6 (full URL) | 0→1→3 | YES | YES | YES | "Rachel, T. Gannon" |
| 2   | ❌ NO   | 5     | Step 4 (URL#reviews) | 0→0 | NO | NO | NO | "cannot complete" |
| 3   | ✅ YES  | 8     | Step 5 (full URL) | 0→links appear | YES | YES | YES | "Rachel, T. Gannon" |
| 4   | ✅ YES  | 7     | Step 4 (full URL) | 0→links appear | YES | YES | YES | "Rachel, T. Gannon" |
| 5   | ✅ YES  | 8     | Step 5 (full URL) | 0→links appear | YES | YES | YES | "Rachel, T. Gannon" |

### Detailed Mechanism (Rep 1 exemplar)

**Steps 1–5 (degraded DOM):**
- Step 1: Agent sees product page. `links=0, listitems=29`. Low variant has converted all `<a>` links to `<span>` (F42 operator). The "Reviews" tab exists as StaticText but is not a clickable link.
- Agent clicks bid 1551 (the Reviews text), scrolls repeatedly. Reviews section header "Reviews (12)" is visible but **no review content appears** — the tabpanel content is invisible in the a11y tree.
- `tabpanel=NO` across all pre-goto steps. This is the content invisibility pathway.

**Step 6 (goto escape):**
- Agent reasons: "The accessibility tree is not showing the clickable elements like the '12 Reviews' link"
- Action: `goto("http://10.0.1.49:7770/3-pack-samsung-galaxy-s6-screen-protector-...html")`
- **After goto: `links=1, listitems=22, tabpanel=YES`**
- The page reloads WITHOUT variant patches. Links reappear. The tabpanel with review content becomes visible.

**Steps 7–9 (clean DOM):**
- Step 7: Agent clicks Reviews tab (bid 1522). Observation now contains `Rachel` and `Gannon` reviewer names. `links=3`.
- Step 8: Agent clicks page 2 of reviews (bid 1906).
- Step 9: `send_msg_to_user("Rachel, T. Gannon")` — correct answer.

### Why Rep 2 Failed

Rep 2 used `goto("...html#reviews")` with a URL fragment. This navigated to the same page with `#reviews` anchor but **did not trigger a full page reload** — the variant patches persisted. The observation after goto still showed `links=0, tabpanel=NO`. The agent gave up after 5 steps.

### Variant Persistence Analysis

- **No `[data-variant-revert]` markers found** in any observation across all 5 reps. The variant revert system is not leaving DOM markers.
- **Before goto:** `links=0` consistently across all steps. F42 (link→span) is fully applied.
- **After goto (full URL):** `links=1→3`. Links reappear. The goto() triggers a fresh page load that bypasses the variant injection init_script.
- **After goto (URL#fragment):** `links=0` persists. Hash navigation doesn't trigger a full reload.

### Conclusion

The 4/5 success rate for ecom:23 low text-only is **entirely due to variant escape**. The agent discovers that reviews are invisible, uses goto() to reload the page, and the variant patches are not re-applied after navigation. This is the same goto escape mechanism identified in Pilot 3b first run (3/5).

The improvement from 3/5 → 4/5 is stochastic: the one failure (rep 2) used a URL fragment instead of a full URL reload, which didn't clear the patches.

**These 4 successes should be reclassified as variant-escape artifacts, not genuine successes under degraded DOM.**

---

## Investigation 2: Vision-only 0/27 at low — what does the agent see?

### Summary

**Verdict: Vision-only agent at low variant gets repeated click failures. The agent can describe what it sees in screenshots but cannot interact with elements. SoM labels are not mentioned in observations — the observation is just `[screenshot only]` with a URL.**

### Trace: ecommerce_low_23_1_1 (vision-only, 30 steps, timeout)

- **Observation format:** `[screenshot only] http://10.0.1.49:7770/...` — just 210 characters. No a11y tree, no SoM label counts, no "labeled N elements" messages.
- **Agent reasoning:** The agent CAN describe what it sees: "I can see this is a product page for a Samsung Galaxy S6 screen protector. There are 12 reviews shown." It mentions visual features like "Impact Resistant", "Anti-Scratch", "Anti-Chip", "Anti-Oil", "HD" labels.
- **Actions:** `click("1421")` succeeds at step 1, then repeated `scroll(0, 500)` actions. The agent scrolls up and down looking for reviews but never finds them.
- **No SoM labels mentioned** in any reasoning. The agent uses bid numbers (like 1421) but these appear to be guessed from the a11y tree structure that isn't actually provided.
- **Outcome:** Timeout after 30 steps. The agent keeps scrolling and clicking but never reaches the review content.

### Trace: ecommerce_admin_low_4_1_1 (vision-only, task 4 admin)

- **Critical finding:** This trace shows the agent on the **reddit** site (http://10.0.1.49:9999/), not the ecommerce admin site. The observation starts with `[screenshot only] http://10.0.1.49:9999/`.
- **Repeated failures:** Steps 1–5+ all show `click("229") result=failure`. The agent keeps trying to click "Forums" in the navigation but every click fails.
- **Agent reasoning:** "I can see this appears to be a Reddit-like forum interface. I need to find the DIY forum." — the agent can read the screenshot but cannot interact.
- **No SoM overlay evidence:** No mention of labeled elements, SoM numbers, or overlay in any observation.

### Trace: reddit_low_29_1_1 (vision-only, 30+ steps)

- **Same pattern:** Agent sees reddit interface, tries `click("52")` then `click("229")` repeatedly. Every click returns `result=failure`.
- **Agent reasoning loop:** "I can see 'Forums' in the navigation menu at the top. Let me click on it to access the forums list." — repeated verbatim across 10+ steps.
- **No adaptation:** The agent doesn't try alternative strategies (goto, different element IDs). It's stuck in a click-failure loop.

### Key Question: Does F42 (link→span) remove SoM labels?

**The evidence is inconclusive on this specific question** because:
1. The observation format is `[screenshot only]` with no SoM metadata
2. No "labeled N elements" or "no clickable elements" messages appear
3. The agent uses bid numbers but they consistently fail at low variant

However, the pattern is clear: **at low variant, the vision-only agent cannot successfully click any elements**. The F42 operator converts links to spans, which likely removes them from the set of clickable/interactive elements that SoM would label. The agent sees the visual appearance of links but the underlying elements are non-interactive spans.

**At non-low variants (base, high), vision-only succeeds on tasks 24 and 67** — see Investigation 4. This confirms that the low variant's DOM mutations do affect vision-only agent interaction, even though the visual appearance is unchanged.

---

## Investigation 3: reddit:67 text-only inverted gradient

### Summary

**Verdict: Small-sample noise + goto escape. The "inversion" is not statistically meaningful.**

### Actual Results

| Variant | Reps available | Successes | Rate | Notes |
|---------|---------------|-----------|------|-------|
| low     | 3 (reps 1,3,4) | 3 | 100% (3/3) | All use goto() escape |
| base    | 5 (reps 1-5) | 2 | 40% (2/5) | 3 failures: 2 LLM errors, 1 navigation loop |
| high    | 2 (reps 3,5) | 0 | 0% (0/2) | Very small sample |
| medium-low | 4 (reps 1,2,4,5) | 3 | 75% (3/4) | |

### Low Successes (3/3) — goto escape mechanism

**Rep 1 (reddit_low_67_0_1):** 5 steps. Agent clicks "Forums" (bid 43), then uses `goto("http://10.0.1.49:9999/forums")` to navigate. After goto, the forums list appears. Agent navigates to books forum via another goto, then reads post titles and answers. `links=0` throughout (low variant applied), but the agent uses goto() to navigate directly by URL, bypassing the need to click links.

**Rep 3 (reddit_low_67_0_3):** 7 steps. Same pattern — goto to forums, goto to books, reads titles, answers correctly.

**Rep 4 (reddit_low_67_0_4):** 5 steps. Same goto-based navigation.

**Key insight:** For reddit:67, the task is "list book names from top 10 posts that recommend a single book." The agent doesn't need to click into individual posts — it can read post titles from the forum listing page. The low variant's F42 (link→span) doesn't hide post titles, which are visible as StaticText. The agent uses goto() to navigate between pages, bypassing the broken links entirely.

### Base Failures (3/5)

**Rep 1 (reddit_base_67_0_1):** 9 steps, failure. Agent navigates to books forum successfully (links work at base). But then it clicks into individual posts to read them (steps 3-8), going back and forth. At step 9: `action=noop()` with reasoning "LLM call failed". **The failure is an LLM error, not a navigation failure.**

**Rep 2 (reddit_base_67_0_2):** 9 steps, failure. Same pattern — agent navigates into individual posts, then hits LLM error at step 9.

**Rep 5 (reddit_base_67_0_5):** 9 steps, failure. Same LLM error pattern.

### Why Low Outperforms Base

The inversion has two causes:

1. **Navigation strategy divergence:** At low variant (links=0), the agent is FORCED to use goto() for navigation, which is actually more efficient for this task. It goes directly to `/f/books` and reads titles. At base variant (links work), the agent clicks into individual posts to read full content, which is slower and leads to more LLM calls.

2. **LLM call failures:** 3/5 base failures end with "LLM call failed" at step 9. The agent's strategy of clicking into posts generates longer context (more observations), which may trigger token limits or API errors. The low variant's simpler goto-based strategy generates shorter traces.

3. **Small sample size:** 3 low reps vs 5 base reps. With n=3 and n=5, the difference (100% vs 40%) is not statistically significant (Fisher's exact p=0.196).

**This is NOT the low variant "accidentally helping" like task 24 in Pilot 2.** It's a combination of forced strategy simplification (goto instead of click-navigate) and LLM reliability issues at longer context lengths.

---

## Investigation 4: Vision-only successes — how do they work?

### Summary

**Verdict: Vision-only succeeds on tasks 24 and 67 at non-low variants by reading screenshot content directly. The agent uses SoM bid numbers for clicks and scrolls to navigate, reading visible text from screenshots.**

### All Vision-Only Successes (21 total)

| Task | Variant | Successes | Total | Rate |
|------|---------|-----------|-------|------|
| ecom:24 | base | 5/5 | 5 | 100% |
| ecom:24 | high | 5/5 | 5 | 100% |
| ecom:24 | medium-low | 3/3 | 3 | 100% |
| reddit:67 | base | 2/3 | 3 | 67% |
| reddit:67 | high | 2/2 | 2 | 100% |
| reddit:67 | medium-low | 4/4 | 4 | 100% |

**Zero successes at low variant for any task.**

### Trace: ecommerce_base_24_1_1 (vision-only, 5 steps, SUCCESS)

Task 24: "List reviewers who mention price is unfair" for Haflinger slippers.

- **Step 1:** `click("853")` → failure. Agent tries to click "2 Reviews" link but fails.
- **Step 2-3:** `scroll(0, 500)` twice. Agent scrolls down looking for reviews section.
- **Step 4:** `click("1557")` → success. Agent finds and clicks "Reviews (2)" tab.
- **Step 5:** `send_msg_to_user("No reviewers mention the price being unfair...")` → success.

**Agent reasoning at step 5:** "I can now see the Customer Reviews section with 2 reviews. Let me examine both reviews: 1. First review by 'Wonderful!' - Rating: 5 stars... 2. Second review by 'Joe' - 'Die Haflinger sind wie beschrieben und erwartet sehr gut' (German)..."

**The agent reads review content directly from the screenshot.** It can see reviewer names, star ratings, and review text. At base variant, the Reviews tab is a clickable element (not degraded by F42), so the click succeeds.

### Trace: reddit_medium-low_67_1_1 (vision-only, 8 steps, SUCCESS)

Task 67: "List book names from top 10 posts recommending a single book."

- **Step 1:** `click("43")` → success. Agent clicks "Forums" link.
- **Steps 2-4:** `scroll(0, 500)` three times. Agent scrolls through forums list looking for "books".
- **Step 5:** `click("542")` → success. Agent finds and clicks "books" forum.
- **Steps 6-7:** `scroll(0, 300)` and `scroll(0, 200)`. Agent scrolls through posts.
- **Step 8:** `send_msg_to_user("The Haunting of Hill House, Misty of Chincoteague, The Hobbit, A Christmas Carol")` → success.

**Agent reasoning at step 6:** "I'm now in the books forum and can see the posts. I can see several posts listed... 1. 'The haunting of hill house was so good' - This appears to recommend a single book. 2. 'The letters of T. S. Eliot to Emily Hale...' — about letters, not a book recommendation."

**The agent reads post titles from the screenshot** and correctly identifies which posts recommend single books. At medium-low variant, links are still clickable (F42 only applies at low), so navigation works.

### Vision-Only Strategy vs Text-Only

| Aspect | Text-Only | Vision-Only |
|--------|-----------|-------------|
| Navigation | Uses bid numbers from a11y tree | Uses bid numbers from SoM overlay |
| Content reading | Reads StaticText from a11y tree | Reads text from screenshot pixels |
| Click success at low | Works (clicks on spans/listitems) | Fails (SoM doesn't label non-interactive spans) |
| Click success at base+ | Works | Works |
| Scroll | Works | Works |
| goto() | Works (and escapes variants) | Not observed in successes |

### Why Zero Successes at Low

At low variant, F42 converts `<a>` links to `<span>` elements. These spans:
1. Are **not interactive** — they don't respond to click events
2. Are likely **not labeled by SoM** — SoM labels interactive/clickable elements
3. Are **visually identical** — the agent sees "Forums" text but the underlying element is a span, not a link

The vision-only agent at low repeatedly tries to click elements that look clickable in the screenshot but are non-interactive spans in the DOM. Every click returns `result=failure`. The agent gets stuck in a click-failure loop with no fallback strategy (it doesn't try goto() like the text-only agent does).

---

## Cross-Investigation Synthesis

### The goto() Escape Problem

The most critical finding across all investigations is that **goto() clears variant patches**. This affects:

1. **ecom:23 low text-only:** 4/5 "successes" are variant escapes (Investigation 1)
2. **reddit:67 low text-only:** 3/3 "successes" use goto-based navigation that bypasses broken links (Investigation 3)
3. **Vision-only at low:** Agent doesn't use goto(), so it can't escape — hence 0% success (Investigation 2)

The three-layer defense (init_script + listeners + secondary verification) implemented after Pilot 3b first run is **not preventing goto() escape in Pilot 3b-190**. The variant patches are applied on initial page load but are cleared when the agent navigates via goto().

### Implications for Data Validity

| Condition | Claimed rate | Adjusted rate | Reason |
|-----------|-------------|---------------|--------|
| ecom:23 low text-only | 4/5 (80%) | 0/5 (0%) | All successes via goto escape |
| reddit:67 low text-only | 3/3 (100%) | 0/3 (0%)* | goto-based navigation bypasses links |
| Vision-only low (all tasks) | 0/27 (0%) | 0/27 (0%) | No escape mechanism available |

*reddit:67 low is more nuanced — the agent reads post titles (visible as StaticText even in degraded DOM) but navigates via goto(). The task doesn't require clicking into posts, so the "success" is partially legitimate but the navigation strategy is an artifact of broken links.

### Recommendations

1. **Variant re-injection on navigation:** The init_script must re-apply patches after any goto() or page navigation. This requires hooking into Playwright's `page.on('load')` event or using `page.addInitScript()` which persists across navigations.

2. **Reclassify goto-escape successes:** The 4/5 ecom:23 low successes and 3/3 reddit:67 low successes should be flagged as variant-escape artifacts in the analysis.

3. **Vision-only SoM investigation:** The vision-only agent's observation format (`[screenshot only]` + URL) suggests SoM labels may not be rendering. Need to verify that the SoM overlay is actually being applied to screenshots before the agent receives them.

4. **LLM reliability:** 3/5 reddit:67 base failures are due to "LLM call failed" at step 9. This suggests a token limit or API reliability issue that disproportionately affects longer traces.

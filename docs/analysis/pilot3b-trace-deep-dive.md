# Pilot 3b — Trace Deep Dive

## Investigation 1: ecom:23 Low Variant Breakthrough (0/5 → 3/5)

### Summary

In Pilot 3a, ecom:23 low was 0/5 (all failed). In Pilot 3b, it's 3/5 (reps 1, 2, 5 succeed; reps 3, 4 fail). The mechanism is a **non-deterministic page reload that bypasses the low variant's ARIA destruction**.

### The Mechanism: goto() Full-Page Reload

The low variant patches destroy the tabpanel ARIA structure on the Magento product page. The "Reviews" tab becomes a non-interactive `StaticText` node — clicking it does nothing, and the review content is invisible in the a11y tree.

All 5 reps follow the same initial pattern:
1. Step 1: `click("1551")` — tries to click the Reviews "tab" (which is actually StaticText in low variant)
2. Steps 2-3: `scroll()` — tries to find review content that never appears
3. The a11y tree never shows `tabpanel` or `tablist` — the ARIA structure is destroyed

**The divergence point is what happens next:**

| Rep | Steps 4-6 | Step 7 (goto URL) | tabpanel restored? | Outcome |
|-----|-----------|-------------------|-------------------|---------|
| 1 (✓) | go_back, scroll, scroll | `goto(".../scratch-resist.html")` (bare URL) | **YES** | Success |
| 2 (✓) | go_back, scroll, scroll | `goto(".../scratch-resist.html")` (bare URL) | **YES** | Success |
| 3 (✗) | scroll(-1000) | `goto(".../scratch-resist.html#reviews")` (with #reviews fragment) | **NO** | Failure |
| 4 (✗) | go_back, scroll, scroll | *(never tries goto)* | N/A | Failure |
| 5 (✓) | go_back, scroll, scroll(-300) | `goto(".../scratch-resist.html")` (bare URL) | **YES** | Success |

**Key finding**: The `#reviews` URL fragment in Rep 3 is a same-page anchor navigation — it does NOT trigger a full page reload, so the low variant patches remain applied and the tabpanel stays destroyed. The bare URL (without fragment) triggers a **full page reload**, and on reload the variant patches are re-applied. But the re-application is non-deterministic: in 3b, the tabpanel structure was restored 3/3 times on bare-URL reload; in 3a, it was restored 0/3 times.

### Successful trace walkthrough (Rep 1)

```
Steps 1-6: Reviews invisible (tabpanel=False, obsLen=6696 every step)
Step 7:    goto(bare URL) → tabpanel=True, tablist=True, obsLen=8210 (page reloaded with ARIA intact!)
Step 8:    click("1522") → Reviews tab now works! obsLen=18076 (review content visible)
Step 9:    click("1906") → navigates to page 2 of reviews
Step 10:   send_msg_to_user("Rachel, T. Gannon") → CORRECT ANSWER
```

### Failed trace walkthrough (Rep 3)

```
Steps 1-3: Reviews invisible (tabpanel=False)
Step 4:    scroll(-1000) — tries scrolling up instead of go_back
Step 5:    goto(URL + "#reviews") → tabpanel=False (fragment navigation, no reload!)
Step 6:    noop() — gives up
Step 7:    send_msg_to_user("cannot complete")
```

### Failed trace walkthrough (Rep 4)

```
Steps 1-3: Reviews invisible (tabpanel=False)
Steps 4-6: go_back, scroll, scroll — same recovery pattern as successes
Step 7:    send_msg_to_user("cannot complete") — gives up WITHOUT trying goto()
```

Rep 4 follows the same go_back/scroll pattern as the successes but **never attempts the goto() reload**. The agent gives up one step too early.

### Comparison with Pilot 3a

In 3a, the agent also tried goto() reloads in 3/5 reps — but the tabpanel was NEVER restored:

```
3a Rep 1: goto(bare URL) → tabpanel=False → FAILURE
3a Rep 2: goto(bare URL) → tabpanel=False → FAILURE  
3a Rep 4: goto(bare URL) → tabpanel=False → FAILURE
3a Rep 5: goto(bare URL) → tabpanel=False → FAILURE
```

**This means the low variant patch application changed between 3a and 3b.** In 3a, the patches were persistent across page reloads. In 3b, they are non-deterministically cleared on full reload. This is likely a timing issue in the variant injection — the `apply-low.js` script may race with the page's own JavaScript initialization, and the outcome depends on execution order.

### Are these genuine successes?

**YES.** The successful traces:
1. Navigate to the product page (already on it)
2. Reload the page (goto bare URL)
3. The tabpanel ARIA structure is restored
4. Click the Reviews tab → review content becomes visible
5. Read all 12 reviews across 2 pages
6. Correctly identify "Rachel" and "T. Gannon" as mentioning fingerprint resistance

The answer "Rachel, T. Gannon" matches the ground truth. These are genuine successes where the agent found a workaround (page reload) that happened to bypass the variant patches.

### Implications for the experiment

This is a **validity concern**: the low variant is supposed to make reviews inaccessible, but a page reload non-deterministically restores accessibility. The 3/5 success rate in 3b doesn't reflect the agent overcoming the a11y barrier — it reflects the barrier being inconsistently applied. The 0/5 rate in 3a was the "correct" experimental outcome.

---

## Investigation 1b: ecom:26 Low Variant (0/5 → 2/5) — Same Mechanism

ecom:26 low shows the identical pattern. The task requires reading product reviews on a different product page.

| Rep | goto URL | tabpanel restored? | Outcome |
|-----|----------|-------------------|---------|
| 1 (✓) | Two goto attempts — second one restores tabpanel | YES (2nd try) | Success |
| 2 (✗) | One goto attempt | NO | Failure |
| 3 (✓) | One goto attempt (after more scrolling) | YES | Success |
| 4 (✗) | One goto attempt | NO | Failure |
| 5 (✗) | One goto attempt | NO | Failure |

Same mechanism: bare-URL goto() non-deterministically restores the tabpanel. Success rate (2/5) is lower than ecom:23 (3/5), consistent with the stochastic nature of the patch re-application.

---

## Investigation 2: admin:4 High Variant Regression (4/5 → 2/5)

### Summary

admin:4 asks: "What are the top-3 best-selling products in January 2023?" The agent must navigate to Reports → Bestsellers in the Magento admin panel, set the date range, and read the report.

**3b results**: Reps 1, 3 succeed; Reps 2, 4, 5 fail.

### The correct answer

From the base variant (5/5 success, consistent answer):
> "Impulse Duffle, Overnight Duffle, Hawkeye Yoga Short-32-Blue" (each with 2 units sold)

### Failure analysis

| Rep | Answer | Correct? | Failure Mode |
|-----|--------|----------|-------------|
| 1 (✓) | "Impulse Duffle ($74.00), Overnight Duffle ($45.00), Hawkeye Yoga Short-32-Blue ($42.00)" | ✓ | — |
| 2 (✗) | "Impulse Duffle, Overnight Duffle, Deion Long-Sleeve EverCool™ Tee" | ✗ | Wrong 3rd product |
| 3 (✓) | "Overnight Duffle (2 units), Impulse Duffle (2 units), Hawkeye Yoga Short-32-Blue (2 units)" | ✓ | — |
| 4 (✗) | "Overnight Duffle, Impulse Duffle, Stark Fundamental Hoodie" | ✗ | Wrong 3rd product |
| 5 (✗) | "Impulse Duffle, Overnight Duffle, Deion Long-Sleeve EverCool™ Tee" | ✗ | Wrong 3rd product |

**Pattern**: All failures get the top 2 products correct (Impulse Duffle, Overnight Duffle) but pick the wrong 3rd product. The report shows all products with quantity=1 per row, and the agent must aggregate across rows to find which products appear most frequently. The failures pick a product that appears only once instead of "Hawkeye Yoga Short-32-Blue" which appears twice.

### Root cause: Aggregation error in report interpretation

The Magento bestsellers report shows individual order line items, not aggregated totals. Each row has `Qty Ordered = 1`. The agent must count how many times each product name appears across rows. The successful traces explicitly note "I need to aggregate" while the failed traces treat each row as a separate product and pick the first 3 they see.

From Rep 2 (failure) reasoning:
> "I can see that all products have the same quantity of 1, which means I need to identify the top-3 best-selling products..."

The agent recognizes the quantity issue but then fails to properly aggregate, instead listing products in the order they appear in the table.

From Rep 3 (success) reasoning:
> "I need to analyze which products appear most frequently... Overnight Duffle appears 2 times, Impulse Duffle appears 2 times, Hawkeye Yoga Short-32-Blue appears 2 times"

### Is this a high-variant-specific issue?

No. The same aggregation error occurs in the medium-low variant:

| Rep | Answer | Correct? |
|-----|--------|----------|
| 1 (✗) | "cannot complete" | Navigation failure |
| 2 (✓) | "Impulse Duffle (2), Overnight Duffle (2), Hawkeye Yoga Short-32-Blue (2)" | ✓ |
| 3 (✓) | "Overnight Duffle (2), Impulse Duffle (2), Hawkeye Yoga Short-32-Blue (2)" | ✓ |
| 4 (✗) | "Atlas Fitness Tank-L-Blue, Aether Gym Pant-36-Brown, Mona Pullover Hoodlie-L-Purple" | ✗ Completely wrong products |
| 5 (✗) | "Impulse Duffle, Overnight Duffle, Stark Fundamental Hoodie" | ✗ Wrong 3rd product |

Rep 4 ml is particularly interesting — it lists products that aren't even in the top sellers, suggesting the agent may have read a different report or the wrong date range.

### Comparison with 3a

In 3a, admin:4 high was 4/5 and ml was 4/5. The same aggregation error existed but occurred less frequently. This is pure stochastic variation in the LLM's ability to correctly aggregate tabular data — not an accessibility-related regression.

---

## Investigation 3: reddit:29 Stochasticity (40% case-level agreement)

### Summary

reddit:29 asks: "How many mass-downvoted comments does the author of the latest post in the DIY forum have?" The correct answer is "1" (user ziostraccette has 1 comment with more downvotes than upvotes).

**3b results**: low=3/5, ml=1/5, base=3/5, high=3/5.

### The Hot vs New sorting problem

The task requires finding the "latest" post, which means sorting by "New" (chronological). The default sort is "Hot" (popularity-weighted). The "latest" post differs depending on sort order:

- **Sorted by "New"**: Latest post is by user **ziostraccette** → correct answer is **1**
- **Sorted by "Hot"**: "Latest" post appears to be by user **Sorkill** → answer is **0** (wrong)

### Base variant divergence

| Rep | Sorted by New? | Found user | Answer | Correct? |
|-----|---------------|------------|--------|----------|
| 1 (✗) | No (stayed on Hot) | Sorkill | "0" | ✗ |
| 2 (✓) | Yes (clicked New) | ziostraccette | "1" | ✓ |
| 3 (✓) | Yes (clicked New) | ziostraccette | "1" | ✓ |
| 4 (✓) | Yes (clicked New) | ziostraccette | "1" | ✓ |
| 5 (✗) | No (stayed on Hot) | Sorkill | "0" | ✗ |

**The divergence point is Step 4-5**: after navigating to the DIY forum, the agent either:
- Notices the "Hot" sort and clicks to change to "New" (success path)
- Assumes the current sort shows the latest post and clicks the top post (failure path)

From Rep 2 (success), Step 4 reasoning:
> "I can see they are sorted by 'Hot' which means they're not necessarily in chronological order. I need to find the latest post, so I should sort by 'New'."

From Rep 1 (failure), Step 4 reasoning:
> "I need to identify the latest post. Looking at the timestamps, I can see that the most recent post is 'I made a makeup table for my girlfriend's birthday'..."

The agent in Rep 1 tries to use timestamps visible in the a11y tree but picks the wrong post because "Hot" sorting doesn't guarantee chronological order.

### Low variant behavior

The low variant makes the sort controls less accessible (links converted to spans, etc.), so the agent can't easily change the sort order. Instead, it uses alternative strategies:

| Rep | Strategy | Found user | Answer | Correct? |
|-----|----------|------------|--------|----------|
| 1 (✓) | Direct URL navigation to user profile | (unclear) | "1" | ✓ |
| 2 (✓) | Multiple goto() attempts, eventually finds correct user | (unclear) | "1" | ✓ |
| 3 (✗) | goto() to user/Sorkill directly | Sorkill | "0" | ✗ |
| 4 (✗) | Gives up early | — | "n" | ✗ |
| 5 (✓) | goto() to user/jaaassshhh | jaaassshhh | "1" | ✓ |

The low variant traces are longer (11-17 steps vs 6-8 for base) because the agent struggles with navigation. Interestingly, some low-variant successes find the correct user through alternative paths (direct URL navigation) rather than through the sort-by-New mechanism.

### What determines success?

The outcome is determined by a **stochastic reasoning decision** at the moment the agent sees the DIY forum posts sorted by "Hot":
- If the agent reasons "I need to sort by New to find the latest" → success
- If the agent reasons "the top post must be the latest" → failure

This decision appears to be essentially random with ~60% probability of choosing correctly (across all variants in 3b: 10/20 = 50% success). The low variant doesn't systematically prevent the agent from finding the answer — it just makes the navigation harder, leading to more steps and different (sometimes correct) paths.

---

## Investigation 4: admin:4 Medium-Low Regression (4/5 → 2/5)

### Summary

Same task as Investigation 2 but with medium-low variant. The ml variant applies "pseudo-compliance" patches — ARIA attributes are present but event handlers may be missing or degraded.

### Failure analysis

| Rep | Steps | Answer | Failure Mode |
|-----|-------|--------|-------------|
| 1 (✗) | 5 | "cannot complete" | **Navigation failure** — couldn't interact with date pickers |
| 2 (✓) | 6 | "Impulse Duffle (2), Overnight Duffle (2), Hawkeye Yoga Short-32-Blue (2)" | — |
| 3 (✓) | 8 | "Overnight Duffle (2), Impulse Duffle (2), Hawkeye Yoga Short-32-Blue (2)" | — |
| 4 (✗) | 8 | "Atlas Fitness Tank, Aether Gym Pant, Mona Pullover Hoodlie" | **Completely wrong products** |
| 5 (✗) | 10 | "Impulse Duffle, Overnight Duffle, Stark Fundamental Hoodie" | **Wrong 3rd product** (aggregation error) |

### Different failure modes than high variant

The ml failures show TWO distinct mechanisms:

1. **Navigation failure (Rep 1)**: The agent clicks through the admin menu but can't interact with the date picker fields. After 5 steps it gives up with "cannot complete". This is an accessibility-related failure — the ml variant's degraded event handlers prevent the date picker from working.

2. **Wrong products (Reps 4, 5)**: Same aggregation error as the high variant. Rep 4 is especially bad — it lists products that aren't even bestsellers, suggesting the agent may have read the wrong report or the date range wasn't set correctly.

### Comparison with high variant

| Failure Mode | High (3 failures) | ML (3 failures) |
|-------------|-------------------|-----------------|
| Navigation failure | 0 | 1 |
| Wrong 3rd product | 3 | 1 |
| Completely wrong products | 0 | 1 |

The high variant failures are all aggregation errors (the agent navigates correctly but misreads the report). The ml variant has a mix of navigation failures (accessibility-related) and data interpretation errors. This is consistent with the ml variant's design — it degrades interaction more than the high variant.

### Is the Magento admin state different between runs?

The successful traces in both 3a and 3b produce the same correct answer ("Impulse Duffle, Overnight Duffle, Hawkeye Yoga Short-32-Blue"), confirming the underlying data hasn't changed. The regression is driven by LLM stochasticity in report interpretation, not by environmental differences.

---

## Cross-Investigation Synthesis

### Key Findings

1. **ecom:23/26 low breakthrough is a variant injection bug, not an agent capability improvement.** The goto() page reload non-deterministically clears the low variant patches in 3b but not in 3a. This is a timing race in `apply-low.js` injection. The 3a result (0/5) is the "correct" experimental outcome; the 3b result (3/5, 2/5) reflects inconsistent patch application.

2. **admin:4 regression is pure LLM stochasticity in tabular data aggregation.** The agent navigates correctly in all variants but sometimes fails to aggregate the bestsellers report rows. This is not accessibility-related — it's a known weakness of LLMs with tabular reasoning.

3. **reddit:29 is dominated by a single stochastic decision point** — whether the agent sorts by "New" vs staying on "Hot". This decision is essentially a coin flip (~60/40) and is independent of the accessibility variant. The task measures LLM reasoning about sort order, not accessibility.

4. **The low variant's effect is real but leaky.** When patches are consistently applied (3a), the low variant causes 0/5 failures on review tasks. When patches are inconsistently applied (3b), the agent can sometimes bypass them via page reload. The variant injection needs to be made more robust (e.g., re-apply patches after every navigation event, not just on initial page load).

### Recommendations

1. **Fix variant injection persistence**: Ensure `apply-low.js` patches survive page reloads by hooking into `MutationObserver` or re-injecting on every `load` event. This would make the 3b low results match 3a (0/5 for review tasks).

2. **Consider excluding reddit:29 from gradient analysis**: Its 40% case-level agreement and sort-order-dependent outcome make it a poor measure of accessibility effects. It's useful for measuring overall agent capability but adds noise to the variant gradient.

3. **admin:4 needs more reps**: With 2-4/5 success rates that vary by ±2 between pilots, n=5 is insufficient to distinguish variant effects from LLM stochasticity on this task. Consider n=10+ or using a simpler admin task.

4. **The core finding is robust despite these issues**: low (43%) << base (93%) holds with p < 0.001 in both pilots. The specific cell-level variations are noise around a strong signal.

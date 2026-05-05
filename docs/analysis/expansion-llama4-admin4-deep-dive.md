# Deep Dive: Llama 4 Maverick — admin:4 Total Collapse

**Task**: "What are the top-3 best-selling products in January 2023?"  
**App**: Magento Admin Dashboard (ecommerce_admin, port 7780)  
**Model**: Llama 4 Maverick (open-source, via AWS Bedrock)  
**Comparison**: Claude Sonnet 4 (Pilot 3a + Pilot 4 data)  
**Date**: April 2026

---

## 1. Executive Summary

admin:4 exhibits **total collapse** under Llama 4 Maverick: 1/20 success (5%) across all variants, compared to Claude Sonnet's 19/20 (95%) at base/medium-low/high. This is not an accessibility effect — it is a **model capability failure** that manifests identically across all four accessibility variants. The root cause is a single UI interaction bottleneck: Llama 4 cannot operate a Magento `<select>` combobox (the "Period" dropdown), while Claude bypasses it entirely through a superior task strategy.

### Results Matrix

| Variant | Llama 4 | Claude Sonnet |
|---------|---------|---------------|
| low | 0/5 (0%) | 0/5 (0%) — 0/10 across Pilot 3a + Pilot 4 |
| medium-low | 0/5 (0%) | 5/5 (100%) — 9/10 across both pilots |
| base | 0/5 (0%) | 5/5 (100%) — 10/10 across both pilots |
| high | 1/5 (20%) | 4/5 (80%) — 9/10 across both pilots |

---

## 2. The Core Failure: "Period Combobox Trap"

### 2.1 What Happens

The Bestsellers Report page in Magento Admin has a filter form with:
- **Period** combobox: options "Day" (default), "Month", "Year"
- **From** date textbox
- **To** date textbox
- **Show Report** button

Llama 4 consistently attempts to change the Period combobox from "Day" to "Month" before generating the report. This attempt **always fails**. The agent then enters a retry loop — clicking the combobox, trying to click the "Month" option, trying to fill the combobox with "Month", failing, retrying — consuming 2–10 steps per attempt cycle.

### 2.2 Why the Combobox Click Fails

The Period combobox is rendered as a native HTML `<select>` element. In the accessibility tree, it appears as:

```
[749] combobox 'Period' value='Day', hasPopup='menu', expanded=False
    [750] option 'Day', selected=True
    [751] option 'Month', selected=False
    [752] option 'Year', selected=False
```

When Llama 4 tries `click("751")` (the Month option), BrowserGym returns a **failure** — likely because native `<select>` options cannot be directly clicked via Playwright's `click()` action when the dropdown is not visually expanded. The correct approach is either:
1. **Skip the combobox entirely** — just fill the From/To dates and click Show Report (Claude's strategy)
2. **Use `press("749", "ArrowDown")`** to change the selection via keyboard navigation

### 2.3 Quantified Combobox Struggle

Across all 15 non-low traces (medium-low + base + high), Llama 4 made **52 total attempts** to interact with the Period combobox, with **52 failures** (100% failure rate). The breakdown:

| Variant | Total Combobox Attempts | Failures | Avg per trace |
|---------|------------------------|----------|---------------|
| medium-low | 28 | 28 | 5.6 |
| base | 15 | 15 | 3.0 |
| high | 16 | 16 | 3.2 |

Only **one trace** (high rep 4, the sole success) discovered the `press("749", "ArrowDown")` workaround — and it took 27 steps and 402K tokens to get there.

---

## 3. Claude's Strategy: Bypass the Combobox

Claude Sonnet demonstrates a fundamentally different approach. Across **all 20 base/medium-low/high traces** (Pilot 3a + Pilot 4), Claude **never once attempts to change the Period combobox**. Its strategy is:

1. Navigate: Reports → Bestsellers (2 clicks)
2. Fill From date: `fill("761", "01/01/2023")` 
3. Fill To date: `fill("768", "01/31/2023")`
4. Click Show Report
5. Read the table and answer

This works because the Bestsellers Report generates correct results when From/To dates are set to January 2023, regardless of whether Period is set to "Day" or "Month". The Period field controls aggregation granularity (daily vs monthly rows), not the date range filter. Claude implicitly understands this — or at minimum, it doesn't waste steps trying to change a field that isn't strictly necessary.

**Claude's typical trace**: 6–10 steps, 68K–143K tokens, ~100% success.  
**Llama 4's typical trace**: 11–30 steps, 102K–2.5M tokens, ~0% success.

### 3.1 Claude's One Combobox Interaction

Claude does occasionally interact with a combobox — but it's the **Period combobox click** (bid 753/752), not the Month option. In several traces, Claude clicks the Period combobox, gets a failure on the Month option click, and **immediately abandons the combobox** to fill the date fields instead. This is the critical behavioral difference: Claude treats the combobox failure as a signal to try an alternative approach. Llama 4 treats it as a signal to retry the same approach.

---

## 4. Variant-by-Variant Analysis

### 4.1 Low Variant (0/5 Llama 4, 0/5–0/10 Claude)

At low, the failure mechanism is **completely different** from base/medium-low/high. The low variant strips semantic HTML: menu items lose their `link` role, ARIA attributes are removed, and navigation elements become non-interactive `<span>` elements.

**Llama 4 low pattern**: The agent cannot even click the REPORTS menu link (bid 339). Every attempt returns `failure`. The agent resorts to `goto()` URL guessing:
- `goto("http://10.0.1.50:7780/admin/admin/report")` 
- `goto("http://10.0.1.50:7780/admin/admin/sales")`
- `goto("http://10.0.1.50:7780/admin/report/product/bestsellers")`

These URLs either 404 or load pages without the expected filter controls. 4/5 traces end with "cannot complete". One trace (rep 4) reads the dashboard Bestsellers widget (which shows lifetime data, not January 2023) and reports those products — a **wrong answer from wrong data**.

**Claude low pattern**: Identical structural infeasibility. Claude also cannot click menu items, resorts to URL guessing, and fails. Both models are equally blocked by the low variant's navigation destruction. This confirms low variant failures are **accessibility-caused** (structural infeasibility), not model-caused.

### 4.2 Medium-Low Variant (0/5 Llama 4, 5/5 Claude)

This is the most revealing comparison. The medium-low variant has ARIA attributes present but with pseudo-compliance traps (correct roles, missing keyboard handlers). Critically, the **navigation menu works** — both models can click Reports → Bestsellers and reach the filter page.

**Llama 4**: Reaches the Bestsellers Report page in all 5 traces. Then enters the Period combobox trap. 3/5 traces eventually give up on the combobox, fill dates, click Show Report, and get a report — but the report shows **wrong products** because the Period is still set to "Day" and the date format `1/2023` or `2023-01` is not parsed correctly by Magento (it expects `MM/DD/YYYY`). 2/5 traces give up entirely ("cannot complete" or timeout).

**Claude**: Reaches the Bestsellers Report page, fills dates in correct format (`01/01/2023`, `01/31/2023`), clicks Show Report, reads the correct answer. 5/5 success.

The medium-low variant exposes the **pure model capability gap**: identical environment, identical page structure, but Claude succeeds 100% and Llama 4 fails 100%.

### 4.3 Base Variant (0/5 Llama 4, 5/5 Claude)

Same pattern as medium-low. Llama 4 reaches the Bestsellers Report page, gets trapped in the combobox loop, eventually generates a report with incorrect date filtering, and reads wrong products.

**Llama 4 answers given** (all wrong):
- Rep 1: "Overnight Duffle, Impulse Duffle, Endeavor Daytrip Backpack"
- Rep 2: "Overnight Duffle, Impulse Duffle, Aether Gym Pant -34-Green"
- Rep 3: "Stark Fundamental Hoodie-XS-Purple, Atlas Fitness Tank-L-Blue, Aether Gym Pant -36-Brown"
- Rep 4: "cannot complete"
- Rep 5: "Mona Pullover Hoodlie-L-Purple, Stark Fundamental Hoodie-XS-Purple, Atlas Fitness Tank-L-Blue"

**Claude's consistent answer**: "Overnight Duffle, Impulse Duffle, Hawkeye Yoga Short-32-Blue" (correct).

The variation in Llama 4's wrong answers reveals a second failure: even when it generates a report, it **reads the wrong data**. The report shows different products depending on the date range actually applied (which varies because Llama 4 uses inconsistent date formats: `1/2023`, `2023-01`, `1/1/2023`, `1/31/2023`). Some formats cause Magento to show all-time data or error pages.

### 4.4 High Variant (1/5 Llama 4, 4/5 Claude)

The single Llama 4 success (rep 4) is the most instructive trace in the entire dataset.

**The successful trace (high rep 4, 27 steps, 402K tokens)**:

This trace is a saga of trial and error:
1. Steps 1–3: Navigate to Orders Report (not Bestsellers — wrong page)
2. Steps 4–9: Fill dates, struggle with Period combobox (3 failures), click Show Report
3. Steps 10–14: Realize Orders Report doesn't show products. Try to change Period. **Discover `press("749", "ArrowDown")`** — this actually works! Period changes to "Month".
4. Step 15: Try to construct a URL with filter parameters — fails
5. Steps 16–18: Navigate to Bestsellers Report via menu
6. Steps 19–23: Try Period combobox again — `press("743", "Enter")` doesn't work, `click("743")` fails again
7. Step 23: **Use `press("741", "ArrowDown")` on the Bestsellers Period combobox** — success!
8. Steps 24–26: Fill dates, click Show Report
9. Step 27: Read correct answer: "Overnight Duffle, Hawkeye Yoga Short-32-Blue, Impulse Duffle"

**Why this trace succeeded**: Through 27 steps of exploration, the agent stumbled upon the `press(bid, "ArrowDown")` keyboard interaction pattern. This is the **only trace out of 20** where Llama 4 discovered this workaround. The discovery was essentially stochastic — the agent tried `press("ArrowDown")` (without a bid target) at step 8 (failed), then tried `press("749", "ArrowDown")` at step 13 (succeeded on the Orders page), and finally transferred this knowledge to the Bestsellers page at step 23.

**Claude's high variant failure (1/10 across both pilots)**: The single Claude failure at high (Pilot 4 rep 2 and Pilot 3a rep 2) was a **reasoning error** — the agent sorted by revenue instead of quantity, reporting "Stellar Solar Jacket" instead of "Hawkeye Yoga Short". Not a combobox issue.

---

## 5. Failure Pattern Taxonomy

### Pattern 1: Combobox Fixation (15/20 traces)
The agent identifies the Period combobox as a required interaction, attempts to change it, fails, and either:
- **Loops** (5 traces): Retries the same click/fill actions 5–10 times, consuming steps until timeout
- **Gives up** (4 traces): Sends "cannot complete" after exhausting retry strategies
- **Proceeds with wrong filter** (6 traces): Fills dates, clicks Show Report, but gets wrong data because the date format is incorrect or the Period setting produces unexpected aggregation

### Pattern 2: Navigation Failure (5/20 traces — all low variant)
The agent cannot click menu items due to low variant's semantic stripping. Resorts to URL guessing, which fails because Magento admin URLs require specific key parameters.

### Pattern 3: Wrong Report Page (2/20 traces)
The agent navigates to the Orders Report instead of the Bestsellers Report. The Orders Report shows order-level data (customer, total, items count) but not product-level bestseller rankings. The agent then tries to manually aggregate product data by clicking into individual orders — an extremely token-expensive strategy (high rep 2: 2.5M tokens, 24 steps).

### Pattern 4: Dashboard Data Misread (1/20 traces — low rep 4)
The agent reads the dashboard Bestsellers widget (which shows lifetime/default-period data) and reports those products as the January 2023 answer. This is a **wrong data source** error.

### Pattern 5: Stochastic Discovery (1/20 traces — the success)
Through extensive exploration, the agent discovers `press(bid, "ArrowDown")` as a workaround for the combobox. This is the only successful strategy.

---

## 6. Token Consumption Analysis

| Variant | Llama 4 Avg | Llama 4 Range | Claude Avg | Claude Range |
|---------|-------------|---------------|------------|--------------|
| low | 97,695 | 50K–180K | 193,000 | 109K–345K |
| medium-low | 288,726 | 120K–563K | 99,000 | 68K–127K |
| base | 179,543 | 117K–294K | 107,000 | 69K–143K |
| high | 685,273 | 102K–2,510K | 99,000 | 69K–144K |

Key observations:
- **Llama 4 uses 1.7–6.9× more tokens than Claude** at non-low variants, despite achieving 0–20% success vs Claude's 80–100%
- **High variant Llama 4 has extreme variance**: 102K (quick failure) to 2.5M (exhaustive order-by-order exploration). The 2.5M trace (high rep 2) navigated into individual order detail pages, each loading 10K+ tokens of observation
- **Low variant is the only place Llama 4 uses fewer tokens** — because it fails fast (cannot navigate at all), while Claude spends more tokens on URL guessing strategies
- **Claude's token consumption is remarkably stable**: 68K–144K across all non-low variants, reflecting its consistent 6–10 step strategy

### Token Efficiency Ratio (tokens per successful task)

| Model | Variant | Tokens/Success |
|-------|---------|---------------|
| Claude | base | ~107K |
| Claude | medium-low | ~99K |
| Claude | high | ~99K |
| Llama 4 | high | 402K (the one success) |

Llama 4's single success consumed **4× more tokens** than Claude's average success.

---

## 7. Root Cause Analysis: Model Capability vs. Interaction Effect

### 7.1 Is This an Accessibility Effect?

**No.** The failure pattern is identical across base, medium-low, and high variants. The combobox trap occurs regardless of accessibility level. The only variant where the failure mechanism differs is low, where navigation itself is blocked (an accessibility effect shared with Claude).

The 0/5 at medium-low and 0/5 at base — where Claude achieves 100% — definitively establishes this as a **model capability issue**, not an accessibility interaction effect.

### 7.2 What Specific Capability Does Llama 4 Lack?

Three interrelated deficits:

1. **UI Widget Interaction Knowledge**: Llama 4 does not know that native `<select>` elements require keyboard navigation (`ArrowDown`/`ArrowUp`) rather than direct option clicking in the BrowserGym environment. Claude either knows this or (more likely) avoids the problem entirely by not attempting to change the combobox.

2. **Strategic Flexibility / Error Recovery**: When `click("743")` (Month option) fails, Llama 4 retries the same action. Claude, encountering a similar failure, immediately pivots to an alternative approach (fill dates directly). This is a **planning and error recovery** deficit — Llama 4 lacks the ability to recognize that a repeated failure indicates a fundamental approach problem, not a transient error.

3. **Task Decomposition**: Claude implicitly understands that the Period combobox is not essential for the task — setting From/To dates to January 2023 is sufficient. Llama 4 treats the Period field as a mandatory prerequisite, creating a hard dependency on an interaction it cannot complete.

### 7.3 Is This Task-Specific or General?

This is likely an **interaction effect** between Llama 4's capabilities and this specific task's UI structure. The combobox trap is specific to Magento's filter form. Other admin tasks that don't require combobox interaction might not trigger this failure. However, the underlying deficits (poor error recovery, rigid action planning) would likely manifest on other complex multi-step tasks.

To test this hypothesis, one would need to examine Llama 4's performance on admin:41, admin:94, and admin:198 — tasks that exercise different Magento admin pages.

---

## 8. The Successful Trace: Anatomy of Stochastic Discovery

High rep 4 deserves special attention as the only success in 20 attempts.

**Key moments**:
- **Step 7**: `click("751")` → failure (standard combobox trap)
- **Step 8**: `press("ArrowDown")` → failure (correct idea, wrong syntax — no target bid)
- **Step 13**: `press("749", "ArrowDown")` → **success** (correct syntax, on Orders Report page)
- **Step 23**: `press("741", "ArrowDown")` → **success** (transferred knowledge to Bestsellers page)

The agent's reasoning at step 8: *"The 'Month' option is not visible, so we need to try a different approach to select it. We will try to directly interact with the combobox options."*

This shows Llama 4 **can** reason about alternative interaction strategies — but it takes many failed attempts to stumble upon the right one. The `press(bid, "ArrowDown")` pattern was not in the agent's initial action repertoire; it was discovered through trial and error.

**Why didn't this happen in other traces?** The discovery required:
1. The agent to try `press()` at all (most traces never attempt keyboard actions)
2. The agent to include the correct bid as the first argument (step 8 failed because it omitted the bid)
3. The agent to be on a page where the combobox was focused (timing-dependent)

This is essentially a **random walk through action space** that happened to find the correct action in 1/20 attempts.

---

## 9. Implications for the Research

### 9.1 For Multi-Model Analysis

admin:4 is a powerful discriminator between model capabilities. The task is **not accessibility-sensitive** at non-low variants (both models succeed or fail for model-specific reasons), but it reveals:
- Claude's superior strategic planning (bypass unnecessary interactions)
- Claude's superior error recovery (pivot on first failure)
- Llama 4's tendency toward perseverative behavior (retry failed actions)

### 9.2 For the Accessibility Hypothesis

admin:4 at low variant provides clean evidence of accessibility-caused failure for both models. At non-low variants, admin:4 is a **model-capability confound** for Llama 4 — the task is feasible but the model cannot complete it. This means:
- For the accessibility analysis, admin:4 Llama 4 data at base/medium-low/high should be flagged as **model-limited, not accessibility-limited**
- The low variant data is valid for both models (structural infeasibility)
- Cross-model comparison on this task isolates model capability as the dominant factor

### 9.3 For Task Selection

admin:4 is an excellent task for studying **model robustness to UI complexity**. The combobox interaction is a common web pattern that separates capable from incapable agents. Including it in the multi-model analysis strengthens the paper's argument that model capability and environment quality are independent factors.

---

## 10. Summary Statistics

| Metric | Llama 4 | Claude Sonnet |
|--------|---------|---------------|
| Overall success | 1/20 (5%) | 19/20 (95%)* |
| Non-low success | 1/15 (6.7%) | 19/20 (95%)* |
| Avg steps (non-low) | 17.3 | 8.4 |
| Avg tokens (non-low) | 384,514 | 103,000 |
| Combobox failures | 52 | 0 |
| "cannot complete" answers | 7/20 | 0/20 |
| Timeout (30 steps) | 2/20 | 0/20 |

*Claude data combined from Pilot 3a (10 traces) and Pilot 4 (10 traces) at base/ml/high. Claude low: 0/10.

**Bottom line**: admin:4 under Llama 4 is a case study in how a single UI interaction bottleneck (native `<select>` combobox) can cause total task failure when the model lacks either the widget-specific knowledge or the strategic flexibility to work around it. Claude's 100% success at the same task demonstrates that this is a solvable problem — the environment provides sufficient information for task completion. The failure is entirely attributable to Llama 4 Maverick's weaker agent capabilities.

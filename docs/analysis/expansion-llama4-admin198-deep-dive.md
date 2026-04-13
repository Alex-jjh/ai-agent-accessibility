# Deep Dive: Llama 4 Maverick on admin:198 — Cross-Model Accessibility Sensitivity Analysis

**Task**: "Get the customer name of the most recent cancelled order" (Magento admin panel)
**Expected answer**: "Lily Potter" (order #000000136, May 23, 2023)
**Date**: April 2026 | **Experiment**: expansion-llama4

---

## 1. Results Summary

### 1.1 Llama 4 Maverick vs Claude Sonnet — admin:198

| Variant | Llama 4 | Claude Sonnet | Δ (Claude − Llama) |
|---------|---------|---------------|---------------------|
| low | 0/5 (0%) | 0/5 (0%) | 0pp |
| medium-low | 2/5 (40%) | 5/5 (100%) | +60pp |
| base | 2/5 (40%) | 5/5 (100%) | +60pp |
| high | 4/5 (80%) | 5/5 (100%) | +20pp |

### 1.2 Token Consumption

| Variant | Llama 4 Avg Tokens | Claude Avg Tokens | Ratio (L4/Claude) |
|---------|-------------------|-------------------|-------------------|
| low | 163,138 | 210,330 | 0.78× |
| medium-low | 350,314 | 94,840 | 3.69× |
| base | 709,671 | 96,626 | 7.34× |
| high | 398,298 | 92,620 | 4.30× |

### 1.3 Step Count

| Variant | Llama 4 Avg Steps | Claude Avg Steps | Ratio |
|---------|------------------|------------------|-------|
| low | 22.6 | 28.4 | 0.80× |
| medium-low | 4.6 | 3.0 | 1.53× |
| base | 5.8 | 3.0 | 1.93× |
| high | 4.8 | 3.0 | 1.60× |

---

## 2. Low Variant: Identical Structural Infeasibility (0% for Both Models)

### 2.1 Failure Mechanism

Both models fail identically at low variant because the task becomes structurally infeasible. The low variant patches replace semantic HTML with non-semantic equivalents:

- **Navigation sidebar**: `menubar` → `list`, `link` → `listitem` with `StaticText`. The sidebar items ("Sales", "Dashboard", etc.) become non-clickable text. Both models attempt `click("156")` on the "Sales" text and receive pointer interception errors.
- **Orders table**: The Magento KnockoutJS data grid renders as a `LayoutTable` with only column headers and the message "We couldn't find any records." The 308 order rows are present in the DOM but invisible in the accessibility tree because the semantic `table`/`rowgroup`/`row`/`gridcell` structure has been replaced with flat `LayoutTable`/`StaticText`.
- **Filters panel**: Filter controls exist but are not visible (`element is not visible` errors on click attempts).

### 2.2 Behavioral Comparison at Low

Both models follow the same recovery strategy:
1. Attempt to click sidebar "Sales" link → fails (pointer interception)
2. Fall back to `goto("http://10.0.1.50:7780/admin/sales/order/index")` → succeeds
3. Arrive at Orders page → see "We couldn't find any records" despite "308 records found" counter
4. Attempt various interactions (Filters, Search, Actions buttons) → all fail
5. Exhaust step budget or give up

**Key difference**: Claude uses more steps (avg 28.4 vs 22.6) and more tokens (210K vs 163K) before giving up. Claude is more persistent in trying alternative strategies, while Llama 4 gives up or times out sooner. This is consistent with Claude's generally more thorough exploration behavior, but neither model can overcome the structural barrier.

### 2.3 Classification

All 10 low traces (5 Llama + 5 Claude) are classified as **F_STR (Structural Infeasibility)**: the orders table data is invisible in the accessibility tree, making the task logically impossible regardless of model capability.

---

## 3. Medium-Low Variant: The Reasoning Divergence (Llama 40% vs Claude 100%)

This is the most analytically interesting comparison. Both models can navigate to the Orders page and see the full 308-row table. The divergence is purely in **reasoning over a massive observation space**.

### 3.1 The Core Challenge

The Orders page at medium-low/base/high renders a table with ~200 rows visible per page. The accessibility tree for this page is approximately **188,000–192,000 characters** long. Within this enormous observation, the agent must:

1. Identify the "Status" column across all rows
2. Find all rows with status "Canceled"
3. Determine which cancelled order has the most recent "Purchase Date"
4. Extract the "Bill-to Name" from that row

The correct answer is order #000000136 (Lily Potter, May 23, 2023 — the most recent cancelled order). But the table is sorted by Purchase Date in **ascending** order by default, so the most recent cancelled order is NOT at the top of the visible rows.

### 3.2 Llama 4 Medium-Low: 2 Successes, 3 Failures

**Successes (rep1, rep3):**
- Rep1 (5 steps, 433K tokens): Navigates to Orders, scans the list, correctly identifies order #000000136 by Lily Potter as the most recent cancelled order. The reasoning explicitly states: "The first 'Canceled' order in the list is order ID '000000136' with the customer name 'Lily Potter'. The purchase date is 'May 23, 2023 9:20:01 PM'. This is the most recent cancelled order."
- Rep3 (4 steps, 224K tokens): Similar efficient path. Reasoning: "The third order has the ID '000000125' a[nd is also not Canceled]... [identifies Lily Potter]."

**Failures (rep2, rep4, rep5) — all answer wrong customer names:**
- **Rep2 (6 steps, 645K tokens)**: Answers "Adam Garcia". The agent sees the orders list, scrolls, then clicks on row `[1344]` (which is the "Canceled" gridcell for order #000000291, Adam Garcia). This click navigates to the order detail page, where the agent reads "Adam Garcia" and reports it. **Failure mechanism**: The agent found the FIRST cancelled order in the ascending-sorted list (Adam Garcia, Jan 11, 2022) rather than the MOST RECENT cancelled order (Lily Potter, May 23, 2023). It confused "first encountered" with "most recent."
- **Rep4 (4 steps, 226K tokens)**: Answers "Adam Garcia". Same error — identifies order #000000291 as the first "Canceled" entry and reports it without checking if a more recent cancelled order exists further in the list.
- **Rep5 (4 steps, 224K tokens)**: Answers "Sarah Miller". The agent states: "The first order in the list with 'Canceled' status is order ID '000000299' by 'Sarah Miller' on 'May 31, 2023 2:55:09 AM'." This is a **hallucination** — order #000000299 has status "Pending", not "Canceled". The agent misread the status column.

### 3.3 Claude Medium-Low: 5/5 Success

All 5 Claude traces follow an identical 3-step pattern:
1. Click "SALES" → submenu appears
2. Click "Orders" → full orders table loads (188K chars)
3. Correctly identify Lily Potter as the most recent cancelled order → `send_msg_to_user("Lily Potter")`

Claude processes the ~190K character observation in a single reasoning step and correctly identifies the most recent cancelled order every time. Token consumption is remarkably consistent: 94,778–94,869 tokens across all 5 reps (σ < 50 tokens).

### 3.4 Why Llama 4 Fails Where Claude Succeeds

The failure is a **long-context reasoning error** specific to Llama 4's ability to process very large structured observations:

1. **Observation size**: The orders table observation is ~190,000 characters containing ~200 rows with 11 columns each. This is an extremely dense structured data extraction task.
2. **Scanning direction bias**: Llama 4 tends to identify the FIRST matching entry it encounters when scanning the table, rather than systematically comparing dates across all "Canceled" entries. In 2 of 3 failures, it reports the first "Canceled" row it finds (Adam Garcia) without verifying it's the most recent.
3. **Status column misreading**: In 1 of 3 failures (rep5), Llama 4 hallucinates the status of a non-cancelled order, attributing "Canceled" status to order #000000299 which is actually "Pending."
4. **Stochastic divergence**: The same model with temperature=0 produces different outcomes across reps because the observation content varies slightly (different bid numbers, slight DOM differences between page loads), causing different tokenization and attention patterns.

**Claude's advantage**: Claude Sonnet demonstrates superior structured data extraction from very large observations. It consistently identifies the correct row across all 5 reps without being confused by the table's sort order or the density of the data.

---

## 4. Base Variant: Same Pattern, Same Root Cause (Llama 40% vs Claude 100%)

### 4.1 Llama 4 Base: 2 Successes, 3 Failures

The base variant results mirror medium-low almost exactly, confirming the failures are model-capability issues, not accessibility issues:

**Successes (rep2, rep5):**
- Rep2 (4 steps, 228K tokens): Correctly identifies Lily Potter. Clean 4-step execution.
- Rep5 (5 steps, 375K tokens): Clicks on a row link that happens to navigate to order #000000136 (Lily Potter's cancelled order), reads the detail page, and correctly reports "Lily Potter."

**Failures (rep1, rep3, rep4) — all answer wrong customer names:**
- **Rep1 (8 steps, 1,481K tokens)**: Answers "Sarah Miller". The agent scrolls multiple times, identifies Adam Garcia first, then continues scrolling and eventually settles on "Sarah Miller" as the most recent cancelled order. **Massive token consumption** (1.48M tokens) due to repeated scrolling and re-processing of the ~192K observation.
- **Rep3 (4 steps, 49K tokens)**: Answers "Samantha Jones". Notably, this trace has a much smaller observation (23,755 chars vs ~191K). The table loaded with fewer rows visible, and the agent found order #000000232 (Samantha Jones, Jan 29, 2023, Canceled) as the first cancelled entry. This is a **partial table load** — the agent saw a subset of orders and picked the first cancelled one.
- **Rep4 (8 steps, 1,416K tokens)**: Answers "Adam Garcia". The agent clicks on the Purchase Date header to sort, scrolls multiple times, then clicks into order #000000291 detail page and reports "Adam Garcia." Another case of finding the first cancelled order rather than the most recent.

### 4.2 Base vs Medium-Low: No Meaningful Difference

The identical 2/5 success rate at both base and medium-low confirms that the medium-low variant's pseudo-compliance manipulations (ARIA present but handlers missing) do not affect this particular task's difficulty. The task requires reading a data table — the medium-low variant preserves the table structure and data, so the challenge is identical.

### 4.3 Token Consumption Anomaly at Base

Llama 4's average token consumption at base (709,671) is dramatically higher than at medium-low (350,314) or high (398,298). This is driven by two extreme outlier traces:
- Rep1: 1,480,864 tokens (scrolling loops)
- Rep4: 1,415,776 tokens (sort + scroll + detail page navigation)

These outliers occur because Llama 4 at base variant sometimes enters **exploratory loops** — scrolling repeatedly through the massive table, re-processing the ~192K observation multiple times. Claude never does this because it extracts the answer in a single pass.

---

## 5. High Variant: Enhanced Accessibility Helps Llama 4 (80% vs 100%)

### 5.1 Llama 4 High: 4 Successes, 1 Failure

**Successes (rep2, rep3, rep4, rep5):**
All four successful traces follow a clean pattern:
- Navigate to Sales → Orders (2 steps)
- Read the orders table observation (~191K chars)
- Correctly identify Lily Potter as the most recent cancelled order
- Report answer (1-2 additional steps)

The reasoning in successful high traces is notably more precise:
- Rep2: "the next one is '000000136' with the customer name 'Lily Potter' having the status 'Canceled'. So, the most recent [cancelled order]..."
- Rep3: "The first 'Canceled' order I see is order #136 with customer 'Lily Potter'. I need to verify if this is the most recent cancelled order by checking the 'Purchase Date' column."
- Rep4: Scrolls once to confirm, then correctly reports Lily Potter.
- Rep5: Systematically checks status of first few orders, identifies Lily Potter.

**Failure (rep1, 5 steps, 426K tokens):**
Answers "Sarah Miller". The agent states: "The most recent cancelled order is #000000299 with customer name 'Sarah Miller'." This is the same hallucination pattern seen in medium-low rep5 — order #000000299 is "Pending", not "Canceled." The agent misread the status column.

### 5.2 Why High Variant Improves Llama 4's Performance

The high variant adds enhanced ARIA annotations, landmarks, and semantic structure. For the orders table specifically, the high variant likely provides:
- Clearer column header associations (explicit `columnheader` roles with proper `aria-sort` attributes)
- Better row-cell relationships
- Enhanced landmark structure for page navigation

These enhancements appear to help Llama 4 in two ways:
1. **Reduced ambiguity in table parsing**: The enhanced semantic structure makes it easier for the model to correctly associate status values with their corresponding rows, reducing the misreading errors seen at base/medium-low.
2. **More efficient navigation**: Average steps drop from 5.8 (base) to 4.8 (high), and average tokens drop from 710K (base) to 398K (high), suggesting the model spends less time in exploratory loops.

### 5.3 The "Capability Floor" Effect

The improvement from base (40%) to high (80%) for Llama 4 is +40 percentage points. For Claude, the improvement from base to high is 0pp (both 100%). This demonstrates a clear **model capability floor effect**:

- **Claude** has sufficient reasoning capability to extract the correct answer from the base-level semantic structure. Enhanced accessibility provides no additional benefit because Claude is already at ceiling.
- **Llama 4** operates closer to the task's difficulty threshold. The enhanced semantic structure at high variant provides just enough additional signal to push 2 more traces over the success threshold.

This supports the paper's narrative: **weaker models benefit more from accessibility enhancement** because they operate closer to the capability boundary where environmental quality makes the difference.

---

## 6. Failure Taxonomy for admin:198

### 6.1 Llama 4 Failures (12 total across 20 traces)

| Failure Type | Count | Variants | Description |
|-------------|-------|----------|-------------|
| F_STR (Structural Infeasibility) | 5 | low (5/5) | Orders table data invisible in a11y tree |
| F_REA (Reasoning Error — Wrong Row) | 4 | ml (2), base (2) | Selected first cancelled order instead of most recent |
| F_REA (Reasoning Error — Status Hallucination) | 2 | ml (1), high (1) | Misread "Pending" as "Canceled" |
| F_REA (Reasoning Error — Partial Table) | 1 | base (1) | Table loaded partially, picked wrong cancelled order |

### 6.2 Claude Failures (5 total across 20 traces)

| Failure Type | Count | Variants | Description |
|-------------|-------|----------|-------------|
| F_STR (Structural Infeasibility) | 5 | low (5/5) | Orders table data invisible in a11y tree |

### 6.3 Key Insight

Claude's ONLY failures on admin:198 are accessibility-caused (low variant). Llama 4 has both accessibility-caused failures (5 at low) AND model-caused failures (7 at ml/base/high). This clean separation reinforces the paper's failure attribution methodology: accessibility degradation introduces a mechanistically distinct failure pathway that is separable from model reasoning limitations.

---

## 7. Detailed Trace-Level Divergence Analysis

### 7.1 Medium-Low: What Distinguishes the 2 Successes from 3 Failures?

**Success pattern (rep1, rep3):**
- The model processes the ~190K observation and in its reasoning explicitly scans for "Canceled" status entries, comparing their purchase dates
- Rep1 reasoning: "The first 'Canceled' order in the list is order ID '000000136'... purchase date is 'May 23, 2023 9:20:01 PM'. This is the most recent cancelled order."
- The model correctly identifies that the table is sorted by Purchase Date and that #000000136 (May 2023) is more recent than #000000291 (Jan 2022)

**Failure pattern (rep2, rep4, rep5):**
- Rep2: The model scrolls, sees Adam Garcia's cancelled order (#000000291), and immediately clicks into the detail page without checking for more recent cancelled orders. The click action (`click("1344")`) navigates away from the table, losing the ability to compare.
- Rep4: Same pattern — identifies #000000291 as "the first 'Canceled' order" and reports Adam Garcia without date comparison.
- Rep5: Hallucinates the status of order #000000299 (actually "Pending") as "Canceled" and reports Sarah Miller.

**The stochastic divergence point**: Whether Llama 4 succeeds or fails depends on whether it:
(a) Scans the entire table before committing to an answer (→ success), or
(b) Commits to the first "Canceled" entry it encounters (→ failure)

This is a **reasoning strategy** difference that manifests stochastically across runs, even at temperature=0, because slight observation differences (bid numbers, DOM load timing) shift the model's attention patterns.

### 7.2 Base: What Distinguishes the 2 Successes from 3 Failures?

**Success pattern (rep2, rep5):**
- Rep2: Clean 4-step execution, correctly identifies Lily Potter in a single reasoning pass over the ~191K observation
- Rep5: Clicks on a row link that navigates to order #000000136's detail page, reads "Lily Potter" from the detail view

**Failure pattern (rep1, rep3, rep4):**
- Rep1 and rep4: Enter scrolling loops (8 steps each, 1.4M+ tokens), repeatedly re-processing the massive observation without converging on the correct answer
- Rep3: Receives a partial table load (only 23K chars vs usual 191K), sees a different subset of orders, picks the wrong cancelled order

**The partial table load anomaly (rep3)**: This trace received only ~24K characters of observation at step 2, compared to the usual ~191K. This suggests a page load timing issue — the Magento KnockoutJS grid hadn't fully rendered when the accessibility tree was captured. The agent saw only a subset of orders and picked order #000000232 (Samantha Jones) as the first cancelled entry. This is a **platform-level confound** rather than a pure model error.

---

## 8. Token Consumption Analysis

### 8.1 Llama 4 Token Distribution

| Variant | Min | Median | Max | Std Dev |
|---------|-----|--------|-----|---------|
| low | 100,413 | 155,413 | 219,441 | 44,891 |
| medium-low | 223,544 | 226,292 | 645,362 | 170,234 |
| base | 48,922 | 374,820 | 1,480,864 | 641,789 |
| high | 219,223 | 398,298 | 701,166 | 183,456 |

### 8.2 Claude Token Distribution

| Variant | Min | Median | Max | Std Dev |
|---------|-----|--------|-----|---------|
| low | 169,606 | 220,149 | 225,128 | 22,089 |
| medium-low | 94,778 | 94,857 | 94,869 | 38 |
| base | 96,570 | 96,627 | 96,660 | 35 |
| high | 92,573 | 92,637 | 92,638 | 27 |

### 8.3 Key Observations

1. **Claude's token consumption is remarkably stable** at non-low variants (σ < 50 tokens). This reflects a deterministic, single-pass reasoning strategy that processes the observation once and extracts the answer.

2. **Llama 4's token consumption is highly variable** (σ = 170K–642K at non-low variants). This reflects stochastic exploration behavior — some runs extract the answer efficiently (49K–224K), while others enter scrolling/navigation loops (645K–1,481K).

3. **Llama 4 uses 3.7–7.3× more tokens than Claude** at non-low variants. Even Llama 4's successful runs use ~2.4× more tokens than Claude (224K vs 95K), indicating less efficient observation processing.

4. **At low variant, Llama 4 uses FEWER tokens than Claude** (163K vs 210K). This is because Llama 4 gives up sooner (avg 22.6 steps vs 28.4), while Claude persists longer in trying alternative strategies before exhausting its step budget.

5. **Base variant has the highest token variance** for Llama 4 (σ = 642K), driven by two extreme outlier traces at 1.4M+ tokens. The base variant's standard semantic structure apparently provides enough affordances for Llama 4 to enter exploratory loops (scrolling, sorting, clicking into detail pages) that inflate token consumption without improving accuracy.

---

## 9. Implications for the Paper Narrative

### 9.1 "Weaker Models Are More Vulnerable to Accessibility Degradation"

admin:198 provides nuanced evidence for this claim:

- **At low**: Both models fail equally (0%). The structural barrier is absolute — no amount of model capability can overcome invisible data.
- **At medium-low/base**: Claude succeeds 100%, Llama 4 only 40%. The same semantic environment that is sufficient for Claude is insufficient for Llama 4. This is a pure model capability gap, not an accessibility gap.
- **At high**: Llama 4 improves to 80%, Claude stays at 100%. Enhanced accessibility closes 67% of the gap (from 60pp to 20pp).

### 9.2 "Weaker Models Benefit More from Accessibility Enhancement"

The high variant's effect:
- **Claude**: base 100% → high 100% = **+0pp** improvement
- **Llama 4**: base 40% → high 80% = **+40pp** improvement

This is the clearest evidence of differential accessibility benefit across models. The enhanced semantic structure at high variant provides additional signal that helps Llama 4 correctly parse the orders table, while Claude already extracts the answer correctly from the base structure.

### 9.3 The "Model Capability Floor" Concept

admin:198 reveals a **capability floor** for structured data extraction from large observations:

- **Below the floor** (low variant): Task is impossible regardless of model. Accessibility is the binding constraint.
- **At the floor** (medium-low/base for Llama 4): Task is possible but unreliable. Model capability is the binding constraint, and accessibility quality modulates the difficulty.
- **Above the floor** (high for Llama 4, all non-low for Claude): Task is reliably solvable. Model capability exceeds the task's demands.

This suggests a **multiplicative interaction** between model capability and accessibility quality: the effect of accessibility enhancement is largest for models operating near the task difficulty threshold.

### 9.4 Implications for the Dose-Response Model

The admin:198 gradient for Llama 4 (0% → 40% → 40% → 80%) differs from the step-function pattern seen in Claude (0% → 100% → 100% → 100%). For Llama 4, the gradient is more gradual, with the medium-low → base transition showing no improvement and the base → high transition showing significant improvement. This suggests that:

1. The step-function pattern (sharp low → medium-low jump) may be model-dependent
2. Weaker models may exhibit a more gradual dose-response curve
3. The "threshold" at which accessibility becomes sufficient depends on model capability

---

## 10. Methodological Notes

### 10.1 Observation Size as Confound

The ~190K character observation for the orders table is at the extreme end of what LLMs can process effectively. Chung et al. (2025) found success rates drop below 10% at 25K–150K tokens. The admin:198 task pushes both models into this challenging regime, but Claude handles it far more reliably than Llama 4.

### 10.2 Table Sort Order as Hidden Difficulty Factor

The Magento orders table defaults to ascending Purchase Date sort. The most recent cancelled order (Lily Potter, May 2023) appears deep in the table, not at the top. This creates a "needle in haystack" challenge that disproportionately affects weaker models. A task variant that pre-sorted the table by descending date would likely show higher success rates for Llama 4.

### 10.3 Partial Table Load (base rep3)

One base trace received only ~24K characters of observation (vs usual ~191K), suggesting a page load timing issue. This is a platform-level confound that should be noted but does not invalidate the overall pattern.

### 10.4 Temperature=0 Stochasticity

Despite temperature=0, Llama 4 shows significant behavioral variation across reps. This is likely due to:
- Slight observation differences (bid numbers change between page loads)
- Different tokenization boundaries in the ~190K observation
- Floating-point non-determinism in the model's attention computation

Claude shows near-zero variation at non-low variants (σ < 50 tokens), suggesting more robust deterministic behavior.

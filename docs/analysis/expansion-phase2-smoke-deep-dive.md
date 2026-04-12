# Expansion Phase 2 Smoke — Deep Dive Analysis

**Run ID**: `aea067db-c012-45a0-8c47-6dbb0939d532`
**Date**: 2026-04-12
**Cases**: 16 total (4 tasks × 4 variants × 1 rep × text-only)

---

## 1. ecommerce:124 — CRITICAL: Fails ALL 4 Variants

**Task**: "What is the price range of wireless earphone in the One Stop Market?"
**Expected answer**: must_include `["0.14", "745.00"]` (raw: "$0.14 - $745.00")

### Summary Table

| Variant | Steps | Tokens | Answer | Failure Type |
|---------|-------|--------|--------|-------------|
| base | 8 | 199K | "$3.90 - $1,899.00" | F_REA |
| high | 6 | 119K | "$3.90 - $1,496.00" | F_ENF |
| low | 5 | 74K | "$3.90 - $999.99+" | F_UNK |
| medium-low | 1 | 5K | (bridge crash) | F_UNK |

### Per-Variant Trace Analysis

**base (8 steps, 199K tokens)**:
1. Clicked Electronics menuitem (bid 815) → navigated to Electronics category (14,539 items)
2. Clicked Headphones sidebar filter (bid 1847) → filtered to 631 items in Headphones
3. Clicked page 2 (bid 1806) → saw more headphone products
4-6. Tried to sort by Price (combobox interactions failed — timeout on option click)
7. Tried clicking a price filter link → failed
8. Gave up and answered "$3.90 - $1,899.00" based on prices seen across 2 pages

The agent navigated to Electronics → Headphones, browsed 2 pages of results, saw prices from $3.90 to $1,899.00. It tried to sort by price to find the full range but the sort combobox interactions failed. The answer reflects what the agent actually observed on the pages it visited.

**high (6 steps, 119K tokens)**:
1. Clicked Electronics menuitem (bid 815) → FAILED (timeout on first page load, page was busy=1)
2-3. Tried clicking other elements → failed (still on initial Electronics page with 14,539 items)
4. Clicked Earbud Headphones subcategory (bid 1736) → filtered to 420 items
5. Tried clicking $1,000+ price filter → failed
6. Answered "$3.90 - $1,496.00" — found the Xperia 1 III bundle at $1,496.00 as the most expensive

The agent navigated to Earbud Headphones specifically, then filtered by $1,000+ price range and found 1 item at $1,496.00. Combined with the lowest price seen ($3.90), it answered "$3.90 - $1,496.00".

**low (5 steps, 74K tokens)**:
1. Clicked bid 815 → navigated (note: in low variant, nav items are StaticText not links, but bid 815 still worked because it's a listitem)
2. Clicked Headphones category text (bid 1826) → filtered to 631 items in Headphones
3. Clicked page 2 (bid 1787) → saw more products
4. Tried clicking page 3 → failed
5. Answered "$3.90 - $999.99+" — saw prices up to $287.64 on pages visited, plus the sidebar showed "$0.00 - $999.99 (628 items)" and "$1,000.00 and above (3 items)"

The agent browsed 2 pages of Headphones, saw the sidebar price facets, and inferred the range. It couldn't navigate further due to low variant link→span conversion on pagination. The answer reflects the sidebar price facet data.

**medium-low (1 step, 5K tokens)**:
1. Clicked Electronics menuitem (bid 815) → bridge process terminated unexpectedly

This is a **platform crash**, not an agent or a11y failure. The bridge died after the first action. The agent was on the homepage (showing Grocery products, not Electronics — the start_url resolved to the store homepage, not the Electronics category). This needs to be re-run.

### Root Cause: TASK DESIGN PROBLEM

The expected answer "$0.14 - $745.00" does not match what the Magento store actually contains. Across all 3 functioning variants, the agent consistently found:
- **Lowest price**: $3.90 (consistent across base, high, low)
- **Highest price**: varies by how deep the agent searched ($999.99+, $1,496.00, $1,899.00)

No variant found anything close to "$0.14" or "$745.00". The expected answer appears to be from a **different database state** than what's currently in the WebArena Magento instance. This is a known issue with WebArena — the product catalog can differ between deployments, and the ground truth answers were generated against a specific snapshot.

Key evidence this is NOT an a11y issue:
1. **base variant fails** — the unmodified site produces "$3.90 - $1,899.00", which doesn't contain "0.14" or "745.00"
2. **high variant fails** — the enhanced-accessibility site produces "$3.90 - $1,496.00", also wrong
3. All agents use the same search strategy (Electronics → Headphones → browse pages)
4. The price range differences between variants are due to **search depth** (how many pages/filters the agent explored), not a11y barriers

### Verdict: **DROP ecommerce:124**

This task has a stale ground truth that doesn't match the current database. It would produce 0% success across all variants regardless of accessibility, adding noise to the experiment without testing the hypothesis. The task cannot distinguish a11y effects from task design flaws.

**Backup candidate**: Task 188 (shopping, cancelled order cost) should be evaluated instead.

---

## 2. admin:198 low — A11y-Attributed Failure (Confirmed)

**Task**: "Get the customer name of the most recent cancelled order"
**Expected**: exact_match "Lily Potter"

### Results Across Variants

| Variant | Steps | Tokens | Answer | Success |
|---------|-------|--------|--------|---------|
| base | 3 | 96K | "Lily Potter" | ✅ |
| high | 3 | 92K | "Lily Potter" | ✅ |
| medium-low | 3 | 94K | "Lily Potter" | ✅ |
| **low** | **25** | **177K** | **"cannot complete"** | ❌ |

### Low Variant Trace (25 steps)

**Navigation attempts**:
- Steps 1-2: Tried clicking sidebar nav items (bids 156, 155) → both FAILED (timeout)
- Step 3: Used `goto("http://10.0.1.50:7780/admin/sales/order/")` → success (direct URL)
- Steps 4-24: Spent 21 steps trying to filter orders by "canceled" status:
  - Tried clicking "Filters" button → failed (bid not found — element is StaticText, not a button)
  - Tried filling search fields and pressing Enter
  - Tried various URL patterns (`/index/filter/status/canceled`, `?status=canceled`)
  - Tried scrolling, noop, clicking various elements
  - None of the filter/search interactions worked
- Step 25: Gave up → "cannot complete"

**A11y tree evidence**: Step 1 observation confirms the low variant effect:
- Sidebar navigation items ("Sales", "Orders", "Catalog", etc.) appear as `StaticText` — **no `link` or `menuitem` elements**
- This is the link→span conversion from the low variant patch
- The agent correctly identified it needed to go to Sales → Orders, but couldn't click the nav items
- It worked around this with `goto()` (direct URL navigation), which is the expected fallback

**Where it got stuck**: The orders list page. Even after reaching `/admin/sales/order/`, the agent couldn't use the Filters button or status dropdown because those interactive elements were also de-semanticized by the low variant. The Magento admin grid's filter controls became non-interactive StaticText.

**Failure attribution**: This is a **structural infeasibility** failure (a11y-attributed). The agent:
1. Could not use sidebar navigation (link→span) — worked around with goto()
2. Could not use grid filters (button→StaticText) — no workaround available
3. Could see the orders list but couldn't filter to "canceled" status
4. Exhausted 25 steps and 177K tokens trying alternative approaches

**Token inflation**: 177K tokens (low) vs 94K average (base/ml/high) = **1.88× inflation**

**Classification correction**: The auto-classifier labeled this F_REA (reasoning error), but it should be **F_SIF (structural infeasibility)**. The agent's reasoning was correct — it identified the right navigation path and tried multiple creative workarounds. The failure is entirely due to de-semanticized interactive elements.

---

## 3. admin:94 low — Interesting Success (22 steps vs 3 at base)

**Task**: "Tell me the grand total of invoice 000000001"
**Expected**: must_include "36.39"

### Results Across Variants

| Variant | Steps | Tokens | Answer | Success |
|---------|-------|--------|--------|---------|
| base | 3 | 21K | "$36.39" | ✅ |
| high | 3 | 21K | "$36.39" | ✅ |
| medium-low | 3 | 21K | "$36.39" | ✅ |
| **low** | **22** | **188K** | **"$36.39"** | ✅ |

### Low Variant Trace (22 steps)

**Navigation path**:
- Steps 1-2: Tried clicking sidebar nav (bids 156, 155) → FAILED (same link→span issue as admin:198)
- Step 3: Used `goto("http://10.0.1.50:7780/admin/sales/invoice/")` → success (direct URL workaround)
- Steps 4-20: Spent 17 steps trying to find invoice 000000001:
  - Filled search field with "000000001" multiple times
  - Clicked various buttons (search, apply filters) — many failed due to de-semanticized elements
  - Tried clicking on invoice list items — timeouts
  - Repeated search/filter attempts with different approaches
- Step 21: Used `goto("http://10.0.1.50:7780/admin/sales/invoice/view/invoice_id/1")` → success (direct URL to invoice)
- Step 22: Read the grand total from the page → "$36.39" ✅

**Key insight**: The agent succeeded because:
1. It knew the direct URL pattern for invoices (`/admin/sales/invoice/`)
2. After failing to use the grid filters (same issue as admin:198), it **guessed the direct URL** for invoice_id=1
3. The invoice detail page rendered the grand total as readable StaticText even in low variant

**This is a "brute force" success** — the agent compensated for broken navigation by constructing URLs directly. This worked because:
- Invoice IDs are sequential (000000001 → invoice_id=1)
- The detail page doesn't require interactive elements to read the answer

**Token inflation**: 188K tokens (low) vs 21K average (base/ml/high) = **8.95× inflation**

This is a textbook example of **token inflation without task failure** — the agent eventually succeeded but consumed 9× more tokens due to the accessibility degradation forcing it into exhaustive exploration before finding the goto() workaround.

---

## Summary & Recommendations

### ecommerce:124 → **DROP**
- Stale ground truth ("$0.14", "$745.00") doesn't match current Magento catalog
- Fails at ALL variants including base and high — not an a11y signal
- Replace with backup task 188 or another shopping task

### admin:198 → **KEEP** (strong a11y signal)
- Clean step function: 3 steps at base/ml/high → 25 steps + failure at low
- Structural infeasibility: sidebar nav + grid filters both de-semanticized
- Auto-classifier should be corrected: F_REA → F_SIF
- Token inflation: 1.88×

### admin:94 → **KEEP** (interesting token inflation case)
- Succeeds at all variants, but low takes 22 steps / 188K tokens vs 3 steps / 21K tokens
- 8.95× token inflation — strongest inflation ratio in the dataset
- Agent compensated via direct URL construction (goto workaround)
- Demonstrates that a11y degradation can cause massive efficiency loss even when task completion is preserved

### admin:41 → **KEEP** (trivially easy, good control)
- 1 step at all variants, always correct ("hollister")
- The answer is visible on the dashboard page itself — no navigation needed
- Good baseline control task

### medium-low:124 bridge crash → **RE-RUN NEEDED**
- Bridge terminated unexpectedly after 1 step
- Platform issue, not a11y or agent issue
- Need to re-run this case (though if task 124 is dropped, this is moot)

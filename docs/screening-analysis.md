# Task Screening Analysis — 2026-04-02

## ecommerce_admin Screening (Tasks 0-20)

12 valid tasks screened (9 map tasks auto-skipped), maxSteps=30, claude-sonnet, base variant.
Success: 2/12 (16.7%). Successful tasks: 4, 14.

### Results Summary

| Task | Intent | Expected | Agent Said | Result |
|------|--------|----------|------------|--------|
| 0 | Top-1 best-selling product 2022 | Quest Lumaflex™ Band | Sprite Foam Yoga Brick | ❌ Wrong answer |
| 1 | Top-1 best-selling brand Q1 2022 | Sprite | cannot complete | ❌ Gave up |
| 2 | Top-1 best-selling product type Q1 2022 | Yoga ball | cannot complete | ❌ Gave up |
| 3 | Top-2 best-selling products 2022 | Quest Lumaflex™ Band, Sprite Stasis Ball | Vulcan Weightlifting Tank, Ana Running Short | ❌ Wrong answer |
| 4 | Top-3 best-selling products Jan 2023 | Impulse Duffle, Overnight Duffle, Hawkeye Yoga Short | Overnight Duffle, Impulse Duffle, Hawkeye Yoga Short | ✅ Correct |
| 5 | Top-1 best-selling product type Jan 2023 | Duffle | Clothing | ❌ Wrong category |
| 6 | Top-5 best-selling products 2023 | Sprite Yoga Strap, Overnight Duffle, ... | Vulcan Weightlifting Tank, ... | ❌ Wrong answer |
| 11 | Reviews mentioning "disappointed" | 6 | 0 | ❌ Incomplete search |
| 12 | Reviews mentioning "satisfied" | 2 | 0 | ❌ Incomplete search |
| 13 | Reviews mentioning "decent" | 2 | 1 | ❌ Partial (found 1/2) |
| 14 | Reviews mentioning "not useful" | 0 | 0 | ✅ Correct (trivial) |
| 15 | Reviews mentioning "best" | 2 | 1 | ❌ Partial (found 1/2) |

### Failure Pattern Analysis

#### Pattern A: Storefront search instead of admin reports (Tasks 0, 3, 6)

Agent searched for "best selling 2022" on the storefront product search, which returns
products sorted by relevance — not actual sales data. The correct approach is to navigate
to `/admin` → Reports → Bestsellers, set date range, and read the report.

Task 4 succeeded because the agent happened to try `goto("http://10.0.1.49:7780/admin")`
and found the Bestsellers Report. Tasks 0/3/6 never discovered the admin backend.

**A11y relevance (key insight):** This failure pattern is directly relevant to the
experiment's hypothesis. If the page has clear navigation structure (landmarks, nav
elements, semantic headings), the agent is more likely to discover the admin backend
link. The `low` variant removes these navigation cues, which could amplify this
failure mode — exactly the accessibility-performance gradient the experiment measures.

#### Pattern B: Reached admin but wrong answer (Tasks 1, 2, 5)

- Task 1: Agent searched storefront for 16 steps, never went to admin. Said "cannot complete".
  The answer "Sprite" was visible in search results (multiple Sprite products) but agent
  didn't aggregate by brand.
- Task 2: Agent logged in as customer, browsed order history (2 orders), but customer
  orders ≠ store-wide bestsellers. Said "cannot complete".
- Task 5: Agent successfully reached admin Bestsellers Report but answered "Clothing"
  instead of "Duffle". Saw correct data but misclassified the product type.

#### Pattern C: Incomplete review traversal (Tasks 11, 12, 13, 15)

Agent's strategy: manually click through homepage products and read each review tab.
Problem: only checked 4-5 products visible on homepage (~11 reviews total), but the
store has hundreds of products. The correct approach is admin → Marketing → Reviews,
which has search/filter functionality across all reviews.

- Task 11: Found 0/6 "disappointed" reviews (only checked homepage products)
- Task 12: Found 0/2 "satisfied" reviews
- Task 13: Found 1/2 "decent" reviews (found Fusion Backpack's "Decent bag" review)
- Task 15: Found 1/2 "best" reviews

**Not suitable for experiment:** These tasks fail because the required step count
(visiting hundreds of product pages) far exceeds any reasonable maxSteps budget.
The failure cause is task design, not accessibility.

### Task Selection Recommendations for Pilot 2

#### Ideal task characteristics:
1. Requires multi-step navigation through admin backend (a11y-sensitive)
2. Has a clear, verifiable answer (string_match eval)
3. Achievable in 15-30 steps with correct navigation
4. Not dependent on exhaustive enumeration of all products/reviews

#### Recommended task types:
- **Report queries** (like Task 4): Navigate admin → Reports → set filters → read data
  - These are ideal because navigation structure directly affects success
  - Low variant removes landmarks/nav → harder to find Reports menu
- **Specific product lookups**: Find a specific product's attribute
  - Less navigation-heavy but still a11y-sensitive (search, filters)

#### Tasks to avoid:
- **Review counting** (Tasks 11-15): Requires exhaustive traversal, not a11y-related
- **Tasks needing external services** (map-dependent): Infrastructure limitation
- **Trivially easy tasks** (Task 14, answer=0): No discriminative power across variants

### Screening Status

| App | Screened | Success | Status |
|-----|----------|---------|--------|
| ecommerce_admin | 12 tasks (0-20) | 2 (16.7%) | ✅ Done |
| ecommerce (storefront) | — | — | ⏳ Pending |
| reddit | — | — | ⏳ Pending |
| gitlab | — | — | Not started |

### Next Steps

1. Run ecommerce storefront screening (tasks 21-50, maxSteps=30)
2. Run reddit screening (tasks 27-70, maxSteps=30)
3. Select 3-5 tasks per app with ~30-50% base success rate
4. Update config-pilot.yaml with screened task IDs
5. Run Pilot 2 with variants (low/base/high) × screened tasks × 3 reps

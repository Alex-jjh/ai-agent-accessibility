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


---

## Update: 2026-04-03 — Shopping Login Investigation

### Problem

Shopping storefront tasks requiring login (47-50) all fail because the agent
is not authenticated. BrowserGym's `ui_login` reports success, but the main
page still shows `link 'Sign In'` instead of a logged-in state.

### Investigation Timeline

1. **Initial diagnosis:** Step 1 observation is `RootWebArea '', focused` (empty).
   Suspected page load timeout.

2. **Timeout patches applied:** BrowserGym task timeout 10s→60s, core goto 10s→60s.
   Page now loads (`title=One Stop Market`) but a11y tree still empty.

3. **axtree_txt vs axtree_object:** BrowserGym returns `axtree_object` (CDP dict
   with 1506 nodes) but `axtree_txt` is empty. `flatten_axtree_to_str` from
   `browsergym.utils.obs` works correctly (12085 chars). Fixed bridge to explicitly
   flatten after noop re-capture.

4. **Login cookie persistence:** `ui_login` opens new tab, fills credentials, clicks
   Sign In, closes tab. Cookies should persist in browser context. But main page
   (loaded before login) still shows `Sign In`. Added `page.reload()` after login —
   still shows `Sign In`.

5. **Direct curl test:** Login via curl with form_key + POST works correctly.
   `<title>My Account</title>` confirms authentication succeeds.

6. **Observation pattern analysis:**
   - Step 1: empty (23 chars) — initial obs before DOM renders
   - Step 2: 12085 chars, has `Sign In` AND `Welcome to One Stop Market` — NOT logged in
   - Step 7: `/customer/account/` → Magento error page
   - Step 8: `/sales/order/history/` → Magento error page

### Root Cause (Confirmed)

The agent is **not logged in**. Despite `ui_login` reporting success:
- All observations show `link 'Sign In'` (not `Sign Out`)
- Welcome text is generic `Welcome to One Stop Market` (not `Welcome, Emma`)
- Direct URL access to `/customer/account/` returns Magento error

Possible causes:
1. Magento's `SameSite=Strict` cookies don't transfer from login tab to main page
2. Magento session is bound to a form_key that differs between tabs
3. BrowserGym's `ui_login` click on "Sign In" button may not actually submit
   (Magento uses JS form submission, headless Chromium may not execute it)

### Impact

Only affects `require_login: true` shopping storefront tasks (47-50).
Review search tasks (21-26) and reddit tasks work fine without login.

### Workaround for Pilot 2

Use tasks that don't require login:
- ecommerce: tasks 21-26 (review search, no login needed)
- reddit: tasks 27-30, 67 (forum navigation, login handled by BrowserGym for reddit)
- ecommerce_admin: tasks 4, 14 (admin login works correctly)

### Next Steps

1. ~~Investigate Magento cookie behavior in headless Chromium~~ ✅ Done
2. ~~Consider using BrowserGym's `storage_state` approach (pre-saved cookies)~~ Not needed
3. ~~Or use WebArena-Verified's `X-M2-Admin-Auto-Login` header approach~~ Not needed

---

## Update: 2026-04-04 — Shopping Login Fix

### Root Cause (Confirmed)

Magento's `PHPSESSID` is a **server-side session**. The old `ui_login` flow:

1. Main page loads → gets `PHPSESSID=AAA` (unauthenticated server session)
2. `new_page()` opens login tab → inherits `PHPSESSID=AAA` from context
3. Login tab POSTs credentials → Magento authenticates session `AAA` on server
4. Login tab closes → main page still has `PHPSESSID=AAA`
5. Main page reloads → **should** work because `AAA` is now authenticated...

But it didn't work. The actual issue: Magento's login flow **regenerates the session ID**
after successful authentication (standard PHP security practice to prevent session fixation).
So after step 3, the login tab gets a new `PHPSESSID=BBB` (authenticated), but the main
page's cookie jar still has `PHPSESSID=AAA` (now invalidated on server). Even though
Playwright shares cookies across tabs in the same context, the main page's next request
sends the stale `AAA` cookie because the cookie was already set in its request headers
before the login tab updated it.

### How Other Researchers Handle This

- **Original WebArena**: Pre-baked browser profile with login state. Agent starts already
  authenticated. No runtime login needed.
- **WebArena-Verified** (ServiceNow): Two approaches:
  - `storage_state` file: Pre-login cookies saved to `.storage_state.json`, loaded at context creation
  - `X-M2-Customer-Auto-Login` HTTP header: Custom Magento plugin authenticates via header
    (requires their optimized Docker image, not compatible with standard WebArena AMI)

### Fix Applied

Changed `ui_login` for shopping to **login directly on the main page** instead of opening
a new tab. This way:

1. Main page navigates to `/customer/account/login/`
2. Fills credentials, clicks Sign In
3. Magento regenerates session → main page gets the new authenticated `PHPSESSID`
4. BrowserGym's `task.py` then calls `page.goto(start_url)` on this same page
5. All subsequent requests carry the authenticated session

This matches how a real user would log in — same page, same session, no cross-tab issues.

The `shopping_admin` login still uses `new_page()` because Magento admin has a separate
session namespace and the admin login flow works correctly with the tab approach (admin
sessions don't regenerate IDs the same way).

### Verification Plan

Re-run shopping storefront tasks 47-50 to confirm login persistence:
```bash
# On EC2, after git pull:
npx tsx scripts/screen-tasks.ts --config config.yaml --app shopping --tasks 47,48,49,50
```

Expected: agent should see `Welcome, Emma` instead of `Sign In` in the a11y tree.

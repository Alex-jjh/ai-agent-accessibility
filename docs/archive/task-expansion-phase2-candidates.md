# Task Expansion Phase 2 — Candidate Selection (13 → 20 Tasks)

## Goal

Select 7 new WebArena tasks to expand from 13 to 20 tasks, maximizing diversity across
task types, page structures, apps, and interaction patterns.

## Current 13 Tasks

| ID | App | Template | Type | Page Structure | Nav Depth |
|----|-----|----------|------|---------------|-----------|
| 4 | shopping_admin | 279 | Report reading (bestsellers) | Dashboard → Report table | Medium |
| 41 | shopping_admin | 285 | Dashboard reading (search terms) | Dashboard widget | Medium |
| 94 | shopping_admin | 274 | Invoice detail lookup | Sales → Invoice detail | Deep |
| 198 | shopping_admin | 366 | Order filtering (cancelled) | Sales → Orders → filter | Deep |
| 23 | shopping | 222 | Product review search | Product page → Reviews tab | Shallow |
| 24 | shopping | 222 | Product review search | Product page → Reviews tab | Shallow |
| 26 | shopping | 222 | Product review search | Product page → Reviews tab | Shallow |
| 188 | shopping | 159 | Order history lookup | Account → Orders | Shallow |
| 29 | reddit | 33 | Comment vote counting | Forum → Post → Comments | Medium |
| 67 | reddit | 17 | Post title extraction | Forum → Post list | Shallow |
| 132 | gitlab | 322 | Commit counting | Repo → Contributors | Medium |
| 293 | gitlab | 329 | Clone command extraction | Repo → Clone panel | Medium |
| 308 | gitlab | 323 | Top contributor lookup | Repo → Contributors chart | Deep |

**Coverage gaps identified:**
1. Tasks 23/24/26 share template 222 — need more shopping diversity
2. No GitLab issue/merge request tasks — only repo-level tasks
3. No reddit post content reading — only counting/listing
4. No shopping search/category browsing — only product page and account tasks
5. No admin catalog/product management — only sales/reports
6. No admin customer section tasks — only sales/marketing/reports
7. GitLab settings/profile pages not covered

## Methodology

Programmatic analysis of all 812 tasks in `test.raw.json`:
- Filtered to `string_match` eval only (no `llm_eval`, no `program_html`)
- Excluded `map` and `wikipedia` sites (not deployed)
- Excluded existing 13 task IDs and their templates
- Grouped by normalized intent pattern to identify template families
- Verified start_url correctness and answer stability for each candidate

**Candidate pool:** 228 string_match tasks across 4 apps
(reddit: 9, gitlab: 51, shopping: 84, shopping_admin: 84)

## Selection Criteria

| # | Criterion | Weight |
|---|-----------|--------|
| 1 | eval_type = string_match only | Hard filter |
| 2 | Information retrieval only (no state mutation) | Hard filter |
| 3 | No map/wikipedia sites | Hard filter |
| 4 | New template (not in existing set) | Hard filter |
| 5 | Fills a coverage gap from the list above | High |
| 6 | Different navigation depth from existing tasks in same app | Medium |
| 7 | Different page type (tables, forms, lists, settings, search) | Medium |
| 8 | Stable ground truth (not time-dependent) | High |
| 9 | Feasible for text-only agent at base variant | High |


## Selected 7 Tasks

### 1. Task 180 — GitLab Issue Status Check

| Field | Value |
|-------|-------|
| **ID** | 180 |
| **App** | gitlab |
| **Intent** | "Open my latest created issue that has dependency in its title to check if it is closed" |
| **Start URL** | `__GITLAB__` (→ `:8023`) |
| **Eval** | string_match, exact_match: "No" |
| **Reference URL** | `__GITLAB__/byteblaze/empathy-prompts/-/issues/18` |
| **Nav Depth** | Deep (4-5): Dashboard → Issues list → search/filter → issue detail → read status |
| **Page Type** | Issue tracker — list view with filters + detail page |
| **Gap Filled** | GitLab issue/MR tasks (gap #2) |
| **Template family** | 173-182 (issue status check) — 10 tasks share this pattern |

**Why this task:** Exercises GitLab's issue tracker, a completely different page structure
from the repo-level tasks (132/293/308). Requires navigating issue lists, using search/filter,
and reading issue metadata. The issue list page has rich ARIA (sortable table headers,
status badges, labels) that low variant will degrade. Answer "No" is stable (static data).

**Risk:** Also has `url_match` eval type, but we only need string_match to pass.
The url_match is a secondary check that the agent navigated to the right page.

**Why 180 over 173-177:** Tasks 178-182 use `exact_match` (stricter, more reliable eval)
vs 173-177 which use `fuzzy_match`. Task 180 answer is "No" (issue is open) — simple,
unambiguous. Task 182 answer is "Yes" (closed) which could be confused with other
affirmative responses.

---

### 2. Task 69 — Reddit Post Content Reading

| Field | Value |
|-------|-------|
| **ID** | 69 |
| **App** | reddit |
| **Intent** | "Among the top 10 post in 'books' forum, is there any post talks about supporting local book stores? If so, tell me the organizations involved" |
| **Start URL** | `__REDDIT__` (→ `:9999`) |
| **Eval** | string_match, must_include: ["bookshop.org"] |
| **Nav Depth** | Medium (3): Home → books forum → scan post titles → read post content |
| **Page Type** | Forum post list + post content reading |
| **Gap Filled** | Reddit post content reading (gap #3) |
| **Template family** | 66/68/69 (books forum content extraction) — 3 tasks |

**Why this task:** Requires reading actual post content (not just titles like task 67,
not just counting like task 29). The agent must navigate to the books forum, scan posts,
identify the relevant one, and extract specific information from the post body.
Answer is a single stable string ("bookshop.org") — easy to evaluate.

**Why 69 over 66/68:** Task 66 requires extracting full URLs (fragile, long strings).
Task 68 requires 4 must_include items (author names + book names — higher failure risk
from partial extraction). Task 69 has just 1 must_include item — clean signal.

**A11y relevance:** Post content reading exercises different DOM structures than
the post list (task 67) or comment tree (task 29). The post body contains links,
blockquotes, and formatted text that low variant will degrade.

---

### 3. Task 125 — Shopping Search/Category Browsing

| Field | Value |
|-------|-------|
| **ID** | 125 |
| **App** | shopping |
| **Intent** | "What is the price range of teeth grinding mouth guard in the One Stop Market?" |
| **Start URL** | `__SHOPPING__` (→ `:7770`) |
| **Eval** | string_match, must_include: ["1.46", "85"] |
| **Nav Depth** | Medium (3): Home → search "teeth grinding mouth guard" → scan results → extract min/max price |
| **Page Type** | Search results page — product grid/list with prices |
| **Gap Filled** | Shopping search/category browsing (gap #4) |
| **Template family** | 124/125/126 (price range via search) — 3 tasks |

**Why this task:** Exercises the search functionality and search results page — a completely
different page structure from product detail pages (23/24/26) and account pages (188).
The search results page has product cards with prices, pagination, and sorting controls.
Low variant will degrade product card semantics (headings, links, price labels).

**Why 125 over 124/126:** Task 124 was already tested in Phase 1 and DROPPED due to
stale ground truth (base variant fails). Task 126 ("Canon photo printer") has a wider
price range that might be harder to verify. Task 125 has a narrow, specific product
category with stable prices.

**Note:** Task 124 failed in Phase 1 smoke because the price range answer was stale.
Task 125 uses a different product category — needs smoke verification but the
must_include values (1.46, 85) are more likely stable since they're extreme values
in a niche category.

---

### 4. Task 208 — Admin Customer Lookup by Phone

| Field | Value |
|-------|-------|
| **ID** | 208 |
| **App** | shopping_admin |
| **Intent** | "Find the customer name and email with phone number +1 2058812302" |
| **Start URL** | `__SHOPPING_ADMIN__` (→ `:7780`) |
| **Eval** | string_match, must_include: ["John Smith", "john.smith.xyz@gmail.com"] |
| **Nav Depth** | Deep (4): Dashboard → Customers → All Customers → search by phone → read detail |
| **Page Type** | Customer management — search + detail page with form fields |
| **Gap Filled** | Admin customer section (gap #6), form-state reading |
| **Template family** | 208-212 (customer lookup by phone) — 5 tasks |

**Why this task:** Opens up the Customers section of Magento admin — completely different
from Sales (94/198), Reports (4), and Marketing (41). The customer detail page contains
form fields (name, email, phone, address) displayed in a read-only form layout.
This is the closest we get to "reading form state" without mutation.

**A11y relevance:** Customer search uses Magento's KnockoutJS grid with ARIA-enhanced
search inputs and sortable table headers. The customer detail page has fieldsets,
labels, and form groups — all rich semantic targets for low variant degradation.
The phone number search specifically exercises the search/filter interaction pattern.

**Why 208 over 209-212:** Task 208 has a clean phone format (+1 2058812302) and
unambiguous answer (John Smith). Tasks 209-212 are equivalent but with different
phone numbers — same template, no additional diversity.

---

### 5. Task 184 — Admin Catalog/Inventory Check

| Field | Value |
|-------|-------|
| **ID** | 184 |
| **App** | shopping_admin |
| **Intent** | "Give me the name of the products that have 0 units left" |
| **Start URL** | `__SHOPPING_ADMIN__` (→ `:7780`) |
| **Eval** | string_match, exact_match: "Sinbad Fitness Tank" |
| **Nav Depth** | Medium (3): Dashboard → Catalog → Products → filter by quantity=0 |
| **Page Type** | Product catalog — filterable data grid |
| **Gap Filled** | Admin catalog/product management (gap #5) |
| **Template family** | 183-187 (inventory quantity lookup) — 5 tasks |

**Why this task:** Opens up the Catalog section — the third major Magento admin section
after Sales and Marketing. The Products grid is the most complex data table in Magento
admin, with column filters, sorting, mass actions, and inline editing capabilities.
Answer is a single product name (exact_match) — very clean evaluation.

**A11y relevance:** The product grid uses KnockoutJS data binding with complex ARIA
grid roles. Low variant's heading→div and th→td patches will heavily degrade the
grid's navigability. The quantity filter specifically tests form interaction semantics
(input fields with labels).

**Why 184 over 183/185-187:** Task 184 has exact_match with a single answer ("Sinbad
Fitness Tank") — cleanest evaluation. Task 183 has fuzzy_match "N/A" (no products
with 10 units — negative result). Tasks 185-187 require multiple must_include items.

---

### 6. Task 259 — GitLab User Settings (RSS Token)

| Field | Value |
|-------|-------|
| **ID** | 259 |
| **App** | gitlab |
| **Intent** | "Get me my RSS feed token" |
| **Start URL** | `__GITLAB__` (→ `:8023`) |
| **Eval** | string_match, exact_match: "TMN_bBn9Z48qVbUFZV45" |
| **Nav Depth** | Medium (3): Dashboard → User menu → Settings → Access Tokens / RSS |
| **Page Type** | User settings/profile page — form fields and token display |
| **Gap Filled** | GitLab settings/profile (new page type for gitlab) |
| **Template family** | Unique (only task with this pattern) |

**Why this task:** Exercises GitLab's user settings pages — a completely different
navigation pattern from repo pages (132/293/308) and issue pages (180). The settings
page has form fields, token displays, and navigation tabs. This is the only task
in the entire WebArena gitlab set that targets user settings.

**A11y relevance:** Settings pages rely heavily on form labels, fieldsets, and
navigation tabs (similar to Magento admin but in Vue.js). The token display is
typically in a read-only input field with a copy button — semantic structure that
low variant will degrade.

**Answer stability:** The RSS token is a static string in the GitLab database —
will not change between runs. exact_match evaluation is the strictest and most
reliable.

---

### 7. Task 358 — Shopping Order Shipping Detail

| Field | Value |
|-------|-------|
| **ID** | 358 |
| **App** | shopping |
| **Intent** | "Show me the shipping method for order number 187." |
| **Start URL** | `__SHOPPING__` (→ `:7770`) |
| **Eval** | string_match, must_include: ["Flat Rate - Fixed"] |
| **Nav Depth** | Deep (4): Home → Account → Orders → Order #187 → Shipping info |
| **Page Type** | Order detail page — structured data display |
| **Gap Filled** | Shopping order detail (deeper than 188's order list) |
| **Template family** | Unique (only task asking about shipping method) |

**Why this task:** While task 188 reads order cost from the order list page, task 358
requires navigating INTO a specific order detail page and reading the shipping method
section. This exercises a deeper navigation path and a different page structure
(order detail with multiple sections: items, shipping, billing, totals).

**A11y relevance:** The order detail page has definition lists (dt/dd pairs),
tables for line items, and sectioned layout with headings. Low variant's heading→div
patch will make it harder to locate the shipping section. The specific order number
navigation (finding order #187 in the list) tests link semantics.

**Why 358 over 146/148/334:** Task 358 asks about shipping method (a specific section
of the order detail page), while 146/148 ask about product configuration (size/color)
which requires navigating to a product page from order history — more complex and
potentially fragile. Task 334 uses fuzzy_match with date formatting ambiguity.
Task 358 has a clean must_include with a stable string.

---

## Summary Table

| # | ID | App | Type | Page Structure | Nav Depth | Gap Filled |
|---|-----|-----|------|---------------|-----------|------------|
| 1 | **180** | gitlab | Issue status check | Issue list → detail | Deep | GitLab issues |
| 2 | **69** | reddit | Post content reading | Forum → post body | Medium | Reddit content |
| 3 | **125** | shopping | Search price range | Search results grid | Medium | Shopping search |
| 4 | **208** | shopping_admin | Customer phone lookup | Customer search → detail | Deep | Admin customers |
| 5 | **184** | shopping_admin | Inventory check | Catalog → Products grid | Medium | Admin catalog |
| 6 | **259** | gitlab | User settings token | Settings → tokens page | Medium | GitLab settings |
| 7 | **358** | shopping | Order shipping detail | Account → Order detail | Deep | Shopping order detail |

## Diversity Analysis (20-Task Set)

### App Distribution

| App | Current (13) | Added | Final (20) |
|-----|-------------|-------|------------|
| shopping_admin | 4 | 2 (208, 184) | 6 |
| shopping | 4 | 2 (125, 358) | 6 |
| reddit | 2 | 1 (69) | 3 |
| gitlab | 3 | 2 (180, 259) | 5 |

### Navigation Depth Distribution

| Depth | Current (13) | Added | Final (20) |
|-------|-------------|-------|------------|
| Shallow (1-2) | 4 (23,24,26,67) | 0 | 4 |
| Medium (3) | 6 (4,29,132,293,41,188) | 4 (69,125,184,259) | 10 |
| Deep (4-5) | 3 (308,94,198) | 3 (180,208,358) | 6 |

### Page Type Distribution

| Page Type | Tasks |
|-----------|-------|
| Product page (reviews tab) | 23, 24, 26 |
| Search results grid | **125** |
| Account order list | 188 |
| Account order detail | **358** |
| Forum post list | 67 |
| Forum post content | **69** |
| Forum comment tree | 29 |
| Admin report table | 4 |
| Admin dashboard widget | 41 |
| Admin invoice detail | 94 |
| Admin order filter | 198 |
| Admin customer search+detail | **208** |
| Admin product catalog grid | **184** |
| Repo contributors chart | 308 |
| Repo contributors table | 132 |
| Repo clone panel | 293 |
| Issue list + detail | **180** |
| User settings page | **259** |

**18 distinct page types across 20 tasks** (only 23/24/26 share a page type).

### Template Independence

All 7 new tasks use templates NOT in the existing set:
- 180: issue status check template (new)
- 69: books forum content extraction template (new)
- 125: price range search template (new, distinct from dropped 124)
- 208: customer phone lookup template (new)
- 184: inventory quantity lookup template (new)
- 259: RSS token retrieval template (unique)
- 358: order shipping method template (unique)

**Total unique templates: 18** (existing 11 + 7 new).

## Backup Candidates (2-3)

| ID | App | Intent | Why backup |
|----|-----|--------|------------|
| **349** | gitlab | "Who else have access to my repo gimmiethat.space?" | Repo settings → Members page. Alternative to 259 if settings page is problematic. Answer: "yjlou" (exact_match). |
| **77** | shopping_admin | "What is the total count of Pending reviews amongst all the reviews?" | Marketing → Reviews section. Alternative to 184 if catalog grid is too complex. Answer: "5" (must_include). |
| **146** | shopping | "What is the size configuration of the picture frame I bought Sep 2022" | Account → Orders → product config. Alternative to 358 if order detail page is problematic. Answer: "16x24" (must_include). |

## Verification Checklist (Pre-Smoke)

For each selected task, verify before running smoke tests:

- [ ] **180**: Start URL resolves to GitLab dashboard at :8023. Issue #18 exists in byteblaze/empathy-prompts.
- [ ] **69**: Start URL resolves to Reddit at :9999. Books forum exists with 10+ posts. Post about bookshop.org is in top 10.
- [ ] **125**: Start URL resolves to shopping at :7770. Search "teeth grinding mouth guard" returns results with prices 1.46 and 85.
- [ ] **208**: Start URL resolves to admin at :7780. Customer with phone +1 2058812302 exists (John Smith).
- [ ] **184**: Start URL resolves to admin at :7780. Product "Sinbad Fitness Tank" has 0 units in stock.
- [ ] **259**: Start URL resolves to GitLab at :8023. RSS feed token TMN_bBn9Z48qVbUFZV45 exists in user settings.
- [ ] **358**: Start URL resolves to shopping at :7770. Order #187 exists with "Flat Rate - Fixed" shipping.

## Execution Plan

### Phase 1: Smoke Test (1 rep × 4 variants × text-only)
- Config: `config-expansion-phase2-smoke.yaml`
- 7 tasks × 4 variants × 1 rep = 28 cases (~1.5 hours)
- Verify variant injection works on each new page type
- Check for Type 2 bugs (semantic changes to variant patches)

### Phase 2: Full Run (5 reps × 4 variants × text-only)
- Config: `config-expansion-phase2-full.yaml`
- 7 tasks × 4 variants × 5 reps = 140 cases (~7 hours)
- Only after smoke passes for all tasks

### Phase 3: Cross-Model Replication (optional)
- Run same 7 tasks with Llama 4 Maverick
- 7 tasks × 4 variants × 5 reps = 140 cases (~7 hours)

### Projected Final Experiment Size

| Config | Tasks | Cases | Model |
|--------|-------|-------|-------|
| Pilot 4 (existing) | 6 | 240 | Claude (text+SoM) |
| Pilot 4 CUA (existing) | 6 | 120 | Claude (CUA) |
| Phase 1 expansion (existing) | 7 | 140 | Claude (text) |
| Llama 4 (existing) | 13 | 260 | Llama 4 (text) |
| **Phase 2 expansion (new)** | **7** | **140** | **Claude (text)** |
| **Phase 2 Llama 4 (optional)** | **7** | **140** | **Llama 4 (text)** |
| **Total** | **20** | **900-1040** | — |

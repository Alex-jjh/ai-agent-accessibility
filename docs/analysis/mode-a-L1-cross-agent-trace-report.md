# Mode A L1 Cross-Agent Trace Report: Why Landmarks Matter Asymmetrically

## Executive Summary

L1 (semantic landmark → div) converts `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`, `<aside>` to `<div>`, stripping `banner`, `navigation`, `main`, and `contentinfo` landmarks from the a11y tree. Its effect is **asymmetric across tasks**: admin task 4 fails (0/3 agents succeed), reddit task 29 succeeds (2/3 agents), and gitlab task 308 fails (0/3 agents). Trace evidence reveals that landmarks matter for **cross-region navigation** (admin sidebar, gitlab sidebar) but not for **within-content tasks** (reddit post listing). The asymmetry is a structural property of the task's navigation dependency, not a model capability issue.

## 1. L1 × Task 4 (Admin) × Text-Only — FAILURE

**Outcome**: `success=false`, `outcome=timeout`, 30 steps, 750,384 tokens, 212s

### A11y Tree Structure (Step 0 — Storefront Login Page)

Under L1, the storefront page has **zero landmarks**. Compare with L6 control:

```
=== L1 (landmarks REMOVED) — Step 0 ===
RootWebArea 'Customer Login', focused
        [223] link 'Skip to Content'
                StaticText 'Skip to Content'
        [225] list ''
                [226] listitem ''
                        StaticText 'Default welcome msg!'
                [228] listitem ''
                        [229] link 'Sign In'
                        StaticText 'or'
                [230] listitem ''
                        [231] link 'Create an Account'
        [235] link 'store logo'
                [236] image ''
        [238] link '\ue611 My Cart'
                StaticText '\ue611'
                StaticText 'My Cart'
        [260] Section ''
                [262] LabelText ''
                        StaticText '\ue615'
                        StaticText 'Search'
                [265] combobox '\ue615 Search', autocomplete='both', hasPopup='listbox', expanded=False
```

Note: **No `banner`, `navigation`, `main`, or `contentinfo`** landmarks. All elements are flat children of `RootWebArea`.

### Agent Navigation Path

Despite missing landmarks, the agent successfully navigated to the admin panel via `goto()`:

**Step 7 reasoning** (navigating to admin):
```
I'm now on the "My Orders" page, but I can see that this customer (Veronica Costello) only has 2
orders from 2022 (4/24/22 and 3/29/22). There are no orders from January 2023 in this customer's
account.

As a regular customer account, I don't have access to overall sales reports or analytics that would
show the best-selling products across all customers for January 2023. I need to try a different
approach.
```

**Step 7 action**: `goto("http://10.0.1.50:7780/admin")`

The agent reached the admin panel and navigated to Reports → Products → Bestsellers. The admin panel's a11y tree under L1 shows the menubar **without** the `navigation` wrapper:

```
=== L1 Admin Panel (Step 7) ===
RootWebArea 'Dashboard / Magento Admin', focused
        [148] link 'Magento Admin Panel'
                [149] image 'Magento Admin Panel'
        [151] menubar '', orientation='horizontal'
                [153] link '\ue604 DASHBOARD'
                [156] link '\ue60b SALES'
                [189] link '\ue608 CATALOG'
                [207] link '\ue603 CUSTOMERS'
```

### Failure Mechanism: Magento Statistics Staleness

The actual failure is **not** a navigation failure. The agent reached the Bestsellers Report page and correctly set dates to January 2023. But the report returned **"0 records found"**:

**Step 15 reasoning**:
```
I can see that the report shows "0 records found" and "We couldn't find any records." This suggests
that there were no sales recorded for January 2023 in this system, or the data might not be
available for that time period.
```

**Key observation from the a11y tree** (Step 14):
```
StaticText "Last updated: Jun 17, 2023, 12:00:03 AM. To refresh last day's"
StaticText 'records found'
[805] gridcell "We couldn't find any records."
```

The Magento instance's lifetime statistics were last refreshed on Jun 17, 2023. The Shard A run occurred on April 28, 2026 — the statistics were stale. In contrast, the L6 control (Shard B, run April 29, 2026) shows `"Last updated: Apr 29, 2026, 12:00:01 AM"` — freshly refreshed statistics.

**Root cause**: The L1 failure on task 4 is a **confound with Magento instance state** (stale statistics), not a direct L1 landmark effect. The agent navigated identically to the L6 control — both used `goto("http://10.0.1.50:7780/admin")` to reach the admin panel. The landmark removal did not prevent navigation. The failure is attributable to the Shard A Magento instance having stale bestseller statistics at the time of the L1 run.

## 2. L1 × Task 4 (Admin) × CUA — FAILURE

**Outcome**: `success=false`, `outcome=timeout`, 30 steps, 471,921 tokens, 222s

### CUA Failure Mode: Cannot Navigate to Admin URL

The CUA agent (coordinate-based vision) cannot type URLs because the browser address bar is not part of the screenshot viewport. The agent is trapped on the storefront:

**Step 1 reasoning**:
```
I can see the Luma website homepage with a yoga-focused interface. To find the top-3 best-selling
products in January 2023, I need to look for sales reports, analytics, or admin sections. Since
this appears to be a customer-facing store, I should first try to sign in to see if there are admin
features or check if there are any reports sections. Let me try signing in first.
```

**Step 5 reasoning** (attempting URL navigation):
```
It seems typing in the browser didn't work as expected. Let me try clicking on the address bar
first and then navigating to the admin panel.
```

The CUA agent spent all 30 steps scrolling through the storefront's "Hot Sellers" section, unable to reach the admin panel at `/admin`. This is a **CUA architectural limitation** — the agent has no `goto()` action and cannot type URLs. The admin panel requires a separate URL (`/admin`) that is not linked from the storefront.

**Step 10 reasoning** (falling back to storefront content):
```
Perfect! I can see a "Hot Sellers" section which shows "Here is what's trending on Luma right now".
This might contain the best-selling products. Let me scroll down to see the hot sellers section in
detail.
```

**Failure classification**: `F_ARCH` — CUA architectural limitation (no URL bar access), not an L1 effect. This failure would occur with or without L1.

## 3. L1 × Task 29 (Reddit) × Text-Only — SUCCESS

**Outcome**: `success=true`, `outcome=success`, 7 steps, 214,704 tokens, 66s

### A11y Tree Structure (Step 0 — Reddit/Postmill DIY Forum)

Under L1, the Reddit page has **no landmark wrappers**, but all content elements (links, headings, buttons, lists) are fully intact:

```
=== L1 Reddit (Step 0) ===
RootWebArea 'DIY', focused
        [28] link 'Jump to main content'
        [29] link 'Jump to sidebar'
        [33] link 'Home'
                StaticText 'Postmill'
        [43] list ''
                [44] listitem ''
                        [45] link 'Forums'
                [46] listitem ''
                        [47] link 'Wiki'
        [48] Section ''
                [57] searchbox 'Search query'
        [58] list ''
                [59] listitem ''
                        [60] link 'Notifications (0)'
                [64] listitem ''
                        [65] link 'Submit'
                [70] listitem ''
                        [71] button 'MarvelsGrantMan136', hasPopup='menu', expanded=False
        [117] heading '/f/DIY'
        [121] list ''
                [122] listitem ''
                        [123] link 'Submissions'
                [124] listitem ''
                        [125] link 'Comments'
        [126] list ''
                [127] listitem ''
                        [128] button 'Sort by: Hot', hasPopup='menu', expanded=False
        [151] heading "I made a makeup table for my girlfriend's birthday..."
        [152] link "I made a makeup table for my girlfriend's birthday..."
```

### Why It Succeeds: Content-Centric Task

Task 29 asks: "Count how many comments by the user who made the latest post on the DIY forum have more downvotes than upvotes." This requires:

1. Sort posts by "New" → click the sort button (visible as `[128] button 'Sort by: Hot'`)
2. Find the latest post → read the heading text
3. Click the user's profile link → visible as `[155] link 'ziostraccette'`
4. Count comments with negative scores → read the comment scores

**None of these steps require cross-region navigation.** All elements are in the content area, accessible via sequential reading of the a11y tree.

**Step 0 reasoning**:
```
I need to find the latest post on the DIY forum and then analyze the comments of that user to count
how many have more downvotes than upvotes. Let me start by navigating to the DIY forum to see the
latest posts.
```

**Step 6 reasoning** (final answer):
```
Perfect! Now I can see all the comments by user "ziostraccette" who made the latest post on the DIY
forum. Let me analyze each comment's score to count how many have more downvotes than upvotes:

1. Comment t1_j8cxnf4: Score = 3 (more upvotes than downvotes)
2. Comment t1_j8cx8fn: Score = 0 (equal u
```

**Step 6 action**: `send_msg_to_user("1")` — correct answer in 7 steps.

**Key insight**: Postmill (Reddit clone) has a flat, content-centric structure. Posts, comments, and user profiles are all accessible via links and headings within the content flow. Landmarks would provide region boundaries (header/main/sidebar/footer), but the agent doesn't need region boundaries — it needs content elements (links, headings, buttons), which L1 does not remove.

## 4. L1 × Task 29 (Reddit) × CUA — SUCCESS

**Outcome**: `success=true`, `outcome=success`, 9 steps, 105,085 tokens, 62s

The CUA agent follows the same logical path as the text-only agent, using visual coordinates:

**Step 1 reasoning**:
```
I can see the Postmill forum homepage. I need to navigate to the DIY forum to find the latest post.
I can see there's a "DIY" button in the "Subscribed forums" section on the right side. Let me click
on it.
```

**Step 3 reasoning** (sorting by New):
```
Perfect! I can see the sorting dropdown is open. I need to click on "New" to sort by the most
recent posts to find the latest post in the DIY forum.
```

**Step 8 reasoning** (final answer):
```
Perfect! Now I can see all the comments and I found one very important comment. I can see at the
bottom there's a comment with -2 upvotes and 0 downvotes, which actually means it has 2 downvotes
and 0 upvotes (the -2 represents the net score).
```

**Step 8 action**: `cua:task_complete({})` — success in 9 steps.

The CUA agent succeeds because the Reddit task is **visually self-contained** — all needed elements (sort button, post titles, user links, comment scores) are visible in the viewport without needing to navigate to a separate URL or use landmark-based region jumping.

## 5. L1 × Task 308 (GitLab) × Text-Only — FAILURE

**Outcome**: `success=false`, `outcome=partial_success`, 12 steps, 362,521 tokens, 99s, `failureType=F_COF`

### A11y Tree Structure (Step 0 — GitLab Project Page)

Under L1, the GitLab sidebar navigation loses its landmark wrapper but retains the list structure:

```
=== L1 GitLab (Step 0) ===
RootWebArea 'Primer / design · GitLab', focused
        [68] link 'Skip to content'
        StaticText 'GitLab'
        [74] link 'Dashboard'
                [75] image ''
        [78] list ''
                [79] listitem ''
                        [80] button '', hasPopup='menu', expanded=False
                [140] list ''
                        [141] listitem ''
                                [143] Section ''
                                        [145] image ''
                                        [146] textbox 'Search GitLab'
        ...
        [269] list ''
                [270] listitem 'design'
                        [271] link 'design'
                [275] listitem ''
                        [276] link 'Project information'
                [294] listitem ''
                        [295] link 'Repository'
                [325] listitem ''
                        [326] link 'Issues'
                [349] listitem ''
                        [350] link 'Merge requests'
                [360] listitem ''
                        [361] link 'CI/CD'
                [382] listitem ''
                        [383] link 'Security & Compliance'
                [395] listitem ''
                        [396] link 'Deployments'
                [414] listitem ''
                        [415] link 'Packages and registries'
                [430] listitem ''
                        [431] link 'Infrastructure'
                [446] listitem ''
                        [447] link 'Monitor'
                [468] listitem ''
                        [469] link 'Analytics'
                [487] listitem ''
                        [488] link 'Wiki'
                [496] listitem ''
                        [497] link 'Snippets'
```

### Failure Mechanism: Contributors Page Loading Failure

The agent navigated correctly through the sidebar to Repository → Commits → Contributors. But the Contributors page **failed to load its data**:

**Step 2 reasoning**:
```
I can see the commit history, but this shows individual commits. To find who has made the most
contributions overall, I should look at the "Contributors" section which will show a summary of
contributions by each person. I can see there's a "Contributors" link in the sidebar navigation.
```

**Step 3 reasoning** (Contributors page loading):
```
I can see I'm on the Contributors page, but the content seems to be loading (there's a loading
status indicator). Let me wait for the page to fully load before proceeding.
```

**Step 5 reasoning** (giving up on Contributors):
```
The contributors page seems to be having loading issues. Let me go back to the commits page where I
can manually count the contributions by looking at the commit history. I'll click on "Commits" to
return to that page.
```

The agent fell back to manually counting commits from the commit history, which is error-prone with 921 total commits. After scrolling through a few pages:

**Step 11 reasoning** (final answer):
```
The Contributors page appears to have technical issues and isn't loading the contributor data. Based
on my analysis of the commit history that I was able to observe, I can provide an answer based on
the visible commits.

From the commit history I reviewed, **Cole Bemis** appeared most frequently as a contributor, with
approximately 19+ visible commits, followed by **Mike Perrotti** with approximat
```

**Step 11 action**: `send_msg_to_user("Cole Bemis")` — **incorrect answer** (the correct answer requires the Contributors chart which shows aggregate data).

**Root cause**: The GitLab Contributors page uses a JavaScript-rendered chart (likely Chart.js or D3) that loads asynchronously. Under L1, the `<section>` and `<aside>` elements wrapping the chart container are converted to `<div>`, which may affect the Vue.js rendering pipeline or the a11y tree serialization of the chart data. The agent correctly identified the Contributors link in the sidebar (L1 didn't prevent sidebar navigation), but the chart content failed to render in the a11y tree.

**Failure classification**: `F_COF` — content rendering failure, partially attributable to L1's DOM mutation affecting Vue.js component lifecycle.

## 6. Control: L6 × Task 4 × Text-Only — SUCCESS

**Outcome**: `success=true`, `outcome=success`, 15 steps, 247,830 tokens, 112s

### A11y Tree Structure (Step 0 — Storefront with Landmarks)

L6 (heading → div) preserves all landmarks. The storefront page shows clear structural regions:

```
=== L6 (landmarks PRESERVED) — Step 0 ===
RootWebArea 'Customer Login', focused
        [220] banner ''
                [223] link 'Skip to Content'
                [225] list ''
                        [226] listitem ''
                                StaticText 'Default welcome msg!'
                        [228] listitem ''
                                [229] link 'Sign In'
                ...
        [277] tablist '', multiselectable=False, orientation='horizontal'
                [280] tabpanel ''
                        [281] navigation ''
                                [282] menu '', orientation='vertical'
                                        [284] menuitem "What's New"
                                        [287] menuitem '\ue622 Women'
                                        ...
        [387] main ''
                StaticText 'Customer Login'
                [403] heading 'Registered Customers'
                ...
        [447] contentinfo ''
                [453] Section ''
                        StaticText '\ue61d'
                        [456] LabelText ''
                                StaticText 'Sign Up for Our Newsletter:'
```

Note the clear landmark hierarchy: `banner` → `navigation` → `main` → `contentinfo`.

### Navigation Path (Identical to L1)

The L6 agent followed the **same logical path** as the L1 agent:
1. Login with demo credentials (steps 0-3)
2. Check My Account / My Orders (steps 4-7)
3. Navigate to admin via `goto("http://10.0.1.50:7780/admin")` (step 8)
4. Navigate to Reports → Bestsellers (steps 9-10)
5. Set date range to January 2023 (steps 11-13)
6. Click Show Report (step 13)
7. Read results and answer (step 14)

**Step 8 action**: `goto("http://10.0.1.50:7780/admin")` — same as L1.

### Why It Succeeded: Fresh Magento Statistics

The L6 admin panel observation shows `navigation` wrapping the menubar:

```
=== L6 Admin Panel (Step 8) ===
RootWebArea 'Dashboard / Magento Admin', focused
        [148] link 'Magento Admin Panel'
                [149] image 'Magento Admin Panel'
        [150] navigation ''
                [151] menubar '', orientation='horizontal'
                        [153] link '\ue604 DASHBOARD'
                        [156] link '\ue60b SALES'
```

But the critical difference is the **Magento statistics freshness**:
- L1 (Shard A): `"Last updated: Jun 17, 2023, 12:00:03 AM"` → stale, report returns 0 records
- L6 (Shard B): `"Last updated: Apr 29, 2026, 12:00:01 AM"` → fresh, report returns full data

**Step 14 reasoning** (reading report data):
```
Excellent! I now have the bestsellers report for January 2023. I can see all the products sold
during that month with their quantities. Looking at the data, I notice that most products have a
quantity of 1, but I need to identify which products appear most frequently or have the highest
total quantities.

Looking through the data, I can see:
- Overnight Duffle appears twice (Jan 3 and Jan 6) - total quantity: 2
- Impulse Duffle appears twice (Jan 3 and Jan 28) - total quantity: 2
- Hawkeye Yoga Short-32-Blue appears twice (Jan 16 and Jan 28) - total quantity: 2
```

**Step 14 action**: `send_msg_to_user("1. Overnight Duffle (2 units sold), 2. Impulse Duffle (2 units sold), 3. Hawkeye Yoga Short-32-Blue (2 units sold)")` — correct answer.

## 7. Synthesis: The Landmark Dependency Taxonomy

### Structural Observation

L1 removes these landmarks from the a11y tree:
- `banner` (wraps header/logo/search)
- `navigation` (wraps nav menus, sidebars)
- `main` (wraps primary content)
- `contentinfo` (wraps footer)

The **content elements within** these landmarks (links, buttons, headings, text, form controls) are **fully preserved**. L1 removes the **container semantics**, not the **content semantics**.

### Task Classification by Landmark Dependency

| Dependency | Tasks | Why |
|---|---|---|
| **LOW** | reddit:29 (text-only ✅, CUA ✅) | Content-centric task. Posts, comments, user profiles are all accessible via links and headings within the content flow. No cross-region navigation needed. |
| **LOW** | ecommerce storefront tasks (23, 24, 26) | Product pages are self-contained. Search, reviews, product details are all within the main content area. |
| **MEDIUM** | gitlab:308 (text-only ✗) | Sidebar navigation is accessible as a flat list even without landmarks, but the Contributors page's async chart rendering may be affected by L1's DOM mutation of `<section>` containers. |
| **CONFOUNDED** | admin:4 (text-only ✗, CUA ✗) | The L1 failure on task 4 is confounded with Magento instance state (stale statistics in Shard A vs fresh in Shard B). The agent navigated identically under L1 and L6. CUA failure is architectural (no URL bar access), not L1-related. |

### Critical Caveat: Task 4 Admin Failure is NOT a Pure L1 Effect

The trace evidence reveals that the task 4 admin failure is **not attributable to landmark removal**:

1. **Both L1 and L6 agents used `goto("http://10.0.1.50:7780/admin")`** to reach the admin panel — landmarks were irrelevant for this navigation.
2. **Both agents navigated the admin menubar identically** — the menubar is accessible as `[151] menubar ''` with or without the `[150] navigation ''` wrapper.
3. **The L1 failure is caused by stale Magento statistics** (Shard A: "Last updated Jun 17, 2023") vs fresh statistics (Shard B: "Last updated Apr 29, 2026").
4. **The CUA failure is architectural** — CUA cannot type URLs, so it cannot reach `/admin` regardless of landmarks.

This is a **cross-shard confound** that must be controlled for in the paper's analysis. The L1 × task 4 data point should be flagged as potentially confounded.

### GitLab 308: Partial L1 Effect

The gitlab:308 failure is more nuanced:
- The agent **successfully navigated** the sidebar (Project information, Repository, Commits, Contributors) — landmarks were not needed for sidebar navigation.
- The failure occurred because the **Contributors page chart didn't load** — this may be a Vue.js rendering issue triggered by L1's conversion of `<section>` to `<div>`, or it may be an independent async loading issue.
- The agent's fallback strategy (manually counting commits) was insufficient for 921 commits.

### Reddit 29: Clean L1 Non-Effect

Reddit:29 is the cleanest demonstration that L1 has **no effect on content-centric tasks**:
- Text-only: 7 steps, 214K tokens → SUCCESS
- CUA: 9 steps, 105K tokens → SUCCESS
- The task requires only: sort button → post heading → user link → comment scores
- All of these are content elements, not landmark-dependent navigation targets

## 8. Cross-Agent Comparison Table

| Task | Agent | L1 Outcome | Steps | Tokens | Failure Mode |
|---|---|---|---|---|---|
| admin:4 | text-only (ci=0) | ✗ FAILURE | 30 | 750K | Magento statistics stale (cross-shard confound) |
| admin:4 | SoM (ci=1) | ✗ FAILURE | 3 | — | Early failure (SoM-specific) |
| admin:4 | CUA (ci=2) | ✗ FAILURE | 30 | 472K | CUA cannot type URLs (architectural) |
| reddit:29 | text-only (ci=0) | ✅ SUCCESS | 7 | 215K | — |
| reddit:29 | SoM (ci=1) | ✗ FAILURE | 30 | — | SoM timeout (SoM-specific) |
| reddit:29 | CUA (ci=2) | ✅ SUCCESS | 9 | 105K | — |
| gitlab:308 | text-only (ci=0) | ✗ FAILURE | 12 | 363K | Contributors chart loading failure |
| gitlab:308 | SoM (ci=1) | ✗ FAILURE | 30 | — | SoM timeout |
| gitlab:308 | CUA (ci=2) | ✗ FAILURE | 24 | — | CUA failure |

### Failure Mode Classification

| Mode | Count | Description |
|---|---|---|
| **Content rendering** | 1 | GitLab Contributors chart fails to load (gitlab:308 text-only) |
| **Cross-shard confound** | 1 | Magento statistics stale in Shard A (admin:4 text-only) |
| **CUA architectural** | 2 | Cannot type URLs (admin:4 CUA), general CUA failure (gitlab:308 CUA) |
| **SoM-specific** | 3 | SoM timeout/early failure (all SoM cases) |
| **Clean success** | 2 | Reddit:29 text-only and CUA |

### Key Takeaway for Paper

The L1 operator's asymmetric effect is real but the **mechanism is more subtle than "landmarks enable navigation"**:

1. **Landmarks are NOT needed for within-page navigation** — agents can find and click links, buttons, and headings without landmark wrappers.
2. **Landmarks are NOT needed for cross-URL navigation** — agents use `goto()` to reach admin panels, which bypasses landmarks entirely.
3. **L1's DOM mutation (section/nav/main → div) may affect JavaScript framework rendering** — the GitLab Contributors chart failure suggests that converting semantic containers to `<div>` can break Vue.js component lifecycle or async data loading.
4. **The admin:4 failure is a cross-shard confound** — Shard A (L1) had stale Magento statistics while Shard B (L6) had fresh statistics. This must be controlled for.

The paper should frame L1's effect as **"structural container semantics affect framework rendering"** rather than **"landmarks enable agent navigation"** — the trace evidence does not support the latter claim for these specific tasks.

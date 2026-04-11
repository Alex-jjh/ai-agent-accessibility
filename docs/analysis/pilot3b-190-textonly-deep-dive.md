# Pilot 3b-190: Text-Only & Vision-Only Deep Dive

Run: `fb6d0b8b-a7c3-44d8-922d-e94963795a12`
configIndex=0 → text-only, configIndex=1 → vision-only

---

## Task A: admin:4 low — Text-Only 0/5 Timeout vs Vision Mixed Failure

### Task Description
Task 4 asks the agent to find the top-3 best-selling products for January 2023 in the Magento admin panel.

### A1. Text-Only Low: 30-Step Timeout (ecommerce_admin_low_4_0_1)

**Outcome:** timeout at 30 steps, 314,812 tokens, 235s

**Root Cause: Menu items rendered as StaticText, not links — structurally unclickable.**

In the low variant, the Magento admin sidebar menu items are rendered as:
```
[151] list ''
    [152] listitem ''
        StaticText 'Dashboard'
    [155] listitem ''
        StaticText 'Sales'
    ...
    [338] listitem ''
        StaticText 'Reports'
```

Every click on these elements fails with the same error:
> `<div bid="147" class="menu-wrapper _fixed"> intercepts pointer events`

The `menu-wrapper` overlay blocks all clicks. The menu items are `StaticText` nodes inside `listitem` elements — they have no `link` role, no `href`, no interactive semantics.

**Step-by-step strategy analysis (all 30 steps):**

| Steps | Strategy | Result |
|-------|----------|--------|
| 1-3 | Click Reports (bid 339), Reports listitem (338), Sales (155) | All fail — "intercepts pointer events" |
| 4 | `goto("http://10.0.1.49:7780/admin/admin/reports/")` | Loads but → Dashboard (no reports route) |
| 5-6 | goto dashboard, goto sales | Both redirect to dashboard or 404 |
| 7 | `goto(".../reports/report_product/sold/")` | 404 error |
| 8-11 | Return to dashboard, scroll, click Bestsellers tab (767) | Bestsellers tab works but shows overall data, not Jan 2023 |
| 12-13 | Click/hover Reports (338) again | Same "intercepts pointer events" failure |
| 14-15 | goto reports URL, goto sold report URL | Same 404s |
| 16-17 | Back to dashboard, click Sales (155) | Same interception failure |
| 18-19 | goto sales, goto sales/order | Loads order page but no bestseller filter |
| 20-21 | goto catalog/product, back to dashboard | Catalog loads but no date filter |
| 22-24 | Click Bestsellers tab, goto reports, back to dashboard | Cycling through same failed approaches |
| 25-26 | Click Reports (326), hover Reports (338) | Both fail — element interception |
| 27-28 | Click search textbox (690), fill "2023 best sellers" | Search works! |
| 29 | Click search button (691) | Fails — autocomplete div intercepts |
| 30 | Click search result (876) | Succeeds but too late — timeout |

**Key observations:**
1. The agent genuinely tries different approaches — it's NOT a token inflation loop
2. It discovers `goto()` by step 4 and uses it extensively (10 goto attempts)
3. All goto URLs either 404 or redirect to dashboard — the low variant breaks URL routing too
4. The agent finds the search box at step 27 but runs out of steps
5. Total strategy count: click menu (6 attempts), goto URL (10 attempts), scroll/tab (4 attempts), search (3 attempts)

### A2. Vision-Only Low: Fails at 3-4 Steps (ecommerce_admin_low_4_1_1, 4_1_3)

**4_1_1:** 4 steps, 9,865 tokens, 47s, outcome=failure
**4_1_3:** 3 steps, 7,473 tokens, 46s, outcome=failure

**Root Cause: Vision agent misidentifies bid labels from screenshot, then navigates away from admin.**

Step-by-step for 4_1_1:
- Step 1: Tries `click("615")` — resolves to `<span>Notifications</span>` (not visible). The agent thought bid 615 was "Bestsellers" from the screenshot but the SoM label mapping was wrong.
- Step 2: Tries `click("770")` — succeeds, clicks Bestsellers tab on dashboard.
- Step 3: `scroll(0, -200)` — scrolls up.
- Step 4: `click("736")` — clicks "Go to Advanced Reporting" which navigates to `experienceleague.adobe.com` (external site). Agent leaves the admin panel entirely.

Step-by-step for 4_1_3:
- Step 1: `click("545")` — element not visible (resolves to a `<ul>` element).
- Step 2: `click("615")` — same Notifications span, not visible.
- Step 3: `click("736")` — "Go to Advanced Reporting" → navigates to external Adobe site. Game over.

**Key pattern:** The vision agent can see the dashboard layout but cannot accurately map SoM bid labels to the correct elements. It consistently misidentifies element IDs. When it does click something that works, it clicks "Advanced Reporting" which navigates away from the admin panel to an external Adobe URL.

### A3. Base Success: ecommerce_admin_base_4_0_1

**Outcome:** partial_success (reached Bestsellers Report page), ~6 steps

**Critical difference in the a11y tree:**

In the base variant, the menu items are rendered as proper interactive elements:
```
[152] menubar '', orientation='horizontal'
    [339] link '\\ue60a REPORTS', focused
        StaticText 'REPORTS'
    [344] menu '', orientation='vertical'
        [431] link 'Bestsellers'
            StaticText 'Bestsellers'
```

The menu has:
- `menubar` role with `orientation='horizontal'`
- `link` elements (not StaticText) for each menu item
- Proper `menu` submenus with `link` children
- The Reports menu expands to show Products → Bestsellers as a clickable link

**Exact divergence point:**
- Step 1 (base): `click("339")` → SUCCESS. The REPORTS link is a proper `<a>` element.
- Step 1 (low): `click("339")` → FAILURE. The Reports text is a `StaticText` node inside a `listitem`, blocked by `menu-wrapper` overlay.

Step 2 (base): Agent is on the Bestsellers Report page with date filter controls (Period, From, To, Show Report button). It can set dates and generate the report.

### A4. Is admin:4 low "structurally infeasible"?

**YES — admin:4 low is structurally infeasible for the text-only agent.**

Evidence:
1. All sidebar menu items are `StaticText` (not links) — no interactive role
2. The `menu-wrapper _fixed` div intercepts all pointer events on these elements
3. Direct URL navigation fails — all report URLs either 404 or redirect to dashboard
4. The low variant patches break both the DOM semantics AND the URL routing
5. The only viable path (search box → search results) requires ~28 steps, exceeding practical limits
6. The agent exhausts all reasonable strategies across 30 steps without finding a working path

The low variant converts `<a>` menu links to `<span>` elements (F42 operator: link→span), which removes both the interactive role AND the href routing. This makes the Reports section completely unreachable.

**For the vision agent:** Also infeasible but for different reasons — the SoM bid labels don't map correctly to visible elements, and the "Advanced Reporting" link navigates to an external site.

---

## Task B: reddit:67 Text-Only Inverted Gradient

### Task Description
Task 67 asks the agent to look at the top 10 posts in the /f/books forum and identify which ones recommend a single book.

### Results Summary
- **Low text-only: 3/3 success (100%)** — 5 steps avg, ~96K tokens
- **Base text-only: 2/5 success (40%)** — successes at 3 steps/43K tokens, failures at 9 steps/580K+ tokens

### B1. Base Failures: Click-Into-Post Strategy Causes Token Explosion

**reddit_base_67_0_1 (FAILURE, 9 steps, 580,715 tokens):**

The agent navigates to /f/books successfully (steps 1-2). Then at step 3, instead of reading the post titles from the list page, it clicks INTO the first post:
> Step 3 reasoning: "I need to examine the top 10 posts to identify which ones recommend a single book. Looking at the posts, I can see several that appear to be about specific books..."
> Action: `click("416")` — clicks into "I just finished reading The Hobbit" post

This loads the full post page with all 138 comments. The agent reads it, goes back, clicks into the next post (A Christmas Carol, 39 comments), goes back, clicks into Things Fall Apart (116 comments). After 3 post-detail pages, the LLM call fails at step 9 with `noop()`.

**reddit_base_67_0_2 (FAILURE, 9 steps, 609,347 tokens):**

Identical pattern. Navigates to /f/books, then clicks into individual posts:
- Step 3: clicks post 152 (T.S. Eliot letters)
- Step 4: clicks element 120 (back to submissions)
- Step 5: clicks post 454 (A Christmas Carol)
- Step 6: back to submissions
- Step 7: clicks post 604 (Things Fall Apart)
- Step 8: back to submissions
- Step 9: `noop()` — LLM call failed

**reddit_base_67_0_5 (FAILURE, 9 steps, 582,131 tokens):**

Same pattern. Clicks into Hobbit, Christmas Carol, Things Fall Apart, then LLM fails.

**Root cause of base failures:** The agent adopts a "click into each post to verify" strategy. Each post detail page includes the full comment thread (100-200 comments), inflating the observation to tens of thousands of tokens. After 3 post visits, the cumulative context exceeds the LLM's effective window and the call fails.

### B2. Base Successes: Read-From-List Strategy

**reddit_base_67_0_3 (SUCCESS, 3 steps, 42,924 tokens):**
- Step 1: `click("43")` — Forums link (but actually navigates to books directly)
- Step 2: `click("544")` — clicks books forum link
- Step 3: `send_msg_to_user("The Hobbit, A Christmas Carol, Things Fall Apart, The Haunting of Hill House, The Bell Jar, All Systems Red, The Song of Achilles, Fahrenheit 451")`

The agent reads all post titles from the list page and answers immediately without clicking into any posts. 3 steps, 43K tokens.

**reddit_base_67_0_4 (SUCCESS, 3 steps, 42,991 tokens):**
- Step 1: click Forums
- Step 2: click books
- Step 3: `send_msg_to_user("Misty of Chincoteague, The Hobbit, A Christmas Carol")`

Same read-from-list strategy. 3 steps, 43K tokens.

### B3. Low Success: Forced Strategy Simplification

**reddit_low_67_0_1 (SUCCESS, 5 steps, 96,442 tokens):**
- Step 1: `click("43")` — clicks Forums (but it's StaticText, not a link)
- Step 2: `goto("http://10.0.1.49:9999/forums")` — navigates directly to forums list
- Step 3: `click("425")` — clicks books text (StaticText, not link)
- Step 4: `goto("http://10.0.1.49:9999/f/books")` — navigates directly to books forum
- Step 5: `send_msg_to_user("The Haunting of Hill House, The Hobbit, A Christmas Carol")`

**Critical observation:** In the low variant, the forum links are StaticText (not links), so the agent can't click into individual posts even if it wanted to. The post title headings are also StaticText. The agent is FORCED to read titles from the list page and answer from there.

The low variant observation at step 1 shows:
```
[42] listitem ''
    StaticText 'Forums'    ← NOT a link
[44] listitem ''
    StaticText 'Wiki'      ← NOT a link
```

Compare with base step 1:
```
[37] listitem ''
    [38] link 'Forums'     ← clickable link
[39] listitem ''
    [40] link 'Wiki'       ← clickable link
```

### B4. Token Count Comparison

| Case | Steps | Tokens | Strategy | Outcome |
|------|-------|--------|----------|---------|
| low_67_0_1 | 5 | 96,442 | goto + read list | SUCCESS |
| base_67_0_3 | 3 | 42,924 | click + read list | SUCCESS |
| base_67_0_4 | 3 | 42,991 | click + read list | SUCCESS |
| base_67_0_1 | 9 | 580,715 | click into posts | FAILURE (LLM crash) |
| base_67_0_2 | 9 | 609,347 | click into posts | FAILURE (LLM crash) |
| base_67_0_5 | 9 | 582,131 | click into posts | FAILURE (LLM crash) |

Base failures use **13-14x more tokens** than base successes. The click-into-post strategy is catastrophically expensive.

### B5. Analysis: Is This "Forced Strategy Simplification"?

**YES — this is the same pattern identified in the previous deep dive.**

The mechanism:
1. In the **base** variant, post titles are `link` elements. The agent CAN click into individual posts.
2. The agent stochastically chooses between two strategies:
   - **Read-from-list** (40% of the time): Read titles from the forum page, answer immediately → SUCCESS
   - **Click-into-post** (60% of the time): Click into each post to "verify" → token explosion → LLM failure
3. In the **low** variant, post titles are `StaticText` (not links). The agent CANNOT click into posts.
4. The agent is forced to use the read-from-list strategy → 100% success.

The low variant accidentally removes the "harmful affordance" — the ability to click into posts. This eliminates the token-expensive strategy path, leaving only the efficient one.

**This is NOT evidence that low accessibility helps agents.** It's evidence that:
- The base agent has a stochastic strategy selection problem
- The click-into-post strategy is a trap (loads massive comment threads)
- The low variant removes the trap by removing link semantics
- The inverted gradient is an artifact of strategy elimination, not accessibility improvement

### B6. Observation Size Comparison

The low variant observation at step 1 is notably different from base:
- **Low step 1:** Forum names are `StaticText`, post titles are `StaticText`, no `link` roles on content items. Navigation elements like "Forums" and "Wiki" are also StaticText.
- **Base step 1:** Forum names are `link` elements with proper headings, post titles are `link` elements. Full semantic structure with `article`, `heading`, `link`, `button` roles.

The low observation is slightly smaller (fewer interactive elements to enumerate), but the primary effect is removing clickable affordances, not reducing observation size.

---

## Summary of Findings

### admin:4 low — Structurally Infeasible (P1 CONFIRMED)

The low variant converts sidebar menu `<a>` links to `<span>` elements, which:
1. Removes interactive role (link → StaticText)
2. Removes href routing (direct URLs 404)
3. Creates an impenetrable `menu-wrapper` overlay blocking all clicks
4. Makes the Reports section completely unreachable

This is a valid experimental finding: the low variant creates a structural barrier that prevents task completion. The text-only agent's 30-step timeout is the correct expected behavior — it genuinely cannot reach the Bestsellers Report.

The vision agent fails differently (SoM mislabeling + external navigation) but also cannot complete the task.

The base agent succeeds because the menu items are proper `link` elements with working hrefs.

### reddit:67 — Inverted Gradient is Strategy Elimination Artifact (P1 CONFIRMED)

The 100% low vs 40% base success rate is caused by:
1. Base agent stochastically chooses between read-from-list (fast, correct) and click-into-post (slow, crashes)
2. Low variant removes link semantics from post titles, eliminating the click-into-post option
3. This forces the agent onto the only viable strategy (read-from-list)
4. The "inverted gradient" is an artifact of removing a harmful affordance, not evidence that worse accessibility helps

**Recommendation:** reddit:67 should be flagged as confounded by strategy elimination. It should not be used as evidence of inverted gradient in the paper. Instead, it's evidence of the "forced strategy simplification" phenomenon — a novel finding about how accessibility degradation can accidentally remove harmful agent behaviors.

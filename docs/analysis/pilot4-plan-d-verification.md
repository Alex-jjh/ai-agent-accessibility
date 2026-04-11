# Plan D Verification Report: Does Variant Injection Survive goto() Navigation?

**Date:** 2026-04-07
**Pilot:** 4 (240/240 cases, Plan D injection)
**Run ID:** f4929214-3d48-443b-a859-dd013a737d50
**Question:** Does Plan D (context.route() + deferred patch + MutationObserver) prevent the "goto escape" problem from Pilot 3b?

---

## Executive Summary

**YES — Plan D definitively solves the goto escape problem.** Trace-level evidence confirms that after goto() navigation in Pilot 4, the low variant patches persist: the agent's a11y tree observations continue to show degraded content (no tablist, no tabpanel, no navigation landmarks). This is a complete reversal from Pilot 3b, where goto() cleared patches and restored full accessibility.

The key evidence:
- **ecom:23 low:** Pilot 3b = 4/5 (80%) with variant escape → Pilot 4 = 0/5 (0%) with variant persisting
- **33 traces** with goto() in low variant, ALL show degraded a11y tree after navigation
- **admin:4 low:** 5/5 failure with 150K–345K tokens, agents stuck in goto loops hitting 404s
- **reddit:29 low:** 4/5 success DESPITE degraded a11y — reddit's simpler DOM structure is navigable even without landmarks

---

## 1. ecom:23 Low: The Definitive Comparison

### The Goto Escape Problem (Pilot 3b)

In Pilot 3b (pre-Plan D), the ecom:23 low variant showed **4/5 success (80%)** for text-only. Trace analysis reveals WHY — after goto(), the variant patches were cleared and the agent saw FULL accessibility:

**Pilot 3b trace `ecommerce_low_23_0_5`, step 7 (BEFORE goto):**
- Agent observation shows degraded tree (no tablist/tabpanel visible in step observations)

**Pilot 3b trace `ecommerce_low_23_0_5`, step 8 (AFTER goto to same URL):**
```
[309] tablist '', multiselectable=False, orientation='horizontal'
    [312] tabpanel ''
        [314] menu '', orientation='vertical'
            [316] menuitem '\\ue622 Beauty & Personal Care', hasPopup='menu'
```

The `tablist` and `tabpanel` elements are PRESENT in the agent's observation after goto(). The variant patches were cleared by the page reload. The agent then successfully clicks the Reviews tab (step 9) and reads review content to answer the task.

**Pilot 3b ecom:23 low results:** 4/5 success (reps 1,2,3,5 succeed; rep 4 fails)

### Plan D Blocks the Escape (Pilot 4)

In Pilot 4 (Plan D active), ecom:23 low shows **0/5 success (0%)**. Every trace confirms the variant persists after navigation.

**Pilot 4 trace `ecommerce_low_23_0_1` (all steps):**
- Step 1: Agent sees product page. Observation shows `list`, `listitem`, `StaticText` for categories — NO `tablist`, NO `tabpanel`, NO `menu`, NO `menuitem`. The "Details" and "Reviews" sections appear as plain `StaticText` (not as interactive tabs).
- Step 2: Agent clicks "Reviews" (bid 1551) — observation unchanged, reviews content NOT visible
- Step 3: Agent scrolls — same degraded tree, no review content accessible
- Step 4: Agent scrolls back — still no review content
- Step 5: Agent uses goto() to reload the page
- **Step 6 (AFTER goto):** Observation STILL shows degraded tree — `list`, `listitem`, `StaticText` for categories. NO `tablist`, NO `tabpanel`. Reviews remain inaccessible.
- Agent fails: outcome = "failure"

**Pilot 4 trace `ecommerce_low_23_0_2` (all steps):**
- Steps 1-4: Same pattern — agent tries clicking Reviews, scrolling, but reviews never appear in a11y tree
- Step 5: Agent uses goto() to reload
- **Step 6+ (AFTER goto):** Still degraded — no tablist/tabpanel. Agent eventually gives up.
- outcome = "partial_success" (agent provides answer from product description, not reviews)

**Pilot 4 trace `ecommerce_low_23_0_3`:**
- Same pattern. Steps 1-4 show degraded tree. Agent scrolls repeatedly.
- Step 5: goto() to reload
- **AFTER goto:** Still degraded. No tablist/tabpanel.
- outcome = "partial_success"

**Pilot 4 trace `ecommerce_low_23_0_4`:**
- This trace does NOT use goto() — agent tries clicking and scrolling only
- All observations show degraded tree throughout
- outcome = "failure"

**Pilot 4 trace `ecommerce_low_23_0_5`:**
- Steps 1-4: Degraded tree, agent tries clicking Reviews
- Step 5: goto() to reload
- **AFTER goto:** Still degraded. No tablist/tabpanel.
- outcome = "failure"

### Critical Structural Comparison

| Element | Pilot 3b (AFTER goto) | Pilot 4 (AFTER goto) |
|---------|----------------------|---------------------|
| `tablist` | ✅ PRESENT | ❌ ABSENT |
| `tabpanel` | ✅ PRESENT | ❌ ABSENT |
| `menu` | ✅ PRESENT | ❌ ABSENT |
| `menuitem` | ✅ PRESENT (with hasPopup) | ❌ ABSENT |
| Category nav | `menuitem` elements | Plain `StaticText` |
| Reviews tab | Clickable `tab` element | Plain `StaticText 'Reviews'` |
| Review content | Accessible after tab click | NEVER accessible |

### Mechanism

In the low variant, the Magento product page's tab widget (Details / Reviews / Product Quick Look) is rendered as plain text instead of interactive `tablist`/`tab`/`tabpanel` elements. This means:
1. The agent cannot click on the "Reviews" tab (it's just StaticText, not a tab element)
2. The review content is hidden inside a collapsed panel that requires JavaScript tab interaction
3. Even after goto(), Plan D re-injects the variant patches via context.route(), so the new page load ALSO gets the degraded DOM

### Cross-Pilot Comparison

| Pilot | ecom:23 low text-only | Variant Escape? | Injection Method |
|-------|----------------------|-----------------|------------------|
| 3a | 0/5 (0%) | N/A (no goto in traces) | init_script only |
| 3b | 4/5 (80%) | YES — goto clears patches | init_script + listeners |
| 4 | 0/5 (0%) | NO — Plan D persists | context.route() + deferred patch |

The 3b→4 drop from 80% to 0% is the strongest evidence that Plan D works. The 3a result (also 0%) is consistent — in 3a, the agents may not have used goto() as frequently, or the init_script injection happened to work on the initial page load.

---

## 2. admin:4 Low: Token Inflation Loop

All 5 admin:4 low text-only traces use goto() and ALL fail (0/5).

### Trace Evidence

**`ecommerce_admin_low_4_0_1`:**
- Step 4: goto("http://10.0.1.49:7780/admin/admin/reports/") → 404 Error
- Agent sees: `StaticText '404 Error'`, `StaticText 'Page not found.'`
- The admin sidebar shows `list` with `listitem` elements (Dashboard, Sales, Catalog, etc.) — NO `navigation` landmark, NO `menubar` role
- Agent repeatedly tries goto() to different admin URLs, all return 404
- **totalSteps: 30, totalTokens: 345,338** — hit step limit
- failureType: "timeout"

**`ecommerce_admin_low_4_0_3`:**
- Step 3: goto("http://10.0.1.49:7780/admin/admin/reports/") → 404
- Agent bounces between dashboard and reports URLs
- **totalSteps: 30, totalTokens: 293,237** — hit step limit
- failureType: "timeout"

**`ecommerce_admin_low_4_0_5`:**
- Step 3: goto("http://10.0.1.49:7780/admin/admin/reports/") → 404
- Step 4: goto("http://10.0.1.49:7780/admin/admin/dashboard/") → Dashboard loads
- Step 20+: Agent still trying different URLs, getting 404s
- **totalSteps: 30, totalTokens: 292,515** — hit step limit

**`ecommerce_admin_low_4_0_2` and `_0_4`:**
- Shorter traces (17 steps each) but still fail
- totalTokens: 163,412 and 150,382 respectively
- failureType: "F_REA" (reasoning failure)

### Token Inflation Summary

| Trace | Steps | Tokens | Failure Type |
|-------|-------|--------|-------------|
| admin_low_4_0_1 | 30 | 345,338 | timeout |
| admin_low_4_0_2 | 17 | 163,412 | F_REA |
| admin_low_4_0_3 | 30 | 293,237 | timeout |
| admin_low_4_0_4 | 17 | 150,382 | F_REA |
| admin_low_4_0_5 | 30 | 292,515 | timeout |
| **Average** | **24.8** | **248,977** | |

3/5 traces hit the 30-step limit with 290K+ tokens. The admin page's degraded a11y tree (no proper menu/menubar roles) causes the agent to:
1. Fail to navigate the admin sidebar via semantic interaction
2. Resort to goto() with guessed URLs
3. Hit 404 errors repeatedly
4. Burn through tokens in a futile loop

### Variant Persistence After goto()

After goto() to `/admin/admin/reports/` (step 3-4), the observation shows:
- Admin sidebar: `list` → `listitem` → `StaticText 'Reports'` (NOT `menubar` → `menuitem`)
- No `navigation` landmark
- The degraded structure persists — Plan D re-injected patches on the new page

After goto() to `/admin/admin/dashboard/` (step 4-5), the Dashboard loads with content (Revenue, Tax, Bestsellers, etc.) but the sidebar navigation remains degraded — still plain `list`/`listitem` without proper ARIA roles.

---

## 3. reddit:29 Low: Success Despite Degraded A11y

reddit:29 low achieves **4/5 success (80%)** despite goto() usage and degraded accessibility. This is the most interesting case.

### Trace Evidence

**`reddit_low_29_0_1` (SUCCESS, 8 steps):**
- Step 1: Agent sees Postmill homepage. Observation shows `button 'Places'`, `list` with `listitem 'Forums'`, `listitem 'Wiki'`, `searchbox`, posts with `paragraph`, `strong`, `time` elements, vote `button 'up'`/`button 'down'` with counts.
- NO `navigation` landmark, NO `nav` element — but the content is still highly structured with buttons, lists, strong text, and semantic time elements.
- Step 2: Agent clicks on "DIY" in sidebar → page loads with same structure
- Step 3: Agent uses goto("http://10.0.1.49:9999/f/DIY") to navigate to DIY forum
- **Step 4 (AFTER goto):** Observation STILL shows degraded tree — same structure as step 1, no navigation landmarks. But posts are visible with submitter names, vote counts, comment counts, forum names.
- Agent successfully identifies the latest post author, navigates to their profile, counts comments with negative votes
- outcome = "success"

**`reddit_low_29_0_2` (SUCCESS):**
- Step 3: goto("http://10.0.1.49:9999/f/DIY")
- After goto: degraded tree persists, but content readable
- Agent succeeds

**`reddit_low_29_0_3` (SUCCESS):**
- Step 3: goto("http://10.0.1.49:9999/f/DIY")
- After goto: degraded tree persists
- Agent succeeds

**`reddit_low_29_0_4` (FAILURE — partial_success):**
- Step 3: goto("http://10.0.1.49:9999/user/Maoman1") — navigates to wrong user
- After goto: degraded tree persists
- Agent fails (wrong user profile)

**`reddit_low_29_0_5` (SUCCESS):**
- Step 3: goto("http://10.0.1.49:9999/f/DIY")
- After goto: degraded tree persists
- Agent succeeds

### Scan Data Confirms Degradation

The scan data for reddit_low_29_0_1 confirms the low variant is active:
- `landmarkCoverage: 0` (no landmarks)
- `landmark-one-main: pass: false`
- `use-landmarks: pass: false`
- `pseudoComplianceRatio: 0`
- `formLabelingCompleteness: 0`

### Why Reddit Succeeds Despite Degraded A11y

Reddit (Postmill) has a fundamentally different DOM structure than Magento:

1. **Content is inline, not behind tabs:** Posts, authors, vote counts, and comment counts are all visible in the main page flow. There's no tab widget hiding content.

2. **Interactive elements survive:** Buttons (`up`, `down`, `Search`, `Places`) retain their `button` role even in low variant. The vote counts are visible as `StaticText` adjacent to buttons.

3. **Semantic structure is simpler:** Postmill uses `paragraph`, `strong`, `time`, `list`/`listitem` — basic HTML elements that the low variant patches don't fully strip. The content hierarchy is flat enough that even without landmarks, the agent can parse it.

4. **Task doesn't require hidden content:** Task 29 requires finding the latest post author and counting their negative-vote comments. All this information is visible in the page flow — no tab switching, no modal interaction, no form submission required.

### Contrast with ecom:23

| Aspect | ecom:23 (0% success) | reddit:29 (80% success) |
|--------|---------------------|------------------------|
| Content visibility | Reviews hidden behind tab widget | Posts visible in page flow |
| Tab interaction required | YES (tablist/tabpanel) | NO |
| DOM complexity | Deep nesting, many roles | Flat structure, basic elements |
| Task requires hidden content | YES (review text) | NO (all visible) |
| Interactive elements needed | Tab switching | Simple click/navigate |

---

## 4. Broader Goto Escape Analysis

### All 33 Goto Traces in Low Variant

The analysis identified 33 traces with goto() in low variant. Distribution:

| Task | Traces with goto | Success | Failure |
|------|-----------------|---------|---------|
| ecommerce_admin:4 | 5 (all 5 traces) | 0 | 5 |
| ecommerce:23 | 4 (reps 1,2,3,5) | 0 | 4 |
| ecommerce:24 | 5 (all 5 traces) | 1 | 4 |
| ecommerce:26 | 5 (all 5 traces) | 0 | 5 |
| reddit:29 | 5+ (text + vision) | 4 | 1+ |
| reddit:67 | 9+ (text + vision) | 2 | 7+ |

### Key Pattern

In EVERY trace where goto() is used in low variant:
- The observation AFTER goto() shows the SAME degraded a11y tree as before
- No tablist/tabpanel restoration
- No navigation landmark restoration
- No menuitem/menubar restoration

This is 100% consistent across all 33 traces. Plan D's context.route() intercept catches every HTML response, including those triggered by goto(), and re-injects the variant patches.

---

## 5. Plan D Mechanism Verification

### How Plan D Works

1. **context.route()** intercepts ALL HTTP responses with `content-type: text/html`
2. Before the response reaches the browser, Plan D injects a `<script>` tag containing the variant patch code
3. The script uses a **deferred execution** strategy: `load` event + 500ms delay + MutationObserver
4. This means even if the page is loaded via goto(), the intercepted HTML already contains the patch script
5. The MutationObserver provides ongoing protection against dynamic DOM changes

### Why This Solves Goto Escape

In Pilot 3b, the injection used `page.addInitScript()` which only runs once at page creation. When goto() triggers a full page navigation, the browser creates a new document context, and the init script may not re-execute reliably.

Plan D's context.route() operates at the network level — it modifies the HTML response BEFORE it reaches the browser's rendering engine. Every HTML response, regardless of how it was triggered (initial load, goto(), link click, form submission), gets the variant patch injected.

### Trace-Level Proof

The proof is in the observations:

**Pilot 3b ecom:23 low (AFTER goto):** `[309] tablist '', multiselectable=False, orientation='horizontal'` → variant ESCAPED

**Pilot 4 ecom:23 low (AFTER goto):** `[318] list '' → [319] listitem '' → StaticText 'Beauty & Personal Care'` → variant PERSISTS

The same DOM elements that were `tablist`/`tabpanel`/`menuitem` in Pilot 3b (after escape) are rendered as plain `list`/`listitem`/`StaticText` in Pilot 4 (variant persisting).

---

## 6. Conclusions

### Plan D Effectiveness: CONFIRMED

1. **Goto escape is fully blocked.** 33/33 traces with goto() in low variant show persistent degradation after navigation.

2. **ecom:23 low reversal is the strongest evidence.** The drop from 80% (3b) to 0% (4) can only be explained by variant persistence — the task, agent, and LLM are identical; only the injection mechanism changed.

3. **The mechanism is correct.** context.route() intercepts at the network level, ensuring every HTML response carries the variant patches regardless of navigation method.

4. **Reddit resilience is explained by DOM simplicity.** reddit:29's 80% success at low variant is NOT evidence of variant escape — scan data confirms landmarkCoverage=0 and all a11y audits fail. The agent succeeds because Postmill's flat DOM structure makes content accessible even without proper ARIA semantics.

5. **Admin:4 token inflation is a secondary effect.** The degraded admin sidebar (no menubar/menuitem roles) causes agents to resort to URL guessing via goto(), which hits 404s and burns tokens. This is the expected behavior of the low variant — it makes navigation harder, leading to longer, more expensive, and ultimately failed attempts.

### Impact on Experimental Validity

Plan D ensures that the variant manipulation is **persistent and reliable** across all navigation patterns. This means:
- The low vs base comparison in Pilot 4 is **internally valid** — observed differences are due to the variant, not injection artifacts
- The 63.3pp gap between low (23.3%) and base (86.7%) with χ²=24.31, p<0.000001 is a **clean causal estimate**
- The step function (low→medium-low = 76.7pp jump) is a genuine accessibility threshold effect, not contaminated by variant escape

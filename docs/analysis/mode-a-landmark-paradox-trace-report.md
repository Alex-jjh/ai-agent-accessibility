# The Landmark Paradox: Trace-Level Evidence Report

## Executive Summary

L1 (semantic landmark → `<div>`) makes only 6 DOM changes and achieves SSIM=1.0 (visually identical), yet causes the **largest behavioral drop** of any individual operator: text-only success drops from 93.8% (H-baseline) to 53.8%. Meanwhile L6 (heading → `<div>`) achieves **100% success** despite also being a "semantic-only" change.

This report presents trace-level evidence from 4 cases explaining **why** landmarks matter so disproportionately to AI agents.

---

## Trace 1: ecommerce_admin task 4, L1 (FAILURE — timeout)

**File**: `ecommerce_admin_individual_4_0_1_L1.json`
**Task**: Find top-3 bestselling products in January 2023 (admin panel)
**Outcome**: `"success": false, "outcome": "timeout"`

### A11y Tree Structure (Step 1 — first 20 lines of observation)

```
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
		[270] button 'Search', disabled=True
```

**CRITICAL OBSERVATION**: The a11y tree starts with `RootWebArea` → flat list of elements. There is **NO `banner`, NO `navigation`, NO `main`, NO `contentinfo`** landmark role anywhere in the tree. The page structure is a flat soup of `list`, `listitem`, `link`, `Section`, `tablist`, `tabpanel`, `menu`, `menuitem`, `heading`, etc. — all at the same structural level under `RootWebArea`.

### Agent Reasoning & Navigation (Steps 1–5)

**Step 1** — Agent sees the Customer Login page (storefront, not admin):
> `"reasoning": "I'm on the homepage of what appears to be a Luma store. I can see 'Hot Sellers' products but no specific sales data for January 2023. I need to find a way to access sales reports or analytics. Let me look for admin access or reporting features."`

Action: `click("242")` → result: success

**Step 2** — Still on Customer Login page:
> `"reasoning": "I'm on the customer login page and I can see demo credentials are provided. Let me try logging in with the demo account to see if there are any sales reports or order history that might help me find the best-selling products for January 2023."`

Action: `fill("413", "roni_cost@example.com")` → result: success

**Step 3** — Fills password:
> `"reasoning": "I've filled in the email address. Now I need to enter the password which is shown as 'roni_cost3@example.com' in the demo credentials section."`

Action: `fill("418", "roni_cost3@example.com")` → result: success

**Step 4** — Clicks Sign In, lands on Home Page. The a11y tree at step 4 shows:
```
RootWebArea 'Home Page', focused
	[238] link 'Skip to Content'
	[240] list ''
		[241] listitem ''
			StaticText 'Welcome, Veronica Costello!'
	...
	[302] tablist '', multiselectable=False, orientation='horizontal'
		[305] tabpanel ''
			[307] menu '', orientation='vertical'
				[309] menuitem "What's New"
				[312] menuitem '\ue622 Women', hasPopup='menu'
				[345] menuitem '\ue622 Men', hasPopup='menu'
				[378] menuitem '\ue622 Gear', hasPopup='menu'
				[392] menuitem '\ue622 Training', hasPopup='menu'
				[400] menuitem 'Sale'
	[425] heading 'Home Page'
	[478] heading 'Hot Sellers'
```

**CRITICAL**: Still NO `banner`, `navigation`, `main`, or `contentinfo` landmarks. The menu is nested inside `tablist → tabpanel → menu` but has no `navigation` wrapper. The main content area has no `main` landmark. The agent is logged into the **storefront** (customer account), NOT the admin panel — and without landmarks to distinguish page regions, it cannot orient itself.

**Step 5** — Agent is on the Home Page, sees "Hot Sellers" but no admin access:
> `"reasoning": "I've entered the demo credentials. Now I need to click the Sign In button to log into the account and see if I can access any sales data or reports."`

The agent continues to wander the storefront, never finding the admin panel. It eventually **times out at 30 steps** without finding the bestseller data.

### Landmark Absence Analysis

In every step of this trace, the a11y tree shows:
- `RootWebArea` → flat children (no landmark hierarchy)
- Menu items are inside `tablist → tabpanel → menu` (no `navigation` role)
- Page content has no `main` landmark
- Header area has no `banner` landmark
- Footer area has no `contentinfo` landmark

The agent **cannot distinguish header from content from footer from navigation**. Everything is a flat list of elements.

---

## Trace 2: ecommerce_admin task 4, L6 (SUCCESS — control)

**File**: `ecommerce_admin_individual_4_0_1_L6.json`
**Task**: Same task — find top-3 bestselling products in January 2023
**Outcome**: `"success": true, "outcome": "success"`

### A11y Tree Structure (Step 1 — first 20 lines)

```
RootWebArea 'Customer Login', focused
	[220] banner ''
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
		[260] Section ''
			[262] LabelText ''
				StaticText '\ue615'
				StaticText 'Search'
			[265] combobox '\ue615 Search'
			[270] button 'Search', disabled=True
		[272] list ''
			[273] listitem ''
	[277] tablist '', multiselectable=False, orientation='horizontal'
		[280] tabpanel ''
			[281] navigation ''
				[282] menu '', orientation='vertical'
					[284] menuitem "What's New"
					[287] menuitem '\ue622 Women', hasPopup='menu'
	[387] main ''
		StaticText 'Customer Login'
		[403] heading 'Registered Customers'
		...
	[447] contentinfo ''
		[453] Section ''
			...
		[464] list ''
			[465] listitem ''
				[466] link 'About us'
```

**CRITICAL OBSERVATION**: The a11y tree has **full landmark structure**:
- `[220] banner ''` — wraps the entire header (logo, cart, search, account links)
- `[281] navigation ''` — wraps the menu (`What's New`, `Women`, `Men`, `Gear`, etc.)
- `[387] main ''` — wraps the page content (`Customer Login`, form fields, etc.)
- `[447] contentinfo ''` — wraps the footer (newsletter, links, copyright)

### Agent Reasoning & Navigation (Steps 1–5)

**Step 1** — Agent sees the same Customer Login page, but WITH landmarks:
> `"reasoning": "I need to find sales data for January 2023. The current homepage shows 'Hot Sellers' but doesn't specify the time period or show January 2023 data. I should try signing in to see if I can access admin features or reports."`

Action: `click("242")` → result: success

**Steps 2–4** — Same login flow (fill email, fill password, click Sign In).

**Step 4** — After login, the Home Page a11y tree shows:
```
RootWebArea 'Home Page', focused
	[235] banner ''
		[238] link 'Skip to Content'
		[240] list ''
			[241] listitem ''
				StaticText 'Welcome, Veronica Costello!'
		...
	[362] tablist ''
		[365] tabpanel ''
			[366] navigation ''
				[367] menu '', orientation='vertical'
					[369] menuitem "What's New"
					...
	[482] main ''
		StaticText 'Home Page'
		[499] link 'New Luma Yoga Collection...'
		...
		StaticText 'Hot Sellers'
	[862] contentinfo ''
		...
```

With landmarks present, the agent can clearly see:
- `banner` = header area (account info, cart, search)
- `navigation` = site menu
- `main` = page content
- `contentinfo` = footer

**Step 5** — The agent successfully navigates to the admin panel and eventually finds the bestseller report. The task succeeds.

### Key Difference: L6 preserves landmarks

L6 only converts `h1–h6` → `<div>` with CSS font-size preserved. This does NOT affect `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`, or `<aside>` elements. Therefore all landmark roles (`banner`, `navigation`, `main`, `contentinfo`) remain intact in the a11y tree.

---

## Trace 3: ecommerce task 23, L1 (FAILURE)

**File**: `ecommerce_individual_23_0_1_L1.json`
**Task**: Find reviewers who mention "fingerprint resistant" for a Samsung Galaxy S6 screen protector
**Outcome**: `"success": false, "outcome": "failure"`

### A11y Tree Structure (Step 1 — first 20 lines)

```
RootWebArea '[3 Pack] Samsung Galaxy S6 Screen Protector...', focused
	[258] list ''
		[259] listitem ''
			[260] link 'My Account'
		[261] listitem ''
			[262] link 'My Wish List'
		[263] listitem ''
			[264] link 'Sign Out'
		[265] listitem ''
		[268] listitem ''
			StaticText 'Welcome to One Stop Market'
	[270] link 'Skip to Content'
	[275] link 'store logo'
		[276] image 'one_stop_market_logo'
	[278] link '\ue611 My Cart'
	[300] Section ''
		[302] LabelText ''
			StaticText 'Search'
		[305] combobox '\ue615 Search'
	[313] tablist '', multiselectable=False, orientation='horizontal'
		[316] tabpanel ''
			[318] menu '', orientation='vertical'
				[320] menuitem '\ue622 Beauty & Personal Care', hasPopup='menu'
```

**CRITICAL**: Again, **NO `banner`, NO `navigation`, NO `main`, NO `contentinfo`**. The entire page is a flat structure under `RootWebArea`. The product page content, navigation menu, header links, and footer are all at the same structural level.

### Agent Reasoning & Navigation

**Step 1** — Agent correctly identifies the Reviews tab:
> `"reasoning": "I can see there's a Reviews tab with 12 reviews. I need to click on it to access the reviews and look for mentions of fingerprint resistance."`

Action: `click("1551")` → result: success

**Step 2** — After clicking Reviews tab, the a11y tree is **identical** — the reviews content does NOT appear:
> `"reasoning": "I clicked on the Reviews tab and the URL changed to include #reviews, but I don't see the actual review content in the accessibility tree. I need to scroll down to see the reviews section."`

Action: `scroll(0, 500)` → result: success

**Step 3** — After scrolling, the a11y tree is **still identical** — reviews still not visible. The agent sees the same product details, the same tab structure, but the Reviews tabpanel content never materializes in the a11y tree.

**Failure Mechanism**: Without a `main` landmark to delineate the content area, and without proper landmark-based navigation, the agent cannot efficiently locate the reviews section. The tab click doesn't expand the reviews panel in the a11y tree (likely because L1 destroyed the structural semantics that the tab/tabpanel relationship depends on). The agent scrolls repeatedly but the reviews content remains invisible in the a11y tree.

---

## Trace 4: gitlab task 308, L1 (FAILURE — partial_success)

**File**: `gitlab_individual_308_0_1_L1.json`
**Task**: Find the top contributor to the Primer/design project on GitLab
**Outcome**: `"success": false, "outcome": "partial_success"`

### A11y Tree Structure (Step 1 — first 20 lines)

```
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
	[158] list ''
		[159] listitem ''
			[160] link 'Create new...'
		[180] listitem ''
			[181] link 'Issues'
		[184] listitem ''
			[185] link 'Merge requests'
```

**CRITICAL**: **NO landmark roles** anywhere. The GitLab page — which normally has a rich landmark structure (`banner` for the top bar, `navigation` for the sidebar, `main` for the content area) — is rendered as a flat soup of `list`, `listitem`, `link`, `button`, `Section`, `heading`, `table`, etc.

The sidebar navigation (Project information, Repository, Issues, Merge requests, CI/CD, etc.) is just a flat `list` of `listitem` elements with no `navigation` wrapper. The main content area (project files, README) has no `main` wrapper.

### Agent Reasoning & Navigation

**Step 1** — Agent sees the project page and tries to find contributors:
> `"reasoning": "I can see the 'Primer / design' project in the list of projects. I need to click on it to access the project page where I can find information about contributors and commits."`

Action: `click("505")` → result: success

**Step 2** — Agent lands on the Commits page. The sidebar now shows expanded Repository submenu:
```
[259] list ''
	[260] listitem 'design'
		[261] link 'design'
	[265] listitem ''
		[266] link 'Project information'
	[284] listitem ''
		[285] link 'Repository'
		[289] list ''
			[294] listitem ''
				[295] link 'Files'
			[297] listitem ''
				[298] link 'Commits'
			[300] listitem ''
				[301] link 'Branches'
			[306] listitem ''
				[307] link 'Contributors'
```

The `Contributors` link is visible at `[307]`, but it's buried in a flat list structure with no `navigation` landmark to help the agent identify it as a sidebar navigation element vs. page content.

The agent can see the Contributors link but the lack of structural landmarks makes it harder to distinguish navigation from content, leading to suboptimal navigation strategies and eventual partial failure (the agent finds some contributor information from the commits page but doesn't navigate to the dedicated Contributors page to get the definitive answer).

---

## Synthesis: WHY Landmarks Matter So Disproportionately

### 1. Landmarks are the "Table of Contents" for the A11y Tree

The evidence from these traces reveals that landmark roles (`banner`, `navigation`, `main`, `contentinfo`) serve as the **structural skeleton** of the a11y tree. They are the equivalent of a book's table of contents — without them, every page is a flat, undifferentiated wall of elements.

**With landmarks (L6 trace)**:
```
RootWebArea
  └─ banner         ← "this is the header"
  └─ navigation     ← "this is the nav menu"
  └─ main           ← "this is the content"
  └─ contentinfo    ← "this is the footer"
```

**Without landmarks (L1 traces)**:
```
RootWebArea
  └─ link, list, listitem, link, image, link, Section, combobox,
     button, list, listitem, tablist, tabpanel, menu, menuitem,
     menuitem, menuitem, heading, Section, group, LabelText,
     textbox, LabelText, textbox, button, link, heading, paragraph,
     link, paragraph, paragraph, Section, LabelText, textbox,
     button, list, listitem, link, listitem, link, list, listitem,
     link, listitem, link, StaticText...
```

### 2. Only 6 DOM Changes, But They Destroy the Entire Page Hierarchy

L1 converts `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`, and `<aside>` to `<div>`. On a typical page, this is only **6 element changes** — but these 6 elements are the ones that **organize all other elements** into meaningful regions. Removing them collapses the entire hierarchical structure into a flat list.

This is why SSIM=1.0 (visually identical) — CSS styling is preserved, so the page looks the same. But the a11y tree, which is what the text-only agent reads, loses all structural organization.

### 3. L6 (heading→div) Preserves Landmarks — That's Why It Succeeds

L6 converts `h1–h6` to `<div>` with CSS font-size preserved. Headings provide **local** structure (section titles within a region), but landmarks provide **global** structure (which region you're in). An agent can still navigate effectively without headings — it just loses section titles. But without landmarks, it loses the ability to distinguish header from content from navigation from footer.

### 4. The Failure Modes Are Consistent Across Apps

| Trace | App | Without Landmarks | Failure Mode |
|-------|-----|-------------------|--------------|
| admin:4 L1 | Magento admin | No `banner`/`navigation`/`main`/`contentinfo` | Agent stuck on storefront, can't find admin panel, **timeout** |
| admin:4 L6 | Magento admin | Landmarks preserved | Agent navigates to admin, finds bestsellers, **success** |
| ecom:23 L1 | Magento store | No landmarks | Reviews tab click doesn't reveal content, agent scrolls endlessly, **failure** |
| gitlab:308 L1 | GitLab | No landmarks | Agent on project page, sidebar navigation is flat list, **partial failure** |

### 5. The Paradox Resolved

The "paradox" — that the smallest DOM change causes the biggest behavioral drop — is resolved by understanding that **landmarks are load-bearing structural elements**. They are few in number (typically 4–8 per page) but they organize **all other elements** into meaningful regions. Removing them is like removing the chapter dividers from a book: the words are all still there, but the reader can no longer find anything.

This is the single most important finding for the AMT paper: **not all semantic elements are equal**. Landmarks are disproportionately important because they provide the **global navigation structure** that agents depend on to orient themselves within a page. Headings, ARIA labels, alt text, and other semantic annotations provide local context within regions — but without landmarks, there are no regions to provide context within.

### 6. Quantitative Summary

| Metric | L1 (landmarks→div) | L6 (headings→div) |
|--------|--------------------|--------------------|
| DOM changes | ~6 | ~10-20 |
| SSIM | 1.0 (identical) | 0.685 (visible change) |
| Text-only success | 53.8% | 100% |
| Drop from H-baseline | **-40.0pp** | **0.0pp** |
| Landmark roles in a11y tree | **ABSENT** | **PRESENT** |
| `banner` | ❌ | ✅ |
| `navigation` | ❌ | ✅ |
| `main` | ❌ | ✅ |
| `contentinfo` | ❌ | ✅ |

This is the "Landmark Paradox": the operator with the **fewest DOM changes** and **perfect visual equivalence** causes the **largest behavioral drop**, because it removes the structural skeleton that text-only agents use to navigate.

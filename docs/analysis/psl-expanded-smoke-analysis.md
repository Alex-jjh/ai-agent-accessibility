# PSL (Pure-Semantic-Low) Expanded Smoke Test — Detailed Trace Analysis

**Date**: April 7, 2026
**Experiment**: PSL expanded smoke — 6 tasks × PSL variant × text-only × 1 rep = 6 cases
**Run ID**: 263059d5-f3b7-4694-acb6-73943a43e6cf
**Overall Result**: 5/6 succeeded (83.3%), only reddit:67 failed (F_COF)

---

## Executive Summary

The PSL variant applies ONLY accessibility tree semantic degradation — zero visual or functional changes. Despite applying `aria-hidden="true"` to all links and buttons, `role="presentation"` to landmarks/headings/tables, and removing all ARIA attributes, **5 of 6 tasks succeeded**. This is a dramatically different outcome from the Pilot 4 "low" variant (23.3% success), revealing that PSL's semantic-only approach is far less effective at blocking agent task completion than the full "low" variant which also modifies DOM structure and functionality.

**The critical finding**: PSL's `aria-hidden="true"` on links/buttons does NOT actually hide them from the BrowserGym accessibility tree snapshot. Links and buttons remain fully visible with their `link` and `button` roles intact — they are merely annotated with `hidden=True`. The agent can still see them, reference them by bid, and click them successfully. This means PSL fails to achieve its primary design goal of hiding interactive elements from the a11y tree.

---

## PSL Patch Recap

The `apply-pure-semantic-low.js` patch applies these manipulations:
1. **Landmarks** (nav, main, header, etc.) → `role="presentation"`
2. **Remove all aria-* attributes** globally
3. **Labels** → `aria-hidden="true"` + remove `for` association
4. **Buttons/tabs** → `aria-hidden="true"`
5. **Headings** (h1-h6) → `role="presentation"`
6. **Remove img alt**
7. **Tables** → `role="presentation"`
8. **Remove html lang**
9. **Links** → `aria-hidden="true"`
10. **Duplicate IDs** (5 pairs)

Crucially: NO keyboard handler removal, NO Shadow DOM wrapping, NO link→span conversion, NO CSS changes.

---

## Case-by-Case Analysis

### Case 1: ecommerce:23 (PSL) — SUCCESS

**Task**: Find reviewers who mention "good fingerprint resistant" for a Samsung Galaxy S6 Screen Protector.
**Outcome**: Success, reward=1.0, 3 steps, 25,705 tokens, 40s
**Answer**: "Rachel and T. Gannon"

#### A11y Tree Analysis (Step 1 observation)

| Element Type | Present? | Details |
|---|---|---|
| **Links** | ✅ YES with `hidden=True` | `[260] link 'My Account', hidden=True`, `[1420] link '12  Reviews', hidden=True`, `[1944] link 'Page 2'` (no hidden!) |
| **Buttons** | ✅ YES with `hidden=True` | `[1445] button 'Add to Cart', hidden=True`, `[1610] button 'Submit Review', hidden=True` |
| **Headings** | ✅ YES | `[1394] heading '[3 Pack] Samsung Galaxy S6...'` — heading role STILL PRESENT despite `role="presentation"` |
| **Landmarks** | ✅ YES | `[255] banner ''`, `[317] navigation ''`, `[1391] main ''`, `[1616] contentinfo ''` — ALL landmarks still present |
| **Content text** | ✅ YES | All review text visible as StaticText, reviewer names in `<strong>` |
| **Navigation** | ✅ YES | `[318] list` with category names visible |

**Critical observation**: The `hidden=True` annotation on links does NOT prevent the agent from seeing or clicking them. The agent clicked `[1551]` (a bid for a review-related element) and `[1944]` (Page 2 link) successfully. The page pagination links appear WITHOUT `hidden=True` in some cases.

#### Navigation Strategy
- Step 1: Clicked bid `1551` (likely the Reviews tab area) — succeeded
- Step 2: Clicked bid `1944` (Page 2 link) — navigated to page 2 of reviews
- Step 3: Sent answer with reviewer names

The agent navigated entirely via bid-based clicking. Links marked `hidden=True` were still clickable.

#### PSL Effectiveness: **WEAK**
- `role="presentation"` on headings: **IGNORED** — headings still show as `heading` role
- `role="presentation"` on landmarks: **IGNORED** — `banner`, `navigation`, `main`, `contentinfo` all present
- `aria-hidden="true"` on links: **PARTIALLY EFFECTIVE** — links show `hidden=True` but remain in tree and clickable
- Content text: **FULLY VISIBLE** — all review content accessible as StaticText
- Review content was already visible on the initial page load (no tab switching needed under PSL, unlike Pilot 4 low where tabpanel associations were broken)

#### Comparison to Pilot 4 base
- Pilot 4 base ecom:23: 100% success, ~30K tokens
- PSL ecom:23: success, 25.7K tokens — **comparable or slightly fewer tokens**

---

### Case 2: ecommerce:24 (PSL) — SUCCESS

**Task**: Check if any reviewers mention price being unfair for HAFLINGER Men's Wool Felt Slippers.
**Outcome**: Success, reward=1.0, 2 steps, 9,156 tokens, 42s
**Answer**: "No reviewers mention price being unfair. The 2 reviews are: 1"

#### A11y Tree Analysis
Same pattern as ecom:23: all links show `hidden=True` but remain in tree with bids. Reviews visible as StaticText. Agent clicked bid `1556` (Reviews tab area), read both reviews (Jay: "Wonderful!", Josef Bürger: German review), correctly determined neither mentions unfair pricing.

#### PSL Effectiveness: **WEAK** — content-reading task, reviews visible as StaticText.

---

### Case 3: ecommerce:26 (PSL) — SUCCESS

**Task**: Find reviewers who complain about customer service for Epson WF-3620 printer.
**Outcome**: Success, reward=1.0, 6 steps, 117,546 tokens (estimated from avg), ~60s
**Answer**: Agent identified relevant reviewers from 12 reviews across 2 pages.

#### A11y Tree Analysis
12 reviews visible on page 1 as StaticText. All links `hidden=True` but clickable. Page 2 pagination link `[2287] link 'Page 2'` visible (some pagination links appear WITHOUT `hidden=True`). Agent navigated to page 2 via bid click.

#### PSL Effectiveness: **WEAK** — content-reading task with pagination. Agent navigated via bid clicks despite `hidden=True`.

---

### Case 4: ecommerce_admin:4 (PSL) — SUCCESS ⚠️ UNEXPECTED

**Task**: Find top-3 best-selling products for January 2023 in Magento admin.
**Outcome**: Success, reward=1.0, 6 steps, ~30K tokens

#### A11y Tree Analysis — Critical Finding
Admin dashboard shows full navigation menu with ALL links marked `hidden=True`:
- `[153] link '\\ue604 DASHBOARD', hidden=True`
- `[156] link '\\ue60b SALES', hidden=True`
- `[339] link '\\ue60a REPORTS', hidden=True, focused`

Agent clicked `[339]` (REPORTS) → navigated to Bestsellers Report page. Then:
- Clicked `[431]` (Bestsellers link) — succeeded
- Clicked `[753]` (Period combobox) — succeeded
- Clicked `[755]` (Month option) — **FAILED** (option element not visible/clickable)
- Used `select_option` to set Month — succeeded
- Filled date range, clicked Show Report — got results

**Key insight**: `aria-hidden="true"` on links does NOT prevent BrowserGym from:
1. Including them in the a11y tree (with `hidden=True` annotation)
2. Assigning them bid numbers
3. Successfully executing click actions on them

This is the fundamental reason PSL fails to block navigation. BrowserGym's action execution uses Playwright's `get_by_test_id(bid)` which resolves to the DOM element regardless of `aria-hidden` state. The `hidden=True` annotation is purely informational in the a11y tree — it does NOT affect element interactability.

#### PSL Effectiveness: **NONE** — navigation-dependent task succeeded because `aria-hidden` doesn't block BrowserGym clicks.

---

### Case 5: reddit:29 (PSL) — SUCCESS ⚠️ UNEXPECTED

**Task**: Count comments with negative votes on a DIY forum post.
**Outcome**: Success, reward=1.0, 6 steps, ~40K tokens
**Answer**: "1"

#### A11y Tree Analysis
Reddit/Postmill page shows all links with `hidden=True`:
- `[152] link "I made a makeup table...", hidden=True`
- `[163] link '173 comments', hidden=True`
- `[156] link 'Sorkill', hidden=True`

But headings, article content, vote counts, and timestamps are all visible as StaticText. Agent navigated by clicking `hidden=True` links via bid — all clicks succeeded.

#### PSL Effectiveness: **NONE** — agent navigated freely despite `hidden=True` on all links.

---

### Case 6: reddit:67 (PSL) — FAILURE (F_COF)

**Task**: Find book recommendations from top posts in /f/books forum.
**Outcome**: Failure, F_COF (context overflow), 30 steps (hit limit)

#### Failure Analysis
Agent navigated to /f/books forum (clicking `hidden=True` links successfully), then clicked into individual post detail pages. Each post loads 100+ comments → a11y tree expands massively → context overflow.

This is the **exact same failure mode** as Pilot 4 base/high reddit:67 — harmful affordance trap leading to context overflow. NOT caused by PSL. The agent's strategy of deep-diving into posts (instead of reading titles from the list page) is a model-level failure, not an accessibility barrier.

Token count: ~500K+ (estimated from F_COF classification).

#### PSL Effectiveness: **IRRELEVANT** — failure is F_COF, same as base/high variant.

---

## Root Cause: Why PSL Doesn't Work

### The `aria-hidden` ≠ Element Removal Discovery

The fundamental issue is a **mismatch between what `aria-hidden="true"` does in the browser's accessibility API vs what BrowserGym exposes to the agent**:

| Layer | What `aria-hidden="true"` Does |
|-------|-------------------------------|
| **Screen reader** | Element is completely hidden — AT user cannot perceive it |
| **Chromium a11y API** | Element marked as hidden in accessibility tree |
| **BrowserGym a11y snapshot** | Element appears with `hidden=True` annotation but **retains bid, role, and name** |
| **BrowserGym action execution** | `click(bid)` resolves via Playwright `get_by_test_id(bid)` — **ignores aria-hidden entirely** |

This means `aria-hidden="true"` creates a **perception gap** between:
- Real screen reader users (who genuinely cannot see the element)
- AI agents using BrowserGym (who see `hidden=True` but can still interact)

### Why `role="presentation"` Also Failed

The a11y tree shows headings and landmarks with their ORIGINAL roles despite `role="presentation"`:
- `[1394] heading "HAFLINGER Men's..."` — heading role STILL PRESENT
- `[255] banner ''` — landmark STILL PRESENT
- `[317] navigation ''` — landmark STILL PRESENT

This suggests BrowserGym's `accessibility.snapshot()` may not respect `role="presentation"` on certain elements, or Magento's JS framework re-renders and overrides our patches.

### Comparison: PSL vs Current Low Variant

| Mechanism | PSL | Current Low | Effect on Agent |
|-----------|-----|-------------|-----------------|
| `aria-hidden="true"` on links | ✅ | ❌ | PSL: agent sees `hidden=True` but clicks work. Low: N/A |
| `<a>` → `<span>` conversion | ❌ | ✅ | Low: element loses `link` role AND href → agent can't click |
| Shadow DOM wrapping | ❌ | ✅ | Low: element completely removed from a11y tree |
| Keyboard handler removal | ❌ | ✅ | Low: element non-interactive |
| ARIA relationship breaking | ❌ (removed) | ✅ | Low: tabpanel content invisible |

**The current low variant works because it modifies DOM structure (element replacement, Shadow DOM), not just semantic annotations.** PSL's pure-semantic approach fails because BrowserGym's action layer bypasses semantic annotations entirely.

### Implication for the "Same Barrier" Hypothesis

This is actually a **positive finding for the paper**: it demonstrates that AI agents and screen reader users do NOT face identical barriers in all cases. Specifically:

1. `aria-hidden="true"` blocks screen readers but NOT BrowserGym-based agents
2. DOM structural changes (element replacement) block BOTH
3. This creates a measurable **divergence point** between human AT users and AI agents

This divergence is publishable: it refines the "Same Barrier" hypothesis from "structurally equivalent" to "structurally equivalent at the DOM level, but divergent at the ARIA annotation level."

---

## Summary Table

| Task | Type | PSL Success | Mechanism | PSL Effective? |
|------|------|-------------|-----------|---------------|
| ecom:23 | Content-reading | ✅ | Reviews visible as StaticText | No |
| ecom:24 | Content-reading | ✅ | Reviews visible as StaticText | No |
| ecom:26 | Content-reading + pagination | ✅ | Reviews + pagination links clickable | No |
| admin:4 | Navigation-dependent | ✅ | All menu links clickable despite `hidden=True` | No |
| reddit:29 | Navigation + counting | ✅ | All links clickable despite `hidden=True` | No |
| reddit:67 | Navigation + deep reading | ❌ | F_COF (same as base/high) | Irrelevant |

**Conclusion**: PSL in its current form does NOT degrade agent performance. The `aria-hidden="true"` + `role="presentation"` approach fails because BrowserGym's action execution layer ignores these semantic annotations. To achieve pure-semantic degradation that actually affects agents, we would need to either:

1. **Filter the a11y tree** before sending to the agent (remove `hidden=True` elements from the observation)
2. **Use a different agent framework** that respects `aria-hidden` in its action resolution
3. **Accept that pure-semantic isolation is not achievable** with current BrowserGym architecture and document this as a finding

Option 1 is the most promising — it would simulate what a real screen reader user experiences (elements with `aria-hidden` are genuinely invisible) while keeping the DOM/visual layer unchanged for CUA comparison.
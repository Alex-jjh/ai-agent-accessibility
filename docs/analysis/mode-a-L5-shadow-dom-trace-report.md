# Mode A L5 (Shadow DOM) Trace-Level Deep Dive

> **Operator**: L5 — Wrap interactive elements in closed Shadow DOM
> **Experiment**: Mode A AMT, shard-b, run `c9d870f9`
> **Date**: 2026-05-01
> **Principle**: trace为王 — trace evidence is king

---

## 1. Executive Summary

L5 is the second most destructive operator in the AMT taxonomy (71.8% text-only success, −22.1pp from H-baseline). This report traces the exact mechanism through 5 cases: 3 agent architectures on task 4, a second task (94) for replication, and an H1 control for comparison.

**Core finding**: L5 creates "ghost buttons" — interactive elements that appear in the a11y tree but lack bid (BrowserGym identifier) numbers. The agent can *see* the button text but cannot *click* it. This is a structural barrier, not a semantic one: the element exists in the DOM inside a closed shadow root, Chromium's a11y tree exposes it (shadow DOM is transparent to the accessibility API), but BrowserGym's bid assignment mechanism cannot reach inside the closed shadow boundary to tag the element.

**Key evidence**:
- L5 trace: `button 'Show Report'` — no bid
- H1 control: `[722] button 'Show Report'` — bid 722, clickable
- SoM agent clicks bid "334" five consecutive times, all fail (F_ENF)
- Task 94 agent explicitly recognizes the problem: *"I can see the 'Continue' button in the accessibility tree, but I don't see its bid number"*
- CUA agent cannot reach admin panel at all (coordinate-based URL entry fails), exhausts token budget (414K tokens, F_COF)

---

## 2. L5 Operator Mechanics

Source: `src/variants/patches/operators/L5.js`

```javascript
// AMT operator L5 — Wrap interactive elements in closed Shadow DOM
(() => {
  const changes = [];
  const interactiveForShadow = Array.from(document.querySelectorAll(
    'button, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]'
  ));
  for (const el of interactiveForShadow) {
    if (el.parentElement && !el.parentElement.shadowRoot) {
      const wrapper = document.createElement('div');
      el.parentElement.insertBefore(wrapper, el);
      const shadow = wrapper.attachShadow({ mode: 'closed' });
      shadow.appendChild(el);
      changes.push({ ... });
    }
  }
  return changes;
})();
```

**What it does**: For every `button`, `[role="button"]`, `[role="link"]`, `[role="checkbox"]`, `[role="tab"]`, and `[role="menuitem"]` on the page, L5 creates a wrapper `<div>`, attaches a **closed** shadow root to it, and moves the interactive element inside. The element remains in the DOM and is visually rendered (CSS cascade resets at the shadow boundary, producing a Stripe-Elements-like visual effect), but the closed shadow root prevents external JavaScript from accessing the element.

**Why it breaks agents**: BrowserGym assigns bid attributes (`data-webarena-id`) by traversing the DOM tree. Closed shadow roots are opaque to `querySelectorAll` and `document.querySelector` — BrowserGym cannot reach inside to tag the element. However, Chromium's accessibility API *does* penetrate shadow boundaries (by design, for screen reader support). The result: the a11y tree shows the button with its role and name, but without a bid number. The agent sees a button it cannot click.

**No WCAG equivalent**: L5 is a novel operator. There is no WCAG failure technique for closed Shadow DOM wrapping. This makes it categorically different from other L-family operators which map to specific WCAG violations.

---

## 3. Trace 1: L5 × Task 4 × Text-Only (FAILURE)

**Case**: `ecommerce_admin_individual_4_0_1_L5`
**Outcome**: `success: false`, `outcome: failure`
**Steps**: 15 | **Tokens**: 199,017 | **Duration**: 96.2s
**Classification**: F_UNK (unclassified — requires manual review)

### 3.1 Task Intent

Task 4 is a Magento admin task: find the top-3 bestselling products in January 2023. This requires navigating to the admin panel, opening Reports → Products → Bestsellers, setting a date range, and clicking "Show Report".

### 3.2 Agent Journey

The agent successfully navigates to the admin panel and reaches the Bestsellers Report page. The critical failure occurs at the "Show Report" button.

**Steps 0–6**: Login and navigation (all succeed). The agent logs into the storefront, then navigates to `/admin`.

**Step 7**: Agent reaches the admin dashboard and clicks REPORTS:

```
Action: click("339")
Result: success
```

**Step 8**: Agent clicks into Products → Bestsellers:

```
Action: click("431")
Result: success
```

**Step 9**: Agent opens the Period dropdown and sees the options:

```
Action: click("750")
Result: success
```

**Step 10**: Agent tries to select "Month" from the dropdown — **FAILS**:

```
Action: click("752")
Result: failure
```

Agent reasoning at step 10:
```
Good! The Period dropdown is now open. I can see the options: Day, Month, and Year.
I need to select "Month" to get monthly data for January 2023.
```

**Steps 12–13**: Agent fills in date fields (From: 01/01/2023, To: 01/31/2023) — these succeed because textboxes have bids.

**Step 14**: Agent clicks bid 719 for "Show Report" — but this navigates to an external Adobe Commerce page instead of generating the report. The agent has clicked the wrong element because the real "Show Report" button has no bid.

### 3.3 Ghost Button Evidence

The a11y tree at step 9 (Bestsellers Report page) shows the critical ghost buttons:

```
  button 'System Messages: 2'          ← no bid
  button 'Search'                       ← no bid
  button 'All Websites', hasPopup='menu' ← no bid
  button 'Show Report'                  ← no bid ← CRITICAL
  button 'undefined'                    ← no bid (date picker)
  button 'undefined'                    ← no bid (date picker)
  button 'Export'                       ← no bid
```

Compare with the H1 control at the same page (Trace 5, step 12):

```
  [646] button 'System Messages: 1'    ← bid 646
  [705] button 'All Websites'          ← bid 705
  [722] button 'Show Report'           ← bid 722 ← CLICKABLE
  [758] button 'undefined \ue627'      ← bid 758
  [765] button 'undefined \ue627'      ← bid 765
  [782] button 'Export'                ← bid 782
```

**Every button on the page is a ghost in L5. Every button has a bid in H1.** This is the direct causal mechanism: L5 wraps all `button` elements in closed Shadow DOM, stripping their bids while preserving their a11y tree presence.

### 3.4 The "Show Report" Smoking Gun

L5 trace, step 9 observation (lines 55–60):
```
[718] link '\ue633 What is this?'
        StaticText '\ue633'
        StaticText 'What is this?'
button 'Show Report'
        StaticText '\ue61a'
        StaticText 'For accurate reporting, be sure to refresh lifetime statistics...'
```

H1 control, step 12 observation (lines 57–63):
```
[716] link '\ue633 What is this?'
        StaticText '\ue633'
        StaticText 'What is this?'
[722] button 'Show Report'
        StaticText 'Show Report'
        StaticText '\ue61a'
        StaticText 'For accurate reporting, be sure to refresh lifetime statistics...'
```

The difference is exactly 5 characters: `[722] `. That's the bid. Without it, the agent cannot issue `click("722")`. The button is visible but untouchable.

---

## 4. Trace 2: L5 × Task 4 × SoM (FAILURE)

**Case**: `ecommerce_admin_individual_4_1_1_L5`
**Outcome**: `success: false`, `outcome: failure`
**Steps**: 11 | **Tokens**: 35,265 | **Duration**: 94.1s
**Classification**: F_ENF (element not found — accessibility domain)

### 4.1 The Phantom Bid Loop

The SoM (Set-of-Mark) agent uses screenshots with bid labels overlaid on interactive elements. The critical failure is a **5-click phantom bid loop** on bid "334":

```
Step 4: click("334") → failure
Step 5: hover("334") → failure
Step 6: click("334") → failure
Step 7: click("334") → failure
Step 8: click("334") → failure
```

Agent reasoning at step 4:
```
I can see I'm currently on a "Terms and Conditions" page, but I need to get to
the Reports section. I can see in the left sidebar there's a "REPORTS" section
(label 334). Let me click on that to access the reports.
```

Agent reasoning at step 8:
```
I can see I'm on the Terms and Conditions page and the REPORTS element (334) is
not visible/clickable. Let me try clicking on the "REPORTS" text in the left
sidebar that I can see (label 334). If that doesn't work, I'll try a different approach.
```

### 4.2 Why SoM Fails Differently

The SoM agent sees bid labels in the screenshot overlay. The SoM overlay is generated from the DOM *before* BrowserGym resolves the bid to an actual element. When the agent issues `click("334")`, BrowserGym tries to find the element with `data-webarena-id="334"` — but that attribute was never written to the element inside the closed shadow root. The bid label exists in the screenshot but not in the DOM.

This is the **phantom bid mechanism** documented in Pilot 4: the SoM label persists in the screenshot, the agent clicks the stale bid, BrowserGym returns "Could not find element", and the agent enters a retry loop.

### 4.3 Token Efficiency

SoM consumed only 35,265 tokens (vs 199,017 for text-only) because it failed fast — 5 consecutive failures on the same bid triggered the agent to give up and try "Advanced Reporting" instead (step 10, bid 732), which also failed to produce the needed data.

---

## 5. Trace 3: L5 × Task 4 × CUA (FAILURE)

**Case**: `ecommerce_admin_individual_4_2_1_L5`
**Outcome**: `success: false`, `outcome: failure`
**Steps**: 27 | **Tokens**: 414,517 | **Duration**: 181.3s
**Classification**: F_COF (context overflow — model domain)

### 5.1 CUA's Unique Failure Mode

The CUA (Computer Use Agent) operates via coordinate-based clicks on screenshots — it has zero dependency on the a11y tree or bid system. Shadow DOM should be invisible to CUA since it clicks pixels, not DOM elements.

**However, CUA fails for a different reason**: it cannot navigate to the admin panel.

Steps 3–9 show the CUA struggling with URL entry:
```
Step 3: cua:key({"action":"key","text":"ctrl+l"})     → success
Step 6: cua:type({"text":"http://10.0.1.50:7780/admin"}) → success
Step 7: cua:key({"text":"Return"})                      → failure
Step 8: cua:key({"text":"Return"})                      → failure
Step 9: cua:key({"text":"Enter"})                       → success
```

After finally pressing Enter, the CUA lands on the storefront homepage instead of the admin panel. It then spends steps 11–24 scrolling through the homepage looking for "Hot Sellers" data, never reaching the admin Bestsellers Report.

### 5.2 Why CUA Fails on Task 4

CUA's failure on task 4 under L5 is **not caused by Shadow DOM**. It's caused by:
1. URL navigation difficulty (coordinate-based typing is fragile)
2. The admin panel requires a separate login flow that CUA cannot complete via screenshots alone
3. Token exhaustion (414K tokens, exceeding the 200K Claude Sonnet limit → F_COF)

Agent reasoning at step 26 (final step):
```
Based on the information I can see from the website, I found the "Hot Sellers"
section which shows the current trending products on Luma. However, this appears
to show current best-selling products rather than specifically January 2023 data.
```

### 5.3 CUA vs Shadow DOM: Theoretical Immunity, Practical Failure

CUA is theoretically immune to L5 because it clicks coordinates, not bids. But task 4 requires admin panel access, which CUA cannot achieve even without L5. This makes task 4 a poor discriminator for CUA's Shadow DOM sensitivity — the task's navigation complexity masks the operator's effect.

---

## 6. Trace 4: L5 × Task 94 × Text-Only (FAILURE)

**Case**: `ecommerce_admin_individual_94_0_1_L5`
**Outcome**: `success: false`, `outcome: timeout`
**Steps**: 30 | **Tokens**: 302,966 | **Duration**: 162.8s
**Classification**: timeout (no classification.json)

### 6.1 Task Intent

Task 94: find the grand total of invoice 000000001. This requires navigating to the admin panel's Sales → Invoices section, or using the storefront's Orders and Returns form.

### 6.2 The Ghost Button Pattern — Replicated

The agent encounters ghost buttons on every page. On the storefront login page:

```
button 'Search'      ← no bid
button 'Sign In'     ← no bid
button 'Subscribe'   ← no bid
```

The "Sign In" button has no bid. The agent clicks bid 387 (which is the password field's submit action, not the button itself) — the login never processes.

### 6.3 The Agent Recognizes the Problem

At step 24, the agent explicitly identifies the ghost button mechanism:

Agent reasoning at step 24:
```
I can see the "Continue" button in the accessibility tree, but I don't see its
bid number. Let me scroll down to see if there are more elements or try a
different approach. Let me scroll down to see if the button becomes visible.
```

This is remarkable: the agent has diagnosed the exact failure mechanism — the button is in the a11y tree but has no bid. It then attempts a desperate workaround, trying nearby bid numbers:

```
Step 22: click("396") → failure
Step 23: click("395") → failure
Step 25: click("394") → failure
Step 27: click("388") → failure
Step 29: click("397") → failure
```

Five consecutive failures on adjacent bids. The agent is probing the bid space around where the button should be, but the button has no bid at all.

### 6.4 Ghost Buttons on the Orders and Returns Page

On the Orders and Returns page (steps 19–29):

```
button 'Search'     ← no bid
button 'Continue'   ← no bid  ← CRITICAL
button 'Subscribe'  ← no bid
```

The "Continue" button is the form submission trigger. Without a bid, the agent cannot submit the form, cannot look up the invoice, and times out after 30 steps.

### 6.5 The Login Trap

Steps 0–17 show the agent trapped in a login loop. The "Sign In" button is a ghost:

```
Step 3:  click("387") → success (but login doesn't process)
Step 5:  click("387") → success (still no login)
Step 11: click("387") → success (third attempt)
Step 16: click("387") → success (fourth attempt)
```

The agent clicks bid 387 four times. Each time BrowserGym reports "success" (the click was dispatched), but the login never processes because bid 387 is not the actual Sign In button — it's a nearby element. The real Sign In button is a ghost.

---

## 7. Trace 5: H1 × Task 4 × Text-Only (SUCCESS — Control)

**Case**: `ecommerce_admin_individual_4_0_1_H1`
**Outcome**: `success: true`, `outcome: success`
**Steps**: 14 | **Tokens**: 218,324 | **Duration**: 114.2s
**Classification**: N/A (success)

### 7.1 Clean Execution Path

The H1 control agent follows nearly the same strategy as the L5 agent but succeeds because all buttons have bids:

```
Step 0:  click("242")  → Sign In link        → success
Step 3:  click("425")  → Sign In button      → success (LOGIN WORKS)
Step 7:  goto("/admin") → admin panel         → success
Step 8:  click("339")  → REPORTS menu        → success
Step 9:  click("431")  → Bestsellers link    → success
Step 10: fill("757", "01/01/2023")           → success
Step 11: fill("764", "01/31/2023")           → success
Step 12: click("722")  → Show Report button  → success ← THE KEY STEP
Step 13: send_msg_to_user("1. Overnight Duffle...")  → success
```

### 7.2 The Critical Difference: Step 12

H1 step 12 reasoning:
```
Perfect! I've now set both date fields:
- From: 01/01/2023
- To: 01/31/2023

Now I need to click the "Show Report" button to generate the bestsellers report
for January 2023.
```

Action: `click("722")` → Result: `success`

The agent clicks bid 722 — the "Show Report" button — and the report generates. In the L5 trace, this button has no bid. That single missing bid is the difference between success and failure.

### 7.3 Final Answer

Agent's response at step 13:
```
1. Overnight Duffle (2 units), 2. Impulse Duffle (2 units),
3. Hawkeye Yoga Short-32-Blue (2 units)
```

---

## 8. Synthesis: Why Shadow DOM Is Uniquely Destructive

### 8.1 The Three-Layer Failure

L5 operates at a unique intersection of three layers:

1. **DOM structural layer**: The element is moved into a closed shadow root. It still exists in the DOM but is structurally isolated.
2. **A11y tree layer**: Chromium's accessibility API penetrates shadow boundaries (by design). The element appears in the a11y tree with its role, name, and state intact.
3. **BrowserGym instrumentation layer**: BrowserGym's bid assignment uses `querySelectorAll` which cannot penetrate closed shadow roots. The element gets no bid.

The result is a **perception-action gap**: the agent perceives the element (via a11y tree) but cannot act on it (no bid for the action API).

### 8.2 Ghost Button Taxonomy

From the traces, ghost buttons manifest in three forms:

| Form | Example | Agent Behavior |
|------|---------|----------------|
| Named ghost | `button 'Show Report'` (no bid) | Agent sees it, tries nearby bids, fails |
| Unnamed ghost | `button 'undefined'` (no bid) | Agent ignores or misidentifies |
| Phantom bid (SoM) | SoM overlay shows bid "334" | Agent clicks stale bid, 5+ retry loop |

### 8.3 Why L5 Is Worse Than L11 (link→span)

L11 (link→span) is the most destructive operator overall, but L5 is more insidious:

- **L11** removes the element entirely from the interactive set. The agent knows the link is gone and can attempt workarounds (goto, URL construction).
- **L5** leaves the element visible but unreachable. The agent *thinks* it can click the button and wastes steps trying. This creates a **false affordance** — the a11y tree promises interactivity that doesn't exist.

### 8.4 Cross-Agent Impact

| Agent | L5 Task 4 | Failure Mode | Root Cause |
|-------|-----------|--------------|------------|
| Text-only | FAIL (15 steps, 199K tokens) | Clicks wrong element, navigates away | Ghost "Show Report" button |
| SoM | FAIL (11 steps, 35K tokens) | 5× phantom bid loop on "334" | Phantom bid in screenshot overlay |
| CUA | FAIL (27 steps, 414K tokens) | Cannot reach admin panel | URL navigation failure (not L5-caused) |

Text-only and SoM failures are directly caused by L5. CUA's failure is task-complexity-driven, not L5-driven.

### 8.5 Token Inflation

| Case | Tokens | Steps | Tokens/Step |
|------|--------|-------|-------------|
| L5 task 4 text-only | 199,017 | 15 | 13,268 |
| L5 task 4 SoM | 35,265 | 11 | 3,206 |
| L5 task 4 CUA | 414,517 | 27 | 15,353 |
| L5 task 94 text-only | 302,966 | 30 | 10,099 |
| H1 task 4 text-only | 218,324 | 14 | 15,595 |

SoM is the most token-efficient because it fails fast (phantom bid loop detected quickly). Text-only on task 94 is the most wasteful — 30 steps of futile button-probing before timeout.

---

## 9. Comparison with L1 (Landmark Paradox)

L1 (semantic landmark → `<div>`) and L5 (closed Shadow DOM) are both structural operators, but they fail through opposite mechanisms:

| Dimension | L1 (Landmark → div) | L5 (Shadow DOM) |
|-----------|---------------------|-----------------|
| What changes | Semantic role removed | Element structurally isolated |
| A11y tree effect | `navigation` → `generic` | Element visible but bid-less |
| Agent perception | Sees generic div, loses navigation cues | Sees button, cannot click it |
| Failure mode | Navigation confusion (can't find sections) | False affordance (sees but can't act) |
| WCAG mapping | SC 1.3.1 (Info and Relationships) | None (novel) |
| Workaround possible? | Yes — agent can use text content | No — no alternative click path |

**The L1 paradox**: L1 removes semantic landmarks, which should degrade navigation. But in practice, Magento admin pages have so many landmarks that removing them actually *reduces* a11y tree noise, sometimes helping the agent. This is the "landmark paradox" — too many landmarks can be worse than none.

**L5 has no paradox**: Shadow DOM wrapping is purely destructive. There is no scenario where hiding buttons behind a closed shadow root helps the agent. The effect is monotonically negative.

### 9.1 Severity Comparison

L1 success rate across all tasks: ~85% (mild degradation)
L5 success rate across all tasks: ~72% (severe degradation)

The 13pp gap reflects L5's unique property: it doesn't just degrade information (like L1), it **breaks the action channel**. An agent that can't click buttons is fundamentally more impaired than one that can't see landmarks.

---

## Appendix A: Bridge Log Structure

The bridge logs for these traces contain 2,287–2,443 entries (character-level logging). The variant application is confirmed by the `data-amt-applied` sentinel on `<body>` after L5 runs. DOM changes count is embedded in the operator's return value (number of elements wrapped in shadow roots).

## Appendix B: File Paths

| Trace | Path |
|-------|------|
| L5 × task 4 × text-only | `data/mode-a-shard-b/track-a/runs/c9d870f9-3967-427c-8a78-bd2f94ba9eff/cases/ecommerce_admin_individual_4_0_1_L5/trace-attempt-1.json` |
| L5 × task 4 × SoM | `data/mode-a-shard-b/track-a/runs/c9d870f9-3967-427c-8a78-bd2f94ba9eff/cases/ecommerce_admin_individual_4_1_1_L5/trace-attempt-1.json` |
| L5 × task 4 × CUA | `data/mode-a-shard-b/track-a/runs/c9d870f9-3967-427c-8a78-bd2f94ba9eff/cases/ecommerce_admin_individual_4_2_1_L5/trace-attempt-1.json` |
| L5 × task 94 × text-only | `data/mode-a-shard-b/track-a/runs/c9d870f9-3967-427c-8a78-bd2f94ba9eff/cases/ecommerce_admin_individual_94_0_1_L5/trace-attempt-1.json` |
| H1 × task 4 × text-only | `data/mode-a-shard-a/track-a/runs/97507afa-7b9e-4064-9852-48f55c238e3c/cases/ecommerce_admin_individual_4_0_1_H1/trace-attempt-1.json` |

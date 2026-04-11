# Pilot 4 — First 52 Cases Analysis

**Run ID:** `f4929214-3d48-443b-a859-dd013a737d50`
**Date:** 2026-04-07
**Cases completed:** 52 / 240 (21.7% of full matrix)

---

## 1. Agent Type Counts

| Agent Type  | Count | Success | Rate  |
|-------------|-------|---------|-------|
| text-only   | 29    | 20      | 69.0% |
| vision-only | 23    | 5       | 21.7% |
| **Total**   | **52**| **25**  | **48.1%** |

Text-only is running ahead of vision-only in the schedule (29 vs 23 completed).

---

## 2. Per-Variant Success Rates by Agent Type

### Text-Only

| Variant    | Success | Total | Rate   |
|------------|---------|-------|--------|
| low        | 3       | 12    | 25.0%  |
| medium-low | 3       | 3     | 100.0% |
| base       | 9       | 9     | 100.0% |
| high       | 5       | 5     | 100.0% |

Gradient is sharp: low (25%) → medium-low+ (100%). Replicates Pilot 3a/3b step-function.

### Vision-Only

| Variant    | Success | Total | Rate   |
|------------|---------|-------|--------|
| low        | 0       | 1     | 0.0%   |
| medium-low | 1       | 9     | 11.1%  |
| base       | 1       | 5     | 20.0%  |
| high       | 3       | 8     | 37.5%  |

Vision-only shows a *reversed* gradient — performance improves with higher a11y quality.
This is unexpected: vision-only should be invariant to DOM mutations (screenshots don't change).
Possible confound: high-variant pages may be structurally simpler, or SoM labels differ.
Needs investigation once full matrix completes.

---

## 3. Text-Only Task × Variant Matrix

| Task      | low  | med-low | base | high |
|-----------|------|---------|------|------|
| admin:4   | 0/3  | —       | 2/2  | —    |
| ecom:23   | 0/2  | 1/1    | 2/2  | —    |
| ecom:24   | 0/1  | 1/1    | 2/2  | 2/2  |
| ecom:26   | 0/1  | —       | 2/2  | 2/2  |
| reddit:29 | 2/2  | 1/1    | —    | —    |
| reddit:67 | 1/3  | —       | 1/1  | 1/1  |

Key observations:
- **Ecommerce tasks (23, 24, 26) are 0% at low** — content invisibility pathway confirmed.
- **admin:4 is 0/3 at low** — token inflation pathway (30-step timeouts, 290K+ tokens).
- **reddit:29 is 2/2 at low** — reddit tasks are resilient to low variant (forum structure survives).
- **reddit:67 is 1/3 at low** — partial resilience, some stochastic failures.

---

## 4. ecom:23 Low Text-Only Deep Dive

**Result: 0/2 — both failures.** Plan D is working.

| Case                   | Steps | Tokens | Outcome |
|------------------------|-------|--------|---------|
| ecommerce_low_23_0_4   | 8     | 94,461 | failure |
| ecommerce_low_23_0_5   | 8     | 95,857 | failure |

Both traces show the same pattern:
1. Agent lands on product page
2. Scrolls up/down looking for review content
3. Sees "Reviews" as StaticText but **no tab role** — can't click to reveal review panel
4. Agent reasoning: *"I clicked on the Reviews tab, but the actual review content is not visible in the accessibility tree"*
5. Gives up: `send_msg_to_user("cannot complete")`

The agent correctly identifies the problem but cannot overcome it — the low variant has stripped
the `tablist`/`tabpanel` ARIA roles, making the review section inaccessible.

---

## 5. Plan D Confirmation (tablist/tabpanel search)

| Trace                  | `tablist` | `tabpanel` |
|------------------------|-----------|------------|
| ecommerce_low_23_0_4   | ❌ absent  | ❌ absent   |
| ecommerce_low_23_0_5   | ❌ absent  | ❌ absent   |

**Plan D confirmed.** The low variant successfully removes tab ARIA roles from the product page.
"Reviews" appears as inert StaticText (not an interactive tab), so the agent cannot navigate
to the reviews panel. This is the content invisibility failure pathway working as designed.

---

## 6. Last Case That Ran

**Case:** `reddit_high_29_1_5`
**File timestamp:** 2026-04-07 09:16:06
**Outcome:** failure (19 steps, 77,276 tokens)
**Duration:** 25,515,355 ms (7.1 hours — see §7)

This was a vision-only run on reddit:29 high that appears to have stalled/hung.

---

## 7. Wall-Clock Timeouts

No traces contain "wall-clock" in `resultDetail` (field is empty for all 52 traces).

However, **7 traces hit the 30-step timeout** (outcome=`timeout`):

| Case                          | Agent       | Steps | Duration  |
|-------------------------------|-------------|-------|-----------|
| ecommerce_admin_low_4_0_1     | text-only   | 30    | 224.5s    |
| ecommerce_admin_low_4_0_3     | text-only   | 30    | 211.6s    |
| ecommerce_admin_low_4_0_5     | text-only   | 30    | 211.1s    |
| ecommerce_admin_high_4_1_5    | vision-only | 30    | 225.1s    |
| reddit_base_29_1_3            | vision-only | 30    | 203.4s    |
| reddit_high_29_1_4            | vision-only | 30    | 252.7s    |
| reddit_medium-low_29_1_5      | vision-only | 30    | 212.9s    |

All 3 text-only timeouts are admin:4 low — the token inflation pathway (293K tokens avg).
4 vision-only timeouts are spread across tasks — vision agent struggles generally.

**Anomaly:** `reddit_high_29_1_5` ran for 7.1 hours (25.5M ms) with only 19 steps.
This is likely a process hang or network stall, not a normal step-limit timeout.
It completed as `failure` not `timeout`, suggesting the process eventually recovered/errored.

---

## 8. Token Comparison

| Metric       | Text-Only   | Vision-Only |
|--------------|-------------|-------------|
| Avg tokens   | 107,143     | 42,030      |
| Median tokens| 68,778      | 27,471      |
| Min tokens   | 9,912       | 3,740       |
| Max tokens   | 395,353     | 129,477     |
| N            | 29          | 23          |

**Text-only uses 2.55× more tokens than vision-only on average.**

This is expected: the a11y tree is verbose (full DOM semantics), while vision-only sends
only screenshots. The token inflation is most extreme in admin:4 low (293K–395K tokens)
where the agent loops through large admin tables.

### Duration Comparison

| Metric       | Text-Only | Vision-Only (excl outlier) |
|--------------|-----------|---------------------------|
| Avg duration | 67.5s     | 99.8s                     |
| Avg steps    | 7.4       | 12.8                      |

Vision-only takes longer per-run despite fewer tokens — each step is slower (screenshot
rendering + SoM overlay + image encoding). Vision-only also takes more steps on average
(12.8 vs 7.4), suggesting it needs more exploration to accomplish tasks.

---

## Outcome Breakdown

| Outcome         | Text-Only | Vision-Only |
|-----------------|-----------|-------------|
| success         | 20        | 5           |
| failure         | 4         | 4           |
| timeout         | 3         | 4           |
| partial_success | 2         | 10          |

Vision-only's dominant failure mode is `partial_success` (10/23 = 43%) — the agent
makes progress but can't complete the task. This contrasts with text-only where
failures are binary (success or clear failure/timeout).

---

## Summary

1. **Core finding replicates:** Text-only shows sharp low→medium-low step function (25%→100%).
2. **Plan D confirmed:** ecom:23 low is 0/2, tablist/tabpanel absent from a11y tree.
3. **Vision-only is weak overall** (21.7%) with unexpected variant gradient — needs investigation.
4. **Token inflation pathway active:** admin:4 low hits 30-step timeout with 290K+ tokens.
5. **One anomalous 7-hour run** (reddit_high_29_1_5) — likely process hang, not systematic.
6. **No wall-clock timeout mechanism recorded** in resultDetail (field empty for all traces).
7. **52/240 complete** — run is ~22% through the full matrix. Need more data for statistical power.

# Expansion-Claude Trace Deep Dive: gitlab:308 low & admin:94 low

**Experiment**: expansion-claude (run 6082c5d1)
**Model**: Claude Sonnet 3.5 via Bedrock
**Date**: April 2026

---

## Group 1: gitlab:308 low — 0/5 success

**Task**: "Tell me who has made the most contributions, in terms of number of commits, to the primer/design project"
**Expected answer**: "Shawn Allen"
**Non-low performance**: base 5/5, medium-low 5/5, high 5/5 (all in 4 steps, ~80K tokens)

### Per-Trace Analysis

| Trace | Steps | Tokens | Duration | Found repo? | Reached Contributors? | Fallback strategy | Final answer | Failure type |
|-------|-------|--------|----------|-------------|----------------------|-------------------|--------------|--------------|
| 1 | 15 | 355,069 | 117s | ✅ Yes | ❌ Page empty | Manual commit counting | Cole Bemis | Structural infeasibility |
| 2 | 13 | 318,342 | 107s | ✅ Yes | ❌ Page empty | Manual commit counting | Mike Perrotti | Structural infeasibility |
| 3 | 12 | 276,155 | 103s | ✅ Yes | ❌ Page empty | Manual commit counting | Cole Bemis | Structural infeasibility |
| 4 | 11 | 225,458 | 98s | ✅ Yes | ❌ Page empty | Manual commit counting | Mike Perrotti | Structural infeasibility |
| 5 | 21 | 514,101 | 152s | ✅ Yes | ❌ Page empty (2× attempts) | Manual commit counting | Cole Bemis | Structural infeasibility |

### Common Failure Pattern

All 5 traces follow an identical three-phase pattern:

**Phase 1 — Navigate to primer/design repo** (3-4 steps): Agent clicks through GitLab sidebar to reach the primer/design project. All 5 succeed.

**Phase 2 — Attempt Contributors page** (2-4 steps): Agent navigates to `/primer/design/-/graphs/main` or `/primer/design/-/graphs/main/contributors`. The page title loads ("Contributors · Primer / design · GitLab") but the **contributor chart data is completely absent from the a11y tree**. The page content area shows only:
```
[469] listitem '' → StaticText 'Contributors'   (breadcrumb)
[477] Section '' → button 'main'
StaticText 'History'
```
No contributor names, no commit counts, no chart data. The agent recognizes this: *"The contributors data doesn't seem to be loading or visible"* and tries noop() to wait, scrolling, and alternate URLs (`?tab=contributors`, `/charts`). Trace 5 attempts the Contributors page twice. All fail.

**Phase 3 — Fallback to commits page** (3-8 steps): Agent navigates to `/primer/design/-/commits/main` and manually counts commit authors from the visible commit list. This shows only the most recent ~20-30 commits (one page), which is a biased sample. The agent counts whoever appears most frequently on that single page and guesses "Cole Bemis" (3/5) or "Mike Perrotti" (2/5). The correct answer "Shawn Allen" requires the full contributor statistics that are only available on the Contributors chart page.

### Root Cause

The GitLab Contributors page renders contributor statistics via JavaScript-generated SVG charts. Under the low variant, the DOM de-semanticization breaks the chart rendering pipeline — the chart container exists but the chart content (contributor names, commit counts, bar graphs) never populates in the a11y tree. This is **structural infeasibility**: the task-critical information (aggregate commit counts per contributor) is genuinely inaccessible. The agent's fallback strategy (counting commits on the first page of the commit log) is reasonable but fundamentally insufficient — it sees only a recency-biased sample, not the full history.

### Classification: Structural Infeasibility (not token inflation)

Despite the auto-classifier labeling all 5 as F_COF (context overflow, confidence 0.95), the actual failure mechanism is **structural infeasibility**. The F_COF classification is misleading — tokens are elevated (225K-514K vs 80K at base) because the agent spends many steps trying alternative navigation strategies, but the root cause is that the Contributors page content is invisible, not that the agent overflows its context window. The agent successfully produces an answer in all 5 traces (it doesn't crash or lose track); it just produces the *wrong* answer because it can only see a partial commit history.

**Recommended reclassification**: F_SIF (Structural Infeasibility) for all 5 traces.

---

## Group 2: admin:94 low — 3/5 success, 2/5 failure

**Task**: "Tell me the grand total of invoice 000000001"
**Expected answer**: must include "36.39"
**Non-low performance**: base 5/5, medium-low 5/5, high 5/5 (all in 3 steps, ~21K tokens)

### Per-Trace Analysis

| Trace | Steps | Tokens | Duration | Outcome | Navigation strategy | Used goto() URL? | Final answer |
|-------|-------|--------|----------|---------|--------------------|--------------------|--------------|
| 1 | 22 | 187,707 | 138s | ✅ success | sidebar → invoice list → search fails → order list → search fails → **direct URL guess** | ✅ Yes | $36.39 |
| 2 | 30 | 256,811 | 187s | ❌ timeout | sidebar → invoice list → search fails → filter loops → stuck | ❌ No | (none — timed out) |
| 3 | 30 | 252,452 | 184s | ❌ timeout | sidebar → invoice list → search fails → filter loops → order list → search fails → stuck | ❌ No | (none — timed out) |
| 4 | 21 | 177,088 | 132s | ✅ success | sidebar → invoice list → search fails → order list → **direct URL guess** | ✅ Yes | $36.39 |
| 5 | 22 | 181,651 | 141s | ✅ success | sidebar → invoice list → search fails → order list → **direct URL guess** | ✅ Yes | $36.39 |

### Common Pattern (All 5 Traces)

All 5 traces begin identically:
1. Click sidebar → Sales → Invoices
2. `goto("http://10.0.1.50:7780/admin/sales/invoice/")` — navigate to invoice list
3. `fill("790", "000000001")` — search for invoice number
4. Click search/filter buttons — **search returns "We couldn't find any records"**

Under the low variant, the Magento admin search/filter functionality is broken. The search textbox accepts input but the filter mechanism fails to return results. This affects both the invoice list and the order list.

### What Distinguishes Successes from Failures

**The 3 successes** all eventually construct a direct URL: `goto("http://10.0.1.50:7780/admin/sales/invoice/view/invoice_id/000000001/")`. This bypasses the broken search entirely. The agent's reasoning: *"The search functionality seems to have issues with the interface. Let me try accessing the invoice directly by going to a specific invoice view URL."*

The path to this insight varies slightly:
- Trace 1: tries invoice search → order search → both fail → constructs direct URL (step 20)
- Trace 4: tries invoice search → order search → constructs direct URL (step 19)
- Trace 5: tries invoice search → order search → constructs direct URL (step 20)

**The 2 failures** never make this conceptual leap. They remain stuck in a loop of:
- Clearing and re-entering search terms
- Toggling filter panels open/closed
- Clicking "Apply Filters" repeatedly
- Scrolling up and down

Trace 2 spends its final 10 steps cycling through filter operations. Trace 3 reaches the order list (step 24) and searches there too, but when that also fails, it continues clicking filter buttons until timeout at step 30.

### Root Cause: Stochastic Strategy Variation

The success/failure split is **purely stochastic**. All 5 traces encounter the same broken search. The divergence point is whether the LLM generates the creative insight to construct a direct URL from the invoice number. This is a classic example of **stochastic strategy variation** in LLM agents — the same model, same prompt, same observation, but different sampling outcomes lead to fundamentally different strategies.

The direct URL construction is not trivial — the agent must:
1. Recognize that search is broken (not just slow)
2. Infer the Magento admin URL pattern (`/admin/sales/invoice/view/invoice_id/XXXXX/`)
3. Construct the URL using the invoice number from the task

This requires domain knowledge about Magento URL conventions that the LLM has from training data, but whether it surfaces this knowledge in any given run is probabilistic.

### Classification

- **3 successes**: Correct answer via goto() URL workaround. Token inflation present (177K-188K vs 21K at base = 8.5× inflation) but task completed.
- **2 failures**: Timeout (F_TMO). The agent exhausts 30 steps without finding the invoice. Root cause is the broken search under low variant, but the proximate cause is failure to discover the URL workaround.

**Recommended classification for failures**: F_SIF (Structural Infeasibility) — the normal navigation pathway (search → click result) is broken. The goto() workaround is a creative bypass, not the intended navigation path.

---

## Combined Summary

### gitlab:308 — Structural Infeasibility (5/5 failures)

The Contributors page is a JavaScript-rendered chart that becomes invisible in the a11y tree under low variant. All 5 traces find the repo, reach the Contributors page, observe it's empty, and fall back to manual commit counting from the first page of the commit log. This produces wrong answers (Cole Bemis or Mike Perrotti instead of Shawn Allen) because the visible commit page is a recency-biased sample. This is a clean case of **structural infeasibility** — the task-critical information (aggregate contributor statistics) is genuinely inaccessible, and no amount of additional steps or tokens would help.

The auto-classifier's F_COF label is incorrect. Token inflation (225K-514K vs 80K base, 2.8×-6.4×) is a *symptom* of the agent exploring alternatives, not the root cause.

### admin:94 — Stochastic Strategy Variation (3/5 success, 2/5 failure)

The Magento admin search is broken under low variant, but the invoice data is still accessible via direct URL construction. Whether the agent discovers this workaround is stochastic — same model, same observations, different sampling outcomes. Successes take 21-22 steps and ~182K tokens (8.5× base). Failures timeout at 30 steps and ~255K tokens.

This is a borderline case: the *intended* navigation pathway is broken (structural infeasibility), but a *creative workaround* exists. The 60% success rate reflects the probability that the LLM generates the URL-construction insight.

### Token Statistics

| Group | Variant | Min tokens | Max tokens | Mean tokens | Median tokens | Base comparison |
|-------|---------|-----------|-----------|-------------|---------------|-----------------|
| gitlab:308 | low | 225,458 | 514,101 | 337,825 | 318,342 | 4.2× base (80K) |
| gitlab:308 | base | 80,343 | 80,703 | 80,485 | 80,392 | — |
| admin:94 | low (success) | 177,088 | 187,707 | 182,149 | 181,651 | 8.4× base (22K) |
| admin:94 | low (failure) | 252,452 | 256,811 | 254,632 | 254,632 | 11.7× base |
| admin:94 | low (all) | 177,088 | 256,811 | 211,142 | 187,707 | 9.7× base |
| admin:94 | base | 21,735 | 21,763 | 21,751 | 21,759 | — |

### Recommended Failure Classifications

| Case | Current classification | Recommended | Rationale |
|------|----------------------|-------------|-----------|
| gitlab:308 low (all 5) | F_COF (0.95) | **F_SIF** (Structural Infeasibility) | Contributors chart invisible in a11y tree; agent gives wrong answer, doesn't overflow |
| admin:94 low trace 2 | timeout (1.0) | **F_SIF** (Structural Infeasibility) | Search broken; agent stuck in filter loop; never discovers URL workaround |
| admin:94 low trace 3 | timeout (1.0) | **F_SIF** (Structural Infeasibility) | Same as trace 2 |

### Key Insights

1. **gitlab:308 is a pure structural infeasibility case** — the Contributors page's JS-rendered chart is completely invisible under low variant. No fallback strategy can recover the aggregate statistics. This is the cleanest example of "content invisibility" in the expansion dataset.

2. **admin:94 reveals stochastic strategy variation** — identical starting conditions produce 60/40 success/failure split based solely on whether the LLM samples the "construct direct URL" strategy. This has implications for experiment design: 5 reps may not be enough to reliably estimate success rates for tasks with creative workarounds.

3. **Token inflation is massive in both groups** — 4.2× for gitlab (where the agent explores alternatives) and 8.5-11.7× for admin (where the agent struggles with broken search). Even the admin successes use 8.5× more tokens than base, reflecting the cost of the workaround discovery process.

4. **The auto-classifier needs refinement** — F_COF is over-applied. gitlab:308 traces don't actually overflow context; they produce wrong answers from insufficient data. The classifier should distinguish "wrong answer from partial information" (F_SIF) from "context window exceeded" (F_COF).

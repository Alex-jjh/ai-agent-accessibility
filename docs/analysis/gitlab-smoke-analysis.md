# GitLab Smoke Test Analysis — 2026-04-12

## Summary

Phase 1 smoke test for task expansion. 3 GitLab tasks × 4 variants × 1 rep = 12 cases.
Run ID: 051f7f57-90fa-437b-b8d6-c8b6110a921f. Duration: 10.8 min.

## Results

Overall: 10/12 (83.3%)

| Task | low | medium-low | base | high |
|------|-----|-----------|------|------|
| 132 (commits) | ✅ 1/1 | ✅ 1/1 | ✅ 1/1 | ✅ 1/1 |
| 293 (clone SSH) | ❌ 0/1 | ✅ 1/1 | ✅ 1/1 | ✅ 1/1 |
| 308 (top contributor) | ❌ 0/1 | ✅ 1/1 | ✅ 1/1 | ✅ 1/1 |

Step function replicated: low 33.3% → medium-low/base/high 100%.

## Token Analysis

| Variant | Avg Tokens |
|---------|-----------|
| low | 109,968 |
| medium-low | 69,667 |
| base | 69,981 |
| high | 66,189 |

Low/base ratio: 1.57× (Pilot 4 Magento/Postmill was 2.15×).
GitLab's Vue.js SSR produces cleaner DOM than Magento KnockoutJS, explaining smaller inflation.

## Failure Analysis

### Task 293 low — Structural Infeasibility (F_UNK → reclassify as F_SIF)

Agent searched for "Super_Awesome_Robot" in search box (step 1-2), typed the query,
but could not submit or navigate to search results. Low variant's link→span (Patch 11)
converted all `<a>` elements to `<span>`, making search result links non-navigable.
Agent gave up at step 3 and sent the search term itself as the answer.

Mechanism: identical to ecom:23 content invisibility in Pilot 4 — navigation links
broken → task-critical page unreachable.

### Task 308 low — Token Inflation / Context Overflow (F_COF)

Agent navigated to primer/design repo but couldn't reach Contributors page (link→span).
Fell back to manually counting commits on the commits list page. Spent 13 steps
scrolling through commits, accumulating 274K tokens. Gave wrong answer "Cole Bemis"
(correct: "Shawn Allen") due to incomplete commit enumeration before context overflow.

Mechanism: identical to admin:4 token inflation in Pilot 4 — broken navigation →
exhaustive exploration → token bloat → wrong answer.

### Task 132 low — Success (interesting)

Agent successfully found commit count despite low variant. The Contributors page
data (commit count = "1") was directly visible on the repo page without requiring
link navigation. The task's critical information didn't depend on the broken links.

This demonstrates within-variant heterogeneity: low variant impact depends on
whether the task's critical information requires link-based navigation.

## Key Findings

1. Cross-app generalizability confirmed: same step function pattern on Vue.js (GitLab)
   as on KnockoutJS (Magento) and Postmill (Reddit).

2. Same two failure pathways replicated on 4th app:
   - Structural infeasibility (293): link→span blocks navigation to target page
   - Token inflation (308): broken nav → exhaustive exploration → context overflow

3. No Type 2 variant injection bugs: Vue.js virtual DOM did not conflict with
   MutationObserver guard. Variant patches applied correctly on all 12 cases.

4. Token inflation range across apps: 1.57×–2.15× (GitLab–Magento).

## Verdict

Phase 1 PASSED. All 3 GitLab tasks validated for full experiment.
No variant script changes needed (Type 1 only — selectors work on GitLab DOM).
Proceed to Phase 2 (admin + shopping tasks).

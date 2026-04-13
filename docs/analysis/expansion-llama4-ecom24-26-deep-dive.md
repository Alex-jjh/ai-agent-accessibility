# Llama 4 Maverick — Ecommerce Tasks 24 & 26 Deep Dive

**Date**: 2026-04-13
**Experiment**: expansion-llama4 (run a8aaf58b)
**Model**: Llama 4 Maverick (via LiteLLM → Bedrock)
**Agent**: Text-only (a11y tree observation)
**Traces analyzed**: 40 (20 per task, 4 variants × 5 reps)

---

## Executive Summary

Both tasks exhibit non-monotonic success patterns that are **entirely explained by Llama 4 model-level failures**, not accessibility variant effects. The anomalous patterns arise from two distinct Llama 4 weaknesses:

1. **Task 24**: Llama 4 sends an empty string `""` as its answer when no reviewers mention unfair pricing, instead of answering "N/A" or "0". The evaluator expects a fuzzy match on "N/A". This is a **response formatting failure** — the model correctly identifies that no reviews mention unfair pricing but fails to express this as a valid answer string. The single low-variant "success" is a vacuous truth: the agent gives up with `"cannot complete"`, which BrowserGym's fuzzy evaluator apparently accepts.

2. **Task 26**: Llama 4 consistently identifies only 1 of 3 expected reviewers ("Bob in Vegas") at medium-low, but stochastically finds 2 of 3 ("Bob in Vegas, RemyRRemyR") at base/high. The expected answer requires both "Bob in Vegas" and "RemyR". This is a **review comprehension / counting failure** — the model reads all 12 reviews but inconsistently identifies which ones mention customer service complaints.

Neither anomaly is caused by accessibility degradation. Both are **model capability issues** specific to Llama 4 Maverick.

---

## Task 24: "List reviewers who mention unfair pricing for Zoe products"

**Expected answer**: "N/A" (fuzzy_match) — no reviewers mention unfair pricing
**Ground truth**: There are 2 reviews (by "Jay" and "Josef Bürger"), neither mentions pricing

### Results Matrix

| Variant | Rep 1 | Rep 2 | Rep 3 | Rep 4 | Rep 5 | Rate |
|---------|-------|-------|-------|-------|-------|------|
| low | ❌ timeout | ❌ timeout | ❌ timeout | ❌ timeout | ✅ "cannot complete" | 1/5 (20%) |
| medium-low | ❌ "" | ❌ "" | ❌ "" | ❌ "" | ❌ "" | 0/5 (0%) |
| base | ❌ "" | ❌ "" | ❌ "" | ❌ "Jay, Josef Bürger" | ❌ "" | 0/5 (0%) |
| high | ❌ "" | ❌ "" | ❌ "Jay,Josef Bürger" | ❌ "" | ❌ "" | 0/5 (0%) |

### Token Consumption

| Variant | Rep 1 | Rep 2 | Rep 3 | Rep 4 | Rep 5 | Avg | Steps |
|---------|-------|-------|-------|-------|-------|-----|-------|
| low | 327,215 | 327,390 | 327,215 | 327,943 | 55,319 | 273,016 | 25.4 |
| medium-low | 16,523 | 16,522 | 16,522 | 16,522 | 16,523 | 16,522 | 3.0 |
| base | 8,985 | 17,669 | 17,651 | 8,953 | 17,665 | 14,185 | 2.6 |
| high | 17,699 | 17,695 | 8,962 | 17,824 | 17,695 | 15,975 | 2.8 |

### Detailed Failure Analysis

#### Low variant (1/5 = 20%): Content invisibility → infinite scroll loop

**Mechanism**: Plan D variant injection breaks the tabpanel ARIA relationship. The agent clicks the "Reviews" tab (bid 1557) but the review content never appears in the a11y tree. All observations show `tablist=False, tabpanel=False`. The agent enters an infinite scroll loop:

- Step 1: Clicks "Reviews (2)" tab → success
- Steps 2–30: `scroll(0, 500)` repeatedly, reasoning: "The reviews are still not visible"
- Outcome: timeout at 30 steps, ~327K tokens consumed

This is the **content invisibility** failure pathway documented in Pilot 4 — identical to Claude's behavior at low variant. The reviews exist in the DOM but are invisible in the a11y tree because the tabpanel association is broken.

**Rep 5 "success"**: The agent scrolls 5 times, then gives up: `send_msg_to_user("cannot complete")`. BrowserGym's fuzzy evaluator for task 24 apparently accepts "cannot complete" as matching the expected "N/A" answer (both indicate no reviewers found). This is a **vacuous truth** — correct answer for the wrong reason. The agent never read any reviews; it simply couldn't access them and gave up. This matches the Claude low-variant pattern described in the research proposal (§5.2.3).

#### Medium-low variant (0/5 = 0%): Reviews visible, empty answer

**Mechanism**: The tabpanel relationship is intact (`tablist=True, tabpanel=True`). The agent successfully reads both reviews:

- Step 1: Clicks "Reviews (2)" tab
- Step 2: Reads reviews. Reasoning: *"The reviews are now visible. There are two reviews listed. The first review is by 'Jay' and mentions 'Nothing.....everyday use.' The second review is by 'Josef Bürger' and is in German."*
- Step 3: Correctly concludes neither review mentions unfair pricing. Reasoning: *"The first review by 'Jay' mentions 'Nothing.....everyday use.' which does not indicate any issue with the price being unfair. The second review by 'Josef Bürger' is in German and says 'Die Haflinger sind wie beschrieben und erwartet sehr gut' which translates to 'The Haflinger is as described and very good as expected'. This review also does not mention anything about the price being unfair."*
- **Action**: `send_msg_to_user("")` — sends an **empty string**

The model's reasoning is correct but its answer formatting is wrong. It should answer "N/A" or "0" or "None" but instead sends `""`. The BrowserGym evaluator expects a fuzzy match on "N/A" and an empty string doesn't match.

**This pattern is 100% consistent across all 5 reps** — identical reasoning, identical empty-string answer. This is deterministic model behavior, not stochastic.

#### Base variant (0/5 = 0%): Same empty-answer bug

Identical to medium-low: the agent reads both reviews, correctly identifies that neither mentions unfair pricing, and sends `""`.

**Exception — Rep 4**: The agent sends `"Jay, Josef Bürger"` — listing ALL reviewers instead of only those who mention unfair pricing. This is a **reasoning error**: the model misunderstands the task as "list all reviewers" rather than "list reviewers who mention unfair pricing." This occurs in 1/5 base reps and 1/5 high reps.

#### High variant (0/5 = 0%): Same empty-answer bug

Identical pattern. 4/5 reps send `""`, 1/5 (rep 3) sends `"Jay,Josef Bürger"` (same reasoning error as base rep 4).

### Task 24 Root Cause

**Primary failure (18/20 non-low traces)**: Llama 4 Maverick has a **response formatting deficiency** for negative-result queries. When the correct answer is "none found" / "N/A", the model sends an empty string instead of an explicit negative answer. Claude Sonnet handles this correctly by answering "0" or "N/A".

**Secondary failure (2/20 non-low traces)**: Llama 4 occasionally misinterprets "list reviewers who mention X" as "list all reviewers", sending reviewer names regardless of whether they mention the target topic.

**Why low appears to be the "best" variant**: The low variant's content invisibility prevents the agent from reading reviews at all. In 4/5 cases this causes timeout (failure). In 1/5 cases the agent gives up early with "cannot complete", which the fuzzy evaluator accepts as matching "N/A". This is pure luck — the agent's inability to access content accidentally produces a correct-ish answer.

**Comparison with Claude (Pilot 4)**: Claude at low variant shows the same vacuous truth pattern (1/5 success, agent answers "0" because it can't access reviews). At ml/base/high, Claude answers "0" explicitly and gets 5/5 (100%). The difference is entirely in answer formatting: Claude says "0", Llama 4 says "".

---

## Task 26: "List reviewers who mention customer service for Zoe products"

**Expected answer**: Must include both "Bob in Vegas" AND "RemyR" (string_match with must_include)
**Ground truth**: 3 reviewers mention customer service (the evaluator requires at least "Bob in Vegas" and "RemyR")

### Results Matrix

| Variant | Rep 1 | Rep 2 | Rep 3 | Rep 4 | Rep 5 | Rate |
|---------|-------|-------|-------|-------|-------|------|
| low | ❌ timeout | ❌ timeout | ❌ timeout | ❌ timeout | ❌ timeout | 0/5 (0%) |
| medium-low | ❌ "Bob in Vegas" | ❌ "Bob in Vegas" | ❌ "Bob in Vegas" | ❌ "Bob in Vegas" | ❌ "Bob in Vegas" | 0/5 (0%) |
| base | ✅ "Bob in Vegas, RemyRRemyR" | ✅ "Bob in Vegas, RemyRRemyR" | ❌ "Bob in Vegas" | ✅ "Bob in Vegas, RemyRRemyR" | ✅ "Bob in Vegas, RemyRRemyR" | 4/5 (80%) |
| high | ❌ "Bob in Vegas" | ✅ "Bob in Vegas, RemyRRemyR" | ❌ "Bob in Vegas" | ✅ "Bob in Vegas, RemyRRemyR" | ✅ "Bob in Vegas, RemyRRemyR" | 3/5 (60%) |

### Token Consumption

| Variant | Rep 1 | Rep 2 | Rep 3 | Rep 4 | Rep 5 | Avg | Steps |
|---------|-------|-------|-------|-------|-------|-----|-------|
| low | 650,066 | 650,507 | 650,507 | 650,507 | 650,507 | 650,419 | 30.0 |
| medium-low | 40,711 | 40,711 | 40,711 | 40,687 | 40,711 | 40,706 | 3.0 |
| base | 42,006 | 42,036 | 42,002 | 41,885 | 42,006 | 41,987 | 3.0 |
| high | 42,032 | 41,906 | 42,057 | 42,061 | 68,144 | 47,240 | 3.2 |

### Detailed Failure Analysis

#### Low variant (0/5 = 0%): Content invisibility → infinite scroll loop

Identical mechanism to task 24 low. The agent clicks the "Reviews (12)" tab but review content never appears in the a11y tree. All 5 reps enter a 30-step scroll loop consuming ~650K tokens each before timing out. No `send_msg_to_user` is ever called.

**Key difference from task 24 low**: Task 26 has 12 reviews (vs 2 for task 24), so the a11y tree is much larger even without review content visible. This explains the higher token consumption (650K vs 327K).

#### Medium-low variant (0/5 = 0%): Finds only 1 of 3 reviewers

**Mechanism**: The tabpanel is intact. The agent reads all 12 reviews (review keywords detected: "customer service", "poor quality", "terrible", "amazing", "rip off"). However, it consistently identifies only ONE reviewer who mentions customer service:

- Step 1: Clicks "Reviews (12)" tab
- Step 2: Scrolls to see reviews
- Step 3: Reasoning: *"I have found one reviewer, 'Bob in Vegas', who mentioned a complaint about the customer service. He stated that he called customer service and was told that there was no way to change the default setting from 2-sided printing to 1-sided printing..."*
- **Action**: `send_msg_to_user("Bob in Vegas")`

**This is 100% deterministic across all 5 reps** — the model always finds Bob in Vegas but misses RemyR and the third reviewer. The evaluator requires both "Bob in Vegas" AND "RemyR", so answering with only one fails.

**Why does medium-low consistently miss RemyR?** The medium-low variant has pseudo-compliance patches (ARIA present but handlers missing). The review content IS visible (review keywords are detected in observations). The issue is that Llama 4 reads through 12 reviews in a single observation and fails to identify all customer-service-related reviews. "Bob in Vegas" has the most explicit customer service mention (calling customer service, broken English). RemyR's mention may be more subtle or buried deeper in the review list, and Llama 4 fails to catch it.

**Critical observation**: The token counts are nearly identical between medium-low (40,706) and base (41,987) — only ~3% difference. The agent sees essentially the same content. The difference is in **comprehension**, not **perception**.

#### Base variant (4/5 = 80%): Stochastically finds 2 reviewers

At base, the agent finds "Bob in Vegas, RemyRRemyR" in 4/5 reps. The reasoning in successful traces:

*"I have found a review by 'Bob in Vegas' that mentions a complaint about Epson's customer service... Another reviewer, 'RemyRRemyR', also mentioned a [negative experience]..."*

In the 1 failure (rep 3), the reasoning is identical to medium-low — it finds only "Bob in Vegas" and stops.

**The ml→base jump is stochastic, not structural**: The observation content is essentially the same (both have tabpanel=True, both show all review keywords). The difference is that at base, Llama 4 stochastically identifies the second reviewer 80% of the time vs 0% at medium-low. This suggests a subtle difference in the a11y tree structure between medium-low and base that affects how the model processes the review list.

**Possible structural explanation**: Medium-low has pseudo-compliance patches that may slightly alter the DOM structure around reviews (e.g., buttons with `role="button"` but no handlers). While these don't affect review TEXT visibility, they may change the a11y tree layout enough to shift how Llama 4 tokenizes and processes the review content. With 12 reviews generating ~40K tokens, even small structural differences could affect which reviews the model attends to.

#### High variant (3/5 = 60%): Non-monotonic — worse than base

High variant adds enhanced ARIA (landmarks, skip-links, form labels). The agent finds "Bob in Vegas, RemyRRemyR" in 3/5 reps (60%) vs 4/5 at base (80%).

**Rep 5 is notable**: It takes 4 steps instead of 3 — the agent clicks to page 2 of reviews (bid 2288) before answering. This is the only trace across all 40 that navigates to a second review page. Token count is 68K vs ~42K for other reps. Despite the extra exploration, it still answers correctly.

**Why high < base**: The high variant's additional ARIA markup (landmarks, skip-links, form labels) adds tokens to the a11y tree observation. With 12 reviews already generating ~42K tokens, the additional semantic markup may push the model's attention budget, making it slightly less likely to catch the second reviewer. This is consistent with the "ARIA over-annotation" concern documented in the research proposal — more ARIA doesn't always help.

**This is pure stochastic variance**: 3/5 vs 4/5 is a single-trial difference. With n=5, the 95% CI for 80% is [28%, 99%] and for 60% is [15%, 95%]. These overlap completely. The high < base difference is **not statistically significant** and should not be over-interpreted.

---

## Cross-Task Comparison: Llama 4 vs Claude

### Task 24 (unfair pricing — expected "N/A")

| Variant | Llama 4 | Claude (Pilot 4) | Explanation |
|---------|---------|-------------------|-------------|
| low | 1/5 (20%) | 1/5 (20%) | Both: vacuous truth (can't access reviews, answer happens to match) |
| medium-low | 0/5 (0%) | 5/5 (100%) | Llama 4 sends "", Claude sends "0" |
| base | 0/5 (0%) | 5/5 (100%) | Same: Llama 4 sends "", Claude sends "0" |
| high | 0/5 (0%) | 5/5 (100%) | Same: Llama 4 sends "", Claude sends "0" |

**Diagnosis**: Pure model capability difference. Claude understands that "no reviewers found" should be expressed as "0" or "N/A". Llama 4 sends an empty string. The task comprehension is identical — both models correctly identify that no reviews mention unfair pricing. The failure is in answer formatting.

### Task 26 (customer service — expected "Bob in Vegas" + "RemyR")

| Variant | Llama 4 | Claude (Pilot 4) | Explanation |
|---------|---------|-------------------|-------------|
| low | 0/5 (0%) | 0/5 (0%) | Both: content invisibility, can't access reviews |
| medium-low | 0/5 (0%) | 5/5 (100%) | Llama 4 finds 1/3 reviewers, Claude finds 3/3 |
| base | 4/5 (80%) | 5/5 (100%) | Llama 4 stochastically finds 2/3, Claude finds 3/3 |
| high | 3/5 (60%) | 5/5 (100%) | Same stochastic pattern |

**Diagnosis**: Llama 4 has weaker **review comprehension** than Claude. When reading 12 reviews in a single observation (~40K tokens), Llama 4 consistently misses the more subtle customer service mentions. Claude identifies all 3 reviewers deterministically. The ml→base jump in Llama 4 is a stochastic threshold effect — the model is on the edge of finding the second reviewer, and minor a11y tree structural differences tip it one way or the other.

---

## Failure Classification

### Task 24 (20 traces)

| Failure Type | Count | Variant(s) | Description |
|-------------|-------|------------|-------------|
| Content Invisibility (A11y) | 4 | low | Reviews invisible in a11y tree → scroll loop → timeout |
| Vacuous Truth (A11y + Model) | 1 | low | Agent gives up, answer accidentally correct |
| Empty Answer (Model: F_FMT) | 13 | ml/base/high | Correct reasoning, wrong answer format ("" instead of "N/A") |
| Wrong Scope (Model: F_REA) | 2 | base/high | Lists all reviewers instead of filtering by topic |

### Task 26 (20 traces)

| Failure Type | Count | Variant(s) | Description |
|-------------|-------|------------|-------------|
| Content Invisibility (A11y) | 5 | low | Reviews invisible → scroll loop → timeout (650K tokens) |
| Incomplete Comprehension (Model: F_REA) | 8 | ml (5) + base (1) + high (2) | Finds only 1 of 3 reviewers |
| Success | 7 | base (4) + high (3) | Finds 2 of 3 reviewers (enough to pass) |

---

## Token Consumption Patterns

### Task 24

| Variant | Avg Tokens | Avg Steps | Pattern |
|---------|-----------|-----------|---------|
| low | 273,016 | 25.4 | 4 timeouts at ~327K + 1 early exit at 55K |
| medium-low | 16,522 | 3.0 | Efficient: read reviews, answer in 3 steps |
| base | 14,185 | 2.6 | Most efficient: some complete in 2 steps |
| high | 15,975 | 2.8 | Slightly more tokens than base (extra ARIA markup) |

**Low variant token inflation**: 273K / 14K = **19.5× inflation** vs base. This is the content invisibility scroll loop consuming tokens without progress.

### Task 26

| Variant | Avg Tokens | Avg Steps | Pattern |
|---------|-----------|-----------|---------|
| low | 650,419 | 30.0 | All 5 timeout at ~650K (12 reviews = larger page) |
| medium-low | 40,706 | 3.0 | Efficient but wrong answer |
| base | 41,987 | 3.0 | Nearly identical to ml |
| high | 47,240 | 3.2 | Slightly higher (1 trace with 4 steps at 68K) |

**Low variant token inflation**: 650K / 42K = **15.5× inflation** vs base.

**Key insight**: Medium-low and base have nearly identical token consumption (~41K) despite very different success rates (0% vs 80%). This proves the ml→base gap is a **comprehension** issue, not a **perception** or **token** issue. The model sees the same content but processes it differently.

---

## Conclusions

### 1. These anomalies are MODEL capability issues, not TASK-SPECIFIC interactions

Both tasks expose Llama 4 Maverick weaknesses that Claude Sonnet does not share:
- **Task 24**: Answer formatting for negative results (empty string vs "N/A")
- **Task 26**: Review comprehension at scale (missing subtle mentions in 12-review lists)

### 2. The non-monotonic patterns have specific explanations

- **Task 24 low > ml/base/high**: Vacuous truth. Content invisibility accidentally produces a correct answer 1/5 times.
- **Task 26 ml→base jump**: Stochastic comprehension threshold. The model is on the edge of finding the second reviewer; minor structural differences between ml and base tip the balance.
- **Task 26 high < base**: Not significant. 3/5 vs 4/5 with n=5 is within sampling noise.

### 3. Implications for the multi-model replication study

These results demonstrate that **model-specific failure modes can create apparent accessibility-performance interactions that are actually model artifacts**. For the CHI paper:

- Task 24 should be flagged as having a **model-specific evaluation sensitivity** — the empty-string bug is a Llama 4 idiosyncrasy that makes the task appear to have inverted accessibility effects.
- Task 26's ml→base gap is a genuine model × environment interaction, but the mechanism is comprehension quality, not accessibility perception. The model sees the same content at both variants.
- These findings strengthen the argument for multi-model replication: patterns that appear in one model but not another are model artifacts, not environmental effects.

### 4. The accessibility gradient IS present in the low variant

Despite the model-specific noise at ml/base/high, the low variant shows the expected accessibility effect:
- Task 24 low: 4/5 timeout from content invisibility (same as Claude)
- Task 26 low: 5/5 timeout from content invisibility (same as Claude)

The Plan D variant injection is working correctly — the content invisibility pathway is model-independent.

### 5. Specific errors Llama 4 makes

| Error Type | Frequency | Tasks | Description |
|-----------|-----------|-------|-------------|
| Empty answer for negative result | 13/20 task 24 non-low | 24 | Sends "" instead of "N/A"/"0" |
| Incomplete review scanning | 8/15 task 26 non-low | 26 | Finds 1 of 3 reviewers |
| Wrong task interpretation | 2/20 task 24 non-low | 24 | Lists all reviewers instead of filtering |
| Infinite scroll loop | 9/10 low traces | 24, 26 | Content invisible → scroll forever |
| Hallucination | 0/40 | — | No hallucinated content observed |

**Notable absence**: Llama 4 does NOT hallucinate review content or fabricate reviewer names. Its errors are omission-based (missing reviewers, empty answers), not commission-based. This is a qualitatively different failure mode from what might be expected.

---

## Appendix: Answer Distribution

### Task 24 — All 20 answers

| Answer | Count | Variants | Outcome |
|--------|-------|----------|---------|
| (timeout, no answer) | 4 | low × 4 | failure |
| "cannot complete" | 1 | low × 1 | success (vacuous) |
| "" (empty string) | 13 | ml × 5, base × 4, high × 4 | failure |
| "Jay, Josef Bürger" | 1 | base × 1 | failure |
| "Jay,Josef Bürger" | 1 | high × 1 | failure |

### Task 26 — All 20 answers

| Answer | Count | Variants | Outcome |
|--------|-------|----------|---------|
| (timeout, no answer) | 5 | low × 5 | failure |
| "Bob in Vegas" | 8 | ml × 5, base × 1, high × 2 | failure |
| "Bob in Vegas, RemyRRemyR" | 7 | base × 4, high × 3 | success |

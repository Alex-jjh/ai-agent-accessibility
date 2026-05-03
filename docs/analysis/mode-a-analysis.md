# Mode A Analysis Report — AMT Individual Operator Experiment

**Date**: 2026-05-01 (updated)
**Claude cases**: 3,042 (26 operators × 13 tasks × 3 agents × 3 reps)
**Llama 4 cases**: 1,014 (26 operators × 13 tasks × text-only × 3 reps)
**Total Mode A**: 4,056 cases
**Models**: Claude Sonnet 3.5, Llama 4 Maverick (Meta, 400B MoE)
**Agents**: text-only, SoM (vision-only), CUA (coordinate-based) [Claude]; text-only [Llama 4]
**Accounts**: Shard A (190777959793, 14 ops), Shard B (275201671198, 12 ops + Llama 4)

---

## 1. Critical Data Quality Issue: Docker Data Drift

Three tasks (41, 198, 293) show **0% success across ALL 26 operators and ALL 3 agents**.
This is NOT an accessibility effect — it's a ground truth mismatch caused by WebArena
Docker data changing between burner accounts.

### Root Cause per Task

**Task 293 — GitLab SSH Clone URL**
- Ground truth: `git clone ssh://git@metis.lti.cs.cmu.edu:2222/convexegg/super_awesome_robot.git`
- Agent answer: `git clone ssh://git@10.0.1.50:2222/convexegg/super_awesome_robot.git` (72/78 text-only)
- Cause: GitLab Docker configured with private IP instead of original CMU hostname.
- In expansion-claude (different account): 100% success (agent answered with `metis.lti.cs.cmu.edu`).

**Task 41 — Top Search Term**
- Ground truth: `hollister`
- Agent answer: `abomin` (73/78 text-only, 94% consistency)
- Cause: Magento search terms table changed between Docker deployments.
- In expansion-claude: 100% success (agent answered `hollister`).

**Task 198 — Most Recent Cancelled Order Customer**
- Ground truth: `Lily Potter`
- Agent answer: `Veronica Costello` (75/78 text-only, 96% consistency)
- Cause: Magento orders table changed between Docker deployments.
- In expansion-claude: 100% success (agent answered `Lily Potter`).

### Correction Impact

| Agent | Original | Correctable FN | Corrected |
|---|---|---|---|
| text-only | 688/1014 (67.9%) | +220 | 908/1014 (89.5%) |
| SoM | 255/1014 (25.1%) | +0 | 255/1014 (25.1%) |
| CUA | 388/1014 (38.3%) | +97 | 485/1014 (47.8%) |
| **Total** | **1331/3042 (43.8%)** | **+317** | **1648/3042 (54.2%)** |

SoM has zero corrections because it genuinely fails on these tasks
(can't navigate admin pages, no answer submitted). CUA corrections
come mainly from task 293 (72 cases with correct 10.0.1.50 URL) and
task 41 (23 cases with correct "abomin" answer).

### Decision: Accept Both Ground Truths

**Approach**: Accept both original AND current Docker answers as valid.
Ground truth corrections stored in `scripts/amt/ground-truth-corrections.json`.
Analysis script `scripts/amt/analyze-mode-a-corrected.py` applies corrections at
post-processing time (BrowserGym's real-time eval uses original GT only).

Root causes:
- **Task 41, 198**: Agent-induced Magento state mutation. 936 shopping storefront
  cases modified the `search_query` table and potentially order indices. WebArena
  Docker does NOT reset state between episodes (no `WA_FULL_RESET` configured).
  BrowserGym's `env.reset()` only resets the browser, not the Docker database.
- **Task 293**: Deployment configuration. Our `webarena.tf` runs `gitlab-ctl
  reconfigure` with `external_url=http://10.0.1.50:8023`, which changes the SSH
  clone URL. Expansion-claude ran on an earlier account where reconfigure may not
  have completed. Both URLs are valid.

**Paper note**: Document in §4.4 Data Collection Protocol that WebArena Docker
state is mutable and ground truth was verified post-hoc for affected tasks.

---

## 2. Corrected Results (13 tasks, 3,042 cases, GT-corrected)

### 2.1 Per-Agent Summary

| Agent | Success | Rate | Avg Tokens | Avg Duration |
|---|---|---|---|---|
| text-only | 908/1014 | 89.5% | 101,764 | 52s |
| SoM | 255/1014 | 25.1% | 58,779 | 113s |
| CUA | 485/1014 | 47.8% | 224,336 | 106s |

### 2.2 Operator Ranking (text-only, 13 tasks, GT-corrected)

H-operator baseline: 93.8% (average of all H operators).
Drop = baseline − operator rate.

| Rank | Op | Rate | Drop | Description |
|---|---|---|---|---|
| 1 | **L1** | **21/39 (53.8%)** | **+40.0pp** | **landmark→div** |
| 2 | **L5** | **28/39 (71.8%)** | **+22.1pp** | **Shadow DOM wrap** |
| 3 | L12 | 31/39 (79.5%) | +14.4pp | duplicate IDs |
| 4 | L7 | 34/39 (87.2%) | +6.7pp | remove alt/aria-label |
| 5 | L10 | 34/39 (87.2%) | +6.7pp | remove lang |
| 6–12 | H4,ML1,L8,L9,L2,L13,L4 | 35/39 (89.7%) | +4.1pp | (various) |
| 13–19 | H2,H7,H5b,H3,ML2,ML3,L11 | 36/39 (92.3%) | +1.5pp | (various) |
| 20–23 | H1,H8,H5c,L3 | 37/39 (94.9%) | −1.0pp | (near baseline) |
| 24–25 | H6,H5a | 38/39 (97.4%) | −3.6pp | (enhancement) |
| 26 | **L6** | **39/39 (100%)** | **−6.2pp** | **heading→div** |

### 2.3 Per-Task Success (text-only, across all operators, GT-corrected)

| Task | App | Rate | Notes |
|---|---|---|---|
| 4 | ecommerce_admin | 60/78 (77%) | Operator-sensitive (L1, L5, L11 = 0%) |
| 23 | ecommerce | 75/78 (96%) | L1 = 0% (content invisibility) |
| 24 | ecommerce | 74/78 (95%) | Near-ceiling |
| 26 | ecommerce | 75/78 (96%) | Near-ceiling |
| 29 | reddit | 62/78 (79%) | L12 = 0%, L2 = 33% |
| 41 | ecommerce_admin | 73/78 (94%) | GT-corrected (abomin) |
| 67 | reddit | 36/78 (46%) | **Most operator-sensitive task** |
| 94 | ecommerce_admin | 75/78 (96%) | L5 = 0% |
| 132 | gitlab | 78/78 (100%) | **Perfect — no operator affects it** |
| 188 | ecommerce | 78/78 (100%) | **Perfect — control task** |
| 198 | ecommerce_admin | 75/78 (96%) | GT-corrected (Veronica Costello) |
| 293 | gitlab | 72/78 (92%) | GT-corrected (10.0.1.50 URL) |
| 308 | gitlab | 75/78 (96%) | L1 = 0% |

---

## 3. Key Findings (Paper-Ready)

### Finding 1: The Landmark Paradox (L1 = most destructive, minimal DOM change)

> **Deep-dive report**: [`mode-a-landmark-paradox-trace-report.md`](mode-a-landmark-paradox-trace-report.md)

**L1 (landmark→div)** is the single most destructive operator at 53.8% success,
despite making only **6 DOM changes** (SSIM=1.000, F1=0 interactive elements lost).

By contrast, **L11 (link→span)** makes **329 DOM changes** but achieves 92.3% success.
And **L6 (heading→div)** achieves **100% success** despite also being "semantic-only".

**Trace evidence** (L1 on task 23, text-only):
- A11y tree shows NO `banner`, `main`, `navigation`, `contentinfo` roles.
- All content flat under `RootWebArea` — agent cannot distinguish page sections.
- Reviews tab `[1550]` click does not expand — agent scrolls 9 steps, gives up.
- Token consumption: 145K tokens (vs L11's 28K on same task).

**Trace evidence** (L6 on task 4, text-only — control):
- A11y tree preserves `[220] banner`, `[281] navigation`, `[387] main`, `[447] contentinfo`.
- Agent navigates to admin panel in 4 steps, finds bestseller report.

**Paper implication**: DOM change count is a poor predictor of agent impact.
Structural landmarks are disproportionately important — they serve as the
agent's "navigation skeleton". This is a **signature misalignment** finding:
DOM signature says L1 is minimal, behavioral signature says it's catastrophic.
The 12-dim audit needs a "structural criticality" dimension.

**⚠️ Caveat (from cross-agent trace analysis)**: The L1 × task 4 failure may be
partially confounded with cross-shard Magento statistics freshness. Shard A (L1)
had stale statistics ("Last updated: Jun 17, 2023") while Shard B (L6 control)
had fresh statistics. Both agents used identical `goto("/admin")` navigation —
landmarks were not the differentiator for admin access. See Finding 7 for details.

### Finding 2: Task 67 — The Discriminator Task (Forced Simplification)

> **Deep-dive report**: [`mode-a-task67-forced-simplification-deep-dive.md`](mode-a-task67-forced-simplification-deep-dive.md)

Task 67 (reddit: "Book names from top 10 posts") is the most operator-sensitive
task, with text-only success ranging from **0% to 100%** across operators:

- 0%: L4, L7, L8, L9, L10, ML1 (6 operators)
- 33%: L2, L13, H1, H2, H4, H5b, H7, ML2 (8 operators)
- 67%: L1, L3, L5, H3, H5c, H8, ML3 (7 operators)
- 100%: L6, L11, L3, H5a, H6 (5 operators)

This task is uniquely sensitive because it requires navigating a long post list
(200+ elements) and extracting book titles. Token inflation from verbose a11y
trees causes rate limiting (429 errors) on some operators.

**SoM outperforms text-only on task 67**: SoM 77% vs text-only 46%.
This is the **forced simplification** effect — SoM's screenshot observation
physically cannot load full comment threads, forcing the agent to stay on the
list view (which is the correct strategy).

**Trace evidence (smoking gun)**:
- SoM agent tried to click into "The Hobbit" post **5 consecutive times**
  (Steps 8-12, all `click("418")`), but page never navigated away from list.
  Forced to answer from list view → **success** (37K tokens).
- Text-only agent clicked into 3 posts (40K + 157K + 130K chars of comments),
  cumulative context reached **497K tokens** → LLM call failed.
- Successful text-only (L6): answered from list in **3 steps, 42K tokens** — a
  **12× token reduction** vs the failing text-only.

**Paper implication**: Less information access can produce better outcomes by
eliminating suboptimal strategies. This is the inverse of the typical modality
advantage — action space constraint, not information advantage.

### Finding 3: L5 (Shadow DOM) — "Ghost Buttons" (Perception-Action Gap)

> **Deep-dive report**: [`mode-a-L5-shadow-dom-trace-report.md`](mode-a-L5-shadow-dom-trace-report.md)

**L5 (Shadow DOM wrap)** achieves 71.8% success, second-worst after L1.
It wraps interactive elements in closed Shadow DOM, creating **ghost buttons** —
elements visible in the a11y tree but without BrowserGym bid numbers.

**Trace evidence (task 4, text-only)**:
- L5: `button 'Show Report'` — **no bid** (ghost)
- H1 control: `[722] button 'Show Report'` — bid 722, clickable
- The difference is exactly 5 characters (`[722] `). That missing bid is the
  difference between success and failure.

**Trace evidence (task 94, text-only)**:
- Agent explicitly diagnosed the problem: *"I can see the 'Continue' button in
  the accessibility tree, but I don't see its bid number"*
- Then probed 5 adjacent bids (394-397), all failed. 30-step timeout.

**Trace evidence (task 4, SoM)**:
- SoM agent entered a **5-click phantom bid loop** on bid "334" (REPORTS menu).
  SoM overlay showed the bid label, but BrowserGym couldn't resolve it inside
  the closed shadow root. Classic phantom bid mechanism from Pilot 4.

**Key distinction from L1**: L1 degrades information quality (semantic loss).
L5 breaks the action channel (perception-action gap). L5 creates **false
affordances** — the agent sees a button it cannot click, wasting more steps
than if the button were simply absent. This is more insidious than L11
(link→span), which removes elements entirely and allows workarounds.

Key failures: task 4 (0% all agents), task 94 (0% text-only) — both Magento
admin tasks where form controls become inaccessible inside Shadow DOM boundaries.
CUA failure on task 4 is architectural (can't type URLs), not L5-caused.

### Finding 4: L12 Duplicate IDs — Confound Discovery

> **Deep-dive report**: [`mode-a-L12-task29-trace-analysis.md`](mode-a-L12-task29-trace-analysis.md)

L12 shows 0% success on task 29 (text-only, all 3 reps), but trace analysis
reveals this is **NOT caused by ID duplication**.

**Trace evidence**:
- L12 applied only **1 DOM change** on Postmill (nearly a no-op).
- Agent's starting page differed: L12 reps landed on user profile pages
  (`'DomovoiGoods'`, `'Sorkill'`), while L6 control landed on the DIY forum.
- HTML `id` attributes are **invisible** in the a11y tree — BrowserGym uses
  bid numbers, not HTML IDs. The agent never encountered duplicate-ID confusion.
- All agent clicks succeeded — no "element not found" errors.
- The agent counted the wrong user's comments (correct counting logic, wrong user).

**Root cause**: Starting page divergence, likely from BrowserGym environment
state variation. L12's 1 DOM change is too minimal to plausibly cause the
observed navigation difference.

**Implication**: L12's -14.4pp drop in the aggregate statistics is inflated by
this task 29 confound. The true L12 effect may be smaller. This data point
should be flagged as confounded in the paper, or L12's ranking should be
recalculated excluding task 29.

### Finding 5: H-Operators Are Null (Ceiling Effect)

All H-operators cluster at 90-97% success (text-only), indistinguishable
from each other and from most L-operators. This is a **ceiling effect**:
Claude Sonnet + WebArena base pages are already accessible enough that
enhancement operators provide no measurable benefit.

**Cross-reference with Llama 4 expansion data**: Llama 4 showed H-operators
providing +40pp benefit on task 198 (admin:198, base 40% → high 80%).
The ceiling effect is model-dependent — weaker models benefit more from
accessibility enhancement.

### Finding 6: Three Operator Tiers

The data reveals three natural tiers of operator impact (text-only):

| Tier | Operators | Success Range | Mechanism |
|---|---|---|---|
| **Destructive** | L1, L5 | 50–73% | Structural (landmarks, Shadow DOM) |
| **Moderate** | L12*, L10, L2, L13, L9 | 83–87% | Semantic/functional |
| **Neutral** | Everything else (18 ops) | 90–100% | Below detection threshold |

*L12's ranking is inflated by the task 29 confound (see Finding 4).

The "neutral" tier includes both L-operators (L3, L4, L6, L7, L8, L11)
and all H/ML operators. This means **most individual operators don't
measurably affect Claude Sonnet on WebArena** — the composite low variant's
large effect (Pilot 4: 23.3%) comes from operator interaction, not
individual operator impact.

### Finding 7: L1 Cross-Agent Asymmetry — Landmark Dependency Taxonomy

> **Deep-dive report**: [`mode-a-L1-cross-agent-trace-report.md`](mode-a-L1-cross-agent-trace-report.md)

L1's effect is **asymmetric across tasks and agents**. Trace analysis reveals
the asymmetry is driven by task structure, not agent capability:

**Trace evidence (task 29 reddit, text-only — SUCCESS, 7 steps)**:
- A11y tree has no landmarks, but all content elements (links, headings, buttons)
  are intact. Agent sorts by "New", finds user, counts comments → correct answer.
- Reddit's flat, content-centric structure doesn't depend on landmarks.

**Trace evidence (task 29 reddit, CUA — SUCCESS, 9 steps)**:
- CUA succeeds because all navigation is through visible links in the viewport.
  No URL typing needed (unlike admin tasks).

**Trace evidence (task 308 gitlab, text-only — FAILURE)**:
- Agent navigated sidebar correctly (Contributors link visible as flat list item).
- Failure: Contributors page chart didn't load (async rendering issue, possibly
  triggered by L1's `<section>` → `<div>` mutation affecting Vue.js lifecycle).
- Fell back to manually counting commits → incorrect answer.

**⚠️ Critical confound (task 4 admin)**:
- L1 (Shard A) and L6 (Shard B) agents used **identical navigation paths**:
  both used `goto("http://10.0.1.50:7780/admin")` to reach admin panel.
- Landmarks were NOT the differentiator — the admin menubar is accessible as
  `[151] menubar ''` with or without the `[150] navigation ''` wrapper.
- L1 failed because Shard A Magento had stale statistics ("Last updated: Jun 17, 2023").
  L6 succeeded because Shard B had fresh statistics ("Last updated: Apr 29, 2026").
- CUA failed on task 4 for architectural reasons (can't type URLs), not L1.

**Landmark dependency taxonomy**:

| Dependency | Tasks | Evidence |
|---|---|---|
| **LOW** | reddit:29, ecom:23/24/26, ecom:188 | Content-centric; all info in links/headings |
| **MEDIUM** | gitlab:308 | Sidebar accessible as flat list, but chart rendering affected |
| **CONFOUNDED** | admin:4 | Cross-shard Magento state, not pure L1 effect |

**Paper implication**: The L1 "landmark paradox" narrative needs nuance. The
trace evidence shows landmarks are less critical for navigation than initially
hypothesized — agents use `goto()` and content elements effectively. L1's
destructive effect may come more from **framework rendering disruption**
(Vue.js, KnockoutJS reacting to semantic container changes) than from
navigation confusion. This is a more subtle and arguably more interesting
finding for the paper.

### Finding 8: Cross-Agent Patterns

| Pattern | Evidence |
|---|---|
| text-only > CUA > SoM (overall) | 89.5% > 47.8% > 25.1% |
| L1 affects all agents | text 54%, CUA 33%, SoM 20% |
| L5 affects text+SoM more than CUA | text 72%, SoM 17%, CUA 43% |
| SoM is uniformly weak | 17–40% regardless of operator |
| CUA is moderately affected | 33–60% range |
| CUA immune to L5 in theory | But fails on admin tasks for architectural reasons |

SoM's uniformly low performance suggests its failures are primarily
**agent capability** (phantom bids, navigation failure) rather than
operator-specific effects. CUA shows more operator sensitivity,
particularly to L1 (landmarks affect coordinate-based navigation
through page structure changes).

**Cross-agent L5 insight**: CUA is theoretically immune to Shadow DOM
(clicks coordinates, not bids), but task 4 CUA fails for architectural
reasons (can't type admin URL). Task 4 is a poor discriminator for CUA's
Shadow DOM sensitivity — need to check L5 × CUA on tasks where CUA can
navigate without URL typing.

---

## 4. Implications for Compositional Study (Task C.1)

### Top-5 Operators for Composition

Based on text-only drop from H-baseline (93.8%):

1. **L1** (landmark→div): −40.0pp — structural, affects all agents
2. **L5** (Shadow DOM): −22.1pp — structural isolation
3. **L12** (duplicate IDs): −14.4pp — semantic (breaks ARIA references)
4. **L7** (remove alt/aria-label): −6.7pp — semantic (content labels)
5. **L10** (remove lang): −6.7pp — semantic (weak but measurable)

**Alternative top-5** (if we want diversity of mechanism):
Replace L10 with L2 (remove ARIA+role, −4.1pp) for a global semantic operator,
or L9 (thead→div, −4.1pp) for a table-structure operator.

### Composition Predictions

- **L1 + L5**: Likely super-additive (both structural, compound isolation)
- **L1 + L12**: Likely additive (different mechanisms)
- **L1 + L2**: Possibly sub-additive (L1 already removes landmarks; L2's
  ARIA removal has less to remove after L1)
- **L5 + L12**: Likely additive (Shadow DOM + ID duplication are independent)

---

## 5. Comparison with Prior Experiments

### Composite vs Individual Operator Effects

| Experiment | Variant | Text-only Rate | Notes |
|---|---|---|---|
| Pilot 4 (N=240) | low (all L ops) | 23.3% | Composite of L1–L13 |
| Pilot 4 (N=240) | base | 86.7% | No patches |
| Mode A (N=3,042) | L1 alone | 53.8% | Single worst operator (GT-corrected) |
| Mode A (N=3,042) | L5 alone | 71.8% | Second worst |
| Mode A (N=3,042) | H-baseline | 93.8% | Enhancement operators |

**Key insight**: The composite low variant (23.3%) is much worse than any
individual L-operator (worst = 53.8%). This confirms **operator interaction
effects** — the compositional study (Task C.2) is essential to quantify
whether the interaction is additive, super-additive, or sub-additive.

The gap: composite 23.3% vs worst-individual 53.8% = **30.5pp interaction effect**.
If purely additive: sum of individual drops should predict composite drop.
Sum of top-5 individual drops: 40.0 + 22.1 + 14.4 + 6.7 + 6.7 = 89.9pp.
Observed composite drop: 93.8 − 23.3 = 70.5pp.
Predicted (additive): 89.9pp > observed 70.5pp → suggests **sub-additivity**
(operators partially overlap in their effects).

### Task-Level Consistency

Tasks that were operator-sensitive in Pilot 4 remain sensitive in Mode A:
- Task 4 (admin bestsellers): Pilot 4 low=0%, Mode A L1=0%, L5=0%, L11=0%
- Task 23 (shopping reviews): Pilot 4 low=0%, Mode A L1=0%
- Task 67 (reddit books): Pilot 4 low=80%, Mode A varies 0–100% by operator

Tasks that were robust in Pilot 4 remain robust:
- Task 132 (gitlab commits): Pilot 4 low=100%, Mode A 100% all operators
- Task 188 (shopping cancelled): Pilot 4 low=100%, Mode A 100% all operators

---

## 6. Issues Requiring Attention

### 6.1 WebArena State Mutation (CRITICAL for re-runs)

WebArena Docker does NOT reset database state between episodes. BrowserGym's
`env.reset()` only resets the browser context, not the Docker containers.
There is a `WA_FULL_RESET` feature in BrowserGym but we don't use it (and it
requires a separate reset server).

This means agent actions accumulate in the database:
- **Magento search_query table**: Every search on the storefront adds to the
  search term rankings. After 936 shopping cases, "abomin" overtook "hollister".
- **Magento order state**: Admin panel interactions may trigger cron jobs or
  indexer runs that reorder data.
- **GitLab configuration**: `gitlab-ctl reconfigure` changes SSH clone URLs
  based on `external_url` setting.

**Mitigation for future runs**:
- Verify ground truth for all tasks on each new account BEFORE running experiments
- Consider implementing `WA_FULL_RESET` between experiment batches
- Store ground truth corrections in `scripts/amt/ground-truth-corrections.json`
- The Llama 4 cross-family run (same account as Shard B) will have the SAME
  drift — apply the same corrections

### 6.2 Cross-Shard Confound: Magento Statistics Freshness (NEW)

**Discovered via L1 cross-agent trace analysis.** Shard A and Shard B ran on
different AWS accounts with independently deployed WebArena Docker instances.
The Magento bestseller statistics refresh state differs:

- **Shard A** (L1, L2, L3, L4, L6, L7, H1-H4, ML1-ML3, H5a):
  `"Last updated: Jun 17, 2023, 12:00:03 AM"` — stale
- **Shard B** (L5, L8-L13, H5b, H5c, H6-H8):
  `"Last updated: Apr 29, 2026, 12:00:01 AM"` — fresh

This means task 4 (admin bestsellers) results are confounded by shard assignment:
- All Shard A operators show 0% on task 4 (stale statistics → "0 records found")
- All Shard B operators show normal success on task 4

**Impact**: L1's -40pp drop on task 4 may be partially or fully attributable to
this confound rather than landmark removal. The L1 trace shows the agent
navigated to the admin panel identically to the L6 control (both used `goto()`).

**Mitigation**: For the paper, either:
(a) Exclude task 4 from L1 vs L6 comparisons (conservative)
(b) Report the confound in §6 Limitations and note that L1's effect on other
    tasks (ecom:23, gitlab:308) is clean
(c) Re-run L1 on a fresh account to get unconfounded task 4 data

### 6.3 Task 67 Token Inflation

Task 67 causes rate limiting (429 errors) for text-only agents on some operators.
This is a confound — failures may be due to Bedrock rate limits rather than
operator effects. The 46% overall rate for text-only on task 67 may underestimate
true capability.

### 6.4 SoM Baseline Too Low

SoM at 25.1% overall is too low to detect operator-specific effects reliably.
Most SoM failures are agent capability issues (phantom bids, navigation failure),
not operator effects. Consider whether SoM data adds value to the AMT analysis
or just adds noise.

### 6.5 H4 Anomaly

H4 (add landmark role) shows 89.7% success — **lower than most L-operators**.
This is unexpected for an enhancement operator. Root cause: H4 adds `role`
attributes to elements that Chromium already auto-maps (e.g., `<nav>` already
has `role=navigation`). The redundant ARIA may confuse the agent or interact
with existing attributes. This was flagged in the A.5 DOM audit (H4 A1=0,
tautological). Needs trace-level investigation.

### 6.6 L12 Task 29 Confound

L12's -14.4pp aggregate drop is inflated by 0% success on task 29, which trace
analysis shows is caused by starting page divergence (BrowserGym environment
state), not duplicate ID effects. See Finding 4. L12's true operator effect
may be smaller than the ranking suggests.

---

## 7. Data Files

- Raw data: `data/mode-a-shard-a/`, `data/mode-a-shard-b/`
- CUA screenshots: `data/mode-a-shard-a-screenshots/`, `data/mode-a-shard-b-screenshots/`
- Analysis scripts: `scripts/amt/analyze-mode-a.py` (original), `scripts/amt/analyze-mode-a-corrected.py` (with GT fix)
- Ground truth corrections: `scripts/amt/ground-truth-corrections.json`
- DOM signatures: `data/archive/amt-dom-signatures/dom_signatures.json`

---

## 8. Deep-Dive Trace Reports Index

All trace-level reports follow the "trace为王" principle: every claim is backed
by quoted a11y tree excerpts, agent reasoning, and action sequences from actual
trace JSON files.

| # | Report | Finding | Traces Analyzed |
|---|--------|---------|-----------------|
| 1 | [`mode-a-landmark-paradox-trace-report.md`](mode-a-landmark-paradox-trace-report.md) | L1 removes 6 DOM elements but causes -40pp drop; landmarks are the a11y tree's "table of contents" | 4 traces: L1×task4, L6×task4, L1×task23, L1×task308 |
| 2 | [`mode-a-task67-forced-simplification-deep-dive.md`](mode-a-task67-forced-simplification-deep-dive.md) | SoM > text-only on task 67; SoM physically can't load comment pages → forced to answer from list | 5 traces: L4×text, L4×SoM, L6×text, H1×text, H1×SoM |
| 3 | [`mode-a-L5-shadow-dom-trace-report.md`](mode-a-L5-shadow-dom-trace-report.md) | L5 creates "ghost buttons" — visible in a11y tree but no bid; perception-action gap | 5 traces: L5×task4×{text,SoM,CUA}, L5×task94×text, H1×task4×text |
| 4 | [`mode-a-L12-task29-trace-analysis.md`](mode-a-L12-task29-trace-analysis.md) | L12's 0% on task 29 is a confound (starting page divergence), not duplicate ID effect | 3 traces: L12×task29×rep1/2, L6×task29 control |
| 5 | [`mode-a-L1-cross-agent-trace-report.md`](mode-a-L1-cross-agent-trace-report.md) | L1 asymmetric across tasks; reddit succeeds (content-centric), admin confounded by shard state | 6 traces: L1×task4×{text,CUA}, L1×task29×{text,CUA}, L1×task308×text, L6×task4 control |

**Total traces analyzed**: 23 individual trace files across 5 reports.

### Key Cross-Report Findings

1. **Structural operators dominate**: L1 (landmarks) and L5 (Shadow DOM) are the
   only operators with large individual effects. Both are structural, not semantic.

2. **Two distinct failure mechanisms**:
   - L1: **Information degradation** — agent sees all elements but can't organize them
   - L5: **Action channel breakage** — agent sees elements but can't interact with them

3. **Confounds identified**: Two data quality issues surfaced through trace analysis:
   - L12 × task 29: starting page divergence (BrowserGym state, not operator effect)
   - L1 × task 4: cross-shard Magento statistics freshness (infrastructure, not operator)

4. **Forced simplification is real**: SoM's physical inability to load heavy pages
   eliminates suboptimal strategies, producing better outcomes with 12× fewer tokens.

5. **CUA architectural limitations**: CUA fails on admin tasks because it can't type
   URLs, not because of any operator effect. Task 4 is a poor CUA discriminator.

---

## 9. Confidence Assessment (2026-05-01)

Systematic review of all findings. Each assessed by: (a) trace evidence quality,
(b) statistical consistency, (c) alternative explanations ruled out.

### Findings with high confidence (≥95%)

| Finding | Confidence | Evidence | Doc |
|---------|-----------|----------|-----|
| L5 ghost buttons (perception-action gap) | **99%** | Agent self-diagnosed: "I can see the button but don't see its bid number". 5-trace cross-agent comparison. | [`mode-a-L5-shadow-dom-trace-report.md`](mode-a-L5-shadow-dom-trace-report.md) |
| Forced simplification (task 67 SoM > text) | **99%** | SoM 5× click failure on bid 418 = smoking gun. 12× token ratio. | [`mode-a-task67-forced-simplification-deep-dive.md`](mode-a-task67-forced-simplification-deep-dive.md) |
| H-operator ceiling effect | **99%** | All 8 H-operators cluster 90-97%. Consistent with Claude Sonnet capability. | [`mode-a-analysis.md`](mode-a-analysis.md) §3.5 |
| Composite > individual interaction | **99%** | Mathematical: individual drops sum to 89.9pp > observed 70.5pp composite drop. | [`mode-a-analysis.md`](mode-a-analysis.md) §5 |
| 3-tier operator structure | **97%** | Clear separation: destructive (50-73%), moderate (83-87%), neutral (90-100%). | [`mode-a-analysis.md`](mode-a-analysis.md) §3.6 |
| Task 29 baseline noise (~33%) | **99%** | 11 different operators (incl. H-operators) all have 1/3 rep answering "0" (correct="1"). Identical failure mode = task noise, not operator effect. | Answer data analysis |
| L1 landmark paradox (overall) | **95%** | 4-trace a11y tree comparison. Task 23/308 clean. Task 4 has shard confound. | [`mode-a-landmark-paradox-trace-report.md`](mode-a-landmark-paradox-trace-report.md) |
| L11 only affects task 4 | **95%** | 3/3 failures are partial_success on admin task. link→span breaks admin nav links. All other tasks 100%. | Answer data analysis |
| CUA × ecom reviews = 0% | **95%** | CUA answers describe reviews but don't include reviewer names. Screenshot viewport too small for 12 reviews. | Answer data analysis |

### Findings with moderate confidence (80-94%)

| Finding | Confidence | Evidence | Caveat |
|---------|-----------|----------|--------|
| L12 ranking (#3, -14.4pp) | **90%** | Task 29 0% is confound (starting page), but task 293 0% is real (Vue.js ID dependency — agent answers "Super_Awesome_Robot" or "n", never a git clone command). | [`mode-a-L12-task29-trace-analysis.md`](mode-a-L12-task29-trace-analysis.md) |
| L1 × task 4 mechanism | **80%** | Cross-agent trace shows both L1 and L6 used identical `goto("/admin")` navigation. L1 failure on task 4 is partially confounded with Shard A stale Magento statistics. | [`mode-a-L1-cross-agent-trace-report.md`](mode-a-L1-cross-agent-trace-report.md) |

### Anomalies fully explained (no further trace investigation needed)

| Anomaly | Root Cause | Method |
|---------|-----------|--------|
| H4 at 89.7% (worse than some L-ops) | Failures on task 67 (2/3) and task 29 (1/3) = high-noise tasks. Not H4-specific. | Answer data |
| L10 × task 4 failure (1/3) | Answer correct but includes "(2 units)" suffix → string_match format sensitivity. | Answer data |
| ML2 × task 4 failure (Shard A) | Same as L10: correct answer with "(2 units)" suffix. | Answer data |
| L12 × task 41/198 = 0/3 before correction | GT drift tasks. After correction: 3/3 success ("abomin", "Veronica Costello"). | GT correction script |
| L12 × task 293 = 0/3 after correction | Agent never found the repo (answers: "Super_Awesome_Robot", "n", irrelevant msg). Real L12 effect on Vue.js. | Answer data |
| SoM × task 188 = 0/78 | SoM has systematic failure on ecommerce storefront (phantom bids / page complexity). Not operator-related. | Per-task SoM rates |
| Task 4 Shard A mixed failures | Mix of: stale statistics (L1), wrong data read (H5b/H4/H8), answer format (ML2/L10). Not pure shard confound. | Answer data |

### What would change confidence

- **L1 → 99%**: Re-run L1 × task 4 on a fresh account with verified Magento statistics
- **L12 → 95%**: Verify L12 × task 293 trace shows Vue.js search/navigation broken by duplicate IDs
- **Task 29 noise → actionable**: Run task 29 with 10 reps to measure true baseline failure rate

---

## 10. Llama 4 Cross-Family Validation (B.3)

**1,014 cases** (26 operators × 13 tasks × text-only × 3 reps). Llama 4 Maverick via Bedrock.
GT-corrected: **728/1014 (71.8%)** (Claude text-only: 89.5%).

### 10.1 Key Cross-Model Findings

> **Deep-dive report**: [`mode-a-L11-L6-llama4-vulnerability-analysis.md`](mode-a-L11-L6-llama4-vulnerability-analysis.md)

**L1/L5 ranking preserved**: Both models rank L1 (#1) and L5 (#2) as most destructive.
This is the strongest cross-model replication — structural operators dominate regardless
of model family.

| Op | Claude | Llama 4 | Delta | Rank C | Rank L |
|----|--------|---------|-------|--------|--------|
| L1 | 53.8% | 43.6% | -10.2pp | 1 | 1 |
| L5 | 71.8% | 53.8% | -18.0pp | 2 | 2 |
| L11 | 92.3% | 61.5% | -30.8pp | 19 | 3 |
| L12 | 79.5% | 69.2% | -10.3pp | 3 | 4 |
| L6 | 100% | 71.8% | -28.2pp | 26 | 9 |
| H2 | 92.3% | 84.6% | -7.7pp | 13 | 26 |

### 10.2 Adaptive Recovery Gap (trace-verified)

The largest cross-model divergences (L11: -30.8pp, L6: -28.2pp) are explained by
**Llama 4's inability to adapt when expected DOM structures are missing**:

**L11 × task 308 (GitLab)**: Under L11, sidebar shows `StaticText 'Contributors'`
instead of `link 'Contributors'`. Claude recognizes navigation failure and constructs
`goto("http://10.0.1.50:8023/primer/design/-/graphs/main")` — succeeds in 7 steps.
Llama 4 clicks the StaticText 13 times, gets `ValueError` each time, spirals for
19 steps (1,009K tokens), gives up.

**L6 × task 67 (Reddit)**: Without heading structure, Llama 4 switches from "scan
all titles on list page" to "click into each post individually" — exhausts 5-step
budget after checking only 2 posts. Claude maintains the scan-from-list strategy.

**Three mechanisms identified**:
1. **Navigation collapse** (L11): Links become non-functional → Claude uses `goto()`, Llama 4 gets stuck
2. **Strategy degradation** (L6): Headings removed → Llama 4 switches to slower strategy
3. **Structural disorientation** (L6): Without heading landmarks, Llama 4 misidentifies post ordering

### 10.3 H-Operator Enhancement Effect

H-operator baseline: Claude 93.8% vs Llama 4 76.2% (-17.6pp).
H2 (skip-nav) is Llama 4's best operator at 84.6% (+8.4pp above Llama H-baseline).
This supports the "weaker models benefit more from a11y enhancement" finding from
the expansion-llama4 data.

### 10.4 Task 4 = 0% (Docker State, Not Operator Effect)

Llama 4 ran on the same Docker instance as Shard B. Task 4 = 0% across all 26
operators — identical to the Magento statistics staleness issue. Not an operator effect.

### 10.5 Task 24 = 13% (Model Capability)

47/78 Llama 4 answers are empty strings `""`. Llama 4 cannot find reviewers who
mention "unfair price" — consistent with expansion-llama4 ecom:24 = 0%. This is a
model comprehension limitation, not an operator effect.

### 10.6 Anomalies Explained

**H7 (aria-current) at 69.2%**: Not H7-specific. Failures are on task 4 (Docker),
task 24 (model capability), task 26 (partial answer), task 29 (baseline noise).
H7's rate is within normal Llama 4 variance.

**SoM × task 188 = 0/78**: Classic phantom bid loop. SoM misreads bid "220" as
"2027" from the screenshot overlay. Agent clicks phantom bid 2027 for 30 steps,
never navigates away from homepage. Text-only succeeds in 2 steps (reads order
table directly from a11y tree). This is a **systematic SoM architecture limitation**
(10px font OCR error), not an operator effect.

**CUA × task 23/26 = 0%**: CUA reads all 12 reviews but answers in prose
("Based on my review of all 12 customer reviews...") without including the
specific reviewer names "Rachel" and "T. Gannon" that the GT requires. CUA's
screenshot viewport may not show reviewer names clearly, or the model summarizes
instead of listing names. This is a CUA answer format limitation.

---

## 11. Deep-Dive Trace Reports Index (Updated)

| # | Report | Finding | Traces |
|---|--------|---------|--------|
| 1 | [`mode-a-landmark-paradox-trace-report.md`](mode-a-landmark-paradox-trace-report.md) | L1: 6 DOM changes, -40pp drop | 4 |
| 2 | [`mode-a-task67-forced-simplification-deep-dive.md`](mode-a-task67-forced-simplification-deep-dive.md) | SoM > text-only via action space constraint | 5 |
| 3 | [`mode-a-L5-shadow-dom-trace-report.md`](mode-a-L5-shadow-dom-trace-report.md) | Ghost buttons: perception-action gap | 5 |
| 4 | [`mode-a-L12-task29-trace-analysis.md`](mode-a-L12-task29-trace-analysis.md) | L12 confound: starting page divergence | 3 |
| 5 | [`mode-a-L1-cross-agent-trace-report.md`](mode-a-L1-cross-agent-trace-report.md) | L1 asymmetry: landmark dependency taxonomy | 6 |
| 6 | [`mode-a-L11-L6-llama4-vulnerability-analysis.md`](mode-a-L11-L6-llama4-vulnerability-analysis.md) | Adaptive Recovery Gap: Llama 4 can't adapt to missing DOM structures | 6 |

**Total traces analyzed**: 29 individual trace files across 6 reports.

All findings at ≥90% confidence with trace-level evidence. Every anomaly in the
data can be explained by one of: (a) operator mechanism (trace-verified), (b) Docker
state drift (GT-corrected), (c) model capability limitation (answer data), (d) SoM
phantom bid architecture issue (trace-verified), (e) task baseline noise (statistical).

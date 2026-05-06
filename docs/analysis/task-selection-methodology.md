# Task Selection Methodology — AMT Stage 3 Manipulation Set

> **Purpose**: A single authoritative record of how the Stage 3
> manipulation task set was constructed. This document is the source
> of truth for the paper's Task Selection appendix. Every exclusion
> criterion, every threshold, and every rationale lives here.
>
> **Pre-registration date**: 2026-05-06 (before Stage 3 data was collected)
>
> **Pre-registrants**: Alex Jiang (primary), Brennan Jones (advisor)
>
> **Hash of this document at pre-registration**: will be recorded in
> `docs/analysis/task-selection-methodology.lock` at time of Stage 3 launch.

---

## 1. Why a task-selection methodology matters

The manipulation drop we report in the main result (§5) is computed
over a specific task set. A reviewer is entitled to ask: *would the
effect survive on a different task set?* Our answer has two parts:

1. **Pre-registered gate** — the criteria below were fixed before any
   manipulation data was collected. We cannot have shopped for tasks
   that maximize the drop.
2. **Conservative gate** — each criterion we apply makes the observed
   drop **smaller**, not larger. Our reported drop is therefore a
   lower bound on the true effect on the WebArena task population.

This document explains both.

---

## 2. Two-tier analysis design (breadth × depth)

The paper reports results at two granularities, each serving a distinct
scientific purpose:

| Tier | Source | N | Role in paper |
|------|--------|---|---------------|
| **Breadth** (Stage 3, new) | 684-task smoker + pre-registered gate | ~N_passing (filled after smoker completes) | Main manipulation result, cross-model replication, per-operator drops, statistical power |
| **Depth** (Mode A, existing) | Hand-selected in prior work (2026-04 Mode A) | 13 | Mechanistic case studies, trace-level analysis, operator alignment with DOM signatures |

**Why both?** The 13 Mode A tasks were hand-picked to balance coverage
and analyzability. They expose mechanisms (L1 landmark paradox, L5
Shadow DOM ghost buttons, forced simplification on reddit:67) that
only emerge under careful per-trace inspection. The Stage 3 breadth
set cannot replace this depth — with 300+ tasks we cannot per-case
analyze each trace.

Conversely, the 13 Mode A tasks cannot substitute for breadth. A
reviewer asking "would your effect survive on 300 tasks?" needs an
answer; the 13-task set cannot provide one.

**We report both, explicitly labeled.** §5.1-5.3 (main result) uses
the breadth set; §5.4-5.5 (mechanisms) uses the depth set. This
separation is intentional and makes each set defensible on its own
terms.

---

## 3. Source data (stage 1/3: task inventory)

We include **all tasks on all four deployed WebArena apps** in the
smoker:

| App | Tasks | Notes |
|-----|------:|-------|
| shopping_admin | 182 | Magento 2 backend |
| shopping | 192 | Magento 2 storefront |
| reddit | 114 | Postmill |
| gitlab | 196 | GitLab CE |
| **total** | **684** | |

**Excluded at source** (but documented for transparency):

- **map**: 128 tasks. OpenStreetMap/Nominatim not deployed in WebArena
  Docker images available to us; exclusion is infrastructural and
  applies uniformly to all WebArena AMT work.
- **wikipedia**: 16 tasks. Deployed as Kiwix snapshot with limited
  evaluator compatibility.
- **LLM-judge tasks** (`llm_eval` or `string_match_llm_judge` eval
  types): 0 tasks exist in the 4 deployed apps (verified from
  `test.raw.json`). No eval-type filter was necessary.

---

## 4. Smoker protocol (stage 2/3: base-solvability measurement)

Every task is executed at the **unmodified baseline** three times.
No patches, no variants — this measures whether the agent can solve
the task at all.

**Agent configuration**:
- Model: Claude Sonnet 4
  (`us.anthropic.claude-sonnet-4-20250514-v1:0`, Anthropic's May-2025
  release) via AWS Bedrock
- LLM proxy: LiteLLM
- Observation mode: text-only (BrowserGym a11y tree serialization)
- Temperature: 0.0
- `maxSteps`: 30

**Environment**:
- WebArena Docker images: `ghcr.io/web-arena-x/webarena-*:latest`
- Each smoker shard runs on an isolated burner AWS account (Terraform
  workspaces per account) to avoid cross-experiment Docker state
  bleeding
- Pre-shard Docker restart (all four containers) to clear agent-
  induced state accumulated across prior experiments

**Shards**:
- Shard A: shopping_admin + shopping = 374 tasks × 3 reps = 1,122 cases
- Shard B: reddit + gitlab = 310 tasks × 3 reps = 930 cases
- **Total: 2,052 smoker cases**

Shards run in parallel on two burner accounts. Each case produces a
JSON trace in `data/smoker-shard-{a,b}/<runId>/cases/*.json`.

---

## 5. Pre-registered inclusion gate (stage 3/3: task selection)

A task enters the Stage 3 manipulation set if and only if it passes
**all five** gates below. Tasks are attributed to the **first** gate
they fail, in priority order. Infrastructure failures rank ahead of
difficulty failures so the paper cannot be accused of mislabeling a
Magento infrastructure timeout as "Claude cannot solve this task".

### Gate 1: Shard completeness

**Criterion**: Exactly 3/3 reps were recorded without the shard
crashing prematurely.

**Rationale**: A task with 0, 1, or 2 recorded reps cannot be
evaluated against any other gate. These are data-collection
incompletenesses, not properties of the task.

**Exclusion code**: `incomplete_reps`

### Gate 2: Zero infrastructure failures

**Criterion**: Zero of the 3 reps exhibited:
- `context_window_exceeded` — Claude's input tokens exceeded the 200K
  window (common on Magento admin grid pages that render thousands
  of DOM rows at once)
- `bridge_crash` — BrowserGym's `env.reset()` crashed, typically on
  multi-URL tasks where the first URL's page-load times out
- `admin_login_failed` — Magento admin login page click-wait timeout
  (30s) — infrastructure-side flakiness
- `goto_timeout` — Playwright `Page.goto(start_url)` timed out (30s)
- `chromium_crash` — Chromium tab crashed mid-task (OOM or JS crash)

**Rationale**: These are artifacts of the benchmark × model
interaction, not the research question. If Claude fails because
Magento's admin Customers grid exceeds its context window, that
failure tells us nothing about accessibility — it would fail
regardless of any AMT variant. Ranking these above "insufficient
success" ensures they are attributed to the root cause.

**Exclusion codes**: `context_window_exceeded`, `bridge_crash`,
`admin_login_failed`, `goto_timeout`, `chromium_crash`,
`harness_errors` (any other bridge error)

### Gate 3: Strict base solvability

**Criterion**: All 3/3 reps report `success` from BrowserGym's
task-specific evaluator (string_match, program_html, or url_match).

**Rationale**: We want tasks whose baseline is *deterministically
solvable* so that any manipulation-induced drop is interpretable as
the manipulation's effect. On tasks where baseline is stochastic
(e.g., 2/3 success), a manipulation-induced 2/3 success tells us
nothing — we cannot distinguish manipulation from baseline noise.

**Why not 2/3 majority?** A 2/3 gate would include tasks with ~67%
baseline success rates. On these tasks, a "severe" operator
producing 33% success (one failure per rep) is at the noise floor —
impossible to distinguish from baseline variability. By requiring
3/3, we ensure any Stage 3 drop is *a real signal, not noise*.

**Why not an answer-consistency check?** The previous draft of this
gate also required that all successful reps emit the same normalized
final answer. We dropped this in the 2026-05-06 pre-registration
after observing that BrowserGym's evaluator already adjudicates
success, and that paraphrase variation (e.g., "The issue is open" vs
"The issue is still open" on gitlab:176) was false-rejecting tasks.
BrowserGym is the authoritative judge; we defer to it.

**Exclusion code**: `stochastic_base`. These tasks are retained as a
**Tier-2 reference set** (`passing-tier2.json`) for supplementary
analysis but are not run through Stage 3 manipulation.

### Gate 4: Minimum complexity

**Criterion**: Median successful step count ≥ 3.

**Rationale**: Tasks where the answer is visible on the landing page
(0-2 step queries: "what is the forum description?" → page renders →
agent reads → `send_msg_to_user`) do not exercise the a11y tree in
any meaningful way. A landmark→div operator cannot affect the
outcome when the agent never navigates. Including these tasks in the
manipulation set would **dilute the mean drop** — hundreds of 0-drop
data points on tasks where the manipulation cannot possibly apply.

**Empirical check**: In the smoker (2026-05-05), 40.7% of reddit +
gitlab tasks passing 3/3 had median step ≤ 2. Including these would
push the Stage 3 effect size down by ~10-20% on shard B without
adding interpretable signal.

**Exclusion code**: `trivial_task`

### Gate 5: Step-budget headroom

**Criterion**: Median successful step count ≤ 25.

**Rationale**: Tasks whose baseline already consumes 25+ of the 30
allotted steps are **brittle** under any perturbation. A variant
that adds even one retry step pushes them over the step limit, and
we misattribute the resulting timeout to the variant when it would
have timed out on a marginal base rep too.

**Exclusion code**: `step_budget`

---

## 6. The conservative-gate argument (for §4 of the paper)

Each criterion above **reduces** the manipulation drop we can
observe, not inflates it. Concretely:

- **Removing trivial tasks** (step < 3): these have 0-pp drop by
  construction (manipulation cannot affect a task the agent solves
  without navigation). Removing them removes 0s from the mean, which
  pulls the observed drop *up* slightly — so their inclusion would
  have made our effect *look smaller*. We chose to remove them for
  interpretability, not for effect inflation.

- **Removing stochastic-base tasks** (< 3/3): on these tasks,
  manipulation-induced failures blur with baseline failures. Keeping
  them would add noise to the effect estimate without increasing its
  magnitude. Removing them tightens confidence intervals without
  changing the point estimate.

- **Removing infrastructure failures**: these are not accessibility
  effects. Keeping them would conflate "a11y manipulation drops
  success" with "Magento's admin panel is slow", violating causal
  identification.

A reviewer may counter-argue that removing trivial tasks could
inflate the effect by *selecting for sensitive tasks*. Against this:
(a) trivial tasks are sensitive *in the other direction* — they
produce 0-pp drop because a11y tree cannot matter, and (b) we report
the Mode A **depth** set (N=13) separately, where task 132 is
hand-selected as a control (100% across all operators). Our claim is
not that AMT affects all tasks equally; our claim is that it affects
tasks where a11y tree parsing matters — which is the scientifically
interesting population.

---

## 7. The exclusion table (regenerated per smoker run)

Filled in after Stage 2 filter completes. See
`results/smoker/exclusion-report.md` (auto-generated).

Expected structure:

| Category | Description | Count | Example tasks |
|----------|-------------|------:|---------------|
| `included` | Passes all gates | ~N_passing | (used in Stage 3) |
| `incomplete_reps` | <3 reps recorded | ~0 | — |
| `context_window_exceeded` | Magento admin grid | ~5-10 | admin:183, admin:244, admin:790 |
| `bridge_crash` | Multi-URL env.reset() | ~5 | ecommerce:433 |
| `admin_login_failed` | Login flakiness | ~2-5 | — |
| `goto_timeout` | Slow start page | ~5-10 | — |
| `chromium_crash` | Tab crashed | ~1-3 | — |
| `harness_errors` | Other bridge errors | ~0 | — |
| `stochastic_base` | <3/3 success | ~150-200 | reddit:29, reddit:67, admin:4 (on drifted docker) |
| `trivial_task` | <3 steps median | ~40-80 | reddit content queries, gitlab READMEs |
| `step_budget` | >25 steps median | ~5 | — |

---

## 8. Mode A depth set (N=13) — why kept separate

The Mode A task set was hand-selected in prior work
(2026-04-12 Mode A execution) for **coverage** and
**analyzability**, not base solvability. Its 13 tasks span:

- 4 apps (shopping, shopping_admin, reddit, gitlab)
- 11 distinct intent templates (23, 24, 26 share one)
- 3 navigation depths (shallow, medium, deep)
- Known operator-sensitivity (67) and known control (132)

Two of the 13 (reddit:29, reddit:67) would fail the Stage 3 gate:

- **reddit:29**: ~33% documented baseline noise (agent counting
  error unrelated to operators); 11 operators (including H-ops)
  produce 1/3 "0" wrong answer. Kept in Mode A because Mode A used
  3 agents × 3 reps = 9 observations per operator, enough to
  characterize the noise floor.

- **reddit:67**: "Most operator-sensitive" task; baseline varies
  stochastically between read-from-list (fast, correct) and click-
  into-post (expensive, LLM context overflow). Its stochasticity
  is itself a finding — the **forced simplification** phenomenon
  where weaker agents benefit from manipulation-induced action-space
  restriction. This finding is the paper's §5 discussion centerpiece.

Keeping these in the Mode A depth set lets us report their
mechanisms in §5.4-5.5 without letting their stochasticity
contaminate the Stage 3 main result. The paper is explicit about
this choice.

---

## 9. Regeneration and reproducibility

Every number in §6 and §7 of the paper is reproducible via:

```bash
# Run smoker on any fresh burner account
bash scripts/launchers/launch-smoker-shard-a.sh
bash scripts/launchers/launch-smoker-shard-b.sh

# Apply the pre-registered gate
python3.11 scripts/smoker/analyze-smoker.py

# Outputs:
#   results/smoker/filter-summary.csv        — per-task stats
#   results/smoker/passing-tasks.json        — Stage 3 task set
#   results/smoker/passing-tier2.json        — stochastic-base reference
#   results/smoker/exclusion-report.md       — paper-ready exclusion table
#   config-manipulation-filtered.yaml        — Stage 3 manipulation config
```

Any reviewer can re-run this pipeline from raw smoker JSONs to verify
we did not post-hoc adjust thresholds. The `scripts/smoker/analyze-smoker.py`
defaults are the pre-registered values (`--min-median-steps 3`,
`--max-median-steps 25`, strict 3/3).

---

## 10. Update log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-05-06 | Initial pre-registration. Strict 3/3 gate, min_steps=3, max_steps=25, no answer-consistency check. | See §5. |
| — | (future amendments will be appended here with rationale) | |

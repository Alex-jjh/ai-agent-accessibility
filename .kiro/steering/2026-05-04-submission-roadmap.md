---
inclusion: auto
---

# CHI 2027 Submission Roadmap — Text-Only Task Expansion

> **Updated**: 2026-05-10 (Stage 3 complete, both models)
> **Deadline**: 2026-09-11 (CHI 2027 submission)
> **Days remaining**: ~124
> **Strategy**: Text-only primary, SSIM visual control, CUA composite-only

> **Project-level narrative**: This roadmap documents **Phase 6 (Task-Set
> Breadth Expansion)**. For the canonical 6-phase narrative connecting
> Phase 1 pilots through Phase 6 task expansion, see
> `docs/project-phases.md`.

## 🎯 Current status (2026-05-10)

**Stage 3 manipulation complete.** Both shards finished ahead of schedule:

| Shard | Cases | Finished | Status |
|---|---|---|---|
| Llama (burner B) | 3,744/3,744 | 2026-05-09 19:16 CST | ✅ audited |
| Claude (burner A) | 3,744/3,744 | 2026-05-10 17:14 CST | ✅ audited |
| **Total** | **7,488** | ~55h wall each | 🟢 ready for analysis |

Both data sets pass sanity audit, rate-limit confound audit, and Mode A
cross-validation. See `results/stage3/{claude,llama}-download-audit.md`
for details. Key headline: **Mode A Claude bottom-5 operator ordering
(L1, L12, L5, L9, ML1) replicates with 5/5 overlap on N=48 task set.**

**Next**: Stage 4b trace-URL SSIM audit (visual control replacement for CUA).
Then joint analysis + paper §5.1-§5.3 rewrite.

---

## Strategic Decision (2026-05-04)

### What changed
After 5 rounds of AI reviewer simulation, the core weakness is **13 tasks**.
Decision: expand to **60-100 tasks** via a Smoker → Filter → Manipulate pipeline.

### What we're NOT doing
- ❌ No new CUA runs (Mode A baseline 48.2% = too noisy)
- ❌ No new SoM runs (Mode A baseline 27.7% = near random)
- ❌ No new models beyond Claude + Llama 4 (budget + diminishing returns)
- ❌ No eval-type filter at smoker stage — run ALL deployed-app tasks

### What we ARE doing
- ✅ Smoker: **684 tasks × base × text-only × 3 reps** on the 4 deployed
  WebArena apps (shopping_admin, shopping, reddit, gitlab)
- ✅ Filter: keep tasks with ≥2/3 base success + consistent answer + median steps ≤25
- ✅ Manipulate: filtered tasks × 26 operators × text-only × 3 reps × {Claude, Llama 4}
- ✅ DOM audit: filtered tasks × 26 operators × before/after screenshots (SSIM)
- ✅ Visual equivalence: SSIM replaces CUA as "visual control" evidence

### Paper narrative adjustment
- **Primary evidence**: text-only (Claude + Llama 4) on 60-100 tasks
- **Visual control**: SSIM from DOM audit screenshots (mathematical proof of visual equivalence)
- **Composite CUA**: retained for pathway decomposition (baseline 93.8%, clean)
- **Mode A CUA/SoM**: supplementary/appendix only

---

## Execution Pipeline

### Stage 1: Smoker (Base Solvability Gate) — READY TO RUN

**Configs** (generated 2026-05-05, committed):
- `config-smoker-shard-a.yaml` — shopping_admin (182) + shopping (192) = **374 tasks**
- `config-smoker-shard-b.yaml` — reddit (114) + gitlab (196) = **310 tasks**
- `data/smoker-task-ids.json` — explicit ID reference

**Task scope decision (2026-05-05)**: run ALL 684 deployed-app tasks,
not just string_match (231). Rationale:
- Eval infrastructure already handles program_html + url_match offline,
  no LLM-judge tasks exist in these 4 apps (verified)
- Larger pool = better statistical power post-filter
- Filter stage drops drifting / unsolvable tasks anyway; running them
  costs little and rules them out definitively

**Matrix**: 684 tasks × 1 base variant × text-only × 3 reps = **2,052 cases**

| Shard | Apps | Tasks | Cases | Est. wall | Est. cost |
|-------|------|------:|------:|----------:|----------:|
| A | shopping_admin + shopping | 374 | 1,122 | ~20-25h | ~$150 |
| B | reddit + gitlab | 310 | 930 | ~17-22h | ~$120 |
| **Total** | 4 apps | **684** | **2,052** | ~1.5 days (parallel) | **~$270** |

**Agent**: Claude Sonnet 4 (`claude-sonnet` alias in LiteLLM →
`us.anthropic.claude-sonnet-4-20250514-v1:0`), temperature 0.0,
maxSteps 30, text-only only.
No SoM. No CUA. No Llama 4 in smoker stage (saves budget).

**Output**: `data/smoker-shard-{a,b}/<runId>/cases/*.json`

**Regeneration**: `python3.11 scripts/smoker/generate-smoker-configs.py`
(idempotent; re-run if `test.raw.json` changes with webarena upgrade)

**Solvability gate** (applied in Stage 2):
- ≥2/3 reps succeed (majority vote)
- All successful reps emit the same final answer (normalized)
- Median successful step count ≤25 (5-step headroom below maxSteps)
- Zero harness errors (bridge/network errors disqualify the task, not the agent)

**Expected yield**: ~180-280 tasks pass (base ~30-40% solvability × answer-consistency gate).

### Stage 2: Filter

**Script**: `scripts/smoker/analyze-smoker.py` (pre-registered 2026-05-06)
**Input**: `data/smoker-shard-{a,b}/`
**Full methodology**: `docs/analysis/task-selection-methodology.md`
**Output**:
- `results/smoker/filter-summary.csv` (per-task stats + drop reason + failure-mode signals)
- `results/smoker/passing-tasks.json` (final app→task_id list, Stage 3 primary set)
- `results/smoker/passing-tier2.json` (stochastic-base reference set, not run in Stage 3)
- `results/smoker/exclusion-report.md` (**paper-ready** exclusion narrative)
- `config-manipulation-filtered.yaml` (ready-to-run Stage 3 config, auto-generated)

**Runtime**: 10-30 min on local machine after S3 download.

**Pre-registered gate** (locked 2026-05-06; amended 2026-05-07):

A task enters Stage 3 **if and only if**:

1. 3/3 reps recorded (shard completeness)
2. Zero infrastructure failures (context window, bridge crash, admin
   login timeout, goto timeout, Chromium crash, harness error)
3. **Strict 3/3 success** via BrowserGym evaluator (2/3 rejected as
   stochastic-base — retained in Tier-2 reference set)
4. Median successful step count ≥ 3 (excludes trivial "click once" queries)
5. Median successful step count ≤ 25 (5-step headroom below 30-step budget)
6. **Non-state-mutation eval** (Gate 6, added 2026-05-07): eval_types
   must not include `url_match` or `program_html`. Rationale: the
   scheduler does not reset Docker between cases, and 156 writes per
   task under the full Stage 3 matrix would accumulate drift of the
   same type that forced Mode A post-hoc GT corrections. See
   `docs/analysis/task-selection-methodology.md` §5.6 and
   `docs/analysis/mode-a-docker-confounds.md`.
7. **Non-trivial must_include** (Gate 7, added 2026-05-07): at least
   one eval token must be ≥3 characters AND not in the canned set
   {yes, no, done, none, null, true, false, n/a}. Rationale: under
   manipulation, confused agent outputs asymmetrically substring-match
   short tokens, biasing observed drops toward zero. Evidence:
   gitlab:306 in shard-B smoker passed strict 3/3 despite 2/3 reps
   emitting factually wrong prose (substring-matched `'0'` via "2023").
   See `docs/analysis/task-selection-methodology.md` §5.7.

**Tasks dropped by gate are attributed** (in priority order):

1. `incomplete_reps` → `context_window_exceeded` → `bridge_crash` →
   `admin_login_failed` → `goto_timeout` → `chromium_crash` →
   `harness_errors` (infrastructure, ranked ahead of difficulty)
2. `stochastic_base` → `trivial_task` → `step_budget`
   (task-characteristic exclusions)
3. `state_mutation` → `trivial_ref` (task-property exclusions,
   pre-registered 2026-05-07)

**No answer-consistency check** — BrowserGym's evaluator is
authoritative; paraphrase variation falsely rejected legitimate tasks
in pilot, so we defer to BrowserGym's per-rep success judgment.

**2/3 majority gate evaluated + rejected (2026-05-07)**: On shard B
alone, relaxing Gate 3 from 3/3 to 2/3 admits **0 additional tasks**
(all 10 candidates fail Gate 6 or Gate 4). Principled reason to keep
3/3 regardless of empirical gain: a 2/3 baseline has 67% success rate,
making a "severe" operator at 33% indistinguishable from baseline
variability in a 3-rep binomial. Recorded in methodology §10.

**Mode A retrospective check (2026-05-07)**: The N=13 Mode A depth
set (selected April 2026 by hand, without any formal gate) evaluated
against Gates 6+7 yields 10/13 pass. 0/13 fail Gate 6 (Mode A was
naturally info-retrieval). 3/13 fail Gate 7: reddit:29 and gitlab:132
are intentional Mode A controls (baseline-noise and operator-immune);
shopping:24 is a post-hoc discovery and produces conservative Mode A
estimates. Two independently-derived selection procedures converge
on the same notion of a11y-relevant tasks. Recorded in methodology
§8.1.

### Stage 3: Manipulate (Full AMT Experiment)

**Config**: auto-generated by Stage 2. Defaults to:
- filtered tasks × 26 operators × 3 reps × 2 models (Claude + Llama 4)
- Text-only agent only, temperature 0.0

**Ballparks** (post Gate 6+7 amendment, observed on shard B alone — shard A pending):
- If Stage 2 yields **14-30 tasks** (shard B only or near-failure shard A): 14 × 26 × 3 × 2 = **2,184 cases**, ~2-3 days wall on 1 burner, ~$150-300
- If Stage 2 yields **25-40 tasks** (realistic post-shard-A): 30 × 26 × 3 × 2 = **4,680 cases**, ~3-4 days wall, ~$300-500
- If Stage 2 yields **50-80 tasks** (upside surprise): 60 × 26 × 3 × 2 = **9,360 cases**, ~5-7 days wall, ~$600-900

**Scope correction note (2026-05-07)**: Prior estimates of ~250-350
passing tasks were formed before Gate 6+7 were added. Shard B alone
yielded 14 passing (pre-shard-A). Gate 6 alone drops ~73% of
3/3-success tasks (they are state-mutation); this was not visible
until the shard-B audit surfaced the Docker-non-reset issue. The
real Stage 3 N is breadth-constrained but still N_breadth >> 1 and
complements the N=13 Mode A depth set.

**Sharding**: duplicate the auto-generated config, split
`individualVariants` across Claude-Shard-A/B and Llama4-Shard-A/B for
parallel runs on 2 burner accounts.

### Stage 4: DOM + Visual Audit (replaces CUA as visual control)

**Motivation**: The CUA agent was originally our "pure visual" control
condition (no DOM access, only pixels). Results showed CUA baseline
varied too much across task types (Mode A: 48.2% — see
`docs/analysis/mode-a-analysis.md` §6.3) to serve as a clean visual
baseline. We replace it with two pixel-level measurements that are
**direct and objective** instead of inferring visual equivalence from
an agent's behavior:

1. **Per-operator DOM audit** — before / after screenshots of the
   same page with each operator applied in isolation, SSIM + pHash +
   WCAG contrast diff. Script: `scripts/audit-operator.ts` (existing).
   Coverage: ~300 Stage-3 tasks × 26 operators × 3 reps = ~23,400
   pixel diff pairs.
2. **Trace-URL replay audit** — for each Stage 3 case, extract every
   URL the agent visited from the trace, replay that URL under base
   and under the variant, SSIM-compare. This gives us a
   *behaviour-informed* visual equivalence measurement at every page
   the agent actually saw, not just start pages. Script:
   `scripts/visual-equiv/replay-url-screenshots.py` (existing, used
   for the Phase 7 CUA visual-equivalence track).

**Paper role**: §5.3 "Visual Control" subsection; F5 DOM heatmap;
new F10 (trace-URL-SSIM distribution) if space permits.

**Why this is stronger than CUA**: An agent's success/failure rate is
a *proxy* for visual equivalence (agent fails under visual change,
succeeds under visual equivalence). A direct pixel diff is the
measurement itself. Reviewers asking "is the visual-CUA confound
real?" get a mathematical answer, not an inferential one.

**Cost**: $0 (Playwright only, no LLM)
**Time**: ~4-6 hours wall per batch (both audits together)
**Output**: `data/dom-audit-v2/` + `data/trace-url-audit-v2/` with
SSIM distributions per operator, screenshot galleries for human
review, and SSIM CSVs for F-figures.

**Input requirements from Stage 3**: trace JSONs must preserve the
URL the agent observed at each step. Confirmed — `src/runner/agents/
executor.ts` embeds `Current URL: ...` in every observation and
`[screenshot only] {url}` for vision modes. No runner changes needed.

**Dependencies on prior work**: `analysis/cua_failure_trace_validation.py`
provides the trace signature extraction logic; re-usable for Stage 3.
Visual-equivalence plan docs in `docs/analysis/visual-equivalence-*.md`
describe the Phase 7 URL-replay harness used for Mode A data, which
we extend for Stage 3.

### Stage 5: Analysis + Paper Update

**Scripts**: existing `amt_statistics.py` + `audit-paper-numbers.py` (extended).

Tasks:
1. Compute per-operator significance on expanded task set
2. Recompute signature alignment with more data points
3. Verify compositional results still hold (or re-run C.2 on expanded tasks)
4. Update all paper numbers
5. Regenerate figures F4-F9
6. **Trace-URL-replay SSIM audit** — replaces CUA as visual control
   (see Stage 4). Must complete before paper §5.3 is finalized.

---

## 🚨 Don't forget after Stage 3: Trace-URL replay audit

**Pre-registered**: 2026-05-06 (alongside the smoker gate).

The CUA agent was originally our visual control condition; results
showed it was too noisy at baseline (48.2%) to cleanly attribute the
visual component of the manipulation drop. We replace CUA with a
**trace-URL replay audit**:

1. For each Stage 3 case, parse the trace JSON and extract the full
   URL list the agent observed (`Current URL: ...` in text-only
   mode, `[screenshot only] {url}` in vision modes).
2. For each unique URL in that list, replay under both base and
   variant in a headless Playwright context, capture full-page
   screenshots.
3. Compute SSIM, pHash distance, and WCAG contrast delta per URL.
4. Aggregate per operator → SSIM distribution figure.

**Scripts** (all existing from Phase 7 Mode A work):
- `scripts/visual-equiv/replay-url-screenshots.py` — replay harness
- `analysis/visual_equivalence_analysis.py` — SSIM aggregation
- `analysis/visual_equivalence_gallery.py` — human review gallery
- `analysis/cua_failure_trace_validation.py` — trace signature
  extraction (re-usable for new data)

**Why this matters for the paper**: Reviewer question — "Is part of
your reported manipulation drop a visual confound rather than
semantic/functional?" The trace-URL audit produces a **direct**
per-operator pixel-equivalence measurement, turning the visual-control
story from agent-inferential (CUA passes/fails) to pixel-empirical
(SSIM distribution). This is a strictly stronger argument.

**Blockers / pre-conditions**:
- ✅ Trace JSONs already embed URLs (confirmed in executor.ts)
- ✅ Replay harness exists (`replay-url-screenshots.py`, used for
  Phase 7 CUA work)
- ⬜ Stage 3 data must complete first
- ⬜ SSIM batch must run on a burner with Playwright + SSIM deps

**Do not skip this.** The alternative — keep CUA as the visual
control — is what we rejected in the 2026-05-04 rescope. If we skip
the SSIM audit too, we have *no* visual control in the paper.

See `docs/analysis/visual-equivalence-validation.md` for the Phase 7
precedent (77.8% of Mode A low CUA failures match the link→span
trace signature), and `docs/analysis/visual-equivalence-plan.md` for
the full architecture.

---

## Docker State Management

Key lesson from Mode A: **no per-episode DB reset** means state drifts
across long runs. Mode A paid for this with post-hoc GT corrections
on tasks 41, 198, 293.

**Smoker stage risk is lower** (base variant only, no patches = no DOM
mutation), but agent's own actions (searches, clicks) can still mutate
server-side state. Strategy documented in `docs/smoker-docker-reset.md`:

- **One clean start per shard**: `docker restart` all 4 containers
  before each shard launches (~2 min per container)
- **No mid-shard resets** (would cost ~68h in pure reset time for 2,052
  cases × 2 min each)
- **Detect drift at filter stage**: the answer-consistency check
  compares literal final answers across reps; any disagreement drops
  the task. This catches DB drift where summary stats would miss it.

Escalation: if >20% of tasks drop for `answer_drift`, the container
restart didn't stick and we re-run affected shards with hard resets.

---

## Paper Writing Tasks (parallel with experiments)

### Immediate (this week, 05-05 → 05-11)

| Task | Owner | Status |
|------|-------|--------|
| Screenshot audit (existing data, L1/L5/L6/L11) | Alex | ⬜ |
| Send PDF + change summary to Brennan | Alex | ⬜ |
| Adjust paper narrative: CUA → supplementary, SSIM → primary visual control | Kiro | ⬜ |
| Deploy new burner, reset Docker, launch smoker shards | Alex | ✅ (05-05) |

### After Smoker completes (~05-08)

| Task | Owner | Status |
|------|-------|--------|
| Run `scripts/smoker/analyze-smoker.py` | Alex | ✅ (05-07) |
| Review drop-reason distribution in filter-summary.csv | Alex | ✅ (05-07) |
| Tune thresholds if needed; finalize task list | Alex | ✅ (05-07, Gate 6+7 added) |
| Split manipulation config into shards | Kiro | ✅ (05-07, model-split replaced app-split) |

### Manipulation + DOM audit (~05-10 → 05-22)

| Task | Owner | Status |
|------|-------|--------|
| Run Stage 3 Claude text-only shards (A+B, 48 tasks × 26 ops × 3 reps) | Alex + Kiro | ✅ 2026-05-10 17:14 CST (3,744 cases, 89.5% success) |
| Run Stage 3 Llama 4 text-only shards (same matrix) | Alex + Kiro | ✅ 2026-05-09 19:16 CST (3,744 cases, 67.4% success) |
| Download + sanity audit Stage 3 data | Kiro | ✅ 2026-05-10 (both audited, 0 hard confounds, Mode A ordering replicates) |
| Run Stage 4a: per-operator DOM audit (`audit-operator.ts` batch) | Kiro | ⬜ |
| **Run Stage 4b: trace-URL replay SSIM audit** — replaces CUA as visual control | Kiro | ⬜ 🚨 **NEXT** |
| Analyze manipulation + audit results; regenerate F4-F9, add F10 if needed | Kiro | ⬜ |
| Update paper numbers with new task set | Kiro | ⬜ |

### Pre-submission (August)

| Task | Owner | Status |
|------|-------|--------|
| Brennan review + feedback incorporation | Alex + Brennan | ⬜ |
| Figure readability check (print PDF) | Alex | ⬜ |
| Supplementary materials package | Kiro | ⬜ |
| Final number audit | Kiro | ⬜ |
| LaTeX format (submission template) | Kiro | ⬜ |
| CHI 2027 submission | Alex | ⬜ Deadline: 09-11 |

---

## Budget Tracker

| Item | Spent | Remaining |
|------|------:|----------:|
| Pilot 1-4 + expansion (historical) | ~$2,000 | — |
| Mode A + C.2 (current data) | ~$3,000-4,000 | — |
| Smoker (Stage 1) | ~$270 | — |
| **Stage 3 manipulation (Claude + Llama 4, 48 tasks × 26 ops × 3 reps × 2 models = 7,488 cases)** | **~$400** (actual) | — |
| DOM audit (Stage 4, no LLM) | — | $0 |
| **Total** | **~$5,700** | **$5K ceiling → under budget** |

Stage 3 final scope (2026-05-10):
- **48 passing tasks** (ecom 22 + admin 12 + gitlab 13 + reddit 1)
- 48 × 26 ops × 3 reps × 2 models = **7,488 cases**
- Actual cost: Claude ~$225 + Llama 4 ~$175 ≈ **$400**
- Wall time: ~55h per shard (run in parallel on 2 burners)
- Data: `data/stage3-claude/` + `data/stage3-llama/` (289 MB + 289 MB)

---

## Key Files (as of 2026-05-05)

### New this week
| File | Purpose |
|------|---------|
| `scripts/smoker/generate-smoker-configs.py` | Generator for both shard configs |
| `scripts/smoker/analyze-smoker.py` | Stage 2 filter + Stage 3 config emitter |
| `scripts/smoker/README.md` | Pipeline documentation |
| `scripts/launchers/launch-smoker-shard-a.sh` | Shard A nohup launcher |
| `scripts/launchers/launch-smoker-shard-b.sh` | Shard B nohup launcher |
| `config-smoker-shard-a.yaml` | 374-task smoker config (generated) |
| `config-smoker-shard-b.yaml` | 310-task smoker config (generated) |
| `scripts/smoker/smoker-task-ids.json` | Task ID reference per app |
| `docs/smoker-docker-reset.md` | Pre-shard reset procedure |

### Existing (referenced)
| File | Purpose |
|------|---------|
| `scripts/amt/audit-paper-numbers.py` | Reproducibility audit (28/28 paper numbers) |
| `analysis/amt_statistics.py` | Inferential statistics |
| `scripts/runners/run-pilot3.ts` | Main experiment runner |
| `task-site-mapping.json` | Task ID → site mapping |
| `test.raw.json` | WebArena 812-task definitions |

---

## Reviewer Concern Resolution

| Concern | Old resolution | New resolution |
|---------|---------------|----------------|
| 13 tasks too few | Power analysis + operator-centric argument | **60-100 tasks via smoker pipeline** |
| CUA baseline 48.2% | Explained in limitations | **CUA removed from Mode A primary; SSIM replaces as visual control** |
| SoM baseline 27.7% | Supplementary only | **Unchanged — supplementary only** |
| Docker state drift | Post-hoc GT correction | **Pre-shard restart + answer-consistency filter** |
| Ecological audit thin (34 sites) | Renamed "probe" | Optional: expand to 100+ sites if time permits |
| All other concerns | Already addressed in paper | Unchanged |

---

## Timeline

| Period | Activity |
|--------|----------|
| **05-05** | ✅ Generate smoker configs + analyzer + docs |
| **05-05 → 05-06** | ✅ Deploy burner accounts, docker reset, launch shards A + B |
| **05-06 → 05-07** | ✅ Smoker runs (684 tasks × 3 reps, parallel shards) |
| **05-06** | ✅ Gate pre-registered (strict 3/3 + min-step 3); analyzer updated |
| **05-07** | ✅ Gate 6+7 amended (state-mutation + trivial-ref) after trace audit |
| **05-07 → 05-08** | ✅ Analyze smoker with locked gate → 48 passing tasks; generate manipulation config |
| **05-07 → 05-10** | ✅ Stage 3 manipulation (Claude + Llama 4, parallel on 2 burners, ~55h each) |
| **05-10** | ✅ Both shards downloaded + audited (0 hard confounds, 5/5 Mode A overlap Claude) |
| **05-10 → 05-13** | **→ Stage 4b trace-URL SSIM audit (next)** + Stage 4a DOM audit |
| **05-13 → 06-07** | Update paper with Stage 3 numbers, regenerate F4-F9, add F10 if needed |
| **06-07 → 07-14** | Brennan review cycle |
| **07-14 → 08-14** | Optional enhancements (ecological audit, polish) |
| **08-14 → 09-11** | Final preparation + submission |

---

## Mantras

1. **Text-only is king** — cleanest signal, cheapest to run, most sensitive to semantic changes
2. **SSIM > CUA** — mathematical proof of visual equivalence beats noisy agent inference
3. **Smoker first** — never manipulate a task you haven't verified is base-solvable
4. **Strict 3/3 over majority** — baseline stochasticity would blur manipulation signal. Tier-2 (2/3) retained as reference set.
5. **Min steps ≥ 3** — trivial "click once" queries cannot exhibit variant effects; exclude to avoid diluting the mean drop
6. **Operator-centric** — our unit of analysis is the operator (26), not the task
7. **Conservative gate = lower bound** — each exclusion *reduces* the observed effect, so our reported drop is a floor, not a ceiling
8. **Breadth × Depth** — ~300 new tasks for statistical power; 13 Mode A tasks for mechanism. Neither replaces the other.
9. **Pre-register before data** — gate criteria locked 2026-05-06 before Stage 3 collection. Defensible against post-hoc threshold shopping.
10. **Run the full 684** — let the filter drop what doesn't belong; never prejudge eligibility upstream
11. **Document every exclusion** — `results/smoker/exclusion-report.md` is the paper's chain of custody
12. **Budget is finite** — $5K ceiling; Claude + Llama 4 on ~300 tasks fits within.

---

## Paper Narrative Commitments

### Two-tier analysis design (§4.2 + §5)

The paper reports results at two granularities, each with a
distinct scientific role and task set:

| Tier | Source | N | Purpose | Paper section |
|------|--------|--:|---------|---------------|
| **Breadth** | Stage 3 (new) | ~N_passing | Main manipulation drop, cross-model replication, statistical power | §5.1-5.3 |
| **Depth** | Mode A (existing, 13 hand-picked) | 13 | Mechanistic case studies, trace-level analysis, signature alignment | §5.4-5.5 |

Both sets are fully documented in
`docs/analysis/task-selection-methodology.md`. The two tiers are
**complementary**: breadth answers "does the effect generalize?",
depth answers "why does the effect occur?".

### Task-selection transparency (§4 Experimental Setup + Appendix X)

Chain of custody documented explicitly:

- **812** total WebArena tasks
- **812 → 684**: excluded `map` (128, not deployed) and `wikipedia`
  (16, Kiwix snapshot with limited evaluator compatibility)
- **684 → N_passing**: base-solvability smoker + pre-registered gate
  (see §5 of methodology doc for each of 5 criteria)
- Each excluded task attributed to a named category; infrastructure
  failures ranked ahead of difficulty failures so reviewers see root
  cause, not symptom
- **Pre-registered 2026-05-06** before Stage 3 data was collected;
  `scripts/smoker/analyze-smoker.py` defaults are the locked values

### Conservative-gate argument (defensive framing)

Each inclusion criterion **reduces** the observed drop, not inflates
it:

- **Excluding trivial tasks** (median < 3 steps): these contribute
  0-pp drop by construction (manipulation cannot affect a task
  solved without navigation). Including them would *dilute* the
  effect, not amplify it.
- **Excluding stochastic-base tasks** (< 3/3): these add baseline
  noise that blurs with manipulation signal. Including them would
  widen confidence intervals.
- **Excluding infrastructure failures**: these are artifacts of
  benchmark × model interaction, not accessibility effects.

Our reported Stage 3 manipulation drops are therefore **lower bounds**
on the true effect on the WebArena task population. A less
conservative gate (2/3 majority, no step floor) would produce a
larger observed drop but at the cost of interpretability.

### Why this matters (reviewer pre-empt)

Reviewer: "Why N_passing tasks and not 684?"

Answer (short, paper-ready):
> "We applied a pre-registered conservative gate (2026-05-06, before
> Stage 3 data collection) excluding (a) trivial queries where a11y
> tree parsing cannot matter, (b) stochastic-base tasks where baseline
> noise would blur manipulation signal, and (c) infrastructure
> failures unrelated to accessibility. Each exclusion is attributed
> to a named category in Appendix X. These exclusions *reduce* the
> observed drop; our estimate is a lower bound. A complementary
> depth set (Mode A, N=13) provides mechanistic case studies
> including two tasks (reddit:29, reddit:67) that exhibit stochastic
> baselines and are therefore excluded from the breadth set but
> retained as qualitative evidence."

Reviewer: "Why keep reddit:67 in depth when it fails your gate?"

Answer:
> "reddit:67 is the source of our forced-simplification finding
> (§5.5). Its stochastic baseline is itself the finding, not a data
> quality concern: different baseline strategies (read-from-list vs
> click-into-post) produce different success trajectories, and
> low-variant manipulation collapses the action space onto the
> faster strategy. We report it in the depth set with full trace
> evidence; we do not include it in the breadth set because its
> stochastic baseline would make main-result confidence intervals
> uninterpretable."


---

## §X. Stage 3 headline numbers (locked 2026-05-10)

Stage 3 breadth experiment complete. Authoritative numbers for paper §5.1-§5.3:

### Overall

| Model | N | Success | p50 steps | p50 tokens |
|---|---:|---:|---:|---:|
| Claude Sonnet 4 | 3,744 | **89.5%** | 6 | 106K |
| Llama 4 Maverick | 3,744 | **67.4%** | 5 | 71K |
| **Combined** | **7,488** | 78.4% | — | — |

Cross-model gap: **+22.1pp** (matches Mode A's 89.5% vs 71.8% pattern).

### Per-operator (bottom-5 most destructive)

| | Claude | Llama | Mode A Claude (ref) | Mode A Llama (ref) |
|---|---:|---:|---:|---:|
| L1  | 63.9% | 45.8% | 62% | 46% |
| L9  | 79.2% | 55.6% | 80% | 55% |
| L5  | 80.6% | 56.2% | 81% | 57% |
| L12 | 84.0% | 68.8% | 82% | 68% |
| L11 | 89.6% | 56.2% | 97% | 52% |
| ML1 | 86.8% | 68.1% | 85% | 68% |

**Claude Mode A overlap: 5/5 (L1, L9, L5, L12, ML1).**
**Llama Mode A overlap: 4/5 (L1, L5, L9, L11; ML2 vs L2 at #5).**

### Key findings that replicate at N=48

1. **L1 Landmark Paradox**: still the single most destructive operator in
   both models. -25.6pp Claude, -24.0pp Llama from the overall mean.
2. **L5 Shadow DOM**: 2nd or 3rd most destructive in both.
3. **L11 adaptive recovery gap**: Claude 89.6% vs Llama 56.2% = **+33.4pp**
   gap. This is the cleanest cross-model finding and the core evidence for
   "agent capability × environment quality" interaction.
4. **H-operator ceiling**: 93-94% Claude, 67-75% Llama. Enhancements don't
   lift Claude (already ceiling) but also don't lift Llama (capability floor
   above A11y floor). **Mode A-confirmed in both directions.**
5. **Sub-additivity in composition** (from C.2 existing data): individual
   operator drops sum > observed composite drop, consistent with failure-
   pathway saturation.

### Known limitations (to document in §6)

- **8 Llama-floor tasks** (Llama-4 capability floor, not operator effect):
  gitlab:316, ecommerce_admin:1, ecommerce_admin:187, ecommerce:230,
  gitlab:788, gitlab:314, ecommerce:47, ecommerce:26. All pass smoker gate
  on Claude, fail on Llama. Claude has only **1** such task (ecommerce:334).
- **L5 rate-limit clustering**: 9.0% of Claude L5 cases hit 429s (Shadow-DOM
  → long trace → TPM). Within-op correlation p<0.001; across-op correlation
  ρ=−0.01 (non-significant). L5 mechanism already documented in Mode A;
  this is a consequence, not a cause. Paper text drafted in
  `results/stage3/claude-download-audit.md` §4.3.

### Derived files (reproducible)

```bash
# Sanity + rate-limit audits (per model)
python3.11 scripts/stage3/sanity-check.py          --data-dir data/stage3-claude --label Claude
python3.11 scripts/stage3/flag-pathological-tasks.py --data-dir data/stage3-claude --label Claude
python3.11 scripts/amt/audit-rate-limit-confound.py \
  --data-dir data/stage3-claude \
  --log-file data/stage3-claude/stage3.log \
  --label "Stage 3 Claude" \
  --out results/stage3/rate-limit-audit-claude.md
```

Audit outputs: `results/stage3/{sanity-*.txt, pathological-*.txt,
rate-limit-audit-*.md, {claude,llama}-download-audit.md}`.

---

## §Y. Next phase: Stage 4 (visual + DOM audits)

**Goal**: Replace CUA as the visual control with direct pixel-level
measurement (SSIM/pHash) + per-operator DOM-change audit. This closes
the §6 "visual confound" reviewer question decisively.

### Stage 4a: Per-operator DOM signature audit

**What**: Run `scripts/audit-operator.ts` × 26 operators × 48 Stage-3
tasks × 3 reps = 3,744 DOM audits. Each produces the 12-dim DOM
signature vector (D1-3, A1-3, V1-3, F1-3) we already have from Mode A
(results/amt/dom_signature_matrix.csv).

**Why re-run**: Mode A DOM audit covered 13 tasks × 26 ops = 338 audits.
Stage 3's 48 tasks × 26 ops = 1,248 task×op × 3 reps = 3,744 audits.
More tasks = more robust per-operator means.

**Cost**: $0 (Playwright only)
**Time**: ~6-8h wall on one EC2 (could parallelize across burners)
**Output**: `results/amt/dom_signature_matrix_stage3.csv`

**Status**: ⬜ not blocked; can run any time before paper rewrite.

### Stage 4b: Trace-URL replay SSIM audit (🚨 the important one)

**What**: For each of the 7,488 Stage 3 cases:
1. Parse trace JSON, extract full URL list the agent observed
2. Dedupe URLs across cases (expect ~200-400 unique URLs)
3. Replay each unique URL under base + each of 26 variants
4. Capture full-page screenshots, compute SSIM / pHash / WCAG contrast
5. Aggregate per operator → F10 visual-equivalence distribution

**Why critical for paper**: Reviewer question "is part of your manipulation
drop a visual confound?" gets a **direct pixel-diff answer**, not an
inferred-from-agent-behavior one. This is the stronger form of the
argument that led us to rescope away from CUA.

**Scripts** (all existing from Phase 7 Mode A):
- `scripts/visual-equiv/replay-url-screenshots.py` — replay harness
- `analysis/visual_equivalence_analysis.py` — SSIM aggregation
- `analysis/visual_equivalence_gallery.py` — human review gallery
- `analysis/cua_failure_trace_validation.py` — trace URL extraction

**Input requirements**: ✅ confirmed — trace JSONs embed `Current URL: ...`
in every text-only observation and `[screenshot only] {url}` in vision
modes. No runner changes needed.

**Cost**: $0 (Playwright only)
**Time**: ~4-8h wall depending on unique URL count
**Output**:
- `results/stage3/trace-url-ssim.csv`
- `figures/F10_trace_url_ssim.{png,pdf}`
- Human-review gallery HTML for spot-checking

**Status**: ⬜ **this is the immediate next task.**

### Stage 4 → 5 sequencing

1. **Stage 4a (DOM audit)** — can run tonight/tomorrow, no dependencies
2. **Stage 4b (SSIM audit)** — run after Stage 4a if we want to reuse the
   URL list, or independently
3. **Analysis pipeline** (post 4a+4b):
   - Update D.1 matrix with Stage 3 DOM signatures
   - Update D.2 matrix with Stage 3 behavioral drops
   - Regenerate D.3 signature alignment
   - Regenerate F4-F9 with N=48 numbers; add F10 SSIM distribution
   - Update `scripts/amt/audit-paper-numbers.py` to include Stage 3
4. **Paper rewrite** (§5.1-§5.3): Stage 3 breadth as primary, Mode A
   as depth case studies. Target 06-07 first draft.

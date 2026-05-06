---
inclusion: auto
---

# CHI 2027 Submission Roadmap — Text-Only Task Expansion

> **Updated**: 2026-05-05 (afternoon session)
> **Deadline**: 2026-09-11 (CHI 2027 submission)
> **Days remaining**: ~129
> **Strategy**: Text-only primary, SSIM visual control, CUA composite-only

> **Project-level narrative**: This roadmap documents **Phase 6 (Task-Set
> Breadth Expansion)**. For the canonical 6-phase narrative connecting
> Phase 1 pilots through Phase 6 task expansion, see
> `docs/project-phases.md`.

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

**Pre-registered gate** (locked 2026-05-06 before Stage 3 data collected):

A task enters Stage 3 **if and only if**:

1. 3/3 reps recorded (shard completeness)
2. Zero infrastructure failures (context window, bridge crash, admin
   login timeout, goto timeout, Chromium crash, harness error)
3. **Strict 3/3 success** via BrowserGym evaluator (2/3 rejected as
   stochastic-base — retained in Tier-2 reference set)
4. Median successful step count ≥ 3 (excludes trivial "click once" queries)
5. Median successful step count ≤ 25 (5-step headroom below 30-step budget)

**Tasks dropped by gate are attributed** (in priority order):

1. `incomplete_reps` → `context_window_exceeded` → `bridge_crash` →
   `admin_login_failed` → `goto_timeout` → `chromium_crash` →
   `harness_errors` (infrastructure, ranked ahead of difficulty)
2. `stochastic_base` → `trivial_task` → `step_budget`
   (task-characteristic exclusions)

**No answer-consistency check** — BrowserGym's evaluator is
authoritative; paraphrase variation falsely rejected legitimate tasks
in pilot, so we defer to BrowserGym's per-rep success judgment.

### Stage 3: Manipulate (Full AMT Experiment)

**Config**: auto-generated by Stage 2. Defaults to:
- filtered tasks × 26 operators × 3 reps × 2 models (Claude + Llama 4)
- Text-only agent only, temperature 0.0

**Ballparks**:
- If Stage 2 yields **80 tasks**: 80 × 26 × 3 × 2 = **12,480 cases**, ~3-5 days wall, ~$800-1,200
- If Stage 2 yields **120 tasks**: 120 × 26 × 3 × 2 = **18,720 cases**, ~5-7 days wall, ~$1,200-1,800

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
| Deploy new burner, reset Docker, launch smoker shards | Alex | ⬜ |

### After Smoker completes (~05-08)

| Task | Owner | Status |
|------|-------|--------|
| Run `scripts/smoker/analyze-smoker.py` | Alex | ⬜ |
| Review drop-reason distribution in filter-summary.csv | Alex | ⬜ |
| Tune thresholds if needed; finalize task list | Alex | ⬜ |
| Split manipulation config into shards | Kiro | ⬜ |

### Manipulation + DOM audit (~05-10 → 05-22)

| Task | Owner | Status |
|------|-------|--------|
| Run Stage 3 Claude text-only shards (A+B, ~300 tasks × 26 ops × 3 reps) | Alex + Kiro | ⬜ |
| Run Stage 3 Llama 4 text-only shards (same matrix) | Alex + Kiro | ⬜ |
| Run Stage 4a: per-operator DOM audit (`audit-operator.ts` batch) | Kiro | ⬜ |
| **Run Stage 4b: trace-URL replay SSIM audit** — replaces CUA as visual control | Kiro | ⬜ 🚨 critical |
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
| **Smoker (Stage 1)** | ~$270 (running) | — |
| **Manipulation (Stage 3)** — Claude + Llama 4 on ~300 tasks | — | **~$3,500-4,500** |
| DOM audit (Stage 4, no LLM) | — | $0 |
| **Total** | ~$5,200-6,200 | **~$3,500-4,500** |

Stage 3 scope (pre-gate estimate):
- Expected passing tasks: ~250-350 (pending smoker completion)
- Cases: ~300 × 26 operators × 3 reps × {Claude, Llama 4} = **~46,800**
- Budget: ~$3,700 at Claude Sonnet 4 + Llama 4 Bedrock rates
- Buffer: $800-1,300 within your $5K ceiling

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
| **05-05** | ✅ Generate smoker configs + analyzer + docs (DONE) |
| **05-05 → 05-06** | Deploy burner accounts, docker reset, launch shards A + B |
| **05-06 → 05-07** | Smoker runs (parallel shards, ~1-1.5 days wall) |
| **05-06** | ✅ Gate pre-registered (strict 3/3 + min-step 3); analyzer updated |
| **05-07 → 05-08** | Analyze smoker with locked gate, generate manipulation config |
| **05-08 → 05-15** | Stage 3 manipulation (Claude + Llama 4, parallel shards) |
| **05-13 → 05-18** | Stage 4a DOM audit + Stage 4b **trace-URL SSIM audit** (parallel with late Stage 3 shards) |
| **05-18 → 06-07** | Update paper with new data, compress pages, new figures |
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

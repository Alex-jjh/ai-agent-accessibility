# AI Agent Accessibility Platform — Project Steering

## Project Overview

Empirical research platform studying web accessibility vs AI agent task success.
Dual-track: Track A (WebArena controlled experiments), Track B (HAR replay ecological survey).
Six modules: Scanner, Variants, Runner, Classifier, Recorder, Analysis (Python).

## Current Status

Tasks 1–22 complete (all 6 modules implemented, 334 TS + 67 Python tests passing).
Scanner verified on real websites (EC2 + local). LiteLLM → Bedrock verified.
Infrastructure: private subnet + SSM (no public access, burner account compliant).
Pilot 1 completed 2026-04-01 — 54 cases, 4 successes (7.4% raw / 66.7% effective).
Root cause analysis identified 5 failure categories; 3 P0 code fixes applied and pushed.
Round 5 regression (2026-04-02): task ID mapping corrected from test.raw.json,
BrowserGym 500ms→3000ms timeout fixed, wikipedia excluded (map dependency),
agent prompt tuned for concise answers, send_msg_to_user sanitized.

Screening completed (2026-04-03):
- ecommerce_admin: 2/12 success (16.7%) — tasks 4, 14. Admin routing fixed (/admin path).
- ecommerce storefront: 3/10 success (30%) — tasks 23, 24, 26 (review search type).
- reddit: 4/9 success (44%) — tasks 27, 29, 30, 67 (forum navigation type).
- Regression v5: 3/9 (33%) — platform stable, zero crashes/timeouts/ValueError.

Shopping login fix completed (2026-04-04):
- Root cause: BrowserGym hooks ALL Playwright navigation after env.reset() +
  Magento regenerates PHPSESSID on login + Docker URL misconfiguration.
- Fix: HTTP login via Python requests (bypasses browser entirely), cookie injection
  via context.add_cookies(), reload via env.step(goto(start_url)).
- Verified: Task 47 agent sees "Sign Out", navigates to My Account, sees order history.
- Tasks 47-50 now viable for Pilot 2.

Literature-driven experiment hardening completed (2026-04-05):
- Low variant patches aligned to Ma11y [ISSTA 2024] WCAG failure operators.
  8 direct matches + 4 novel extensions (E1-E4) documented.
  3 new operators added: F42 (link→span), F77 (duplicate IDs), F55 (focus blur).
- Vision-only agent control condition implemented. ObservationMode extended to
  'text-only' | 'vision' | 'vision-only'. Vision-only agent receives screenshot
  only (no a11y tree) — serves as causal control since DOM mutations change
  semantics but not visual appearance.
- Semantic density metric defined: interactive_nodes / total_a11y_tree_tokens.
  Python module with CLI and 11 tests. Quantifies "token inflation pathway".
- Aegis failure taxonomy comparison: 6 modes vs our 12 types, 5 novel types.
- Pilot 3 config updated: 2 agents × 6 tasks × 4 variants × 5 reps = 240 runs.

Pilot 4 in progress (2026-04-07): 240 cases with Plan D variant injection.
- Plan D: context.route() + deferred patch (load+500ms) + MutationObserver guard
- Smoke test confirmed: ecom:23 low 0/1, no tablist/tabpanel in trace (goto escape blocked)
- 52/240 completed before bridge hang fix; resumed with 120s bridge timeout + vision skip
- Mid-run text-only: low 25% → ml/base/high 100% (step function replicates)
- Three-layer hang prevention: bridge 120s timeout, wall-clock 10min, vision-only skip

Open issues:
- Pilot 4 running (~188 cases remaining, ~10-12 hours)
- reddit × vision-only may still be slow (large SoM overlay on 200+ elements)
- Composite score compression persists (0.386–0.461 vs 0.00–1.00)

Pilot 3a completed (2026-04-05): 120 cases, 87/120 (72.5%).
- Monotonic gradient: low 20% → ml 86.7% → base 90% → high 93.3%
- Low vs base: χ²=29.70, p<0.0001, V=0.704. Core finding confirmed.
- Dose-response is step function: low→ml jump = 91% of total effect.
- Two failure pathways: token inflation (admin:4, reddit:67) + content invisibility (ecom:23/24/26).

Pilot 3b completed (2026-04-05/06): 240 cases (text-only + vision-only).
- Text-only replicates 3a: 71.7% overall, low vs base p<0.001.
- Vision-only failed first run (LiteLLM config not loaded), re-running.
- Variant injection race condition discovered: goto() reload clears patches non-deterministically.
  Fixed with three-layer defense (init_script + listeners + secondary verification).
- SoM overlay implemented for vision-only agent (PIL-based bid label rendering).

Next: Analyze Pilot 3b vision-only results when re-run completes.
See docs/platform-engineering-log.md for full bug catalog and analysis reports.

Pilot 4 completed (2026-04-07): 240/240 cases, N=240 full design matrix.
- Text-only: low 23.3% → ml 100% → base 86.7% → high 76.7%
- Vision-only (SoM): low 0% → ml 23.3% → base 20% → high 30%
- Primary stat: low vs base χ²=24.31, p<0.000001, Cramér's V=0.637
- Plan D verified: 33/33 goto traces show persistent degradation
- Three failure pathways: content invisibility, token inflation, phantom bids

CUA (Computer Use Agent) integration completed (2026-04-07):
- Pure coordinate-based vision agent via Anthropic Computer Use tool + Bedrock
- LiteLLM cannot forward computer_use → direct boto3 Bedrock Converse API
- Architecture: bridge self-driven (cua_bridge.py), fully decoupled from existing modes
- Smoke test: ecom:23 base, reward=1.0, 11 steps, 139K tokens, 72s
- Two rounds of code review: 11 issues found, all fixed
- Pilot 4 CUA running: 6 tasks × 4 variants × 5 reps = 120 cases

Pilot 4 CUA completed (2026-04-08): 120/120 cases, 109/120 (90.8%).
- CUA: low 66.7% → ml 100% → base 96.7% → high 100%
- Low vs base: χ²=9.02, p=0.0027, V=0.388
- Causal decomposition: text-only 63.3pp drop = ~33.3pp semantic + ~30.0pp cross-layer
- reddit:29 INVERSION: CUA 0/5 vs text-only 4/5 at low (link→span breaks navigation)
- All 10 low-variant CUA failures are cross-layer confounds (0 pure-semantic)
- admin:4 base 1 failure = UI complexity (coordinate precision), not a11y-related
- Detailed analysis: data/pilot4-cua-analysis.md

PSL expanded smoke completed (2026-04-08): 6 cases, 5/6 (83.3%).
- PSL does NOT work: aria-hidden="true" shows as `hidden=True` in BrowserGym but
  elements retain bid/role/name and are fully clickable via click(bid)
- role="presentation" on headings/landmarks also ignored in BrowserGym snapshot
- BrowserGym serialization divergence from real screen readers = publishable finding
- Detailed analysis: data/psl-expanded-smoke-analysis.md

Cross-layer confound identified — low variant patches classified:
- ✅ Pure semantic (~6 patches): alt, aria-label, lang, tabindex, heading role
- ⚠️ Cross-layer (~3 patches): label removal, thead→div
- 🔴 Functional breakage (~4 patches): link→span (deletes href), Shadow DOM

Three-layer independence framework established (2026-04-09):
- DOM semantic layer, JS behavior layer, Visual/CSS layer are independent
- Normal users perceive via visual+JS; screen readers and AI agents via DOM semantic
- Low variant breaks DOM semantic layer → all agent types affected
- ARIA annotation layer divergence: BrowserGym agents have "superpower" over real
  screen readers at ARIA level (aria-hidden elements remain clickable)
- Experimental results are conservative lower bound of true accessibility impact
- BrowserGym serialization fidelity gap affects ALL BrowserGym benchmarks
  (WebArena, VisualWebArena, WorkArena) — systematic overestimation of agent robustness

Architecture diagrams generated (2026-04-08):
- 4 figures in figures/ (matplotlib, 300dpi PNG):
  - figure1_system_architecture.png: system overview with 3-layer injection mechanism
  - figure2_axtree_pipeline.png: a11y tree processing from Chrome to agent observation
  - figure3_variant_injection.png: variant patch detail per level + agent impact matrix
  - figure4_layer_model.png: five-layer architecture (L0-L4) with bid lifecycle
- figure4_layer_model_spec.md: detailed text spec for hand-drawing the layer diagram
- Five-layer model documented: L0 Server (untouched) → L1 DOM (all patches target here)
  → L2 Blink AX Tree (auto-derived) → L3 BrowserGym (serialization + bid + SoM)
  → L4 Agent (observation + action)
- bid lifecycle: born in L3, written to L1, read via L2, serialized in L3, used by L4, resolved back to L1
- Phantom bid mechanism: variant patch replaces DOM node → bid attr lost → SoM label persists
  in screenshot → agent clicks stale bid → "Could not find element" → 20+ retry loop

Task expansion plan finalized (2026-04-12): 6 → 13 tasks across 4 apps.
- 7 new tasks selected: gitlab 132/293/308, admin 41/94/198, shopping 124
- GitLab added as 4th app (Vue.js DOM — critical for generalizability)
- 11 unique intent templates across 13 tasks (23/24/26 share template 222)
- Navigation depth: 4 shallow + 6 medium + 3 deep (was all shallow/medium)
- All string_match eval, info retrieval only, no state mutation
- Backup candidates: gitlab 349, shopping 188
- Detailed plan: docs/analysis/task-expansion-plan.md

Execution phases:
  Phase 1: GitLab smoke (132, 293, 308) — ✅ PASSED 2026-04-12
    10/12 (83.3%). Step function replicated: low 33.3% → ml/base/high 100%.
    Two failure pathways confirmed on Vue.js: structural infeasibility + token inflation.
    No Type 2 bugs. Token inflation 1.57× (vs Pilot 4 Magento 2.15×).
  Phase 2: Admin + Shopping smoke (41, 94, 198, 124) — ✅ PASSED 2026-04-12
    11/16 (68.8%). ecommerce:124 DROPPED (stale ground truth — base fails).
    Replaced with ecommerce:188 (4/4 smoke, control task — low also succeeds).
  Phase 3: Claude expansion full run — ✅ COMPLETED 2026-04-13
    140 cases (7 new tasks × 4 variants × 5 reps × text-only).
    Results: low 51.4% → ml 100% → base 100% → high 100%. Perfect step function.
    Deep dive: admin:198 low F_SIF (KnockoutJS grid invisible), gitlab:293 low F_SIF
    (search autocomplete ARIA destroyed), gitlab:308 low F_SIF (Contributors chart invisible),
    admin:94 low 3/5 (stochastic URL construction workaround, 60% success).
  Phase 4: Llama 4 cross-model replication — ✅ COMPLETED 2026-04-13
    260 cases (13 tasks × 4 variants × 5 reps × text-only, Llama 4 Maverick).
    Overall: 159/260 (61.2%). Gradient: low 36.9% → ml 61.5% → base 70.8% → high 75.4%.
    Key findings — see "Cross-Model Replication" section below.

  Phase 5: SoM expansion — ✅ COMPLETED 2026-04-14
    140 cases (7 tasks × 4 variants × 5 reps × vision-only SoM).
    Overall: 38/140 (27.1%). low 8.6% → ml 31.4% → base 34.3% → high 34.3%.
    5 failure modes: phantom bid 48%, visual misread 22%, nav failure 16%,
    exploration spiral 10%, form interaction 5%.
    gitlab:293 0% ALL variants (Vue.js search fill failure).
    ecom:188 forced simplification (low 20% > others 0%).
  Phase 6: CUA expansion — ✅ COMPLETED 2026-04-14
    140 cases (7 tasks × 4 variants × 5 reps × CUA coordinate-based).
    Overall: 116/140 (82.9%). low 51.4% → ml 97.1% → base 91.4% → high 91.4%.
    24 failures: 17 cross-layer functional (low), 6 UI complexity (admin:198), 1 step budget.
    admin:198 anomaly: ml 80% > base 60% > high 40% (Columns dialog + screenshot timeout).

  Phase 7: Visual Equivalence Validation — 🟡 IN PROGRESS 2026-04-22
    Goal: close CHI 2027 paper §6 Limitations #7 (CUA visual-equivalence confound).
    Approach: URL replay — replay the 137 unique URLs agents actually visited
    (extracted from 3,379 trace cases) under base + low variant, directly via
    Playwright (no BrowserGym). SSIM/pHash/MAD pixel-diff analysis +
    per-patch ablation + human-review gallery.
    Status:
      - 137 URLs extracted, 136 replayable
      - CUA trace signature analysis: 42/54 = 77.8% of low failures match
        link→span click-inert signature (≥8 clicks, ≥90% inert, ≥3 same-region
        loops) → paper-ready behavioral evidence
      - All tooling committed: replay-url-screenshots.py,
        replay-url-patch-ablation.py, visual_equivalence_analysis.py,
        visual_equivalence_gallery.py
      - apply-low-individual.js: 13 patches each gated on window.__ONLY_PATCH_ID,
        byte-identical to apply-low.js
      - New burner 840744349421 deployed, both EC2 online
      - Login smoke PASSED on all 4 apps (commit d104d01)
      - Pending: run Phase B (137 URL × 2 variant ≈ 25min) + Phase C (56 captures ≈ 5min),
        download + analyze, write final §6 drop-in.
    Architecture: docs/analysis/visual-equivalence-architecture.md

Actual total: N=1,040 (Pilot 4: 240 text/SoM + 120 CUA + Expansion: 140 Claude + 260 Llama 4 + 140 SoM + 140 CUA)

Ecological validity audit completed (2026-04-13):
- scan-a11y-audit/ tool built: Playwright + axe-core scanner for 30 real-world websites
  + 4 WebArena Docker instances (34 total sites scanned)
- 34 sites across 6 categories: ecommerce (8), china (6), saas (6), media (5),
  government (5), webarena (4)
- 7 sites scanned via local HTML snapshots (manual Chrome DevTools save) due to
  login walls / bot detection: taobao, zhihu, weibo, xiaohongshu, walmart, ebay, bestbuy
- Three-layer severity framework: L1 decorative, L2 annotation, L3 structural
- Key findings:
  - L3 structural violations present on 83.3% (25/30) of real-world sites, avg 37.4 nodes/site
  - P7 landmark→div: 82% prevalence (most common)
  - P5 heading→div: 62% prevalence
  - P1 img alt: 38% prevalence
  - P11 link→span: 12% detected (conservative lower bound; true prevalence ~40-60%
    due to JS event delegation)
  - WebArena base ≈ real-world L1/L2 level, L3-clean → validates experimental design
- Data: scan-a11y-audit/results/ (34 JSON files + prevalence_matrix.csv)
- Analysis: 5 tables (patch prevalence, full matrix, severity distribution,
  WebArena vs real-world, per-site heatmap)
- Paper placement: Table 3 (severity) in §4/§7 main text; Table 1 (per-patch) in
  supplementary; Table 4 (WebArena comparison) in §7 Discussion

Next steps — CHI 2027 submission (September deadline):

Priority 1 (MUST for paper):
- Task expansion: 6 → 13 tasks across 4 WebArena apps (April-May)
  Phase 1 GitLab first (variant injection on Vue.js is unknown risk)
  Follow incremental validation workflow (smoke → full per task)
- Paper writing: Track A only for CHI submission (N=360 existing + expanded tasks)
  Track B, Design Guidelines, Developer Interview → separate papers

Priority 2 (SHOULD — strengthens paper):
- low-functional-fix variant: restore href in link→span, re-run CUA+text 60 cases
  Isolates functional breakage from semantic degradation more cleanly
- Multi-model replication: ✅ DONE — Llama 4 Maverick 260 cases (2026-04-13)
  Cross-model a11y effect confirmed. See "Cross-Model Replication" section.

Priority 3 (COULD — independent contributions):
- SRF serialization: filter hidden=True nodes, re-run PSL → confirms Same Barrier at ARIA level
- Track B: HAR landscape survey (200+ public sites) → ecological validation paper
  ✅ Ecological validity audit (30 real-world sites + 4 WebArena) DONE (2026-04-13).
  L3 structural violations on 83.3% of sites validates that low variant patches
  model real-world conditions. Provides data for CHI paper's ecological validity
  argument (§7 Discussion). Full 200+ site survey remains optional future work.
- Dual-Audience Design Guidelines: 5-8 evidence-backed guidelines → W4A/ASSETS paper
- Front-end developer interview study: 10-15 semi-structured interviews → Design Guidelines paper
- Framework accessibility audit: Top 10 frontend frameworks × standard pages × axe-core

Timeline:
  Apr 12-13: New AWS account deployment + GitLab smoke test
  Apr 14-20: Task expansion full runs (7 new tasks × 20 cases each = 140 cases)
  Apr-May: Optional CUA runs + any re-runs needed
  May-Jun: Related Work + Methodology finalized
  Jun-Jul: Results + Discussion (summer, concentrated writing)
  Jul-Aug: Brennan review + revision
  Aug: Complete draft
  Sep: LaTeX formatting + CHI 2027 submission

## v8 AMT Refactor — Phase A EOD (2026-04-28)

Following the 2026-04-27 roadmap rescope to the "Accessibility Manipulation
Taxonomy (AMT)" framing. Phase A is the foundation for Mode A's 2,808 cases
and the signature-alignment paper core contribution.

### A.4 — 26 operators extracted (COMPLETE)

See `docs/amt-operator-spec.md` for the normative spec. 26 operator source
files in `src/variants/patches/operators/` (13 L + 3 ML + 10 H incl. H5a/b/c);
build artefact `src/variants/patches/inject/apply-all-individual.js` via
`npm run build:operators`. Runtime: set `window.__OPERATOR_IDS = ["L3","H2"]`
before evaluating the artefact. Canonical application order H → ML → L.
Legacy composite files are frozen (SHA-256-pinned, see CI guards below) —
existing N=1,040 data stays valid for cross-batch merging.

57-test contract+parity+idempotence+non-commutativity suite.

### A.5 — 12-dim DOM signature audit (COMPLETE)

See `scripts/audit-operator.ts` + `analysis/ssim_helper.py`. Per-operator
Playwright audit: fresh context → BEFORE metrics → inject single operator →
wait for DOM-quiet → AFTER metrics → 12-dim delta (DOM D1-D3, A11y A1-A3,
Visual V1-V3, Functional F1-F3).

Two paper-ready misalignment findings surfaced even on the static fixture:
- **L11** (a→span): prior "semantic only" but data shows sem+FUN
  (-7 focusables, -7 interactive, href deleted)
- **H4** (add landmark role): prior "semantic positive" but actual no-op
  because Chromium auto-maps `<nav>` to role=navigation

### Mode-A blocker fixes — all 4 CRITICAL from reviewer audit resolved

Three parallel reviewer-audit sub-agents (code-review, production-readiness,
reviewer-#2) ran against today's A.4/A.5 deliverables, producing ~60 issues.
4/4 CRITICAL blockers cleared by EOD:

- **B2+B3 CI guards** (`src/variants/patches/ci-guards.test.ts`, commit
  bc2018e): build artefact freshness + legacy composite SHA-256 freeze. Both
  negative-tested during development (correctly fails on deliberate
  pollution of L3.js and apply-low.js).
- **B1 individual-mode wiring** (bad7749): new `VariantSpec` discriminated
  union in TS + `applyVariantSpec()` dispatcher; Python `_build_variant_js()`
  assembles `__OPERATOR_IDS` preamble + IIFE so Plan D re-injection receives
  the right globals every time. `VARIANT_SCRIPTS["individual"]` registered.
- **C3 audit authentication** (978f68c, 7fdc116, 1c2e3b4):
  `scripts/webarena_login.py` CLI helper (4-app login, ported from
  replay-url-screenshots.py); audit-operator.ts gains `--login-app`
  + `--login-base-url`; fail-loud exit=3 on login failure (no silent
  login-page audits). Run-dir layout `data/amt-audit-runs/<run-id>/` with
  screenshots + run.log persisted; `scripts/audit-{upload,download}.sh`
  mirror the experiment data pipeline; S3 prefix `audits/` (parallel to
  `experiments/`). Full spec at `docs/amt-audit-artifacts.md`.
- **C4+H1 DOM-quiet settle** (b2ce425): default settleMs 1500→5000ms
  (Pilot-validated Magento floor); new `--quiet-ms` flag (default 500ms)
  uses MutationObserver + Node-side polling to detect genuine DOM
  convergence before AFTER snapshot. Subtle bug discovered in the process:
  `page.evaluate(async () => new Promise(...))` does NOT reliably host
  long-lived `setTimeout` loops under Playwright's CDP managed Promise —
  first impl produced mutations=0, maxQuietSeen=0 for every operator
  because the tick function never ran. Node-side polling with stateful
  window globals works correctly.

### A.1 / A.3 — visual-equivalence admin rerun (deferred)

Not blocking Mode A. Root cause diagnosed in
`docs/analysis/visual-equivalence-decision-memo.md` §Addendum (Magento
admin session TTL < Phase B duration + URL-pattern detection blind to
Magento's URL-stable login page). Defer until we return to Phase 7
visual-equivalence track.

### Deployment — burner 190777959793

- `ada credentials update` + `terraform apply` succeeded (retry after AWS
  `PendingVerification` cleared ~20 min)
- Platform + WebArena EC2 up, Docker boot in progress at EOD
- Next session: bootstrap Platform EC2 + run live A.5 smoke against one
  WebArena URL per app (sanity-check audit pipeline end-to-end before
  committing to a 1,014-run batch)

### Repo hygiene + tooling

- Win→Mac transfer cleanup: `.gitattributes` (LF normalization); `.gitignore`
  extended (data archives, IDE config, terraform backups, AMT audit
  outputs, .DS_Store); node_modules rebuilt for darwin-arm64; jsdom added
  as devDep.
- Python 3.11 installed locally (matches EC2); `pip install requests` for
  `webarena_login.py`.
- `docs/amt-audit-artifacts.md` (new) + `docs/amt-operator-spec.md` §5.4
  cross-reference (new) document the audit output layout + S3 pipeline.

### Test state (EOD)

- TS: 402/402 across 25 files
- Python: 13/13 assertions (`src/runner/test_build_variant_js.py`)
- `tsc --noEmit`: clean

### Commit timeline (2026-04-28)

```
b2ce425  feat(audit): mutation-based DOM quiet wait + 5s initial settle   ← C4/H1
1c2e3b4  docs(spec): cross-reference audit artefacts in §5 file layout
7fdc116  feat(audit): run-dir output + S3 upload/download pipeline        ← C3 persistence
07512e7  chore(git): ignore .DS_Store
978f68c  feat(audit): authenticate to WebArena before audit               ← C3 login
bad7749  feat(variants): wire individual-mode operator injection          ← B1
bc2018e  test(variants): CI guards for build freshness + legacy freeze    ← B2+B3
0431809  feat(variants): AMT 24-operator taxonomy                         ← A.4
f5b4452  test(variants): update VARIANT_LEVELS count for pure-semantic-low
0a57beb  chore(git): ignore IDE config, terraform backups, AMT outputs
1c02f65  chore: enforce LF line endings, ignore local data archives
+ 4 more docs/rename commits
```

### Still blocking Mode A B.1

~~Two reviewer-audit items still on the critical path.~~ All resolved:

- **C1 Plan D sentinel coverage** — ✅ FIXED. `apply-all-individual.js`
  sets `data-amt-applied` on `<body>` after all operators run. Bridge
  uses this for individual-mode (composite keeps `[data-variant-revert]`).
- **H5 scheduler operatorIds dimension** — ✅ FIXED. `ExperimentMatrix`
  gains `individualVariants: string[][]`. 6-part case IDs for individual
  mode: `{app}:individual:{taskId}:{ci}:{attempt}:{opIds}`.

### Next up (Mode A ready)

1. ~~**A.5 batch wrapper**~~: ✅ Running on EC2 — 13 task URLs × 3 reps
   × 26 operators = 1,014 audit runs → `results/amt/dom_signatures.json`
2. **B.1 Mode A full run**: 2,808 cases × Claude × ~8 days × ~$850
   All blockers cleared. operatorIds wired end-to-end through
   executor → bridge. Config supports `individualVariants` in YAML.
   411/411 TS tests (9 new individual-mode scheduler tests).


- Added `.gitattributes` (`* text=auto eol=lf`) to prevent recurrence
- `.gitignore` extended to ignore root-level data archives (`data.tar`,
  `data.tar.gz`, `scan-a11y-audit/results.tar`, `terraform-apply.log`)
- Reinstalled `node_modules` for darwin-arm64 (old install was Windows-native);
  added `jsdom` as devDep (needed by the operator test suite under
  `@vitest-environment jsdom`)

### Next up (blocks Mode A)

1. Smoke A.5 audit on a live WebArena URL once bootstrap finishes (not on the
   fixture, to catch DOM quirks specific to Magento/KnockoutJS/GitLab/Postmill)
2. **A.5 batch wrapper**: roadmap §2.4 asks for per-operator signatures averaged
   across 13 task URLs × 3 page-load reps = 78 audit runs per operator = ~2,028
   total. Build `scripts/audit-operator-batch.ts` that loops over URLs + reps
   and produces `results/amt/dom_signatures.json` with mean + stddev per dim
3. Only after (2) → start B.1 (Mode A full run: 24 operators × 13 tasks × 3
   agents × 3 reps = 2,808 cases). This is the big cost (~$850, 8 days wall)

## Task Expansion Workflow

When adding new tasks to the experiment, follow this incremental validation process:

### Step 1: Select candidate tasks
- Check test.raw.json for tasks on the target app (use task-site-mapping.json)
- Prefer tasks with eval_type: string_match or program_html (avoid llm_eval)
- Prefer tasks that exercise different page types (product pages, search, forms, lists)

### Step 2: Smoke test — variant DOM observation
- Create a smoke config with the new task(s), all 4 variants, 1 rep, text-only only
- Run on EC2: `npx tsx scripts/run-pilot3.ts --config config-smoke-newtask.yaml`
- Download traces and READ THEM — verify for each variant:
  - low: ARIA attrs removed, headings→div, links→span in a11y tree
  - medium-low: role="button" present but no keyboard handlers
  - base: original DOM, no patches
  - high: aria-label added, landmarks present, skip-link exists
- Check: does the task's critical information survive each variant?
  (e.g., if task asks "what is the price?" — is the price still visible in low?)
- Annotate task feasibility per variant (feasible / infeasible / ambiguous)

### Step 3: Full experiment run
- Only after smoke validation passes for all variants
- Config: task-X × 4 variants × 5 reps × text-only (+ optionally SoM, CUA)
- Naming: task-X-full (e.g., task-5-full, task-23-full)
- Use experiment-run-and-upload.sh for auto S3 upload on completion
- Download locally, run per-task analysis, verify results make sense
- This is the FINAL data for task X — no need to re-run later in a batch

### Step 4: Data integration (analysis time, not experiment time)
- Per-task data directories: data/task-5-full/, data/task-23-full/, etc.
- At analysis time, merge all task-*-full/ traces into a single CSV:
  `python analysis/merge_tasks.py data/task-*-full/ > data/combined-experiment.csv`
- CLMM/GEE treats task as random effect — doesn't matter if data was collected
  in one batch or 20 separate runs, as long as conditions are consistent
- No need to re-run all tasks together in a single "full experiment" batch

### Consistency requirements (CRITICAL for cross-task data merging)
Data from different task runs can ONLY be merged if these conditions are identical:
- LLM model version: same Bedrock model ID (e.g., us.anthropic.claude-sonnet-4-20250514-v1:0)
- Variant patch scripts: same apply-low.js / apply-medium-low.js / apply-high.js
- BrowserGym version: same pip package version
- Bridge code: same browsergym_bridge.py and cua_bridge.py

If ANY of these change mid-experiment (e.g., you fix the link→span cross-layer confound
in apply-low.js), you MUST:
1. Record the change with a batch marker (e.g., "batch-v1" vs "batch-v2")
2. Either: re-run affected tasks with the new code, OR
3. Analyze batches separately and report as distinct experimental conditions
4. NEVER silently merge data from different patch versions

Practical approach: freeze variant scripts before starting task expansion.
Make all patch fixes first, then run tasks. If a fix is needed mid-expansion,
tag the batch boundary in a manifest file and document it.

### Handling variant bugs discovered during task expansion
New tasks will inevitably expose variant patch bugs (every Pilot 2→3→4 expansion did).
Classify the bug before deciding how to handle it:

**Type 1: Selector/coverage bug (does NOT invalidate existing data)**
- Symptom: patch doesn't fire on a new page type (e.g., querySelector misses GitLab's
  DOM structure, or Magento admin uses different class names than storefront)
- Fix: broaden the selector or add a new querySelector target
- Impact: the patch's semantic intent is unchanged — it still "removes all ARIA attrs"
  or "replaces headings with divs", just on more elements
- Action: fix the selector, re-smoke the current task, proceed. Existing task data is valid
  because those pages were already correctly patched.
- Example: Pilot 3 added F42/F77/F55 operators — these were new selectors, not changes
  to existing patch semantics. Pilot 2 data remained valid.

**Type 2: Semantic/behavioral change (INVALIDATES data collected before the fix)**
- Symptom: the patch's definition changes (e.g., link→span with href deletion changed to
  link with aria-hidden="true" to fix cross-layer confound)
- Fix: changes what the variant MEANS, not just where it applies
- Impact: the low variant before and after the fix are different experimental conditions
- Action: mark a batch boundary. Options:
  a) Re-run ALL previously completed tasks with the new patch (clean but expensive)
  b) Analyze pre-fix and post-fix data as separate batches (report both)
  c) Discard pre-fix data for the affected variant only (wasteful but clean)
- Example: Pilot 3b→4 Plan D change was Type 2 for goto-dependent tasks (ecom:23 went
  from 80% to 0% at low). All Pilot 3b data was analyzed separately, not merged with Pilot 4.

**Decision flowchart when smoke test reveals a bug:**
1. Does the fix change what the variant DOES (its semantic definition)?
   - YES → Type 2. Stop expansion. Fix first. Decide on batch strategy.
   - NO → continue to 2.
2. Does the fix change which DOM elements are affected on ALREADY-TESTED pages?
   - YES → re-smoke those tasks to verify no behavioral change. If results match, keep data.
   - NO → Type 1. Fix, re-smoke current task only, proceed.

**Historical precedent (bugs discovered during expansion):**
- Pilot 2→3: Added 3 new Ma11y operators (F42, F77, F55) = Type 1 (new selectors)
- Pilot 3a→3b: Discovered goto() escape vulnerability = Type 2 (variant persistence changed)
- Pilot 3b→4: Implemented Plan D = Type 2 (injection mechanism fundamentally different)
- Pilot 4→CUA: Discovered cross-layer confound in link→span = Type 2 (patch semantics)
- PSL smoke: Discovered BrowserGym serialization divergence = not a patch bug, platform finding

## Weekly Account Rotation Workflow

Burner accounts expire after 7 days. Deployment is automated:

### Before account expires (day 5-6):
1. Upload experiment data: `bash scripts/experiment-upload.sh <name> ./data/<dir>`
2. Or use auto-upload wrapper in launch scripts
3. Download to local: `bash scripts/experiment-download.sh --latest <name>`

### New account setup (day 1):
1. Get new burner account from https://iad.merlon.amazon.dev/burner-accounts
2. Configure credentials:
   `ada credentials update --account=<ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot`
3. Enable Bedrock model access in console (Claude Sonnet 4, Haiku 3.5, Nova Pro, Llama 4)
4. Run: `bash scripts/deploy-new-account.sh` (terraform apply + SSM wait, ~5 min)
5. SSM into Platform EC2, run `bash scripts/bootstrap-platform.sh`
6. Start LiteLLM, run smoke test to verify

### What does NOT change between accounts:
- WebArena private IP: fixed at 10.0.1.50 (Terraform `private_ip` parameter)
- Platform private IP: fixed at 10.0.1.51
- All config YAML files: no changes needed
- All source code: git clone from repo
- Region: always us-east-2

### What DOES change:
- EC2 instance IDs (update in steering if needed for reference)
- S3 bucket name (auto-detected by scripts)
- IAM role ARNs (managed by Terraform, transparent to code)

## Experiment Data Pipeline

Data flows: EC2 → S3 → Local machine

### On EC2 (after experiment):
- Manual: `bash scripts/experiment-upload.sh pilot5 ./data/pilot5`
  → Creates s3://bucket/experiments/pilot5-20260411-143022.tar.gz + manifest
- Auto: Use `scripts/experiment-run-and-upload.sh` wrapper in launch scripts
  → Uploads automatically when experiment finishes (success or failure)

### On local machine:
- List: `bash scripts/experiment-download.sh --list`
- Download latest: `bash scripts/experiment-download.sh --latest pilot5`
  → Downloads, extracts to data/pilot5/
- Download specific: `bash scripts/experiment-download.sh pilot5-20260411-143022`

### S3 layout:
```
s3://a11y-platform-data-XXXX/
  experiments/
    pilot4-full-20260407-120000.tar.gz
    pilot4-full-20260407-120000-manifest.txt
    pilot5-smoke-20260412-090000.tar.gz
    pilot5-20260412-180000.tar.gz
```

### Naming convention:
- Experiment name: descriptive, no timestamp (e.g., pilot5, pilot5-cua, smoke-newtask)
- Archive name: experiment-name + timestamp (auto-generated by upload script)
- Local directory: experiment name only (timestamp stripped on download)

## WebArena Task ID Mapping (CRITICAL)

Task IDs are interleaved across sites in webarena/test.raw.json — NOT contiguous ranges.
Each task_id maps to exactly one site. Using wrong IDs = silent misrouting.

```
shopping_admin (Magento backend :7780):  182 tasks, first: 0,1,2,3,4,5,6,11,12,13
shopping       (Magento storefront :7770): 192 tasks, first: 21,22,23,24,25,26,47,48
reddit         (Postmill :9999):         114 tasks, first: 27,28,29,30,31,66,67,68
gitlab         (:8023):                  196 tasks, first: 44,45,46,102,103,104,105
wikipedia      (Kiwix :8888):             16 tasks, first: 265,266,267,268,424,425
map            (:3000):                  128 tasks — NOT DEPLOYED, excluded
```

NEVER assume contiguous ranges (e.g. "reddit=100-199" is WRONG).
Always use explicit tasksPerApp in YAML config, or verify against test.raw.json.

### Experiment Task Set (13 tasks, 11 templates, 4 apps)

Existing (Pilot 4):
  4   shopping_admin  template=279  Top-3 bestsellers Jan 2023       nav=medium
  23  shopping        template=222  Reviewers: fingerprint resistant  nav=shallow
  24  shopping        template=222  Reviewers: unfair price           nav=shallow
  26  shopping        template=222  Reviewers: customer service       nav=shallow
  29  reddit          template=33   Count downvoted comments          nav=medium
  67  reddit          template=17   Book names from top 10 posts      nav=shallow

New (task expansion, validated):
  132 gitlab          template=322  Commits by kilian on 3/5/2023     nav=medium
  293 gitlab          template=329  Clone SSH command for repo        nav=medium
  308 gitlab          template=323  Top contributor to primer/design  nav=deep
  41  shopping_admin  template=285  Top 1 search term in store        nav=medium
  94  shopping_admin  template=274  Invoice 000000001 grand total     nav=deep
  198 shopping_admin  template=366  Customer name of cancelled order  nav=deep
  188 shopping        template=159  Cancelled order cost              nav=shallow

Backup: 349 (gitlab, repo members), 124 (DROPPED — stale ground truth)

## Deployment Rules (CRITICAL)

- ALWAYS run experiments via nohup or the launch-*.sh scripts on EC2.
  SSM sessions disconnect after ~20 min idle. Running `npx tsx` directly
  in foreground WILL be killed when the session drops. Use:
  `bash scripts/launch-pilot3b.sh` (nohup wrapper with PID tracking)
  or: `nohup npx tsx scripts/run-pilot3.ts --config X.yaml > log 2>&1 &`
- For auto S3 upload after experiment, use the wrapper:
  `bash scripts/experiment-run-and-upload.sh <name> <data-dir> <command>`
- Burner accounts auto-close after 7 days. Use `scripts/deploy-new-account.sh`
  for one-command deployment to new accounts.
- Burner accounts auto-close if EC2 has public access (0.0.0.0/0 inbound SG)
- ALWAYS use private subnet + SSM Session Manager (no SSH, no public IP)
- Use `terraform apply` from infra/ — it handles all security correctly
- NEVER manually create EC2 via AWS console
- Connect via: `aws ssm start-session --target <instance-id>`
- Fixed IPs (no config changes needed between accounts):
  - WebArena EC2: 10.0.1.50 (r6i.2xlarge, 8 vCPU, 64GB)
  - Platform EC2: 10.0.1.51 (r6i.4xlarge, 16 vCPU, 128GB)
- Instance IDs change per account — get from `terraform output`
- See docs/deployment.md and docs/new-account-migration-guide.md for full guide

## Deployment Lessons Learned (2026-04-22, burner 840744349421)

Five root-cause issues that cost iterations; all now codified in infra/ and scripts/:

1. **IMDSv2 required on new AMIs.** AL2023 and recent Ubuntu AMIs reject
   IMDSv1 unauthenticated curl to `169.254.169.254`. infra/webarena.tf
   user-data previously used `curl -s http://169.254.169.254/...` without
   a token → PRIVATE_IP came back empty → `magento setup:store-config:set
   --base-url=http://:7770/` failed silently → Magento kept its stale AMI-baked
   public hostname and every request 302-redirected to an unreachable host.
   Fix: always get an IMDSv2 token first. If user-data already failed
   on an existing EC2, run scripts/ssm-fix-magento-baseurl.json as one-shot.

2. **AL2023 uses dnf, not yum.** `yum` is a Python shim that silently
   fails on AL2023 when python3-dnf is missing or when /usr/bin/python3
   is re-symlinked. chromium's libnspr4.so (required for Playwright)
   ships as nspr and nss on AL2023.
   Fix: `sudo dnf install -y nspr nss nss-util atk at-spi2-atk cups-libs
   libdrm libXcomposite libXdamage libXrandr libXtst libXScrnSaver
   mesa-libgbm pango alsa-lib libxkbcommon`.

3. **Don't overwrite /usr/bin/python3.** AL2023's dnf and yum scripts
   shebang to /usr/bin/python3. Symlinking python3 to a user-installed
   python3.11 (to make it the default) breaks dnf system-wide. Always
   call `python3.11` or `/usr/bin/python3.11` explicitly; keep
   /usr/bin/python3 → python3.9 intact.

4. **Ubuntu WebArena uses sh, not bash** for SSM commands. `set -eo pipefail`
   fails on Ubuntu's /bin/sh (dash). Use `set -e` only in ssm-*.json
   command arrays targeting the WebArena Ubuntu instance; `set -eo pipefail`
   is fine on Platform EC2 (AL2023 /bin/sh → bash).

5. **ALWAYS push before asking EC2 to pull.** `git pull` on EC2 picks up
   what's on origin/master. Local commits without push = EC2 runs stale
   code. When iterating on a script that runs remotely, commit + push +
   pull is one atomic action. Do NOT send an SSM command that `git pull`s
   before verifying origin/master contains the change.

## EC2 Reproducibility Rules (CRITICAL)

- NEVER make manual edits on EC2 that aren't tracked in the repo
- All config, scripts, and code changes MUST go through git (edit locally → push → pull on EC2)
- EC2 instances are ephemeral — redeployed weekly on new burner accounts
- The only exception is one-time env setup (BrowserGym timeout sed patch, pip installs)
  which MUST be documented in scripts/ec2-setup.sh so they can be re-applied
- Experiment data lifecycle: EC2 → S3 (experiment-upload.sh) → local (experiment-download.sh)
  Never store data only on EC2 — it will be destroyed when the account expires.
- `task-site-mapping.json` (repo root) is committed — do NOT regenerate on EC2 unless
  the webarena package version changes
- ALWAYS download experiment data to local workspace and read actual trace files
  before drawing conclusions. Never assume outcomes from summary statistics alone —
  trace-level analysis has repeatedly revealed unexpected mechanisms (variant escape,
  false positives, stochastic divergence points) that summary numbers hide.

## Architecture Rules

- TypeScript (ES2022, strict mode) for modules 1–5; Python for module 6
- Modules communicate via TypeScript interfaces and JSON files, no runtime RPC
- Experiment matrix scheduler (Module 3) orchestrates sequential execution
- Python Analysis Engine consumes CSV exports only
- Always read before you edit if the file exists
- Commit when a feature is completed
- TRACE IS KING: After any change to variant injection, observation extraction,
  bridge communication, or agent prompts, ALWAYS run a smoke test (config-reinject-smoke.yaml),
  download the trace data, and read the actual agent observations step-by-step before
  concluding the fix works. Summary statistics (success rates) are not sufficient —
  multiple times a "fix" appeared to work from summary numbers but trace analysis
  revealed the underlying mechanism was unchanged (e.g., goto escape, Magento re-rendering).
  Never assume a code change affects what the agent sees without reading the trace.

## Coding Standards

- All metric values must be 0.0–1.0 inclusive (use `isValidMetricValue`)
- Use `.js` extensions in all TypeScript imports (ESM)
- Prefer `Promise.allSettled()` for parallel operations that should not fail together
- Log errors and continue — never crash the pipeline on a single URL/tool failure
- Every module exports from its `index.ts` barrel file
- Tests use vitest; run with `npx vitest --run`
- Type check with `npx tsc --noEmit`

## Key Design Decisions

- Composite Score is supplementary — primary analysis uses criterion-level feature vectors
- Vision-only agent is a control condition (expected weak/null a11y gradient).
  Uses screenshot only, no a11y tree. Causal logic: if text-only drops but
  vision-only stays constant across variants → a11y tree is the causal factor.
  NOTE: Pilot 4 proved SoM overlays depend on DOM (phantom bids at low=0%).
- CUA agent is the TRUE pure-vision control (zero DOM dependency).
  Uses Anthropic Computer Use tool via direct Bedrock Converse API (bypasses LiteLLM).
  Bridge self-driven: cua_bridge.py runs agent loop internally, executor just waits.
  ObservationMode: 'text-only' | 'vision' | 'vision-only' | 'cua'
  CUA bridge read timeout: wallClockTimeoutMs + 30s (default 630s, vs 120s for others).
  Screenshot eviction: sliding window keeps last 5 turns to avoid 20MB Bedrock limit.
  CUA RESULTS: 109/120 (90.8%). Low 66.7% vs base 96.7%. Causal decomposition:
  text-only 63.3pp drop = ~33pp semantic + ~30pp cross-layer functional.
  reddit:29 inversion (CUA 0/5 vs text-only 4/5) = link→span functional breakage.
- PSL (Pure-Semantic-Low) variant: DOES NOT WORK with default BrowserGym serialization.
  aria-hidden="true" → BrowserGym shows `hidden=True` but elements remain clickable.
  role="presentation" → ignored on headings/landmarks in BrowserGym snapshot.
  Root cause: BrowserGym serialization is more permissive than real screen readers.
  Solution: SRF (Screen-Reader-Faithful) mode — filter hidden=True nodes in bridge.
- DOM Projection Theory: HTML/DOM is the single source of truth ("first principle").
  Every agent observation pathway is a lossy projection of the DOM:
    CDP a11y tree (loses visual layout, adds computed roles),
    Screenshot/SoM (loses DOM semantics, adds pixel info + bid overlays),
    Screen reader (loses visual, filters aria-hidden, adds virtual navigation).
  Three-agent experiment = differential analysis across three projection pathways.
  63.3pp (text-only) - 30.0pp (CUA) = 33.3pp attributable to a11y tree projection.
- BrowserGym serialization divergence is NOT limited to aria-hidden:
  Suspected gaps: AccName computation differences (Igalia 2023), live region changes
  lost (static snapshots), virtual cursor/type-navigation absent, Shadow DOM boundary
  penetration, table row/column semantics flattened. aria-hidden is confirmed;
  others are high-probability but untested — each is a potential SRF sub-project.
- Low variant cross-layer confound: Patch 11 (link→span) deletes href functionality,
  not just semantics. CUA data proves 100% of low CUA failures are functional breakage.
  Fix: preserve <a href> but add aria-hidden="true" (semantic-only degradation).
- Variant levels: low (0.0–0.25), medium-low (0.25–0.50), base (0.40–0.70), high (0.75–1.0)
- Medium-Low variant models real-world pseudo-compliance (ARIA present, handlers missing)
- Low variant operators grounded in Ma11y [ISSTA 2024] WCAG failure techniques:
  8 direct matches (F2, F42, F44, F55, F65, F68, F77, F91, F96) + 4 novel extensions
- Semantic density metric: interactive_nodes / total_a11y_tree_tokens (novel contribution)
- A11y Tree stability: poll at 2s intervals, SHA-256 hash comparison, 30s timeout
- Config: only `webarena.apps` is required; all other fields have documented defaults
- Failure taxonomy: 12 types across 5 domains (accessibility, model, environmental, task, unclassified)
  — 5 types novel vs Aegis [2025] (F_KBT, F_PCT, F_SDI, F_AMB, F_UNK)

## Key Reference Files (repo root)

- `test.raw.json` — WebArena's 812 task definitions (from `webarena` Python package).
  Contains task_id, sites, start_url, intent, eval config, and ground truth for each task.
  Eval types: `string_match` (substring), `url_match`, `program_html` (DOM check),
  `llm_eval` (GPT-4 judge — requires OPENAI_API_KEY via LiteLLM proxy).
- `task-site-mapping.json` — Derived lookup: task_id → site name. Used by screen-tasks
  to filter tasks by app. Regenerate only if webarena package version changes.

## File Structure

```
src/scanner/     — Tier 1 (axe-core + Lighthouse) + Tier 2 (CDP metrics)
src/variants/    — DOM patch engine for 4 accessibility variant levels
src/runner/      — Agent executor, LLM backend, experiment matrix scheduler
  cua_bridge.py  — CUA agent loop (boto3 Bedrock, coordinate actions, screenshot eviction)
src/classifier/  — Auto-classifier (12 failure types) + manual review
src/recorder/    — HAR capture and replay for Track B
src/config/      — YAML/JSON config loader with validation and defaults
src/export/      — Manifest, CSV export, JSON store
analysis/        — Python: CLMM, GEE, Random Forest + SHAP, semantic density
docs/            — Engineering log, analysis reports, literature comparisons
  docs/analysis/ — Experiment analysis reports (moved from data/*.md, git tracked)
                   Write all new analysis reports here, NOT in data/.
                   Naming: <experiment>-<type>.md (e.g., pilot4-full-analysis.md,
                   task-5-deep-dive.md, pilot5-cross-task-stats.md)
scripts/         — Launch scripts, smoke tests, analysis tools, deployment automation
  deploy-new-account.sh — One-command deployment to new burner account
  experiment-upload.sh  — Package + upload experiment data to S3 (run on EC2)
  experiment-download.sh — Download + extract experiment data from S3 (run locally)
  experiment-run-and-upload.sh — Wrapper: run experiment then auto-upload
  smoke-cua-*.   — CUA API verification scripts (LiteLLM + Bedrock direct)
figures/         — Architecture diagrams (matplotlib-generated PNGs + source scripts)
scan-a11y-audit/  — Ecological validity audit (axe-core scan of 30+ real websites)
  scan.ts         — Main scanner (Playwright + axe-core, --local mode for HTML snapshots)
  config.ts       — 34 site configs with patch↔axe-core rule mapping
  custom-checks.ts — Custom DOM checks (P11 div-as-link, Shadow DOM, etc.)
  analysis.py     — Python analysis: 5 tables + CSV export + severity framework
  html-snapshots/ — Manual HTML snapshots for login-walled sites
  results/        — Scan results JSON (not git tracked, synced via S3)
```

## Key Documentation Files

- `docs/platform-engineering-log.md` — Full bug/fix/regression history
- `docs/new-account-migration-guide.md` — Complete guide for deploying to new AWS accounts
- `docs/ma11y-operator-mapping.md` — Ma11y operator audit + novel extensions
- `docs/aegis-taxonomy-comparison.md` — Failure taxonomy comparison with Aegis
- `docs/pilot2-trace-deep-dive.md` — Pilot 2 trace analysis
- `docs/screening-analysis.md` — Task screening results
- `docs/analysis/` — All experiment analysis reports (git tracked):
  - pilot4-full-analysis.md, pilot4-cua-analysis.md, pilot4-deep-dives.md, etc.
  - expansion-claude-trace-deep-dive.md — Claude expansion low-variant failure attribution
  - expansion-llama4-reddit29-deep-dive.md — Forced simplification cross-model replication
  - expansion-llama4-admin4-deep-dive.md — Llama 4 combobox trap (model capability)
  - expansion-llama4-admin198-deep-dive.md — Model capability floor effect
  - expansion-llama4-ecom24-26-deep-dive.md — Answer formatting + comprehension gaps
  - expansion-som-smoke-deep-dive.md — SoM smoke 5 failure modes
  - expansion-som-full-deep-dive.md — SoM full 102 failures classified
  - expansion-cua-full-deep-dive.md — CUA full 24 failures analyzed
  - expansion-vision-full-analysis.md — Combined SoM+CUA analysis (N=280)
  - expansion-cross-agent-comparison.md — 4-agent comparison table
  - visual-equivalence-plan.md — CUA visual confound validation approach (v2: URL replay)
  - visual-equivalence-architecture.md — System topology + data pipeline for replay
  - visual-equivalence-validation.md — §6 Limitations drop-in template
  - Write NEW analysis reports here (not in data/)
- `docs/task-expansion-plan.md` — Task expansion from 6→13 tasks (selection rationale + execution plan)
- `figures/figure4_layer_model_spec.md` — Five-layer architecture text spec
- `analysis/` — Python analysis code (CLMM, GEE, SHAP, semantic density) — git tracked
- `data/` — Raw experiment traces (JSON, CSV) — NOT git tracked, synced via S3

## Paper Narrative (CHI 2027)

Core thesis: Web accessibility degradation causally reduces AI agent task success.

Key framing decisions:
- CHI paper = Track A only (controlled causal experiment). Clean story, no scope bloat.
- Track B, Design Guidelines, Developer Interviews = separate follow-up papers.
- BrowserGym serialization divergence framed as nuance to "Same Barrier" hypothesis,
  NOT as "BrowserGym has a bug". The finding that agents still fail catastrophically
  even with ARIA-level superpowers STRENGTHENS the DOM structural barrier argument.
- Low variant ecological validity defended via: HTTP Archive data (div+span=40%),
  Ma11y F42 precedent (ISSTA 2024), "outcome equivalence" argument (SPA div-onclick
  produces same DOM state as our link→span manipulation).
- Three-agent causal decomposition follows epidemiological attributable fraction
  (Levin 1953 → Donders 1868 → O'Connell & Ferguson 2022).
- Environment-centric paradigm: inverts existing agent-centric benchmarks.
  WebArena etc. fix environment, vary agent. We fix agent, vary environment.
  This is an independent methodological contribution.

Key statistics (Pilot 4, 6 tasks):
  N=360 (240 text-only/SoM + 120 CUA)
  Text-only: low 23.3% vs base 86.7% (p<0.000001, V=0.637)
  CUA: low 66.7% vs base 96.7% (p=0.0027, V=0.388)
  Causal decomposition: 63.3pp - 30.0pp = 33.3pp a11y tree pathway
  Token inflation: low 366K vs base 178K = 2.15x

Key statistics (Claude expansion, 7 new tasks):
  N=140 (text-only). low 51.4% → ml 100% → base 100% → high 100%.
  Perfect step function on new tasks. Cross-app generalizability confirmed (GitLab Vue.js).

Key statistics (Llama 4 expansion, 13 tasks):
  N=260 (text-only). Overall 61.2%. low 36.9% → ml 61.5% → base 70.8% → high 75.4%.
  Monotonic gradient (not step function — more gradual for weaker model).
  Cross-model a11y effect confirmed: both models show low < base, but Llama 4 is
  weaker at ALL variants and shows a more gradual dose-response curve.

Combined experiment total: N=1,040 (360 Pilot 4 + 140 Claude expansion + 260 Llama 4 + 140 SoM + 140 CUA)

## Cross-Model Replication (Llama 4 Maverick, 2026-04-13)

Llama 4 Maverick (Meta, open-source, 400B MoE) via AWS Bedrock. 260 cases.
Confirms a11y effect generalizes across model families (closed Anthropic + open Meta).

### Key Findings

1. **A11y gradient confirmed**: low 36.9% → ml 61.5% → base 70.8% → high 75.4%.
   Direction matches Claude but curve is more gradual (not step function).
   Llama 4 is weaker at ALL variants — base 70.8% vs Claude 92.3%.

2. **Forced simplification cross-model replication** (reddit:29):
   Llama 4: low 40% > ml 0% = base 0% (INVERTED — low is best).
   Claude: low 80%, ml/base 100% (normal direction).
   Same mechanism: link→span prevents clicking into 168K-char post detail pages,
   forcing agent onto goto() + user profile strategy (15K chars, tractable).
   Weaker model benefits MORE from action space constraint.
   Detailed analysis: docs/analysis/expansion-llama4-reddit29-deep-dive.md

3. **Model capability floor effect** (admin:198):
   Llama 4: base 40% → high 80% (+40pp from enhanced a11y).
   Claude: base 100% → high 100% (+0pp — already at ceiling).
   Weaker models benefit MORE from accessibility enhancement.
   Root cause: Llama 4 struggles with 190K-char orders table (picks first cancelled
   order instead of most recent). Enhanced ARIA helps parse table structure.
   Detailed analysis: docs/analysis/expansion-llama4-admin198-deep-dive.md

4. **Model-specific failures (not a11y effects)**:
   - admin:4: Llama 4 1/20 (5%) vs Claude 19/20 (95%). Cannot operate native
     <select> combobox (52 failed attempts). Claude bypasses combobox entirely.
     Detailed analysis: docs/analysis/expansion-llama4-admin4-deep-dive.md
   - ecom:24: Llama 4 sends "" instead of "N/A" for negative results → 0% at ml/base/high.
     Claude sends "0" → 100%. Pure answer formatting deficiency.
   - ecom:26: Llama 4 finds 1/3 reviewers at ml (0%), stochastically 2/3 at base (80%).
     Claude finds 3/3 deterministically (100%). Review comprehension gap.
     Detailed analysis: docs/analysis/expansion-llama4-ecom24-26-deep-dive.md

5. **Tasks where both models agree** (a11y effect is model-independent):
   - ecom:23: both 0% at low, 100% at ml/base/high (content invisibility)
   - gitlab:293/308: both 0% at low, 100% at ml/base/high (structural infeasibility)
   - admin:41/188: both 100% at ALL variants (control tasks, low also succeeds)
   - admin:94: both ~60% at low (stochastic URL workaround), 100% at ml/base/high

6. **Paper narrative implications**:
   - "Effect generalizes across closed-source (Claude) and open-source (Llama) models"
   - "Weaker models are more vulnerable to a11y degradation AND benefit more from enhancement"
   - "Forced simplification is a general agent-environment property, not model-specific"
   - Model capability × environment quality = multiplicative interaction
   - performance = task demand (ADeLe) × environment quality (ours) × agent capability

### Llama 4 Task × Variant Matrix (text-only, N=260)

| Task | low | ml | base | high | Notes |
|------|-----|----|------|------|-------|
| admin:4 | 0% | 0% | 0% | 20% | Model capability (combobox trap) |
| admin:41 | 100% | 100% | 100% | 100% | Control task |
| admin:94 | 60% | 100% | 100% | 100% | Stochastic URL workaround at low |
| admin:198 | 0% | 40% | 40% | 80% | Model capability floor |
| ecom:23 | 0% | 100% | 100% | 100% | Content invisibility at low |
| ecom:24 | 20%* | 0% | 0% | 0% | Answer formatting bug ("" vs "N/A") |
| ecom:26 | 0% | 0% | 80% | 60% | Review comprehension threshold |
| ecom:188 | 100% | 100% | 100% | 100% | Control task |
| reddit:29 | 40% | 0% | 0% | 20% | **Forced simplification inversion** |
| reddit:67 | 60% | 80% | 100% | 100% | Gradual gradient |
| gitlab:132 | 100% | 100% | 100% | 100% | Control task |
| gitlab:293 | 0% | 80% | 100% | 100% | Structural infeasibility at low |
| gitlab:308 | 0% | 100% | 100% | 100% | Structural infeasibility at low |

*ecom:24 low "success" is vacuous truth (can't access reviews, "cannot complete" matches "N/A")

## Spec Reference

Full requirements, design, and tasks at:
#[[file:.kiro/specs/ai-agent-accessibility-platform/requirements.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/design.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/tasks.md]]

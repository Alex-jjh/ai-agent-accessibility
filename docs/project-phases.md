# Project Phases — AI Agent Accessibility / AMT

> **Purpose**: Single-page canonical narrative of how this project unfolded,
> from April 2026 pilots to the May 2026 task-set expansion. Every phase
> ties to (a) what we physically did, (b) what we discovered, (c) what
> role it plays in the CHI 2027 paper. Use this doc as the source of truth
> when answering "how did you get from X to Y?" questions — in the paper,
> in Brennan sync, or in future handoffs.
>
> **Last updated**: 2026-05-06
>
> **Canonical citation for this project**: 6 phases, ~7,000+ total cases,
> ~12 months calendar time (from conception to CHI submission).

---

## The headline sentence (drop into §4.1 Method Overview)

> We validated the instrument on a 6-task pilot (Phase 1), extended it to
> three agent modalities and discovered three platform artifacts (Phase
> 2), verified ecological relevance and visual equivalence with outside-
> the-lab data (Phase 3), formalized the Accessibility Manipulation
> Taxonomy with 26 independent operators (Phase 4), tested operator
> composition to falsify additivity (Phase 5), and scaled to a pre-
> registered task set of ~300 base-solvable WebArena tasks for the main
> manipulation result (Phase 6). Each phase produced data that the
> subsequent phase built on; none is redundant.

---

## Phase 1 — Instrument Calibration & Proof-of-Concept

**Dates**: 2026-03-31 → 2026-04-06 (≈1 week)  
**Scope**: Track A platform build + Pilots 1/2/3a  
**Scale**: 6 hand-picked WebArena tasks × 4 composite variants × ~5 reps = 120-240 cases per pilot

### What we did
- Built the six-module platform (Scanner, Variants, Runner, Classifier,
  Recorder, Analysis) per the pre-registered spec
- Ran Pilot 1 → Pilot 2 → Pilot 3a on a fixed 6-task set
- Discovered and fixed ~24 platform bugs (documented in
  `docs/platform-engineering-log.md`): variant injection persistence,
  BrowserGym bridge timeouts, Magento login races, crypto.subtle on HTTP,
  Bedrock geo-inference IAM, WebArena shopping URL rewriting, etc.

### What we found
- **Monotonic accessibility gradient confirmed** at composite level:
  low 20% → ML 87% → base 90% → high 93% (Pilot 3a, χ² = 29.70, p < 0.0001, V = 0.704)
- **Two failure pathways** identified from per-trace analysis: token
  inflation (admin:4, reddit:67) and content invisibility (ecom:23/24/26)
- **Failure taxonomy** extended from Aegis [2025]'s 6 modes to 12 types
  across 5 domains — 5 novel types (F_KBT keyboard trap, F_PCT pseudo-
  compliance trap, F_SDI Shadow DOM invisible, F_AMB ambiguity, F_UNK
  unclassified)

### What this becomes in the paper
- **§4.1 Instrument** — composite-variant pipeline (now the historical
  starting point, superseded by AMT individual operators in Phase 4)
- **§4.5 Failure Taxonomy** — our 12-type taxonomy with the 5 novel
  categories, compared against Aegis
- **Appendix** — platform engineering log as supplementary material
  (reproducibility asset, 24 documented lessons)
- **Pilot 3a gradient** — framed as motivation / preliminary evidence
  in §1 introduction

---

## Phase 2 — Multi-Modal Agent Extension & Platform Discovery

**Dates**: 2026-04-06 → 2026-04-09 (≈4 days)  
**Scope**: Pilot 3b + Pilot 4 — added SoM vision-only and CUA coordinate-based agents  
**Scale**: 6 tasks × 4 variants × 5 reps × {text-only, SoM, CUA} = 360 cases

### What we did
- Extended the Agent Runner to three observation modalities:
  - Text-only (a11y tree serialization, primary)
  - SoM (Set-of-Mark: screenshot + DOM-derived bid overlays)
  - CUA (pure screenshot + pixel coordinates, via Anthropic Computer Use)
- Anchored Low variant operators to **Ma11y [ISSTA 2024]** WCAG failure
  techniques: 8 direct matches (F2, F42, F44, F55, F65, F68, F77, F91,
  F96) + 4 novel extensions (E1-E4)
- Added **Semantic Density** metric (`interactive_nodes /
  a11y_tree_tokens`) as a novel measurement instrument
- Implemented Plan D variant injection (`context.route` + deferred patch
  + `MutationObserver` guard) after Pilot 3a revealed goto() escape
- Ran a pure-semantic-low (PSL) smoke test to isolate ARIA-only effects

### What we found
- **Three platform artifacts** — each a novel and separately publishable
  platform finding:
  1. **Phantom bid (SoM)**: bid overlay renders in screenshot from prior
     DOM state but underlying elements are gone → agent clicks stale
     label, fails. 2026-04-08 formalized.
  2. **Cross-layer confound (CUA)**: patch 11 (link→span) deletes
     `href` functionality, not just semantics. 100% of low-variant CUA
     failures are functional breakage (0 pure-semantic). Led to §5
     decomposition: low drop = ~33% semantic + ~30% functional.
  3. **BrowserGym serialization divergence (PSL)**: `aria-hidden="true"`
     shows as `hidden=True` in BrowserGym but elements retain bid and
     are fully clickable via `click(bid)`. BrowserGym is more permissive
     than real screen readers — affects **all** BrowserGym benchmarks
     (WebArena, VisualWebArena, WorkArena) with systematic
     overestimation of agent robustness.

### What this becomes in the paper
- **§3.4 Agent architectures** — three observation modalities as
  projections of the same underlying DOM (setup for §3.3 DOM Projection
  Theory)
- **§5.3 Visual control** — CUA decomposition showing the a11y-tree
  attributable fraction (33pp of 63pp total drop)
- **§6.3 Platform limitations** — BrowserGym serialization divergence
  is the headline limitation; framed as "our results are a conservative
  lower bound because BrowserGym gives agents ARIA-level superpowers"
- **§5.5 Semantic density** — the novel measurement metric (token
  inflation pathway quantification)

### Three-Layer Independence Framework (established 2026-04-09)

During Phase 2 synthesis, we formalized the theoretical framework that
underpins §3:

> DOM semantic layer, JS behavior layer, and Visual/CSS layer are
> **independent channels**. Normal sighted users perceive via
> visual+JS; screen readers and AI agents perceive via the DOM semantic
> layer (rendered through browser accessibility tree). A Low variant
> degrades the DOM semantic layer without touching visual appearance,
> producing a condition where normal users still perceive the page
> correctly but AI agents lose structural information.

This framework is `figures/figure4_layer_model_spec.md` and becomes the
§3 conceptual anchor. Distinct from Phase 4's AMT framework which
operationalizes the theory.

---

## Phase 3 — Ecological Validation & Visual-Equivalence Verification

**Dates**: 2026-04-09 → 2026-04-22 (≈2 weeks)  
**Scope**: Outside-the-lab validation on two axes  
**Scale**: 34 real-world sites (axe-core) + 137 unique URLs from 3,379 historical cases (URL replay)

### What we did

**(a) Ecological validity audit** (`scan-a11y-audit/`, 2026-04-13):
- Built a Playwright + axe-core scanner for 30 real-world sites + 4
  WebArena Docker instances
- 6 sector categories: ecommerce (8), china (6), saas (6), media (5),
  government (5), WebArena (4)
- Custom DOM checks for our patches (P11 div-as-link, Shadow DOM
  boundary)
- Three-layer severity framework (L1 decorative / L2 annotation / L3
  structural) applied to violation counts

**(b) Visual-equivalence verification** (Phase 7 URL-replay, 2026-04-22):
- Extracted every URL the agent visited from 3,379 historical traces →
  137 unique URLs
- Replayed each URL under base vs low variants in Playwright (no
  BrowserGym, no agent)
- Computed SSIM, pHash, WCAG contrast delta per URL
- Analyzed CUA failure trace signatures: link→span click-inert pattern
  (≥8 clicks, ≥90% inert, ≥3 same-region loops)

### What we found

**Ecological:**
- **L3 structural violations on 83.3% (25/30) of real-world sites**
  (avg 37.4 violating nodes per site)
- P7 landmark→div: 82% prevalence (most common)
- P5 heading→div: 62%, P1 img alt: 38%, P11 link→span: 12% detected
  (conservative; JS event delegation inflates true prevalence to ~40-60%)
- **WebArena base ≈ real-world L1/L2 level, L3-clean** — validates that
  Low variant patches model real-world degraded conditions

**Visual:**
- **77.8% of CUA low-variant failures (42/54)** match the link→span
  click-inert signature — direct trace evidence that CUA's drop is
  cross-layer functional, not visual. This becomes the empirical
  basis for retaining CUA as one leg of the 3-agent causal
  decomposition (despite its noisy baseline in Mode A).
- The **URL-replay pipeline itself** is re-usable for Stage 4b SSIM
  audit on new Stage 3 data, replacing CUA as the visual control

### What this becomes in the paper
- **§7 Ecological validity** — Table 3 (severity distribution across
  34 sites) + Table 4 (WebArena vs real-world comparison). Direct
  counter to "WebArena is a toy benchmark" reviewer attack.
- **§5.3 Visual control** — CUA link→span signature (Phase 3) +
  planned Stage 4b SSIM audit (Phase 6) together form the visual-
  equivalence argument
- **§6.5 Ecological validity discussion** — reframes our Low variant
  as "conservative ceiling of what WCAG allows as WCAG-A failure"
  rather than a straw-man extreme

---

## Phase 4 — AMT Framework Formalization

**Dates**: 2026-04-27 → 2026-05-02 (≈6 days)  
**Scope**: Decompose composite variants into 26 independent operators + measure per-operator signature  
**Scale**: 3,042 Claude cases + 1,014 Llama 4 cases = **4,056 Mode A cases**

### What we did
- Refactored `apply-low.js + apply-midlow.js + apply-high.js` monoliths
  into **26 independent operators**:
  - 13 Low (L1-L13) — aggressive degradation
  - 3 Midlow (ML1-ML3) — pseudo-compliance edge cases
  - 8 High (H1-H8, incl. H5a/b/c) — positive enhancement (novel direction)
- Implemented **12-dimensional DOM signature audit** (D1-D3 DOM, A1-A3
  a11y tree, V1-V3 visual, F1-F3 functional) per operator, averaged
  across 13 task URLs × 3 reps
- Ran **Mode A full matrix**: 26 operators × 13 tasks × 3 agents × 3
  reps = 3,042 Claude cases (dual-account shards)
- Ran **Mode A cross-family**: 26 operators × 13 tasks × Llama 4 × 3
  reps = 1,014 cases
- Applied post-hoc GT corrections for 3 Docker-drift tasks (41, 198,
  293) — accepted both original and current docker-state answers as
  valid
- Implemented signature alignment analysis: DOM signature × behavioral
  signature → alignment classification (matched / misaligned-DOM-active /
  misaligned-Behavior-active / matched-null)

### What we found

**Core AMT findings** (§3-§5 of the paper):

1. **L1 Landmark Paradox** (95% confidence): L1 (landmark→div) is the
   single most destructive operator at 53.8% success, despite making
   only 6 DOM changes (SSIM=1.000, F1=0). Landmarks are the a11y
   tree's structural skeleton.

2. **L5 Shadow DOM Ghost Buttons** (99%): Closed Shadow DOM creates
   perception-action gap — agent sees buttons in a11y tree but cannot
   click them (BrowserGym's bid assignment can't penetrate shadow
   boundary).

3. **Forced Simplification** (99%, task 67 reddit): SoM agent
   outperforms text-only (L11 low) by physically preventing token-
   inflating post dives. 12× token reduction. Counter-intuitive
   finding where degradation helps.

4. **Three-tier operator structure** (97%): Destructive (L1, L5),
   moderate (L12, L10, L2), neutral (18 operators including all
   H/ML). Fisher-exact: only L1 and L5 significant after Holm-
   Bonferroni → "sparsity is the finding".

5. **Signature Alignment**: 42% of operators show DOM-active /
   behavior-null misalignment (agent adaptation); 15% show DOM-
   minimal / behavior-active (structural criticality). L11 has
   365 DOM changes but only 1.5pp drop on Claude (vs 14.6pp on
   Llama 4 — adaptive-recovery gap).

6. **Cross-model replication**: L1 and L5 destructive on both Claude
   and Llama 4. Breslow-Day confirms operator × family interaction
   is significant only for adaptive operators (L11, L6).

7. **H-operator ceiling** (99%): All H-operators cluster at 90-97% on
   Claude — Claude Sonnet + WebArena base is already accessible
   enough that enhancement cannot measurably help. Llama 4 shows
   the same H-operators with +8-40pp benefit → weaker models benefit
   more from accessibility enhancement.

8. **Causal decomposition** (Pilot 4): text-only 63.3pp drop = ~33pp
   semantic (a11y-tree pathway) + ~30pp cross-layer functional. Uses
   Levin 1953 / O'Connell & Ferguson 2022 attributable-fraction
   methodology.

### What this becomes in the paper
- **§3 AMT Framework** — the methodological contribution. 26 operators
  + 12-dim DOM signature + 3-arch behavioral signature + alignment
- **§5.1 Per-operator drops** — F4 bar chart (the flagship figure)
- **§5.2 Signature alignment** — F6 scatter (the "core scientific
  contribution" figure)
- **§5.3 Cross-model** — F7 side-by-side
- **§5.4 Mechanisms** — §5.4.1 landmark paradox, §5.4.2 shadow DOM,
  §5.4.3 forced simplification (depth-tier case studies on Mode A's
  hand-picked 13 tasks)
- **§6.1-6.2 Interpretation** — why signatures align (or don't), what
  the asymmetry tells us about agent robustness design

---

## Phase 5 — Compositional Interaction Study (C.2)

**Dates**: 2026-05-02 (≈1 day data collection, analysis concurrent with Phase 4)  
**Scope**: Test whether operators combine additively or interact  
**Scale**: 28 pairwise combinations × 13 tasks × 2 agents × 3 reps = **2,184 cases**

### What we did
- Selected Top-8 operators by mechanism diversity (L1, L2, L4, L5, L6,
  L9, L11, L12) → C(8,2) = 28 pairs
- Ran pairwise combinations at text-only + CUA agents
- Applied same GT corrections + Docker confound audit
- For each pair, computed `drop(A+B) - (drop(A) + drop(B))` and
  classified as additive / super-additive / sub-additive using
  binomial test

### What we found

**Compositional findings**:

1. **14/28 pairs super-additive (50%)** — binomial p = 0.019 rejects
   symmetric additivity. Operators **amplify** each other, not
   saturate.

2. **L11 "amplifier"**: zero individual effect (1.5pp), but +24pp
   interaction with L6 (heading→div + link→span together break
   agents far more than either alone).

3. **L6 "latent damage"**: zero individual effect (H-ops all 3/3),
   but massive interaction effects — damage is latent until another
   operator exposes it.

4. **L5 "ceiling"**: sub-additive with most pairs — when L5 already
   destroys task access via Shadow DOM, adding another operator
   cannot damage further.

5. **L1+L5 sub-additive**: trace-verified — failure pathway
   saturation (both drive to 0% individually, cannot go lower).

6. **New operator taxonomy dimension**: beyond {destructive, moderate,
   neutral} from Phase 4, we add {independent, amplifier, latent,
   ceiling} characterizing compositional behavior.

7. **Composite-low explanation**: Pilot 4's composite low (23.3%) is
   driven by L1+L11+L6 amplifier chain, not 13 independent hits.

### What this becomes in the paper
- **§5.4 Compositional Interaction** — F8 scatter (expected vs
  observed drop per pair) + the super-additive / sub-additive / independent
  classification table
- **§6.1 Interpretation extension** — "operators are not independent
  axes of accessibility; real-world WCAG failures rarely occur alone,
  and their interactions matter more than individual severity"
- **Generative claim**: "Our AMT can predict compositional drop to
  within X pp accuracy" — this is the "generative" in the paper's
  methodology contribution

---

## Phase 6 — Task-Set Breadth Expansion (current, pending)

**Dates**: 2026-05-04 → ~2026-05-20 (current phase)  
**Scope**: Scale from mechanistic depth (N=13) to statistical breadth (N~300)  
**Scale**: 684 smoker cases → ~250-350 primary tasks × 26 operators × 3 reps × 2 models = **~46,800 Stage 3 cases**

### What we did / are doing
- Wrote a 684-task smoker (all deployed-app WebArena tasks × 3 reps ×
  base variant) — 2,052 cases total
- Pre-registered a conservative inclusion gate on **2026-05-06**
  (before any Stage 3 data collected):
  - 3/3 reps recorded
  - 0 infrastructure failures (context window, bridge crash, admin
    login, goto timeout, Chromium crash, harness error)
  - 3/3 reps report success (strict, not majority vote)
  - Median successful step count in [3, 25]
- Each exclusion attributed to a named category; infrastructure ranked
  ahead of difficulty so "Magento context overflow" is not mislabeled
  as "Claude can't solve"
- Tier-2 reference set of stochastic-base tasks (e.g. reddit:29,
  reddit:67) retained for supplementary analysis — **not** in
  Stage 3 manipulation

### Still to do (2026-05-07 →)

1. **Filter**: run `scripts/smoker/analyze-smoker.py` on completed
   smoker data, finalize Stage 3 task set, generate
   `config-manipulation-filtered.yaml`

2. **Stage 3 manipulation**: the filtered task set × 26 operators × 3
   reps × {Claude Sonnet 4, Llama 4 Maverick} = ~46,800 cases, ~$3,500-4,500

3. **Stage 4a DOM audit**: per-operator before/after screenshots with
   SSIM + pHash + WCAG contrast delta via `audit-operator.ts`

4. **Stage 4b Trace-URL SSIM audit**: replay every URL the Stage 3
   agents observed, base vs each variant, measure pixel-level
   equivalence. **Replaces CUA as the visual control** — direct per-
   URL pixel measurement is mathematically stronger than inferring
   visual equivalence from CUA success rates.

### What this becomes in the paper
- **§4.2 Task selection** — pre-registered gate + chain of custody
  from 812 → 684 → N_passing, with paper-ready exclusion table
- **§5.1-5.3 Main manipulation result (breadth tier)** — per-operator
  significance, cross-model replication, signature alignment on
  expanded N
- **§5.3 Visual control (Stage 4b)** — F10 SSIM distribution per
  operator
- **Appendix X** — full exclusion report with per-task rationale
  (reviewer can verify consistency)

---

## Two-tier paper narrative (how all 6 phases cohere)

The paper reports results at two granularities, each with distinct
scientific purpose:

| Tier | Source | N | Paper section |
|------|--------|---|---------------|
| **Breadth** | Phase 6 (Stage 3) | ~300 tasks × 26 ops × 3 reps × 2 models ≈ 46,800 cases | §5.1-5.3 main result |
| **Depth** | Phase 4 (Mode A) | 13 tasks × 26 ops × 3 agents × 3 reps = 3,042 + 1,014 Llama 4 | §5.4-5.5 mechanisms |
| **Composition** | Phase 5 (C.2) | 28 pairs × 13 tasks × 2 agents × 3 reps = 2,184 | §5.4 |
| **Ecological** | Phase 3 | 34 sites × axe-core scan | §7 |
| **Visual** | Phase 3 + Phase 6 Stage 4b | 137 URLs historical + ~300-task trace-URL new | §5.3 |
| **Pilot motivation** | Phase 1 + 2 | Composite N=1,040 across Pilots 1-4 + expansion | §1 / §4.1 |

**Why both depth and breadth?** The 13 Mode A tasks were hand-picked
to balance coverage and analyzability. They expose mechanisms (L1
landmark paradox, L5 ghost buttons, forced simplification on
reddit:67) that only emerge under per-trace inspection. The Stage 3
breadth set cannot replace this depth — 300+ tasks precludes per-case
analysis. Conversely, the 13-task set cannot provide statistical
power to answer "would the effect generalize to a broader task
population?" Both are needed; neither is redundant.

---

## Canonical reviewer Q&A (anticipated)

**Q: "Why N tasks and not 684?"**  
A: Phase 6 pre-registered conservative gate (2026-05-06, before data
collection). Each criterion *reduces* the observed drop — trivial
tasks add 0-pp cases that dilute the mean; stochastic-base tasks add
noise that blurs signal; infrastructure failures are benchmark × model
artifacts, not accessibility effects. Observed drop is a **lower
bound**. Full chain-of-custody in Appendix X.

**Q: "Why 13 Mode A tasks for the main result?"**  
A: 13 tasks support the depth tier (mechanism interpretability). The
breadth tier uses ~300 Stage 3 tasks (Phase 6). Each answers a
different question; Appendix Y has the rationale.

**Q: "Your effect is 63.3pp — is some of it visual, not semantic?"**  
A: (a) Phase 2 CUA decomposition: 63.3pp text-only = ~33pp semantic
(a11y-tree pathway) + ~30pp functional (link→span href deletion).
(b) Phase 3 visual-equivalence replay: 77.8% of CUA failures match
the link→span signature, direct trace evidence. (c) Phase 6 Stage 4b
(planned): per-URL SSIM distribution for every Stage 3 URL, replacing
CUA as the visual control with direct pixel measurement.

**Q: "WebArena is a toy benchmark, doesn't generalize."**  
A: Phase 3 ecological audit (`scan-a11y-audit/`) scanned 30
real-world sites. L3 structural violations present on 83.3% of them.
WebArena base sits at real-world L1/L2 level; our Low variant is a
conservative floor of what real-world WCAG-A-failing sites look like.

**Q: "Compositional effects — couldn't your 'super-additive' pairs
just be multiplicative instead?"**  
A: Phase 5 C.2 data ran `drop(A+B) - (drop(A) + drop(B))` per pair
with binomial test (p = 0.019 against symmetric additivity).
Multiplicative models produce different sign patterns (L11+L6 would
be multiplicative-null because L11 alone = 0); our super-additivity
(L11+L6 = +24pp amplifier) rejects that. Trace-verified.

---

## What comes after the paper (deferred)

- **SRF (Screen-Reader-Faithful) serialization**: filter `hidden=True`
  nodes in bridge, re-run PSL → confirms Same Barrier at ARIA level.
  Deferred — independent paper scope.
- **Track B HAR landscape survey**: 200+ public sites as follow-up.
  Ecological audit (Phase 3) serves as the preliminary version.
- **Design guidelines for dual audience** (W4A/ASSETS paper).
- **Developer interview study** (design-guidelines paper).
- **Framework accessibility audit**: top-10 frontend frameworks ×
  standard pages × axe-core.

These are outside CHI 2027 submission scope but documented for future
work reference.

---

## References

- `docs/platform-engineering-log.md` — Phase 1 bug catalog (24 entries)
- `docs/analysis/mode-a-analysis.md` — Phase 4 main report
- `docs/analysis/mode-a-C2-composition-analysis.md` — Phase 5 main report
- `docs/analysis/visual-equivalence-plan.md` / `visual-equivalence-validation.md` — Phase 3 methodology
- `docs/analysis/task-selection-methodology.md` — Phase 6 pre-registration record
- `docs/a11y-cua-to-webarena-mapping.md` — A11y-CUA cross-study triangulation (Phase 3/5 supplementary)
- `scan-a11y-audit/` — Phase 3 ecological audit subproject
- `docs/amt-operator-spec.md` — Phase 4 operator catalog normative spec
- `docs/amt-audit-artifacts.md` — Phase 4 DOM signature audit infrastructure
- `.kiro/steering/2026-04-27-chi2027-roadmap-v8.md` — v8 paper roadmap (Phase 4 framing)
- `.kiro/steering/2026-05-04-submission-roadmap.md` — Phase 6 submission plan

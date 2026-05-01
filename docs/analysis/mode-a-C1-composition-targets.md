# C.1 Compositional Study — Operator Selection & Interaction Predictions

**Date**: 2026-05-01
**Selected operators**: L1, L2, L4, L5, L6, L9, L11, L12
**Pairwise combinations**: C(8,2) = 28
**Total cases**: 2,184 (28 × 13 tasks × 2 agents × 3 reps)
**Agents**: text-only + CUA (SoM excluded — see §4)

---

## 1. Selection Criteria

We select 8 operators from the 26-operator AMT taxonomy for pairwise
compositional testing. Selection is driven by **three criteria**, applied
in order:

### Criterion 1: Mechanism diversity (primary)

The compositional study tests whether pairwise effects are additive,
super-additive, or sub-additive. Detecting interaction requires operators
with **distinct failure mechanisms** — if two operators fail through the
same mechanism, their combination is trivially sub-additive (ceiling on
the shared pathway). We require representation from all three mechanism
categories identified in Mode A:

| Category | Definition | Selected |
|----------|-----------|----------|
| **Structural** | Alters DOM topology or element accessibility | L1, L5 |
| **Semantic** | Removes or corrupts semantic annotations | L2, L6, L9, L12 |
| **Functional** | Removes behavioral capabilities (handlers, href) | L4, L11 |

### Criterion 2: Sufficient individual signal (secondary)

Operators with near-zero individual effect (e.g., H-operators at 90-97%)
cannot contribute detectable interaction signal in a 3-rep design. We
require each selected operator to show **either**:
- ≥5pp drop in Claude text-only, **or**
- ≥10pp drop in Llama 4 text-only (cross-model signal)

All 8 selected operators meet this threshold on at least one model.

### Criterion 3: Theoretical interaction predictions (tertiary)

We prioritize operators where we can make **a priori predictions** about
interaction type (additive/super/sub). This makes the compositional study
a **hypothesis test**, not a fishing expedition. See §3 for all 28 predictions.

---

## 2. Selected Operators — Individual Justification

### L1 — Semantic landmark → `<div>` (STRUCTURAL)

| Metric | Value |
|--------|-------|
| Claude text-only | 53.8% (-40.0pp from H-baseline) |
| Llama 4 text-only | 43.6% (-32.6pp) |
| Mechanism | Removes `<nav>`, `<main>`, `<header>`, `<footer>`, `<article>`, `<section>`, `<aside>` → `<div>`. Strips `banner`, `navigation`, `main`, `contentinfo` landmarks from a11y tree. |
| Trace evidence | Agent sees 500+ elements as flat list under RootWebArea. Cannot distinguish page regions. (See `mode-a-landmark-paradox-trace-report.md`) |
| Selection reason | **Strongest individual effect.** Must-include for any compositional study. Structural mechanism is unique — no other operator removes landmark container semantics. |

### L5 — Closed Shadow DOM wrap (STRUCTURAL)

| Metric | Value |
|--------|-------|
| Claude text-only | 71.8% (-22.1pp) |
| Llama 4 text-only | 53.8% (-22.3pp) |
| Mechanism | Wraps `<button>`, `[role="button"]`, `[role="link"]`, etc. in closed Shadow DOM. Elements visible in a11y tree but without BrowserGym bid numbers. |
| Trace evidence | "Ghost buttons" — agent sees `button 'Show Report'` (no bid) vs control `[722] button 'Show Report'`. Agent on task 94 explicitly diagnosed: "I can see the 'Continue' button but I don't see its bid number." (See `mode-a-L5-shadow-dom-trace-report.md`) |
| Selection reason | **Second strongest effect, completely independent mechanism from L1.** L1 degrades information (semantic loss); L5 breaks the action channel (perception-action gap). Their combination tests whether information degradation + action breakage is super-additive. |

### L11 — `<a href>` → `<span onclick>` (FUNCTIONAL)

| Metric | Value |
|--------|-------|
| Claude text-only | 92.3% (-1.5pp) |
| Llama 4 text-only | 61.5% (-14.6pp, rank #3) |
| Mechanism | Converts links to spans with onclick handlers. Preserves visual appearance (blue + underline) but removes `href` attribute and `link` role from a11y tree. |
| Trace evidence | Under L11, GitLab sidebar shows `StaticText 'Contributors'` instead of `link 'Contributors'`. Claude constructs `goto()` URL as fallback; Llama 4 clicks StaticText 13 times and spirals. (See `mode-a-L11-L6-llama4-vulnerability-analysis.md`) |
| Selection reason | **Core component of composite low variant.** L11 alone is weak for Claude but devastating for Llama 4. The L1+L11 combination is the theoretical core of the composite low effect (landmark loss + link deletion = navigation collapse). This pair is the single most important interaction to test. |

### L2 — Remove all `aria-*` + `role` globally (SEMANTIC)

| Metric | Value |
|--------|-------|
| Claude text-only | 89.7% (-4.1pp) |
| Llama 4 text-only | 71.8% (-4.4pp) |
| Mechanism | Strips all ARIA attributes and explicit `role` from every element. Chromium's implicit role mapping still applies (e.g., `<nav>` still gets `navigation` role). |
| Trace evidence | Moderate effect — removes explicit ARIA labels and states but implicit roles survive. |
| Selection reason | **Tests overlap with L1.** L1 removes landmark *elements* (which carry implicit roles). L2 removes ARIA *attributes* (explicit roles). When L1 has already removed `<nav>`, L2's removal of `role="navigation"` is redundant. **Prediction: L1+L2 is sub-additive** due to this overlap. This is the key sub-additivity test case. |

### L6 — `<h1-h6>` → `<div>` with CSS preserved (SEMANTIC)

| Metric | Value |
|--------|-------|
| Claude text-only | 100% (0.0pp — zero effect) |
| Llama 4 text-only | 71.8% (-4.4pp) |
| Mechanism | Converts heading elements to divs, preserving font-size via inline CSS. Removes `heading` role from a11y tree but visual appearance unchanged. |
| Trace evidence | Claude 100% — headings are not needed when landmarks are present. Llama 4 switches from "scan headings" to "click into each post" strategy under L6. (See `mode-a-L11-L6-llama4-vulnerability-analysis.md`) |
| Selection reason | **Tests "null + X" interaction.** L6 has zero Claude effect individually. If L1+L6 > L1 alone, it means headings become critical when landmarks are absent (compensatory role). If L1+L6 ≈ L1, headings are truly redundant. This distinguishes "headings are always irrelevant" from "headings are a backup navigation mechanism." |

### L9 — `<thead>/<tbody>/<tfoot>/<th>` → `<div>/<td>` (SEMANTIC)

| Metric | Value |
|--------|-------|
| Claude text-only | 89.7% (-4.1pp) |
| Llama 4 text-only | 71.8% (-4.4pp) |
| Mechanism | Destroys table semantic structure. `<thead>` → `<div>`, `<th>` → `<td>`. Table data becomes a flat grid without header associations. |
| Trace evidence | Primarily affects admin tasks with data tables (task 4 bestsellers, task 94 invoices). |
| Selection reason | **Tests task-specificity of interaction.** L9 only affects table-heavy pages. L1+L9 tests whether landmark loss + table structure loss is additive (independent page regions) or super-additive (agent needs landmarks to *find* the table, then table structure to *read* it — sequential dependency). |

### L12 — Duplicate IDs on adjacent elements (SEMANTIC)

| Metric | Value |
|--------|-------|
| Claude text-only | 79.5% (-14.4pp) |
| Llama 4 text-only | 69.2% (-6.9pp) |
| Mechanism | Copies element IDs to create duplicates (up to 5 pairs). Breaks `getElementById` lookups and ARIA `id`-based references (`aria-labelledby`, `aria-describedby`). |
| Trace evidence | Task 293 (GitLab): agent can't find repo via search (Vue.js ID dependency). Task 29: confound (starting page divergence, not ID effect). (See `mode-a-L12-task29-trace-analysis.md`) |
| Selection reason | **Tests framework-specific interaction.** L12's effect is concentrated on Vue.js (GitLab) pages where component state depends on ID lookups. L5+L12 and L11+L12 test whether Shadow DOM or link deletion compounds with ID corruption on framework-heavy pages. |

### L4 — Remove keyboard event handlers (FUNCTIONAL)

| Metric | Value |
|--------|-------|
| Claude text-only | 89.7% (-4.1pp) |
| Llama 4 text-only | 69.2% (-6.9pp) |
| Mechanism | Removes `onkeydown`, `onkeyup`, `onkeypress` attributes from all elements. Keyboard navigation and shortcuts stop working. |
| Trace evidence | Moderate effect — BrowserGym agents primarily use click() not keyboard, so direct impact is limited. Indirect impact: some dropdown menus require keyboard to navigate. |
| Selection reason | **Pure functional operator with no semantic overlap.** L4 doesn't change the a11y tree at all — it only removes behavioral handlers. L4+L5 tests "keyboard removal + button isolation" (double interaction barrier). L4+L11 tests "keyboard removal + link deletion" (both functional, but different targets). |

---

## 3. Interaction Predictions (28 pairs)

Each prediction is classified as: **super-additive** (combination worse than
sum of parts), **additive** (combination ≈ sum), **sub-additive** (combination
better than sum, due to overlap), or **null** (both operators too weak to detect).

### Tier 1: High-confidence predictions (testable hypotheses)

| # | Pair | Prediction | Mechanism rationale |
|---|------|-----------|-------------------|
| 1 | **L1+L11** | **Super-additive** | Composite low's core. L1 removes navigation skeleton, L11 removes navigation links. Individually: L1 agent can still click links to navigate; L11 agent can still use landmarks to orient. Together: no skeleton AND no links = complete navigation collapse. The composite low (23.3%) is far worse than L1 alone (53.8%) + L11 alone (92.3%), suggesting massive super-additivity. |
| 2 | **L1+L5** | **Super-additive** | L1 makes page flat (no regions), L5 makes buttons unclickable (ghost buttons). Agent can't find the right region AND can't click buttons even if found. Sequential dependency: need landmarks to find buttons, need buttons to act. |
| 3 | **L1+L2** | **Sub-additive** | L1 removes landmark elements (which carry implicit ARIA roles). L2 removes explicit ARIA attributes. After L1 removes `<nav>`, L2's removal of `role="navigation"` on remaining elements has less to remove. Shared pathway: both degrade the a11y tree's semantic richness. |
| 4 | **L5+L11** | **Additive** | Independent mechanisms on independent DOM targets. L5 wraps buttons/role-elements in Shadow DOM. L11 converts `<a>` to `<span>`. No DOM overlap (buttons ≠ links). No shared failure pathway. |
| 5 | **L1+L6** | **Additive or null** | L6 has zero Claude effect. If L1+L6 > L1: headings serve as backup navigation when landmarks are absent. If L1+L6 ≈ L1: headings are truly redundant for Claude. Either outcome is informative. |

### Tier 2: Exploratory predictions

| # | Pair | Prediction | Mechanism rationale |
|---|------|-----------|-------------------|
| 6 | L1+L9 | Additive | Landmark loss (navigation) + table destruction (content). Independent page regions. |
| 7 | L1+L4 | Additive | Landmark loss + keyboard removal. BrowserGym agents rarely use keyboard, so L4 adds little to L1. |
| 8 | L1+L12 | Additive | Landmark loss + ID duplication. Different DOM targets. |
| 9 | L5+L12 | Unknown | Shadow DOM + duplicate IDs. May interact on Vue.js components where ID-based lookups fail inside shadow boundaries. |
| 10 | L11+L12 | Unknown | Link deletion + ID duplication. Both affect GitLab Vue.js. Possible super-additivity on framework-heavy pages. |
| 11 | L4+L5 | Additive | Keyboard removal + Shadow DOM. Double interaction barrier but BrowserGym agents don't use keyboard much. |
| 12 | L2+L5 | Additive | ARIA removal + Shadow DOM. Independent: ARIA is on elements outside shadow roots. |
| 13 | L2+L11 | Additive | ARIA removal + link deletion. Independent mechanisms. |
| 14 | L6+L9 | Null | Both weak individually. Heading removal + table destruction on different page regions. |
| 15 | L2+L6 | Sub-additive | Both semantic. L2 removes ARIA (including heading-related ARIA). L6 removes heading elements. Partial overlap on heading semantics. |
| 16 | L4+L11 | Additive | Both functional but different targets (keyboard handlers vs href). No DOM overlap. |
| 17-28 | Remaining | Additive (default) | Most remaining pairs involve operators with independent mechanisms and non-overlapping DOM targets. Default prediction is additive. |

### Prediction summary

| Type | Count | Key pairs |
|------|-------|-----------|
| Super-additive | 2 | L1+L11, L1+L5 |
| Sub-additive | 2 | L1+L2, L2+L6 |
| Additive | 18 | L5+L11, L1+L9, L1+L4, ... |
| Null | 1 | L6+L9 |
| Unknown | 2 | L5+L12, L11+L12 |
| **Total** | **28** | |

---

## 4. SoM Exclusion Rationale

SoM (Set-of-Mark, vision-only) is excluded from C.2 for three reasons:

1. **Low signal-to-noise**: SoM achieved 25.1% overall in Mode A, with most
   failures attributable to phantom bid architecture issues (bid OCR errors),
   not operator effects. Operator-specific signal is undetectable against
   this noise floor.

2. **Phantom bid confound**: SoM's failure mechanism (misreading bid labels
   from screenshots) is independent of which operators are applied. Adding
   a second operator doesn't change the SoM overlay rendering, so pairwise
   interaction effects would be masked by the constant phantom bid failure rate.

3. **Cost efficiency**: Dropping SoM saves 33% of cases (1,092 fewer cases),
   reducing runtime from ~4.5 days to ~1.5 days per shard. This is critical
   given the 3-4 day account lifetime constraint.

Text-only and CUA are retained because:
- **Text-only** is the primary agent (89.5% baseline, highest operator sensitivity)
- **CUA** provides the vision-only control (47.8% baseline, tests whether
  compositional effects transfer to coordinate-based agents)

---

## 5. Shard Assignment

| Shard | Account | Expires | Pairs | Cases | Key content |
|-------|---------|---------|-------|-------|-------------|
| A | 190777959793 | May 04 23:56 UTC | 14 | 1,092 | All L1× (7) + all L2× excl L1 (6) + L4×L5 |
| B | 275201671198 | May 05 12:50 UTC | 14 | 1,092 | L4×{L6-L12} + L5×{L6-L12} + L6×{L9-L12} + L9×{L11,L12} + L11×L12 |

Shard A contains all L1 pairs — the most informative combinations (L1 is
the strongest individual operator, so its interactions have the highest
signal). Shard B contains the exploratory pairs.

---

## 6. Additivity Metric

For each pair (A, B), we compute:

```
interaction_effect = drop(A+B) - drop(A) - drop(B)
```

Where `drop(X) = H_baseline - success_rate(X)`.

Classification:
- **Super-additive**: interaction_effect > +5pp (combination worse than sum)
- **Additive**: |interaction_effect| ≤ 5pp
- **Sub-additive**: interaction_effect < -5pp (combination better than sum)

The 5pp threshold accounts for sampling noise at 3 reps × 13 tasks = 39 cases
per condition (95% CI ≈ ±10pp for a proportion near 0.5).

---

## 7. Paper Placement

Results from C.2 populate:
- **§5.4 Compositional Interaction Analysis**: main table (28 pairs × interaction_effect)
- **Figure 6**: Scatterplot of expected (additive) vs observed drop for 28 pairs
- **§6.1 "Why signatures align (or don't)"**: super-additive pairs reveal
  sequential dependencies between operator mechanisms

# Stale Figure Redraw Prompts (2026-06-17)

Self-contained image-generation prompts for the 4 stale figures (fig1, fig4,
fig5, figA1). **Each prompt carries its own RESEARCH CONTEXT block** so it can be
pasted into GPT Image (or handed to an illustrator) standalone. All numbers were
triple-checked against `figures/README.md`, the paper's frozen
`\Description`/`\caption` (paper repo `sections/*.tex`), and the paper §3.4/§5.2
definitions. **Do not alter any number.**

**Shared frozen facts (true for every figure here):**
- Paper: CHI 2027, "Structure, Not Magnitude: How Web-Accessibility Degradation
  Shapes LLM Web-Agent Behavior." Single-column ACM `manuscript` format.
- 26 AMT operators in 3 families: **Low L1–L13 (13)**, **Midlow ML1–ML3 (3)**,
  **High H1–H8 = 10 total** (H5 splits into H5a/b/c).
- 3 agent architectures: **text-only** (reads a11y tree), **SoM** (screenshot +
  DOM-derived bid overlays), **CUA** (raw screenshot pixels, zero DOM dependency).
- 2 models: **Claude Sonnet 4** (primary) + **Llama 4 Maverick** (text-only).
- Total N = 14,768 cases.
- Palette: Low `#C0392B`, Midlow `#E67E22`, High `#27AE60`, base/neutral
  `#2471A3`. Semantic pathway = blue `#2471A3`; functional pathway = orange
  `#E67E22`; misaligned = red `#C0392B`; aligned = green `#27AE60`.
- Style: white background, flat, no shadows/gradients/3D/noise, rounded 4px
  corners, thin 1–2px borders, clean sans-serif (Inter / Helvetica Neue /
  DejaVu Sans), legible at 7pt print size. Single-column ≈ 3.33in wide,
  full-width ≈ 7in. Nature/Science/CHI publication quality, no chartjunk.

> ⚠️ **fig1 alt-text caveat:** the paper's current fig1 `\Description` still
> lists the OLD 6/11/4/5 quadrant counts. After fig1 is regenerated with the
> corrected 2/13/9/2, the `\Description` in `01-introduction.tex` must be updated
> to match (Claude can do this text edit). Otherwise an accessibility paper's
> alt-text contradicts its own figure.

---

## FIG 1 — AMT Framework Teaser (§1, full-width 16:9)

The maintained source of truth is `prompts/F1_amt_framework.md` (kept in sync;
fixed 2026-06-17: stale title, ML2/ML3 descriptions, DOM-signature dimension
labels, and injection-mechanism label). The full corrected prompt is reproduced
here for convenience.

```
RESEARCH CONTEXT:

I'm writing a CHI 2027 paper titled "Structure, Not Magnitude: How
Web-Accessibility Degradation Shapes LLM Web-Agent Behavior." Core question:
does web-accessibility degradation reduce AI web-agent task success, and which
violations matter and why? We answer with a taxonomy (AMT) of 26 DOM-level
operators, each measured two independent ways, and a "signature alignment"
analysis cross-referencing the two. Key finding: it is the STRUCTURE of the
observation space, not the MAGNITUDE of DOM change, that governs behavior —
most violations are benign, a structural minority (landmarks) is catastrophic,
and 42% of operators are MISALIGNED between DOM change and behavioral impact.

THIS FIGURE (fig1) is the paper's teaser/overview. A reader should grasp at a
glance: 26 operators in 3 families → measured two ways (DOM + behavioral) →
cross-referenced for alignment.

FRAMING NOTE (drives the behavioral side): the VISUAL dimension is captured
OBJECTIVELY by the SSIM row inside the DOM signature (9,408-screenshot audit),
NOT by a vision agent. So the behavioral signature is NOT three co-equal agents:
it is text-only (PRIMARY — the only agent in the 48-task breadth set, N=7,488),
plus CUA as a DOM-BYPASS CONTROL (it enables the functional/semantic
decomposition and the super-additivity dissociation), plus SoM as a minor
single-phase phantom-bid probe. Drawing three equal agent columns over-claims
SoM/CUA and invites "where is the breadth data for those agents?"

---

Create a clean academic teaser figure, landscape 16:9 (2560×1440px), for a
CHI 2027 paper on how web accessibility affects AI agents.

Title at top center (bold, 12pt): "Accessibility Manipulation Taxonomy (AMT) — Experimental Framework"

THREE horizontal bands, top to bottom, connected by downward arrows:
"Define operators → Measure two ways → Cross-reference for alignment."

═══ BAND 1 (~30% height): "26 Operators in 3 Families" ═══
Three equal-width rounded rectangles side by side:

LEFT (Low): fill light red #FDEDEC, border #C0392B 2px.
- Header (bold 11pt): "Low (L1–L13)"   Subheader (italic 9pt): "13 degradation operators"
- Body (8pt): L1 Landmark→div | L2 Remove ARIA | L3 Remove labels |
  L4 Remove kbd handlers | L5 Shadow DOM | L6 Heading→div | L7 Remove alt |
  L8 Remove tabindex | L9 Table→div | L10 Remove lang | L11 Link→span |
  L12 Dup IDs | L13 Focus blur

MIDDLE (Midlow): fill light orange #FEF5E7, border #E67E22 2px.
- Header: "Midlow (ML1–ML3)"   Subheader: "3 pseudo-compliance operators"
- Body: ML1 Empty btn→div | ML2 Remove kbd handlers (role=button) |
  ML3 Remove labels (no placeholder)

RIGHT (High): fill light green #EAFAF1, border #27AE60 2px.
- Header: "High (H1–H8)"   Subheader: "10 enhancement operators (H1–H4, H5a/b/c, H6–H8)"
- Body: H1 Auto aria-label | H2 Skip-nav | H3 Associate labels | H4 Add landmarks |
  H5a-c Auto alt/lang/links | H6–H8 States + table scope

═══ BAND 2 (~30% height): "Dual Signature Measurement" ═══
Two parallel rounded rectangles, a small "×" between them (cross-product):

LEFT (DOM Signature): fill light blue #EBF5FB, border #2471A3.
- Header (bold): "DOM Signature (12 dimensions, 4 categories)"
- Body — use EXACTLY these labels, do NOT invent D2/D3 or V2/V3:
  "Structure (D1): tag-count delta"
  "Semantics (A1–A3): role, accessible-name, ARIA-state changes"
  "Visual (V1): full-page SSIM  ← objective visual-equivalence audit"
  "Functional (F1–F3): interactive-element, handler, focusable-element deltas"
- Footer: "Objective, per-operator (39 samples); the V1/SSIM row rules out
  visual confounds — e.g. L1 changes behavior at SSIM=1.000"

RIGHT (Behavioral Signature): fill light purple #F4ECF7, border #7D3C98.
- Header (bold): "Behavioral Signature"
- NOT three equal agents (the visual dimension is handled by the SSIM row on the
  left, not by a vision agent here). Draw ONE prominent primary row, ONE smaller
  control row, and a single muted footnote line:
  • PRIMARY (bold, larger, ~55% height): "Text-only agent — a11y tree → text
    actions · PRIMARY · Claude Sonnet 4 + Llama 4 Maverick · all phases incl.
    the 48-task breadth set (N=7,488)"
  • CONTROL (smaller, ~30% height, secondary): "CUA agent — raw pixels →
    coordinates · DOM-BYPASS CONTROL (isolates the functional pathway; yields
    the super-additivity dissociation)"
  • FOOTNOTE (small, muted, ~15% height): "SoM overlay agent: single-phase
    phantom-bid probe (Phase 1 + depth only); see §5.7"
- Footer: "Behavioral drop vs. High-operator baseline"

═══ BAND 3 (~30% height): "Signature Alignment (Core Contribution)" — make this
the most visually prominent band ═══
A 2×2 matrix (confusion-matrix style):
- Column headers: "Behavior ACTIVE (drop ≥ 5pp)" | "Behavior NULL (drop < 5pp)"
- Row headers: "DOM ACTIVE (≥ threshold)" | "DOM MINIMAL (< threshold)"

Top-left (light green fill, green border): "✓ ALIGNED" /
  "Both active — 2 ops (8%)" / small "L1, L5 (destructive)"
Top-right (light red fill, red border): "✗ MISALIGNED" /
  "Agent Adaptation — 9 ops (35%)" / small "DOM devastated, agents adapt (e.g. L11)"
Bottom-left (light red fill, red border): "✗ MISALIGNED" /
  "Structural Criticality — 2 ops (8%)" / small "tiny DOM change, large impact (L10, L12)"
Bottom-right (light green fill, green border): "✓ ALIGNED" /
  "Both null — 13 ops (50%)" / small "most High operators (no effect)"

Connecting elements:
- Thick arrow Band 1 → Band 2: "JavaScript DOM injection after page load
  (idempotent IIFE via page.evaluate)"
- Two arrows Band 2 → Band 3: left "12-dim vector", right "drop in pp"

CRITICAL ACCURACY:
- Quadrant counts are 2 / 13 / 9 / 2 (aligned-active / aligned-null /
  agent-adaptation / structural-criticality). Overall misalignment = 9 + 2 =
  11 of 26 = 42%. Do NOT label any single cell "42%".
- Thresholds: DOM-active = (|D1|+|A1|+|A2| ≥ 5.0) OR (SSIM < 0.99);
  behavior-active = Claude text-only drop ≥ 5pp. Must match paper §3.4/§5.2.
- High family is 10 operators total (H5 → H5a/b/c). Model is "Claude Sonnet 4".
```

---

## FIG 4 — Three-Tier Severity Framework (§4, single-column, 3 cards)

```
RESEARCH CONTEXT:

CHI 2027 paper "Structure, Not Magnitude" — how web-accessibility degradation
affects LLM web agents. We propose a three-tier severity framework that sorts
accessibility violations by their impact on the Accessibility Tree's structural
integrity, and show that only the structural tier collapses AI-agent success.
This reframes the widely cited "95.9% of sites fail WCAG" statistic: most
violations are decorative or annotative and agent-benign; only a structural
minority is fatal. The tiers (1/2/3) are a severity axis distinct from the
operator IDs (L1–L13) — never conflate them.

THIS FIGURE (fig4) presents that framework as three escalating-severity cards.

---

Create a clean academic figure: a three-tier accessibility-severity framework
as THREE side-by-side cards of equal width in one row. Single-column width
(~3.33in; design at 1000×620px, keep text large). White background, flat, no
shadows/gradients, rounded 4px corners, thin 2px borders, clean sans-serif.

Title (bold 11pt): "Three-Tier Accessibility Severity Framework"

Each card has: bold tier header, italic category name, an "Examples" line, a
"Prevalence" line, a "Human impact" line, and a prominent "Agent impact" badge.

CARD 1 — gray (fill #F4F4F4, border #7F8C8D):
- Header: "Tier 1 — Decorative"
- Examples: "Missing alt text on decorative images; empty headings"
- Prevalence: "~70% of sites"
- Human impact: "Minor (screen readers skip)"
- Agent impact badge (gray): "0 pp — none"

CARD 2 — amber (fill #FEF5E7, border #E67E22):
- Header: "Tier 2 — Annotative"
- Examples: "Missing/incorrect ARIA labels; broken form-label association"
- Prevalence: "~20% of sites"
- Human impact: "Moderate (confusing labels)"
- Agent impact badge (amber): "0 pp — none"

CARD 3 — red (fill #FDEDEC, border #C0392B, THICKER border — this is the punchline):
- Header: "Tier 3 — Structural"
- Examples: "Semantic HTML replaced by generic containers (nav→div, a→span)"
- Prevalence: "82.4% of 34 audited sites"
- Human impact: "Severe (navigation breaks)"
- Agent impact badge (red, largest/boldest): "≈ −55 pp — catastrophic"

Bottom banner (bold, light-red strip, full width): "Only Tier 3 structural
violations cascade into AI agent failure."

CRITICAL ACCURACY (the old figure was WRONG here):
- Use "Tier 1 / Tier 2 / Tier 3", NEVER "L1 / L2 / L3" (those are operator IDs).
- Tier-3 prevalence is "82.4%" over "34 audited sites" (NOT 83.3%, NOT 30 sites).
- Tier 1 and Tier 2 agent impact are BOTH "0 pp"; only Tier 3 is catastrophic.
```

---

## FIG 5 — Contribution Decomposition Schematic (§5.1, single-column flow)

```
RESEARCH CONTEXT:

CHI 2027 paper "Structure, Not Magnitude." One experiment isolates WHY a
structural accessibility violation hurts agents by comparing two agent types on
the same degraded pages: a text-only agent (depends on the DOM/Accessibility
Tree) and a CUA agent (acts on raw pixels, bypasses the DOM). The gap between
their success drops decomposes the total effect into a SEMANTIC pathway (a11y
tree degraded — only the text-only agent sees this) and a FUNCTIONAL pathway
(DOM structure broken — both agents see this). This is a contribution
decomposition, NOT a precisely estimated causal effect; the semantic residual's
confidence interval crosses zero, so it is reported as an upper bound — that
hedge is load-bearing and must appear.

THIS FIGURE (fig5) is the two-pathway decomposition schematic (Claude only).

---

Create a clean academic flow diagram decomposing one effect into two pathways.
Single-column width (~3.33in; design at 1000×720px, large text). White
background, flat, clean sans-serif, thin 2px borders, rounded corners.

Title (bold 11pt): "Contribution Decomposition of the Composite-Low Effect (Claude)"

TOP — one source box (red fill #FDEDEC, red border #C0392B, bold):
"Tier 3 Structural Violation  (nav→div, a→span)"

Two arrows fan downward into two parallel pathways:

LEFT/UPPER — Semantic (blue #2471A3):
- Arrow label: "Semantic pathway"
- Mid box (light blue): "A11y Tree degraded — roles & labels lost"
- End box (blue border): "Text-only agent fails"
- Big number: "≈ 20.0 pp"  with smaller "(95% CI [−13.8, 52.3])"
- Gray annotation: "Screen-reader users face the same semantic loss"

RIGHT/LOWER — Functional (orange #E67E22):
- Arrow label: "Functional pathway"
- Mid box (light orange): "DOM structure broken — hrefs & handlers lost"
- End box (orange border): "CUA agent fails"
- Big number: "≈ 35.4 pp"  with smaller "(95% CI [15.4, 55.4])"
- Gray annotation: "Keyboard-navigation users face the same structural loss"

Small dashed purple callout to one side: "SoM phantom bids: 4.6% success at Low"

FOOTER equation box (light gray, centered, bold), exactly:
"Text-only drop 55.4 pp  −  CUA drop 35.4 pp  =  ≈ 20.0 pp semantic pathway
 (upper-bound estimate; the residual semantic CI crosses zero)"

CRITICAL ACCURACY (old version had stale numbers):
- Source box says "Tier 3 Structural", NEVER "L3".
- Functional = 35.4 pp, CI [15.4, 55.4] (NOT "Δ23pp", not 35 alone).
- Semantic = 20.0 pp, CI [−13.8, 52.3] — the CI MUST be shown and noted as
  crossing zero / an upper bound (load-bearing honesty hedge).
- Text-only total = 55.4 pp. SoM = 4.6%. Exact; do not re-round.
- The functional estimate is an upper bound on the pure functional pathway; the
  20.0 pp semantic residual is a lower bound. Label them so if room allows.
```

---

## FIG A1 — Full Five-Layer Architecture (Appendix B, single-column stack)

```
RESEARCH CONTEXT:

CHI 2027 paper "Structure, Not Magnitude." Three AI-agent types observe and act
on the SAME web page through different pipelines. The experiment modifies only
the live DOM (variant injection); everything above is auto-derived. The key
control: the CUA agent acts on rendered pixels and BYPASSES the Accessibility
Tree entirely, which is what lets us separate DOM-dependent from
DOM-independent failure. This appendix figure is the detailed five-layer
companion to the simpler three-column main-text architecture figure (fig2);
keep the same visual language.

THIS FIGURE (figA1) is the full L0→L4 stack with the CUA DOM-bypass path.

---

Create a clean academic architecture diagram: a FIVE-LAYER stack (L0 bottom to
L4 top) showing how three AI-agent types observe/act on a shared web page.
Single-column width (~3.33in; design at 1100×900px, large legible text). White
background, flat, clean sans-serif, thin 2px borders.

Title (bold 11pt): "Full Five-Layer Observation Architecture"

FIVE horizontal layer bands, bottom to top, labeled on the left edge:

L0 — Web server (gray): "Magento · GitLab · Reddit (Postmill) · PHP-MMA · Kiwix"

L1 — Live DOM (highlighted, red accent border #C0392B): bold "L1: Live DOM —
the ONLY layer we modify". Annotation: "Variant injection applies idempotent
JavaScript patches after page load, before agent interaction."

L2 — Accessibility Tree (blue #2471A3): "Chrome-internal AX tree, auto-derived
from the DOM (CDP Accessibility.getFullAXTree)."

L3 — BrowserGym processing (blue): "AXTree serialization (text-only path) ·
screenshot + numbered bid-overlay generation (SoM path) · bid lifecycle."

L4 — Agent observation & action (top): THREE columns side by side:
  • Text-only: "AXTree text → click-by-bid"
  • SoM vision: "screenshot + bid overlays → click labels"  (hazard note:
    "phantom bid: DOM node removed, bid label persists")
  • CUA coordinate: "raw screenshot pixels → mouse coordinates"

PATHWAYS:
- Text-only and SoM rise through L1→L2→L3→L4 (solid arrows).
- CUA BYPASSES L2 and L3: a dashed vertical arrow straight from L1 (rendered
  pixels) up to the CUA column in L4, labeled "DOM-bypass"; mark L2/L3
  "skipped" for that path.

RESULTS CALLOUT (bottom-right, light gray), Claude Sonnet 4:
  "Composite Low success (Claude Sonnet 4):
     Text-only 38.5%  ·  SoM 4.6%  ·  CUA 58.5%
   Decomposition: 55.4 pp total = 35.4 functional + 20.0 semantic"

CRITICAL ACCURACY (old version had stale numbers):
- Model is "Claude Sonnet 4" (NOT "Sonnet 3.5", NOT "Pilot-4").
- Composite-Low rates: text-only 38.5%, SoM 4.6%, CUA 58.5%.
- Decomposition: 55.4 pp = 35.4 functional + 20.0 semantic (NOT "63.3pp").
- L1 is the only modified layer; the CUA dashed bypass of L2/L3 is the key visual.
```

# F1: AMT Framework Overview

## Background Context (给 GPT 的研究背景)

```
RESEARCH CONTEXT:

I'm writing a CHI 2027 paper titled "Structure, Not Magnitude: How Web-Accessibility Degradation Shapes LLM Web-Agent Behavior."

The core research question: Does web accessibility degradation causally reduce AI agent task success? We answer YES, and we provide a systematic taxonomy (AMT) to characterize exactly HOW different types of accessibility violations affect different types of AI agents.

KEY CONCEPTS:
- We have 26 "operators" — small JavaScript patches that modify a live web page's DOM to simulate real-world accessibility violations (or enhancements).
- These operators are organized into 3 families:
  - Low (L1-L13): Aggressive degradation — removes landmarks, headings, links, ARIA attributes
  - Midlow (ML1-ML3): Pseudo-compliance — looks accessible but handlers are broken
  - High (H1-H8): Enhancement — adds ARIA labels, skip-nav, landmarks (positive direction)
- We measure each operator's effect in TWO independent ways:
  1. DOM Signature: 12-dimensional objective measurement of what changed in the page (structure, semantics, visual, functional)
  2. Behavioral Signature: How much each of 3 different AI agent architectures drops in task success
- The 3 agent architectures (but with DELIBERATELY UNEQUAL evidentiary weight — see framing note):
  - Text-only: reads the accessibility tree (most sensitive to semantic changes) — the PRIMARY measure, the only agent in the 48-task breadth set (N=7,488)
  - CUA (Computer Use Agent): sees only screenshot, clicks coordinates (zero DOM dependency) — used as a DOM-BYPASS CONTROL, not as a "vision" arm; it is what makes the functional/semantic decomposition and the super-additivity dissociation possible
  - SoM (Set-of-Mark): screenshot + DOM-derived numbered overlays — the weakest arm; only a single-phase phantom-bid probe

- FRAMING NOTE (important for how to draw the behavioral side): the VISUAL
  dimension is captured OBJECTIVELY by the SSIM row inside the DOM signature
  (we audited 9,408 screenshots), NOT by pitting a vision agent against a text
  agent. So the behavioral signature is NOT three co-equal agents — it is
  text-only (primary) + CUA (DOM-bypass control), with SoM as a minor probe.
  Drawing three equal agent columns would over-claim SoM/CUA and invite the
  reviewer question "where is the breadth data for those agents?"
- The CORE CONTRIBUTION is "Signature Alignment" — cross-referencing DOM signatures with behavioral signatures to empirically determine which layer (semantic/visual/functional) each operator actually affects.
- KEY FINDING: 42% of operators show MISALIGNMENT — the DOM changes a lot but agents don't care (agent adaptation), or the DOM barely changes but agents collapse (structural criticality). The misalignments are the most scientifically interesting cases.

PAPER VENUE: ACM CHI 2027 (top HCI conference). Figures should look like high-quality CHI/UIST/Nature HCI figures — clean, minimal, professional.

THIS FIGURE (F1) is the paper's teaser/overview figure. It should communicate the ENTIRE experimental framework at a glance. A reader should look at this and immediately understand: "They have a taxonomy of 26 operators, they measure each one two ways, and they cross-reference to find alignment."
```

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (16:9, 2560×1440px). This is Figure 1 (teaser) for a CHI 2027 paper on how web accessibility affects AI agents.

Title at top center (bold, 12pt): "Accessibility Manipulation Taxonomy (AMT) — Experimental Framework"

The figure has THREE horizontal bands flowing top-to-bottom, connected by downward arrows. The visual flow communicates: "We define operators → We measure them two ways → We cross-reference for alignment."

═══ BAND 1 (top, ~30% height): "26 Operators in 3 Families" ═══

Three rounded rectangles side by side with equal width:

LEFT BOX:
- Fill: very light red (#FDEDEC), border: dark red (#C0392B), 2px
- Header (bold, 11pt): "Low (L1–L13)"
- Subheader (italic, 9pt): "13 degradation operators"
- Body (8pt, compact list):
  L1 Landmark→div | L2 Remove ARIA | L3 Remove labels
  L4 Remove kbd handlers | L5 Shadow DOM | L6 Heading→div
  L7 Remove alt | L8 Remove tabindex | L9 Table→div
  L10 Remove lang | L11 Link→span | L12 Dup IDs | L13 Focus blur

MIDDLE BOX:
- Fill: very light orange (#FEF5E7), border: dark orange (#E67E22), 2px
- Header: "Midlow (ML1–ML3)"
- Subheader: "3 pseudo-compliance operators"
- Body: ML1 Empty btn→div | ML2 Remove kbd handlers (role=button) | ML3 Remove labels (no placeholder)

RIGHT BOX:
- Fill: very light green (#EAFAF1), border: dark green (#27AE60), 2px
- Header: "High (H1–H8)"
- Subheader: "10 enhancement operators (H1–H4, H5a/b/c, H6–H8)"
- Body: H1 Auto aria-label | H2 Skip-nav | H3 Associate labels | H4 Add landmarks | H5a-c Auto alt/lang/links | H6-H8 States+scope

═══ BAND 2 (middle, ~30% height): "Dual Signature Measurement" ═══

Two parallel rounded rectangles side by side:

LEFT BOX (DOM Signature):
- Fill: light blue (#EBF5FB), border: #2471A3
- Header (bold): "DOM Signature (12 dimensions, 4 categories)"
- Body as 4 compact rows (use EXACTLY these dimension labels — they must match
  the paper; do NOT invent D2/D3 or V2/V3):
  "Structure (D1): tag-count delta"
  "Semantics (A1–A3): role, accessible-name, ARIA-state changes"
  "Visual (V1): full-page SSIM  ← objective visual-equivalence audit"
  "Functional (F1–F3): interactive-element, handler, focusable-element deltas"
- Small footer: "Objective, per-operator (39 samples); the V1/SSIM row is how we
  rule out visual confounds — e.g. L1 changes behavior at SSIM=1.000"

RIGHT BOX (Behavioral Signature):
- Fill: light purple (#F4ECF7), border: #7D3C98
- Header (bold): "Behavioral Signature"
- This box is NOT three equal agents. Draw ONE prominent primary row, ONE
  smaller control row, and a single footnote line — reflecting that the visual
  dimension is handled objectively by the SSIM row on the left, not by a vision
  agent here:
  • PRIMARY row (bold, larger, take ~55% of the box height):
    "Text-only agent — a11y tree → text actions
     PRIMARY measure · Claude Sonnet 4 + Llama 4 Maverick · all phases,
     incl. the 48-task breadth set (N=7,488)"
  • CONTROL row (smaller, ~30% height, visually secondary):
    "CUA agent — raw pixels → coordinates · DOM-BYPASS CONTROL
     (isolates the functional pathway; yields the super-additivity dissociation)"
  • FOOTNOTE line (small, muted, ~15% height):
    "SoM overlay agent: single-phase phantom-bid probe (Phase 1 + depth only); see §5.7"
- Small footer: "Behavioral drop vs. High-operator baseline"

Between the two boxes, a small "×" symbol indicating cross-product measurement.

═══ BAND 3 (bottom, ~30% height): "Signature Alignment (Core Contribution)" ═══

A 2×2 matrix (confusion-matrix style):

Column headers: "Behavior ACTIVE (drop > 5pp)" | "Behavior NULL (drop < 5pp)"
Row headers: "DOM ACTIVE (changes > threshold)" | "DOM MINIMAL (changes < threshold)"

Top-left cell (light green fill, green border):
- "✓ ALIGNED" (bold)
- "Both active — 2 ops (8%)"
- Small: "L1, L5 (destructive)"

Top-right cell (light red fill, red border):
- "✗ MISALIGNED" (bold)
- "Agent Adaptation — 9 ops (35%)"
- Small: "DOM devastated but agents find workarounds (e.g. L11)"

Bottom-left cell (light red fill, red border):
- "✗ MISALIGNED" (bold)
- "Structural Criticality — 2 ops (8%)"
- Small: "Tiny DOM change, outsized behavioral impact (L10, L12)"

Bottom-right cell (light green fill, green border):
- "✓ ALIGNED" (bold)
- "Both null — 13 ops (50%)"
- Small: "most H operators (no measurable effect)"

NOTE (for whoever regenerates this figure): the overall misalignment headline
is 11 of 26 = 42% (= the 9 agent-adaptation + 2 structural-criticality cells).
Do NOT label any single cell "42%" — 42% is the SUM of the two misaligned cells.
These counts use the paper-default thresholds (DOM-active ≥5.0 on |D1|+|A1|+|A2|
or SSIM<0.99; behavior-active ≥5pp) and must match paper §5.2 exactly.

═══ CONNECTING ELEMENTS ═══

- Thick downward arrow from Band 1 → Band 2, labeled "JavaScript DOM injection after page load (idempotent IIFE via page.evaluate)"
- Two arrows from Band 2 → Band 3: left arrow "12-dim vector", right arrow "drop in pp"
- The overall visual flow is clearly top-to-bottom: Define → Measure → Analyze

═══ STYLE REQUIREMENTS ═══

- White background, no texture, no noise
- All borders: thin (1-2px), rounded corners (4px radius)
- Font: clean sans-serif (Inter, Helvetica Neue, or similar)
- No shadows, no gradients, no 3D effects, no decorative elements
- Muted academic color palette (pastels for fills, dark for borders/text)
- All text must be perfectly legible at CHI paper print size (~7" wide)
- Visual hierarchy: Band 3 (alignment matrix) should be the most visually prominent element — it's the punchline
- Overall aesthetic: Nature/Science/CHI publication quality
```

## Iteration Guidance
- If text is too dense, prioritize Band 3 (alignment matrix) — it's the core contribution
- If layout is cramped, switch to 4:3 aspect ratio or make figure taller
- The 2×2 alignment matrix should visually "pop" — consider slightly larger or bolder borders
- Band 1 operator lists can be abbreviated if space is tight (just show L1-L5 + "..." + L13)

# F1: AMT Framework Overview

## Background Context (给 GPT 的研究背景)

```
RESEARCH CONTEXT:

I'm writing a CHI 2027 paper titled "Same Barrier, Different Signatures: An Accessibility Manipulation Taxonomy for Web Agents."

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
- The 3 agent architectures:
  - Text-only: reads the accessibility tree (most sensitive to semantic changes)
  - SoM (Set-of-Mark): sees screenshot with numbered labels (hybrid)
  - CUA (Computer Use Agent): sees only screenshot, clicks coordinates (pure vision, zero DOM dependency)
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
- Body: ML1 Empty btn→div | ML2 Clone-replace handlers | ML3 Remove label+aria

RIGHT BOX:
- Fill: very light green (#EAFAF1), border: dark green (#27AE60), 2px
- Header: "High (H1–H8)"
- Subheader: "8 enhancement operators"
- Body: H1 Auto aria-label | H2 Skip-nav | H3 Associate labels | H4 Add landmarks | H5a-c Auto alt/lang/links | H6-H8 States+scope

═══ BAND 2 (middle, ~30% height): "Dual Signature Measurement" ═══

Two parallel rounded rectangles side by side:

LEFT BOX (DOM Signature):
- Fill: light blue (#EBF5FB), border: #2471A3
- Header (bold): "DOM Signature (12 dimensions)"
- Body as 4 compact rows:
  "D1-D3: Structure (tags, attributes, nodes)"
  "A1-A3: Semantics (roles, names, ARIA states)"
  "V1-V3: Visual (SSIM, bbox shift, contrast)"
  "F1-F3: Functional (interactive count, handlers, focusable)"
- Small footer: "Objective, per-operator, averaged over 13 tasks × 3 reps"

RIGHT BOX (Behavioral Signature):
- Fill: light purple (#F4ECF7), border: #7D3C98
- Header (bold): "Behavioral Signature (3 agents × 2 models)"
- Body as 3 rows:
  "Text-only: a11y tree → text actions (most sensitive)"
  "SoM Vision: screenshot + bid overlay → click actions"
  "CUA Coordinate: screenshot only → coordinate actions (zero DOM dependency)"
- Small footer: "Claude Sonnet 3.5 + Llama 4 Maverick, 13 tasks × 3 reps"

Between the two boxes, a small "×" symbol indicating cross-product measurement.

═══ BAND 3 (bottom, ~30% height): "Signature Alignment (Core Contribution)" ═══

A 2×2 matrix (confusion-matrix style):

Column headers: "Behavior ACTIVE (drop > 5pp)" | "Behavior NULL (drop < 5pp)"
Row headers: "DOM ACTIVE (changes > threshold)" | "DOM MINIMAL (changes < threshold)"

Top-left cell (light green fill, green border):
- "✓ ALIGNED" (bold)
- "Both active — 6 ops (23%)"
- Small: "L1, L5 (destructive)"

Top-right cell (light red fill, red border):
- "✗ MISALIGNED" (bold)
- "Agent Adaptation — 11 ops (42%)"
- Small: "DOM devastated but agents find workarounds"

Bottom-left cell (light red fill, red border):
- "✗ MISALIGNED" (bold)
- "Structural Criticality — 4 ops (15%)"
- Small: "Tiny DOM change, outsized behavioral impact"

Bottom-right cell (light green fill, green border):
- "✓ ALIGNED" (bold)
- "Both null — 5 ops (19%)"
- Small: "H5a, H5b, H6 (no measurable effect)"

═══ CONNECTING ELEMENTS ═══

- Thick downward arrow from Band 1 → Band 2, labeled "JavaScript injection via Plan D (context.route + MutationObserver)"
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

# F1: AMT Framework Overview

## Purpose
Paper teaser figure (§1 or §3). Shows the full AMT pipeline:
operators → injection → dual measurement → alignment analysis.

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (16:9, 2560×1440px).

Title at top center: "Accessibility Manipulation Taxonomy (AMT) — Experimental Framework"

The figure has THREE horizontal bands flowing top-to-bottom, connected by downward arrows.

═══ BAND 1 (top, ~30% height): "26 Operators in 3 Families" ═══

Three rounded rectangles side by side with equal width:

LEFT BOX:
- Fill: very light red (#FDEDEC), border: dark red (#C0392B), 2px
- Header (bold, 11pt): "Low (L1–L13)"
- Subheader (italic, 9pt): "13 degradation operators"
- Body (8pt, 2 columns):
  Column 1: L1 Landmark→div, L2 Remove ARIA, L3 Remove labels, L4 Remove kbd, L5 Shadow DOM, L6 Heading→div, L7 Remove alt
  Column 2: L8 Remove tabindex, L9 Table→div, L10 Remove lang, L11 Link→span, L12 Dup IDs, L13 Focus blur

MIDDLE BOX:
- Fill: very light orange (#FEF5E7), border: dark orange (#E67E22), 2px
- Header: "Midlow (ML1–ML3)"
- Subheader: "3 pseudo-compliance operators"
- Body: ML1 Empty btn→div, ML2 Clone-replace handlers, ML3 Remove label+aria

RIGHT BOX:
- Fill: very light green (#EAFAF1), border: dark green (#27AE60), 2px
- Header: "High (H1–H8)"
- Subheader: "8 enhancement operators"
- Body: H1 Auto aria-label, H2 Skip-nav, H3 Associate labels, H4 Add landmarks, H5a-c Auto alt/lang/links, H6-H8 States+scope

═══ BAND 2 (middle, ~30% height): "Dual Signature Measurement" ═══

Two parallel rounded rectangles with a vertical divider between them:

LEFT MEASUREMENT BOX:
- Fill: light blue (#EBF5FB), border: #2471A3
- Header: "DOM Signature (12 dimensions)"
- Body as 4 rows:
  "D1-D3: Structure (tags, attributes, nodes)"
  "A1-A3: Semantics (roles, names, states)"
  "V1-V3: Visual (SSIM, bbox shift, contrast)"
  "F1-F3: Functional (interactive, handlers, focusable)"
- Footer: "Measured via Playwright + CDP audit"

RIGHT MEASUREMENT BOX:
- Fill: light purple (#F4ECF7), border: #7D3C98
- Header: "Behavioral Signature (3 agents × 2 models)"
- Body as 3 rows with icons:
  "🔤 Text-only: DOM a11y tree → text actions"
  "👁️ SoM Vision: Screenshot + bid overlay → click actions"
  "🖱️ CUA Coordinate: Screenshot only → coordinate actions"
- Footer: "Claude Sonnet 3.5 + Llama 4 Maverick"

Between the two boxes, a small diamond shape labeled "×" indicating cross-product.

═══ BAND 3 (bottom, ~30% height): "Signature Alignment Analysis" ═══

A 2×2 matrix (like a confusion matrix) with:

Top-left cell (light green fill):
- "✓ ALIGNED"
- "Both active"
- "6 operators (23%)"
- Small text: "L1, L5, L11, ML3, H1, H5c"

Top-right cell (light red fill):
- "✗ MISALIGNED"
- "DOM active → Behavior null"
- "11 operators (42%)"
- Small text: "Agent Adaptation"

Bottom-left cell (light red fill):
- "✗ MISALIGNED"
- "DOM minimal → Behavior active"
- "4 operators (15%)"
- Small text: "Structural Criticality"

Bottom-right cell (light green fill):
- "✓ ALIGNED"
- "Both null"
- "5 operators (19%)"
- Small text: "ML2, H4, H5a, H5b, H6"

Matrix has column headers: "Behavior Active" | "Behavior Null"
Matrix has row headers: "DOM Active" | "DOM Minimal"

═══ CONNECTING ARROWS ═══

- From Band 1 bottom → Band 2 top: thick downward arrow labeled "context.route() + Plan D injection"
- From Band 2 left box bottom → Band 3: arrow labeled "12-dim vector per operator"
- From Band 2 right box bottom → Band 3: arrow labeled "drop (pp) per operator"

═══ STYLE ═══

- White background, no texture
- All borders: thin (1-2px), rounded corners
- Font: clean sans-serif (similar to Helvetica Neue or Inter)
- No shadows, no gradients, no 3D effects
- Muted academic color palette
- All text must be perfectly legible at printed size
- Similar visual style to figures in CHI, UIST, or Nature HCI papers
```

## Iteration Notes
- If text is too small, ask to increase font size and reduce content density
- If layout is cramped, ask to make it taller (switch to 4:3 aspect)
- The 2×2 alignment matrix is the visual punchline — make it prominent

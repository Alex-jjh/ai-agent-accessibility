# F2: Injection Pipeline & Causal Decomposition

## Purpose
Shows HOW operators are injected into the live DOM (Plan D mechanism) AND
the three-agent causal decomposition logic. Combines the "how it works"
with the "why three agents" in one figure.

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (16:9, 2560×1440px). White background.

Title: "Operator Injection Mechanism & Three-Agent Causal Decomposition"

The figure is split into TWO PANELS side by side (left 55%, right 45%), separated by a thin vertical line.

═══ LEFT PANEL: "Plan D Injection Pipeline" ═══

A vertical flow diagram with 5 stages, connected by downward arrows:

STAGE 1 (top):
- Rounded box, light gray fill
- Text: "WebArena Docker (Magento / GitLab / Postmill)"
- Subtitle: "Serves unmodified HTML via HTTP"

↓ arrow labeled "HTTP response"

STAGE 2:
- Rounded box, light blue fill
- Text: "Playwright Browser Context"
- Subtitle: "BrowserGym manages page lifecycle"

↓ arrow labeled "context.route() intercept"

STAGE 3 (highlighted with dashed red border):
- Rounded box, light red fill (#FDEDEC)
- Header: "Plan D: Deferred Injection"
- Body (smaller text):
  "1. page.addInitScript() — registers operator JS"
  "2. DOMContentLoaded + 500ms delay"
  "3. Execute operator mutations"
  "4. MutationObserver guard — re-inject on DOM reset"
  "5. Set sentinel: data-amt-applied on <body>"
- Footer: "Survives SPA navigation, goto() reloads, framework re-renders"

↓ arrow labeled "DOM mutated"

STAGE 4:
- Rounded box, light green fill
- Text: "Modified Live DOM"
- Subtitle: "Operator effects visible in a11y tree + screenshot"

↓ arrow (splits into 3 branches)

STAGE 5 (three boxes side by side):
- Box A (blue): "Text-only Agent" — "Reads a11y tree serialization"
- Box B (purple): "SoM Agent" — "Sees screenshot + bid overlays"
- Box C (orange): "CUA Agent" — "Sees screenshot, clicks coordinates"

═══ RIGHT PANEL: "Causal Decomposition" ═══

A diagram showing how three agents isolate the causal pathway:

TOP: A horizontal bar labeled "Total a11y effect on text-only agent: −40pp (L1 example)"

Below it, the bar is decomposed into two segments:

SEGMENT 1 (left, larger, red):
- Label: "Semantic pathway: −30pp"
- Annotation below: "Text-only drops but CUA does not"
- Arrow pointing to: "Caused by: a11y tree degradation"

SEGMENT 2 (right, smaller, orange):
- Label: "Cross-layer: −10pp"
- Annotation below: "CUA also drops"
- Arrow pointing to: "Caused by: functional/visual side-effects"

Below the decomposition bar, three agent icons with their roles:

AGENT 1 (blue circle with "T"):
- "Text-only: FULL DOM dependency"
- "Perceives via a11y tree serialization"
- "Most sensitive to semantic operators"

AGENT 2 (purple circle with "S"):
- "SoM: PARTIAL DOM dependency"
- "Screenshot + DOM-derived bid labels"
- "Sensitive to phantom bid mechanism"

AGENT 3 (orange circle with "C"):
- "CUA: ZERO DOM dependency"
- "Pure screenshot + coordinate clicks"
- "Only affected by visual/functional changes"

At the bottom, a key insight box with light yellow fill:
"If text-only drops but CUA doesn't → effect is purely semantic (a11y tree pathway)"
"If both drop → effect has cross-layer functional component"

═══ STYLE ═══
- Clean, minimal, academic
- Thin borders (1px), rounded corners
- No shadows, no gradients, no 3D
- Sans-serif font, 9-11pt
- Muted colors (pastels for fills, dark borders)
- All text perfectly legible
- Similar to CHI/UIST system architecture figures
```

## Iteration Notes
- The left panel explains the engineering; the right panel explains the science
- If too dense, split into two separate figures
- The causal decomposition bar should be visually prominent (it's the key insight)
- CUA's "zero DOM dependency" is the crucial control condition — emphasize it

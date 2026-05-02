# F2: Injection Pipeline & Causal Decomposition

## Background Context (给 GPT 的研究背景)

```
RESEARCH CONTEXT:

This is Figure 2 for a CHI 2027 paper studying how web accessibility degradation affects AI agents. The paper uses WebArena (a realistic web benchmark with 4 live web apps: Magento e-commerce, GitLab, Reddit-like forum) as the test environment.

KEY TECHNICAL CHALLENGE WE SOLVED:
Web pages are dynamic — SPAs (Single Page Applications) re-render the DOM constantly. If we just inject JavaScript once, the page framework (KnockoutJS, Vue.js) will overwrite our changes. We developed "Plan D" — a three-layer defense mechanism that ensures our accessibility mutations PERSIST across page navigations, framework re-renders, and agent actions.

HOW INJECTION WORKS:
1. We intercept the page load via Playwright's context.route() API
2. We inject operator JavaScript via page.addInitScript() — runs before any page code
3. After DOMContentLoaded + 500ms (letting frameworks finish rendering), we execute mutations
4. A MutationObserver watches for DOM resets and re-applies mutations if the framework undoes them
5. A sentinel attribute (data-amt-applied) on <body> confirms injection succeeded

WHY THREE AGENTS (CAUSAL DECOMPOSITION):
The three agent architectures form a natural experiment for causal attribution:
- Text-only agent: reads the DOM accessibility tree → FULLY dependent on DOM semantics
- SoM agent: sees screenshot + DOM-derived bid labels → PARTIALLY dependent on DOM
- CUA agent: sees ONLY the screenshot, clicks by coordinates → ZERO DOM dependency

This creates a causal decomposition:
- If text-only drops 40pp but CUA drops 0pp → the effect is PURELY semantic (a11y tree pathway)
- If both text-only AND CUA drop → the effect has functional/visual side-effects beyond semantics
- Example: L1 (landmark→div) drops text-only by 40pp but CUA by only 10pp → 30pp is pure semantic, 10pp is cross-layer

This is analogous to epidemiological "attributable fraction" (Levin 1953) — we're decomposing the total effect into pathway-specific components.

VISUAL IDENTITY IS KEY:
Our operators change the DOM but NOT the visual appearance (SSIM ≈ 0.99-1.00 for most operators). The page LOOKS identical to a human user. Only the underlying semantic structure changes. This is what makes the experiment clean — we're isolating the semantic layer.

THIS FIGURE should communicate: (1) the injection mechanism is robust and invisible, and (2) the three agents let us decompose effects into semantic vs functional pathways.
```

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (16:9, 2560×1440px). This is Figure 2 for a CHI 2027 paper. It has TWO PANELS side by side.

Title at top: "Operator Injection Mechanism & Three-Agent Causal Decomposition"

═══ LEFT PANEL (55% width): "Plan D: Persistent DOM Injection" ═══

A vertical flow diagram with 5 stages connected by downward arrows. The flow shows how we inject accessibility mutations into a live web page without changing its visual appearance.

STAGE 1 (top, gray fill):
- Rounded box
- Icon: small server/docker icon
- Text: "WebArena Docker"
- Subtitle: "4 live web apps (Magento, GitLab, Postmill)"
- Small note: "Serves unmodified HTML — we never touch server code"

↓ thick arrow labeled "HTTP Response (original HTML)"

STAGE 2 (light blue fill):
- Rounded box
- Text: "Playwright Browser Context"
- Subtitle: "BrowserGym manages page lifecycle"
- Small note: "context.route() intercepts all navigation"

↓ arrow labeled "addInitScript() — before page code runs"

STAGE 3 (HIGHLIGHTED — dashed red border, light red fill, this is the key innovation):
- Larger rounded box
- Header (bold): "Plan D: Deferred Injection Engine"
- Body (numbered list, 8pt):
  "① Wait: DOMContentLoaded + 500ms (frameworks finish rendering)"
  "② Execute: Apply operator mutations to live DOM"
  "③ Guard: MutationObserver re-applies if framework resets DOM"
  "④ Verify: Set sentinel data-amt-applied on <body>"
  "⑤ Persist: Re-inject on every navigation/reload via init script"
- Footer badge: "Survives: SPA routing, goto() reloads, Vue/KnockoutJS re-renders"

↓ arrow labeled "DOM mutated (visual appearance unchanged, SSIM ≈ 1.0)"

STAGE 4 (light green fill):
- Rounded box
- Text: "Modified Live DOM"
- Two sub-labels side by side:
  Left: "Semantic structure: CHANGED ✗"
  Right: "Visual appearance: UNCHANGED ✓"

↓ arrow splits into 3 branches (fan-out)

STAGE 5 (three small boxes side by side):
- Box A (blue fill): "Text-only" — "Reads a11y tree"
- Box B (purple fill): "SoM" — "Screenshot + bids"
- Box C (orange fill): "CUA" — "Screenshot only"

═══ RIGHT PANEL (45% width): "Causal Decomposition via Agent Architecture" ═══

This panel explains WHY we use three agents — they form a natural experiment for isolating causal pathways.

TOP SECTION — "The Logic":
A simple diagram showing three agents as circles arranged vertically:
- Blue circle "T" (Text-only): arrow pointing to "DOM a11y tree" box → label "FULL dependency"
- Purple circle "S" (SoM): arrow pointing to both "DOM" and "Screenshot" → label "PARTIAL dependency"
- Orange circle "C" (CUA): arrow pointing to "Screenshot" only → label "ZERO DOM dependency"

MIDDLE SECTION — "Example: L1 (Landmark → div)":
A horizontal stacked bar showing the total effect decomposed:

Full bar width represents: "Text-only drop: −40pp"
The bar is split into two colored segments:
- Left segment (larger, red, ~75%): "Semantic pathway: −30pp"
  Annotation below: "Text-only drops, CUA does NOT → pure a11y tree effect"
- Right segment (smaller, orange, ~25%): "Cross-layer: −10pp"
  Annotation below: "CUA also drops → functional/visual side-effect"

BOTTOM SECTION — "Interpretation Key" (in a light yellow box):
Three rules in compact text:
"• Text drops, CUA doesn't → SEMANTIC effect (a11y tree pathway)"
"• Both drop equally → FUNCTIONAL effect (action channel broken)"
"• CUA drops, Text doesn't → VISUAL effect (screenshot changed)"
"→ Most operators: semantic-dominant (text >> CUA)"

═══ STYLE ═══
- White background, clean, minimal
- Thin borders (1-2px), rounded corners
- No shadows, no gradients, no 3D, no decorative elements
- Sans-serif font (Inter or similar), 8-11pt
- The LEFT panel is engineering (how); the RIGHT panel is science (why)
- The Plan D box (Stage 3) should be visually prominent — it's the technical contribution
- The decomposition bar in the right panel should be visually clear — it's the scientific contribution
- Overall: CHI/UIST publication quality
```

## Iteration Guidance
- If too dense, the right panel's "Example" section is the priority — keep the decomposition bar
- The left panel can be simplified by merging Stages 1+2 if needed
- The "SSIM ≈ 1.0" annotation is crucial — it communicates visual invisibility
- Consider adding a small "magnifying glass" icon on Stage 4 to emphasize "looks same, is different"

# AI Agent Accessibility Platform

Empirical research platform studying the relationship between web accessibility and AI agent task success. Tests the **"Same Barrier" hypothesis**: AI agents and screen reader users face structurally equivalent barriers because both depend on the browser Accessibility Tree.

**Target**: CHI 2027 / ASSETS 2027

## Key Finding

Degrading web accessibility from baseline to low causes text-only agent success to drop from 93.8% to 38.5% (Cochran-Armitage Z=6.635, p<0.000001) across 13 tasks and 1,040 experimental cases. Three-agent causal decomposition reveals two comparable pathways: DOM semantic degradation contributes ~20pp and functional breakage ~35pp. The effect replicates across both closed-source (Claude Sonnet) and open-source (Llama 4 Maverick) models.

## How It Works

We hold the agent constant and programmatically manipulate web accessibility at the DOM level, then measure how each agent type is affected.

### Reproducing the Verification

```bash
# Setup (first time only)
python3 -m venv analysis/.venv
source analysis/.venv/bin/activate  # Windows: analysis\.venv\Scripts\activate
pip install -r analysis/requirements.txt

# Verify all paper numbers against raw data
make verify-numbers

# Full pipeline: export CSV → verify → run statistics
make all
```

### Five-Layer Architecture

```
L4: Agent          Three agent types observe and act differently
L3: BrowserGym     Serializes AX Tree to text, draws SoM overlays, manages bid mapping
L2: Blink AX Tree  Chrome auto-derives from DOM (we never modify this directly)
L1: DOM            ★ THE ONLY LAYER WE MODIFY — all variant patches target here
L0: Server         WebArena apps (Magento, Postmill, GitLab) — untouched
```

We only modify the DOM. The AX Tree changes are automatic consequences. Three delivery mechanisms (page.evaluate, page.on("load"), Plan D context.route) are just different ways to get the same JavaScript to the DOM layer — Plan D is the persistence mechanism that survives page navigations.

### Accessibility Variants

Four levels applied via client-side DOM manipulation:

| Variant | What it does | Example patches |
|---------|-------------|-----------------|
| **Low** | Aggressively degrade accessibility | Strip all ARIA attrs, replace `<nav>`→`<div>`, `<a>`→`<span>`, Shadow DOM wrapping, focus traps |
| **Medium-Low** | Fake accessibility (pseudo-compliance) | ARIA roles present but keyboard handlers removed, form labels stripped |
| **Base** | Original website, no changes | Control condition |
| **High** | Enhance accessibility | Add aria-labels, skip-nav link, landmark roles, form labels, image alt text |

Same website, same content, same tasks — only DOM semantic quality varies.

### Three Agent Types

| Agent | Observes | Acts | Layers Used | Pilot 4 Low |
|-------|----------|------|-------------|-------------|
| **Text-Only** | AX Tree serialized as text (`[42] link "Home"`) | `click("bid")` via BrowserGym | L1→L2→L3→L4 (full chain) | 23.3% |
| **SoM Vision** | Screenshot with bid number overlays | `click("bid")` — same as Text-Only | L1→L2→L3→L4 (same chain, different L3 output) | 0.0% |
| **CUA** | Raw screenshot (no bid, no AX Tree) | `mouse.click(x, y)` via Playwright | L1→L4 direct (skips L2+L3) | 66.7% |

Text-Only and SoM share the same pipeline through L1→L2→L3; they differ only in how L3 encodes the output (text vs image+overlay). CUA bypasses L2 and L3 entirely — it's the "pure vision" control condition.

### bid Lifecycle

BrowserGym assigns a numeric identifier (bid) to each interactive DOM element. This bid is:
1. Born in L3 (BrowserGym), written back to L1 (DOM) as `browsergym_set_of_marks="42"`
2. Read by Chrome into L2 (AX Tree) as a node property
3. Serialized by L3 into text (`[42] link "Home"`) or drawn as SoM overlay labels
4. Used by agents to act: `click("42")` → BrowserGym finds DOM element → Playwright clicks it

When variant patches replace a DOM element (e.g., `<a>` → `<span>`), the old node with its bid is deleted. The SoM overlay label persists in the screenshot as a stale bitmap — this is the **phantom bid** phenomenon that causes SoM agents to fail at 0% under low accessibility.

## Pilot Results (N=240+120)

### Pilot 4: Text-Only + SoM (N=240)

| Variant | Text-Only | SoM Vision |
|---------|-----------|------------|
| Low | 23.3% | 0.0% |
| Medium-Low | 100.0% | 23.3% |
| Base | 86.7% | 20.0% |
| High | 76.7% | 30.0% |

Primary stat: Low vs Base χ²=24.31, p<0.000001, Cramér's V=0.637

### Pilot 4 CUA (N=120)

| Variant | CUA |
|---------|-----|
| Low | 66.7% |
| Medium-Low | 100.0% |
| Base | 96.7% |
| High | 100.0% |

Causal decomposition: Text-only 63.3pp drop = ~33pp semantic (invisible to CUA) + ~30pp functional breakage (affects all agents)

## Research Design

**Track A — Controlled Experiments**: WebArena apps × 4 accessibility variants × 3 agent types × 5 repetitions. Environment-centric evaluation paradigm — we vary the environment, not the agent.

**Track B — Ecological Survey**: 200+ real-world websites captured as HAR archives for landscape measurement and ecological validation.

## Architecture

Six modules (TypeScript for 1–5, Python for 6):

```
src/scanner/        Tier 1 (axe-core + Lighthouse) + Tier 2 (7 CDP metrics)
src/variants/       DOM patch engine for 4 accessibility levels
src/runner/         Agent executor, LLM backend, experiment scheduler
  browsergym_bridge.py   BrowserGym bridge (AX Tree, SoM overlay, bid mapping)
  cua_bridge.py          CUA agent loop (boto3 Bedrock, coordinate actions)
src/classifier/     Auto-classifier (12 failure types across 5 domains)
src/recorder/       HAR capture and replay for Track B
src/config/         YAML/JSON config loader with validation
src/export/         Manifest, CSV export, JSON store
analysis/           Python: CLMM, GEE, Random Forest + SHAP, semantic density
figures/            Architecture diagrams (matplotlib, 300dpi PNG)
```

## Variant Injection (Plan D)

All variant patches are pure browser JavaScript that modify the live DOM via standard APIs (`querySelector`, `replaceWith`, `removeAttribute`). Three delivery mechanisms ensure patches persist:

1. **page.evaluate** — one-shot after `env.reset()`
2. **page.on("load")** — re-inject on same-page navigation
3. **context.route("**/*")** (Plan D) — intercept HTTP responses at the network level, inject `<script>` into HTML with deferred execution (window.load + 500ms + MutationObserver guard)

Plan D is the primary persistence mechanism. It catches all HTML responses including agent-triggered `goto()` navigations. Verified: 33/33 goto traces show persistent degradation in Pilot 4.

## Failure Taxonomy

12 failure types across 5 domains:

| Domain | Types |
|--------|-------|
| Accessibility | Content invisibility, Structural infeasibility, Token inflation, Phantom bid (SoM), Keyboard trap, Pseudo-compliance trap, Shadow DOM invisible |
| Model | Context overflow, Reasoning error, Harmful affordance trap |
| Platform | Action serialization error |
| Environmental | Anti-bot block, Network timeout |

Pilot 4 finding: accessibility-attributed failures dominate the low variant (78%), model-attributed failures dominate non-low variants (100%). Clean separation supports the claim that accessibility degradation introduces a mechanistically distinct failure pathway.

## Prerequisites

- Node.js >= 18
- Python >= 3.10 (for analysis)
- Playwright browsers: `npx playwright install`
- LiteLLM proxy at localhost:4000 (for Text-Only/SoM agents)
- AWS Bedrock access (for CUA agent via boto3)
- WebArena Docker apps (Magento, Postmill, GitLab)

## Setup

```bash
# TypeScript platform
npm install
npx playwright install

# Python analysis
cd analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Experiments

Experiments are configured via YAML and run on EC2 via nohup (SSM sessions disconnect after ~20 min):

```bash
# Run a pilot experiment
bash scripts/launch-pilot4.sh

# Or directly
nohup npx tsx scripts/run-pilot3.ts --config config-pilot4.yaml > pilot4.log 2>&1 &
```

## Testing

```bash
# TypeScript (334 tests)
npm test        # vitest
npm run lint    # tsc --noEmit

# Python (67 tests)
cd analysis && python -m pytest -v
```

## Key Documentation

- `docs/platform-engineering-log.md` — Full bug/fix/regression history
- `docs/ma11y-operator-mapping.md` — Ma11y operator audit + novel extensions
- `docs/design-variant-injection.md` — Variant injection design evolution
- `figures/figure4_layer_model_spec.md` — Five-layer architecture detailed spec
- `data/*.md` — Per-pilot analysis reports

## Contributions

| Type | Contribution |
|------|-------------|
| Empirical | First controlled evidence that web accessibility predicts AI agent task success (p<0.000001, replicated 5x) |
| Paradigmatic | Environment-centric evaluation paradigm for web agents |
| Methodological | Failure taxonomy, multi-tier measurement, Plan D variant injection |
| Conceptual | "Same Barrier" hypothesis bridging accessibility and AI agent research |
| Novel Finding | DOM semantic quality affects vision agents through SoM overlay infrastructure (phantom bids) |
| Theoretical | Duality framework: same DOM change causes failure (phantom bids) OR success (forced strategy simplification) |

## License

Research use. Not yet published.

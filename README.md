# AI Agent Accessibility Platform

Empirical research platform studying the relationship between web accessibility and AI agent task success. Tests the **"Same Barrier" hypothesis**: AI agents and screen reader users face structurally equivalent barriers because both depend on the browser Accessibility Tree.

Targets CHI 2027 / ASSETS 2027 submission.

## Research Design

**Track A — Controlled Experiments**: 4 WebArena self-hosted apps × 4 accessibility variant levels (Low → High) × multiple agent configurations. Measures how degrading or enhancing accessibility affects agent task success.

**Track B — Ecological Survey**: 50+ real-world websites captured as HAR archives and replayed for reproducible scanning and agent testing.

## Architecture

Six modules, TypeScript for modules 1–5, Python for module 6:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Configuration Layer                         │
│              YAML/JSON config · Manifest generator               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
  ┌────────────┬───────────┼───────────┬──────────────┐
  ▼            ▼           ▼           ▼              ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐
│Scan- │  │Variant │  │Agent   │  │Failure   │  │HAR       │
│ner   │  │Genera- │  │Runner  │  │Classi-   │  │Recorder  │
│(M1)  │  │tor(M2) │  │(M3)    │  │fier(M4)  │  │(M5)      │
└──┬───┘  └───┬────┘  └───┬────┘  └────┬─────┘  └────┬─────┘
   │          │            │            │              │
   └──────────┴────────────┴────────────┴──────────────┘
                           │
                    JSON Store + CSV Export
                           │
                           ▼
                ┌─────────────────────┐
                │  Analysis Engine    │
                │  (M6 · Python)     │
                │  CLMM · GEE · SHAP │
                └─────────────────────┘
```

Modules communicate via TypeScript interfaces and JSON files — no runtime RPC. The Python Analysis Engine consumes CSV exports only.

## Modules

### Module 1: Scanner (`src/scanner/`)

Accessibility measurement with two tiers:

- **Tier 1**: axe-core violations + Lighthouse accessibility score (standard automated tools)
- **Tier 2**: 7 novel functional metrics via Playwright + CDP:
  - Semantic HTML ratio
  - Accessible name coverage
  - Keyboard navigability (with trap detection)
  - ARIA correctness
  - Pseudo-compliance detection (role present, handler absent)
  - Form labeling completeness
  - Landmark coverage
- **A11y Tree Stability**: polls at configurable intervals, SHA-256 hash comparison, proceeds on timeout
- **Composite Score**: supplementary weighted aggregate (primary analysis uses criterion-level vectors)
- **Serialization**: round-trip JSON serialize/deserialize with property-based testing
- **Concurrent scanning**: configurable parallelism with isolated browser contexts

### Module 2: Variant Generator (`src/variants/`)

Creates four accessibility levels for WebArena apps via DOM manipulation:

| Level | Composite Score Range | Strategy |
|-------|----------------------|----------|
| Low | 0.00 – 0.25 | Strip semantics, remove ARIA, disable keyboard handlers, Shadow DOM wrapping |
| Medium-Low | 0.25 – 0.50 | Pseudo-compliance: ARIA roles present but handlers removed (models real-world inaccessible state) |
| Base | 0.40 – 0.70 | Unmodified DOM (no-op) |
| High | 0.75 – 1.00 | Add missing labels, skip-nav, landmarks, fix axe-core auto-remediable violations |

All manipulations are recorded as reversible diffs with DOM hash verification.

### Module 3: Agent Runner (`src/runner/`)

Executes AI agents against target websites via BrowserGym:

- **Agent Executor**: BrowserGym subprocess bridge, action trace logging, step limit enforcement
- **LLM Backend**: LiteLLM proxy adapter supporting Claude and GPT-4o with exponential backoff retry
- **Experiment Matrix Scheduler**: Fisher-Yates randomized execution, configurable repetitions, resume support
- **Concurrency**: parallel test case execution with browser context isolation and resource monitoring
- **WebArena Integration**: Docker app connectivity verification, state reset between runs

### Module 4: Failure Classifier (`src/classifier/`)

Attributes agent failures to an 11-type taxonomy across 4 domains:

| Domain | Failure Types |
|--------|--------------|
| Accessibility | Element not found (F_ENF), Wrong element actuation (F_WEA), Keyboard trap (F_KBT), Pseudo-compliance trap (F_PCT), Shadow DOM invisible (F_SDI) |
| Model | Hallucination (F_HAL), Context overflow (F_COF), Reasoning error (F_REA) |
| Environmental | Anti-bot block (F_ABB), Network timeout (F_NET) |
| Task | Task ambiguity (F_AMB) |

Supports dual reporting modes (conservative: accessibility-only, inclusive: all), confidence scoring, and low-confidence flagging for manual review. Includes Cohen's kappa inter-rater reliability computation.

### Module 5: HAR Recorder (`src/recorder/`)

Captures and replays HTTP archives for Track B:

- **Capture**: Playwright-based HAR recording with dynamic content wait, concurrent capture, metadata sidecar (geo, sector, language)
- **Replay**: `routeFromHAR` serving with 404 fallback, functional vs non-functional request classification, coverage gap metric, low-fidelity flagging (>20% functional gap)

### Module 6: Analysis Engine (`analysis/`)

Python statistical analysis consuming CSV exports:

- **Primary Analysis**: Mixed-effects logistic regression (CLMM via pymer4 or GEE fallback) for Track A; GEE with criterion-level feature vectors for Track B; interaction effect testing (Text-Only vs Vision agent gradient)
- **Secondary Analysis**: Random Forest with SHAP values ranking WCAG criteria by predictive importance; partial dependence plots
- **Visualization**: Heatmaps, SHAP beeswarm plots, interaction effect plots, failure taxonomy Sankey diagrams

See [`analysis/README.md`](analysis/README.md) for setup details and CLMM implementation decision tree.

### Cross-Cutting: Data Export (`src/export/`)

- **Manifest Generator**: software versions, full config, test case outcomes for reproducibility
- **CSV Exporter**: R/Python-ready exports with PII anonymization and optional site identity anonymization
- **JSON Store**: structured filesystem layout (`data/track-a/runs/`, `data/track-b/har/`, `data/exports/`)

## Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.10 (for Analysis Engine)
- **Playwright browsers**: installed via `npx playwright install`
- **LiteLLM proxy** running at `localhost:4000` (for agent execution)
- **WebArena Docker apps** (for Track A): Reddit, GitLab, CMS, E-commerce

## Setup

### TypeScript Platform (Modules 1–5)

```bash
npm install
npx playwright install
```

### Python Analysis Engine (Module 6)

```bash
cd analysis
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

See [`analysis/README.md`](analysis/README.md) for pymer4/R dependency details.

## Usage

### Configuration

Create a YAML or JSON config file. Only `webarena.apps` is required — all other fields have documented defaults:

```yaml
webarena:
  apps:
    reddit:
      url: "http://localhost:9999"
    gitlab:
      url: "http://localhost:8023"
    cms:
      url: "http://localhost:7770"
    ecommerce:
      url: "http://localhost:7780"

scanner:
  wcagLevels: ["A", "AA"]
  concurrency: 5

runner:
  repetitions: 3
  maxSteps: 30
  concurrency: 3
  agentConfigs:
    - observationMode: "text-only"
      llmBackend: "claude-opus"
    - observationMode: "vision"
      llmBackend: "gpt-4o"

output:
  dataDir: "./data"
  exportFormats: ["json", "csv"]
```

### Running Experiments

```typescript
import { runTrackA, runTrackB } from './src/index.js';
import { chromium } from 'playwright';

const browser = await chromium.launch();

// Track A: Controlled WebArena experiments
const trackAResult = await runTrackA({
  configPath: './config.yaml',
  browser,
});

// Track B: Ecological survey via HAR replay
const trackBResult = await runTrackB({
  configPath: './config.yaml',
  urls: ['https://example.com', 'https://example.org'],
  browser,
});

await browser.close();
```

## Testing

### TypeScript Tests

```bash
# Run all tests
npm test

# Type check
npm run lint
```

318 tests across 23 test files covering all TypeScript modules.

### Python Tests

```bash
cd analysis
.venv/bin/python -m pytest -v   # Windows: .venv\Scripts\python -m pytest -v
```

56 tests covering statistical models and visualization.

## Project Structure

```
├── src/
│   ├── index.ts                    # End-to-end pipeline (Track A + Track B)
│   ├── scanner/
│   │   ├── tier1/scan.ts           # axe-core + Lighthouse
│   │   ├── tier2/scan.ts           # 7 CDP-based functional metrics
│   │   ├── snapshot/stability.ts   # A11y Tree stability detection
│   │   ├── composite.ts            # Supplementary composite score
│   │   ├── serialization.ts        # Scan result round-trip serialization
│   │   ├── concurrent.ts           # Parallel URL scanning
│   │   └── types.ts
│   ├── variants/
│   │   ├── patches/                # DOM patch engine (Low/Med-Low/Base/High)
│   │   ├── validation/             # Variant score range validation
│   │   └── types.ts
│   ├── runner/
│   │   ├── agents/executor.ts      # BrowserGym agent executor
│   │   ├── backends/llm.ts         # LiteLLM adapter with retry
│   │   ├── scheduler.ts            # Experiment matrix scheduler
│   │   ├── concurrency.ts          # Parallel execution with isolation
│   │   ├── webarena.ts             # Docker app integration
│   │   ├── serialization.ts        # Action trace round-trip serialization
│   │   └── types.ts
│   ├── classifier/
│   │   ├── taxonomy/classify.ts    # 11-type auto-classifier
│   │   ├── review/                 # Manual review + Cohen's kappa
│   │   └── types.ts
│   ├── recorder/
│   │   ├── capture/capture.ts      # HAR recording
│   │   ├── replay/replay.ts        # HAR replay with coverage gap
│   │   └── types.ts
│   ├── config/
│   │   ├── loader.ts               # YAML/JSON config loader + validator
│   │   └── types.ts
│   └── export/
│       ├── manifest.ts             # Experiment manifest generator
│       ├── csv.ts                  # CSV export with PII scrubbing
│       └── store.ts                # Filesystem JSON store
├── analysis/
│   ├── models/
│   │   ├── primary.py              # CLMM + GEE (Req 13)
│   │   └── secondary.py            # Random Forest + SHAP (Req 14)
│   ├── viz/
│   │   └── figures.py              # Paper-ready figures
│   ├── requirements.txt
│   └── README.md
├── docs/
│   └── browsergym-notes.md         # BrowserGym API findings
├── package.json
└── tsconfig.json
```

## Key Design Decisions

- **Criterion-level feature vectors** are the primary independent variables — Composite Score is supplementary for interpretability only
- **Vision agent is a control condition**: expected to show weak/null accessibility gradient (bypasses A11y Tree), confirming the causal mechanism
- **Medium-Low variant** models real-world pseudo-compliance (ARIA present, handlers missing) — the most common inaccessible state
- **`Promise.allSettled()`** for parallel operations — one tool's failure never blocks another
- **All metrics normalized to 0.0–1.0** inclusive
- **Deterministic variants**: same input DOM + variant level = same output
- **Resume support**: experiment scheduler persists completed cases to disk, can resume interrupted runs

## License

Research use. Not yet published.

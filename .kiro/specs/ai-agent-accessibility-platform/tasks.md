# Implementation Plan: AI Agent Accessibility Platform

## Overview

Incremental implementation of the six-module research platform, starting with shared types and configuration, then building each module (Scanner → Variants → Runner → Classifier → Recorder → Analysis) with cross-cutting data export and manifest generation wired in at the end. TypeScript for modules 1–5, Python for module 6.

## Tasks

- [x] 1. Project scaffolding and shared types
  - [x] 1.1 Initialize TypeScript project with Playwright, axe-core, and Lighthouse dependencies
    - Create `package.json`, `tsconfig.json`, install `@axe-core/playwright`, `lighthouse`, `playwright`, `litellm` client, `js-yaml`
    - Create directory structure: `src/scanner/`, `src/variants/`, `src/runner/`, `src/classifier/`, `src/recorder/`, `src/config/`, `src/export/`
    - _Requirements: 1.1, 2.1, 18.1_

  - [x] 1.2 Define core TypeScript interfaces and types
    - Implement `Tier1Metrics`, `Tier2Metrics`, `CompositeScoreResult`, `SensitivityMode` interfaces in `src/scanner/types.ts`
    - Implement `VariantLevel`, `DomChange`, `VariantDiff` types in `src/variants/types.ts`
    - Implement `AgentConfig`, `ActionTraceStep`, `ActionTrace`, `TaskOutcome`, `ObservationMode`, `LlmBackend` in `src/runner/types.ts`
    - Implement `FailureDomain`, `FailureType` (11 types), `FailureClassification`, `ReportingMode` in `src/classifier/types.ts`
    - Implement `HarCaptureOptions`, `HarMetadata`, `HarCaptureResult`, `HarReplayOptions`, `ReplaySession` in `src/recorder/types.ts`
    - Implement `ExperimentConfig`, `ExperimentManifest`, `CsvExportOptions` in `src/config/types.ts`
    - _Requirements: 1.1–1.5, 2.1–2.9, 5.1–5.7, 7.1–7.8, 9.1–9.6, 11.1–11.6, 15.1–15.4, 18.1–18.4_

  - [x] 1.3 Write unit tests for type validation helpers
    - Test that metric values enforce 0.0–1.0 range (Req 2.9)
    - Test VariantLevel enum completeness
    - Test FailureType enum covers all 11 types across 4 domains
    - _Requirements: 2.9, 9.1_

- [x] 2. Configuration management
  - [x] 2.1 Implement config loader and validator (`src/config/loader.ts`)
    - `loadConfig(filePath: string): ExperimentConfig` — parse YAML or JSON config files
    - `validateConfig(config: unknown): { valid: boolean; errors: string[] }` — validate all required fields, report specific errors for missing/invalid values
    - Apply documented default values for unspecified fields (step limits, retry counts, concurrency, intervals)
    - _Requirements: 18.1, 18.2, 18.4_

  - [x] 2.2 Write unit tests for config loader
    - Test valid YAML and JSON parsing
    - Test validation error reporting for missing required fields
    - Test default value application
    - _Requirements: 18.1, 18.2, 18.4_

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Module 1: Scanner — Tier 1
  - [x] 4.1 Implement Tier 1 Scanner (`src/scanner/tier1/scan.ts`)
    - `scanTier1(page, options): Promise<Tier1Metrics>` — run axe-core via `AxeBuilder(page).withTags(wcagLevels).analyze()` and Lighthouse via Node API with shared CDP session
    - Use `Promise.allSettled()` so one tool's failure doesn't block the other (Req 1.4)
    - Return merged `Tier1Metrics` object with violation count, violations by WCAG criterion, impact severity, Lighthouse score, and per-audit details
    - Log errors with URL and tool name on failure, continue processing
    - Accept configurable WCAG conformance levels (A, AA, AAA) to filter axe-core rules
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 4.2 Write unit tests for Tier 1 Scanner
    - Test axe-core result parsing and grouping by WCAG criterion
    - Test Lighthouse score extraction
    - Test error handling when one tool fails (partial results returned)
    - Test WCAG level filtering
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 5. Module 1: Scanner — Tier 2
  - [x] 5.1 Implement A11y Tree Stability Detector (`src/scanner/snapshot/stability.ts`)
    - `waitForA11yTreeStable(page, options?): Promise<StabilityResult>` — poll A11y tree at configurable interval (default 2000ms), compare SHA-256 hashes of consecutive serialized snapshots
    - Return stable when two consecutive snapshots match; log warning and proceed with latest snapshot on timeout (default 30s)
    - Serialize the snapshot used for measurement alongside results
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 5.2 Implement Tier 2 Scanner (`src/scanner/tier2/scan.ts`)
    - `scanTier2(page, cdpSession): Promise<Tier2Metrics>` — compute all 7 functional metrics
    - Semantic HTML ratio: count semantic elements / total elements (Req 2.1)
    - Accessible name coverage: CDP `Accessibility.getFullAXTree()`, filter interactive roles, check non-empty `name` (Req 2.2)
    - Keyboard navigability: programmatic Tab cycle with safety guards (max 200 tabs, 30s timeout, trap detection — 5 consecutive same-element = trapped) (Req 2.3)
    - ARIA correctness: validate `[role]`/`[aria-*]` elements against WAI-ARIA 1.2 spec (Req 2.4)
    - Pseudo-compliance detection: `DOMDebugger.getEventListeners()` for interactive ARIA roles, flag role-without-handler (Req 2.5)
    - Form labeling completeness: check `<label for>`, `aria-label`, `aria-labelledby` for form controls (Req 2.6)
    - Landmark coverage: text length inside landmark regions / total visible text length (Req 2.7)
    - Shadow DOM traversal: recursive `shadowRoot.querySelectorAll('*')` when enabled (Req 2.8)
    - All metrics returned as decimals 0.0–1.0 (Req 2.9)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

  - [x] 5.3 Write unit tests for Tier 2 Scanner
    - Test each metric computation with mock DOM structures
    - Test keyboard navigability safety guards (trap detection, max tabs, timeout)
    - Test pseudo-compliance detection with role-without-handler elements
    - Test Shadow DOM traversal inclusion
    - _Requirements: 2.1–2.9_

  - [x] 5.4 Implement Composite Score Calculator (`src/scanner/composite.ts`)
    - `computeCompositeScore(tier1, tier2, options): CompositeScoreResult` — normalize all components to 0–1, apply configurable weights
    - Support sensitivity modes: `tier1-only`, `tier2-only`, `composite`
    - Lighthouse score / 100, axe violations inverted (1 - min(count/maxExpected, 1))
    - Output composite score alongside all individual metric values in structured JSON
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.5 Write property test for Composite Score round-trip consistency
    - Verify serialize → deserialize produces equivalent object for any valid scan result (Req 16.3)
    - _Requirements: 16.3_

- [x] 6. Module 1: Scanner — Serialization
  - [x] 6.1 Implement scan result serialization/deserialization (`src/scanner/serialization.ts`)
    - `serializeScanResult(result): string` — serialize Tier1, Tier2, CompositeScore, A11y snapshot to JSON
    - `deserializeScanResult(json): ScanResult` — parse JSON back to structured objects
    - Return descriptive error with location and nature of parsing failure on invalid JSON
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [x] 6.2 Write property test for scan result round-trip
    - For all valid scan result objects, serialize then deserialize produces equivalent object
    - _Requirements: 16.3_

- [x] 7. Checkpoint — Ensure all Scanner tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Module 2: Variant Generator
  - [x] 8.1 Implement DOM Patch Engine (`src/variants/patches/`)
    - `applyVariant(page, level, appName): Promise<VariantDiff>` — apply DOM manipulations per variant level
    - Low: replace semantic elements with divs, remove ARIA/role attrs, remove labels, remove keyboard handlers, wrap in closed Shadow DOM
    - Medium-Low: rule-based pseudo-compliance strategy (deterministic, self-adaptive across apps):
      - Keep all `<nav>` and `<main>` elements intact (preserve page skeleton)
      - Replace `<button>` elements that have no text content with `<div>` equivalents (empty buttons are most likely to be missed)
      - Remove `keydown`/`keyup` handlers from ALL elements with `role="button"` (core pseudo-compliance scenario)
      - Remove `<label>` association for all `<input>` elements that lack a `placeholder` attribute (inputs with placeholder still visually guessable)
      - Keep existing landmark `aria-label` values unchanged (no randomization — real sites don't do that)
    - Base: no-op, return empty diff
    - High: add missing `aria-label` to interactive elements, insert skip-nav link, ensure all form controls labeled, add landmark roles, fix axe-core auto-remediable violations
    - Record all changes as reversible `DomChange[]` with original/modified state and DOM hash before/after
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 6.1_

  - [x] 8.2 Implement variant reversal (`src/variants/patches/revert.ts`)
    - `revertVariant(page, diff): Promise<{ success: boolean; domHashAfterRevert: string }>` — restore DOM using recorded diff
    - Verify restored DOM matches original by comparing SHA-256 hash of serialized DOM tree
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 8.3 Implement Variant Validator (`src/variants/validation/`)
    - `validateVariant(page, level, scanner): Promise<VariantValidationResult>` — run Scanner on variant, check composite score falls within expected range per level
    - Expected ranges: Low 0.0–0.25, Medium-Low 0.25–0.50, Base 0.40–0.70, High 0.75–1.0
    - Apply to all 4 WebArena apps (Reddit, GitLab, CMS, E-commerce)
    - _Requirements: 5.5, 5.6_

  - [x] 8.4 Write unit tests for Variant Generator
    - Test Low variant removes semantic elements and ARIA attributes
    - Test Medium-Low variant creates pseudo-compliance (role present, handler absent)
    - Test Base variant returns empty diff
    - Test High variant adds missing labels and landmarks
    - Test reversal restores original DOM hash
    - Test deterministic output for same input DOM and variant level (Req 5.7)
    - _Requirements: 5.1–5.7, 6.1–6.3_

- [ ] 9. Checkpoint — Ensure all Scanner and Variant tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Module 3: Agent Runner — Core
  - [x] 10.0 BrowserGym exploration spike
    - Install BrowserGym and run its example agent against one WebArena app to understand the API surface
    - Document: `env.reset()` / `env.step(action)` interface, how A11y Tree observation is exposed (raw text vs parsed), screenshot format (base64 vs file path), action space encoding
    - Determine how to inject variant DOM patches before/after `env.reset()`
    - Determine how to extract per-step token usage from the LLM call
    - Output: a short `docs/browsergym-notes.md` with API findings and integration plan
    - _Requirements: 7.1, 7.4, 7.5_

  - [x] 10.1 Implement LLM Backend Adapter (`src/runner/backends/llm.ts`)
    - `callLlm(request, retryConfig): Promise<LlmResponse>` — call LiteLLM proxy at `localhost:4000/v1/chat/completions`
    - Support Claude and GPT-4o backends via model name prefix
    - Implement exponential backoff retry: delay = `backoffMs * 2^attempt`, up to configurable max retries (default 3)
    - _Requirements: 7.6, 7.8_

  - [x] 10.2 Implement Agent Executor (`src/runner/agents/executor.ts`)
    - Initialize BrowserGym environment with target URL and AgentConfig
    - Execute agent step loop: capture observation (A11y tree text for text-only, screenshot for vision), send to LLM, parse action, execute action, log result
    - Log `ActionTraceStep` per step: stepNum, timestamp, observation, reasoning, action, result
    - Record task outcome (success/partial_success/failure/timeout) with total steps, elapsed time, token usage
    - Terminate on configurable step limit (default 30) with timeout outcome
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7_

  - [x] 10.3 Write unit tests for Agent Executor
    - Test action trace logging captures all required fields
    - Test step limit enforcement and timeout recording
    - Test LLM retry with exponential backoff
    - Test text-only vs vision observation modes
    - _Requirements: 7.1–7.8_

- [x] 11. Module 3: Agent Runner — Experiment Matrix
  - [x] 11.1 Implement Experiment Matrix Scheduler (`src/runner/scheduler.ts`)
    - `executeExperiment(matrix, resumeFrom?): Promise<ExperimentRun>` — execute all combinations: 4 apps × 4 variants × 3–5 tasks per app
    - Fisher-Yates shuffle for randomized execution order
    - Configurable repetitions (default 3) per test case
    - Persist `completedCases` to disk after each test case for resume support
    - Store ActionTrace, task outcome, scan results, and AgentConfig as single experiment record in JSON
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 11.2 Implement Action Trace serialization/deserialization (`src/runner/serialization.ts`)
    - `serializeActionTrace(trace): string` — serialize preserving step order, timestamps, observations, reasoning, actions, results
    - `deserializeActionTrace(json): ActionTrace` — parse back to structured objects
    - Return descriptive error on invalid JSON
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

  - [x] 11.3 Write property test for Action Trace round-trip
    - For all valid ActionTrace objects, serialize then deserialize produces equivalent object
    - _Requirements: 17.3_

  - [x] 11.4 Write unit tests for Experiment Matrix Scheduler
    - Test matrix generates correct number of test cases (apps × variants × tasks × repetitions)
    - Test randomization produces different orderings
    - Test resume skips completed cases
    - _Requirements: 8.1–8.5_

- [x] 12. Module 3: Agent Runner — Concurrency and WebArena integration
  - [x] 12.1 Implement concurrent execution with browser context isolation (`src/runner/concurrency.ts`)
    - Support concurrent test case execution with configurable limit (default 3)
    - Isolate each browser context to prevent cross-contamination
    - Log resource utilization (memory, CPU) at configurable intervals
    - _Requirements: 19.2, 19.3, 19.4_

  - [x] 12.2 Implement WebArena Docker integration (`src/runner/webarena.ts`)
    - Configure connections to 4 WebArena Docker apps (Reddit, GitLab, CMS, E-commerce) via URLs
    - Verify all services reachable before experiment start, report connectivity failures
    - Spike: investigate WebArena's reset mechanism (`bash prepare.sh` vs `docker compose down && up` vs DB restore). Document which apps support clean reset and which don't.
    - If reset is unreliable for some apps (GitLab/Reddit have persistent data), fall back to using separate Docker Compose stacks per variant level (space for reliability trade-off)
    - Support resetting app state between experiment runs via the most reliable available method
    - _Requirements: 20.1, 20.2, 20.3_

- [ ] 13. Checkpoint — Ensure all Runner tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Module 4: Failure Classifier
  - [x] 14.1 Implement Auto-Classifier (`src/classifier/taxonomy/classify.ts`)
    - `classifyFailure(trace: ActionTrace): FailureClassification` — pattern matching on ActionTrace entries
    - Implement all 11 failure type detectors across 4 domains:
      - Accessibility: F_ENF (≥3 consecutive failed selectors), F_WEA (wrong element actuation), F_KBT (tab cycles), F_PCT (role + no handler), F_SDI (shadow DOM invisible)
      - Model: F_HAL (action on non-existent element), F_COF (token overflow), F_REA (reasoning contradicts observation)
      - Environmental: F_ABB (HTTP 403/429), F_NET (timeout/connection errors)
      - Task: F_AMB (agent asks for clarification)
    - Assign primary classification and secondary contributing factors when multiple domains match
    - Compute confidence score 0.0–1.0 per classification
    - Flag classifications with confidence < 0.7 for manual review
    - Support dual reporting: conservative (accessibility-only) and inclusive (all failures)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 14.2 Write unit tests for Auto-Classifier
    - Test each of the 11 failure type pattern detectors with mock traces
    - Test multi-domain classification with primary/secondary assignment
    - Test confidence scoring and review flagging threshold
    - Test conservative vs inclusive reporting modes
    - _Requirements: 9.1–9.6_

  - [x] 14.3 Implement Manual Review interface (`src/classifier/review/`)
    - `selectForReview(classifications, sampleRate): ReviewItem[]` — randomly select 10% of classified failures
    - Present ActionTrace, auto-classification, confidence, page screenshot, and A11y tree snapshot
    - Store both auto and manual classifications for inter-rater reliability
    - `computeCohensKappa(auto, manual): InterRaterResult` — compute Cohen's kappa, agreement rate, confusion matrix
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 14.4 Write unit tests for Cohen's kappa computation
    - Test perfect agreement (kappa = 1.0)
    - Test random agreement (kappa ≈ 0.0)
    - Test confusion matrix correctness
    - _Requirements: 10.4_

- [ ] 15. Checkpoint — Ensure all Classifier tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Module 5: HAR Recorder
  - [x] 16.1 Implement HAR Capture (`src/recorder/capture/capture.ts`)
    - `captureHar(options): Promise<HarCaptureResult[]>` — navigate to each URL via Playwright, capture full HTTP transaction log as HAR
    - Capture all sub-resource requests (scripts, stylesheets, images, fonts, API calls)
    - Execute page JS and wait configurable time (default 10s after load) for dynamic content
    - Store metadata sidecar: recording timestamp, target URL, geo region, sector classification, page language (from `Content-Language` header)
    - Log errors and continue on URL load failure/timeout
    - Support concurrent capture with configurable limit (default 5)
    - Support at least 50 websites across multiple sectors and geographies
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 19.1_

  - [x] 16.2 Implement HAR Replay Server (`src/recorder/replay/replay.ts`)
    - `createReplaySession(browser, options): Promise<ReplaySession>` — serve recorded HTTP responses via Playwright's `routeFromHAR`
    - Intercept unmatched requests: return 404 and log URL
    - Classify requests as functional (HTML, JS, CSS, API) vs non-functional (analytics, ads, tracking — matched by domain patterns)
    - Compute coverage gap over functional requests only
    - Flag as "low fidelity" and exclude from primary analysis if functional coverage gap > 20%
    - Support running Scanner and Agent_Runner against replayed pages identically to live pages
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 16.3 Write unit tests for HAR Recorder
    - Test HAR capture produces valid HAR files with metadata
    - Test replay serves recorded responses and returns 404 for unmatched
    - Test functional vs non-functional request classification
    - Test coverage gap computation and low-fidelity flagging
    - _Requirements: 11.1–11.6, 12.1–12.5_

- [ ] 17. Checkpoint — Ensure all TypeScript module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Module 6: Analysis Engine (Python)
  - [x] 18.1 Set up Python analysis project (`analysis/`)
    - Create `requirements.txt` with `statsmodels`, `scikit-learn`, `shap`, `matplotlib`, `seaborn`, `pandas`, `pymer4` (Python wrapper for R's lme4, preferred for mixed-effects logistic regression)
    - If `pymer4` install fails (requires R runtime): fall back to `statsmodels.genmod.generalized_estimating_equations.GEE` with ordinal coding for Track A. Document the trade-off in `analysis/README.md` — paper should justify the model choice.
    - Alternative path: install R + `ordinal` package + `rpy2` for true CLMM. Only pursue if `pymer4` is insufficient for the paper's statistical claims.
    - Create directory structure: `analysis/models/`, `analysis/viz/`
    - _Requirements: 13.1, 14.1_

  - [x] 18.2 Implement Primary Analysis models (`analysis/models/primary.py`)
    - `PrimaryAnalysis.fit_clmm(data)` — mixed-effects logistic regression for Track A via `pymer4` (or `statsmodels.GEE` with ordinal coding as fallback); DV: agent_success (binary), IV: a11y_variant_level (ordinal, 4 levels), random effects: (1|app), (1|llm_backend). Note: true CLMM (ordinal DV) only needed if using three-level outcome (failure/partial/success).
    - `PrimaryAnalysis.fit_gee(data)` — GEE with logit link for Track B; DV: agent_success (binary), IV: criterion-level Tier 1+2 feature vector (NOT Composite_Score), random intercepts: (1|website), (1|llm_backend)
    - `PrimaryAnalysis.interaction_effect(data)` — test a11y_variant × observation_mode interaction; expected: Text-Only shows strong gradient, Vision shows weak/null gradient
    - `PrimaryAnalysis.sensitivity_analysis(data)` — fit models with tier1-only, tier2-only, and supplementary composite
    - `PrimaryAnalysis.post_hoc_power(data, target_effect)` — post-hoc power analysis after pilot
    - Report coefficients, confidence intervals, p-values, effect sizes for all predictors
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 8.6_

  - [x] 18.3 Implement Secondary Analysis models (`analysis/models/secondary.py`)
    - `SecondaryAnalysis.train_random_forest(X, y)` — features: individual WCAG criterion pass/fail indicators, target: agent success (binary)
    - `SecondaryAnalysis.compute_shap(model, X)` — SHAP values for each WCAG criterion
    - `SecondaryAnalysis.partial_dependence_plots(model, X, top_n=10)` — PDP for top 10 most important criteria
    - Rank WCAG criteria by SHAP importance, output top predictors with scores
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [x] 18.4 Implement Visualization Engine (`analysis/viz/figures.py`)
    - `variant_success_heatmap(data)` — heatmap of success rates by variant × app
    - `shap_summary_plot(shap_values, features)` — SHAP summary beeswarm plot
    - `interaction_effect_plot(data)` — Text-Only vs Vision gradient comparison
    - `failure_taxonomy_sankey(classifications)` — Sankey diagram of failure type distribution
    - _Requirements: 13.3, 14.2, 14.4_

  - [x] 18.5 Write unit tests for Analysis Engine
    - Test CLMM and GEE model fitting with synthetic data
    - Test Random Forest training and SHAP computation
    - Test interaction effect detection with known gradient patterns
    - Test sensitivity analysis runs all three modes
    - _Requirements: 13.1–13.5, 14.1–14.4_

- [x] 19. Checkpoint — Ensure all Analysis Engine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Cross-cutting: Data Export and Manifest
  - [x] 20.1 Implement Experiment Manifest generator (`src/export/manifest.ts`)
    - `generateManifest(run): ExperimentManifest` — list all test cases, outcomes, software versions (axe-core, Lighthouse, Playwright, LLM model versions), and config parameters
    - Include full configuration file content for reproducibility
    - _Requirements: 15.2, 15.3, 18.3_

  - [x] 20.2 Implement CSV Exporter (`src/export/csv.ts`)
    - `exportToCsv(records, options): string[]` — export experiment data as CSV files for R/Python import
    - Generate: `experiment-data.csv`, `scan-metrics.csv`, `failure-classifications.csv`, `trace-summaries.csv`
    - PII anonymization: regex-based scrubbing of cookies, auth tokens, emails, user-specific URL segments from HAR metadata
    - Site identity anonymization: replace URLs with opaque IDs (e.g. `site_001`) when `anonymizeSiteIdentity` enabled, store private mapping separately
    - _Requirements: 15.1, 15.3, 15.4_

  - [x] 20.3 Implement JSON data store (`src/export/store.ts`)
    - Store all experiment records (scan results, ActionTraces, task outcomes, failure classifications) in structured JSON with documented schema
    - Follow file system layout: `data/track-a/runs/{runId}/cases/{caseId}/`, `data/track-b/har/{harId}/`, `data/exports/`
    - _Requirements: 15.1_

  - [x] 20.4 Write unit tests for Data Export
    - Test manifest includes all required software versions and config
    - Test CSV export produces valid CSV with correct columns
    - Test PII anonymization removes cookies, tokens, emails
    - Test site identity anonymization replaces URLs with opaque IDs
    - _Requirements: 15.1–15.4_

- [ ] 21. Integration wiring
  - [ ] 21.1 Wire Scanner concurrent execution (`src/scanner/concurrent.ts`)
    - Support concurrent scanning of multiple URLs with configurable limit (default 5)
    - Isolate browser contexts per scan
    - _Requirements: 19.1, 19.3_

  - [ ] 21.2 Wire end-to-end experiment pipeline (`src/index.ts`)
    - Load config → validate → generate variants → scan → run agents → classify failures → export results → generate manifest
    - Connect all modules through the experiment matrix scheduler
    - Ensure Track A (WebArena variants) and Track B (HAR replay) pipelines both work through the same runner
    - _Requirements: 8.1, 8.4, 12.4, 18.1, 18.3_

  - [ ] 21.3 Write integration tests for end-to-end pipeline
    - Test config → scan → export flow with mock browser
    - Test variant generation → validation → agent run flow
    - Test HAR capture → replay → scan flow
    - _Requirements: 8.1–8.5, 12.1–12.5, 15.1–15.4_

- [ ] 22. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 23. Pilot Study Execution (20 sites)
  - [ ] 23.1 Select 20 pilot websites spanning accessibility levels 0–2 across at least 3 sectors (e-commerce, government, SaaS)
  - [ ] 23.2 Run Scanner (Tier 1 + Tier 2) on all 20 pilot sites, verify pipeline stability and metric output
  - [ ] 23.3 Create Low + High variants for 1 WebArena app (e.g., Reddit), validate with Variant Validator
  - [ ] 23.4 Run Text-Only agent on the variant pair (1 LLM backend, 3 attempts per task), collect action traces
  - [ ] 23.5 Run Failure Classifier on pilot traces, review 10% sample manually
  - [ ] 23.6 Export pilot data to CSV, run Analysis Engine on pilot dataset (GEE + SHAP)
  - [ ] 23.7 Post-hoc power analysis: determine if N=50 is sufficient for Track B target effect size
  - [ ] 23.8 Document pilot findings in `docs/pilot-report.md`: pipeline stability, data quality, metric distributions, power analysis results, adjustments needed for full experiment

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- TypeScript modules 1–5 share a single project; Python module 6 is a separate `analysis/` project
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between major modules
- Composite Score is supplementary only — primary analysis uses criterion-level vectors
- Vision agent is a control condition tested via `interaction_effect()` in the Analysis Engine
- Task 10.0 and 12.2 include spike/exploration work — budget half a day each before writing production code
- Task 18.1 has a decision tree for CLMM implementation: pymer4 → statsmodels GEE fallback → rpy2+R last resort
- Task 23 (Pilot) validates the full pipeline end-to-end before committing to the full experiment matrix

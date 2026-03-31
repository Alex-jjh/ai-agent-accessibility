# Requirements Document

## Introduction

This document specifies the requirements for an empirical research platform that studies the relationship between web accessibility and AI agent task success. The platform supports a dual-track research design: Track A (controlled A/B experiments on WebArena self-hosted apps with accessibility variants) and Track B (ecological survey of real-world websites via HAR replay). The platform comprises six modules: Scanner, Variants, Runner, Classifier, Recorder, and Analysis.

The core hypothesis ("Same Barrier") posits that AI agents and screen reader users face structurally equivalent barriers on inaccessible websites because both depend on the browser Accessibility Tree.

## Glossary

- **Platform**: The complete empirical research platform comprising all six modules
- **Scanner**: Module 1 — the accessibility measurement subsystem that computes Tier 1 and Tier 2 metrics for a given web page
- **Variant_Generator**: Module 2 — the subsystem that creates accessibility variants of WebArena apps by manipulating the DOM
- **Agent_Runner**: Module 3 — the agent execution engine that runs AI agents against target websites and records action traces
- **Failure_Classifier**: Module 4 — the subsystem that attributes agent failures to a taxonomy of 11 failure types across 4 domains
- **HAR_Recorder**: Module 5 — the subsystem that captures and replays HAR archives of real-world websites for Track B
- **Analysis_Engine**: Module 6 — the Python-based statistical analysis subsystem
- **Accessibility_Tree**: The browser's semantic representation of the DOM used by assistive technologies and AI agents
- **Tier_1_Metrics**: Automated accessibility scores from axe-core and Lighthouse
- **Tier_2_Metrics**: Novel functional accessibility metrics computed via Playwright and CDP (semantic HTML ratio, accessible name coverage, keyboard navigability, ARIA correctness, Shadow DOM exposure, form labeling completeness, landmark coverage)
- **A11y_Variant**: One of four accessibility levels applied to a WebArena app: Low, Medium-Low, Base, or High
- **Action_Trace**: A per-step log of an agent's observation, reasoning, action, and result during task execution
- **WebArena**: A self-hosted web environment providing four applications (Reddit, GitLab, CMS, E-commerce) for controlled experiments
- **BrowserGym**: WebArena's agent execution framework used by the Agent_Runner
- **LiteLLM**: A unified LLM API proxy supporting multiple model backends
- **CLMM**: Cumulative Link Mixed Model — an ordinal regression model used for the primary research question
- **GEE**: Generalized Estimating Equations — a statistical method for binary success outcomes with random intercepts
- **SHAP**: SHapley Additive exPlanations — a method for interpreting feature importance in machine learning models
- **HAR**: HTTP Archive format — a JSON-based format for recording HTTP transactions
- **CDP**: Chrome DevTools Protocol — a low-level browser instrumentation API
- **WCAG_2_2**: Web Content Accessibility Guidelines version 2.2
- **Composite_Score**: A supplementary weighted combination of Tier 1 and Tier 2 metrics for interpretability reporting; primary analysis uses criterion-level feature vectors
- **Agent_Config**: A configuration specifying the agent's observation mode (Text-Only or Vision) and LLM backend

## Requirements

### Requirement 1: Tier 1 Accessibility Scanning

**User Story:** As a researcher, I want to scan web pages using axe-core and Lighthouse, so that I can obtain standardized accessibility violation counts and scores.

#### Acceptance Criteria

1. WHEN a URL is provided, THE Scanner SHALL run axe-core analysis and return a structured result containing violation count, violation details grouped by WCAG criterion, and impact severity levels (critical, serious, moderate, minor).
2. WHEN a URL is provided, THE Scanner SHALL run Lighthouse accessibility audit and return the overall accessibility score (0–100) along with per-audit pass/fail details.
3. WHEN both axe-core and Lighthouse scans complete, THE Scanner SHALL merge the results into a single Tier_1_Metrics object keyed by the scanned URL.
4. IF axe-core or Lighthouse fails during execution, THEN THE Scanner SHALL log the error with the URL and tool name, and continue processing remaining URLs without terminating.
5. THE Scanner SHALL accept a configurable list of WCAG conformance levels (A, AA, AAA) to filter axe-core rules.

### Requirement 2: Tier 2 Functional Accessibility Metrics

**User Story:** As a researcher, I want to compute novel functional accessibility metrics beyond standard automated tools, so that I can capture accessibility properties that axe-core and Lighthouse miss.

#### Acceptance Criteria

1. WHEN a page is loaded in Playwright, THE Scanner SHALL compute the semantic HTML ratio as the count of semantic elements (nav, main, header, footer, article, section, aside, figure, figcaption, details, summary, dialog, time, mark, address) divided by the total element count.
2. WHEN a page is loaded, THE Scanner SHALL compute accessible name coverage as the proportion of interactive elements (links, buttons, inputs, selects, textareas, roles with widget semantics) that have a non-empty accessible name via the Accessibility_Tree.
3. WHEN a page is loaded, THE Scanner SHALL compute keyboard navigability by programmatically tabbing through all focusable elements and reporting the ratio of elements that receive visible focus to total focusable elements.
4. WHEN a page is loaded, THE Scanner SHALL compute ARIA correctness by identifying elements with ARIA attributes and checking for: roles with missing required properties, invalid aria-* attribute values, and aria-hidden="true" on focusable elements.
5. WHEN a page is loaded, THE Scanner SHALL detect pseudo-compliance by using CDP DOMDebugger.getEventListeners() to verify that elements with interactive ARIA roles (button, link, checkbox, tab, menuitem) have corresponding event listeners registered (click, keydown, or keyup). Elements with interactive roles but no matching handlers SHALL be flagged as pseudo-compliant and counted separately in the ARIA correctness metric.
6. WHEN a page is loaded, THE Scanner SHALL compute form labeling completeness as the proportion of form controls (input, select, textarea) that have an associated label element or aria-label or aria-labelledby attribute.
7. WHEN a page is loaded, THE Scanner SHALL compute landmark coverage as the proportion of visible text content contained within ARIA landmark regions (banner, navigation, main, contentinfo, complementary, form, region, search).
8. WHEN a page contains Shadow DOM elements, THE Scanner SHALL traverse shadow roots and include shadow DOM content in all Tier_2_Metrics calculations.
9. THE Scanner SHALL return all Tier 2 metrics as decimal values between 0.0 and 1.0 inclusive.

### Requirement 3: Accessibility Tree Stability Detection

**User Story:** As a researcher, I want the scanner to wait for the Accessibility Tree to stabilize before measuring, so that I get consistent and reliable metric readings.

#### Acceptance Criteria

1. WHEN a page is loaded, THE Scanner SHALL poll the Accessibility_Tree at a configurable interval (default 2000ms) and compare consecutive snapshots.
2. WHEN at least two consecutive Accessibility_Tree snapshots are structurally equivalent, THE Scanner SHALL consider the tree stable and proceed with metric computation.
3. IF the Accessibility_Tree does not stabilize within a configurable timeout (default 30 seconds), THEN THE Scanner SHALL log a warning with the URL and proceed with the most recent snapshot.
4. THE Scanner SHALL serialize the Accessibility_Tree snapshot used for measurement alongside the scan results for reproducibility.

### Requirement 4: Composite Accessibility Score (Supplementary)

**User Story:** As a researcher, I want an optional composite score combining Tier 1 and Tier 2 metrics, so that I can report an interpretable aggregate alongside the primary criterion-level analysis.

#### Acceptance Criteria

1. WHEN Tier_1_Metrics and Tier_2_Metrics are available for a URL, THE Scanner SHALL optionally compute a Composite_Score using configurable weights for each metric component. This score is supplementary — primary statistical analysis (Requirements 13 and 14) SHALL use criterion-level feature vectors, not the Composite_Score.
2. THE Scanner SHALL normalize all component metrics to a 0.0–1.0 scale before computing the Composite_Score.
3. THE Scanner SHALL support sensitivity analysis by allowing computation with Tier 1 only, Tier 2 only, or the full composite.
4. THE Scanner SHALL output the Composite_Score alongside all individual metric values in a structured JSON format.

### Requirement 5: WebArena Accessibility Variant Generation

**User Story:** As a researcher, I want to create four accessibility variants (Low, Medium-Low, Base, High) of each WebArena app, so that I can run controlled A/B experiments across accessibility levels.

#### Acceptance Criteria

1. WHEN the "Low" variant is requested, THE Variant_Generator SHALL apply DOM manipulations that degrade accessibility: replacing semantic elements with generic divs, removing ARIA labels, disabling keyboard event handlers, and removing form labels.
2. WHEN the "Medium-Low" variant is requested, THE Variant_Generator SHALL apply pseudo-compliance manipulations: preserving ARIA role attributes on interactive elements but removing their keyboard event handlers (creating role-without-handler mismatches), maintaining some landmark structure with inconsistent labeling, and leaving partial form label associations. This variant models the most common real-world inaccessible state where ARIA is present but not functionally backed.
3. WHEN the "Base" variant is requested, THE Variant_Generator SHALL serve the unmodified WebArena application DOM.
4. WHEN the "High" variant is requested, THE Variant_Generator SHALL apply DOM enhancements: adding missing ARIA labels to interactive elements, adding skip-navigation links, ensuring all form controls have associated labels, and adding landmark roles to major page sections.
5. THE Variant_Generator SHALL apply variant manipulations to all four WebArena apps (Reddit, GitLab, CMS, E-commerce).
6. WHEN a variant is generated, THE Variant_Generator SHALL verify the variant by running the Scanner and confirming the Composite_Score falls within the expected range for that variant level.
7. THE Variant_Generator SHALL produce deterministic output given the same input DOM and variant level.

### Requirement 6: Variant Manipulation Reversibility

**User Story:** As a researcher, I want variant manipulations to be reversible, so that I can restore the original DOM state and verify experimental integrity.

#### Acceptance Criteria

1. WHEN a variant manipulation is applied, THE Variant_Generator SHALL record all DOM changes as a reversible diff (original element, modified element, change type).
2. WHEN a reversal is requested, THE Variant_Generator SHALL restore the DOM to its pre-manipulation state using the recorded diff.
3. WHEN a reversal completes, THE Variant_Generator SHALL verify the restored DOM matches the original by comparing a hash of the serialized DOM tree.

### Requirement 7: Agent Execution with Action Trace Logging

**User Story:** As a researcher, I want to execute AI agents against target websites and capture detailed action traces, so that I can analyze agent behavior and attribute failures.

#### Acceptance Criteria

1. WHEN a task is submitted, THE Agent_Runner SHALL initialize a BrowserGym environment with the specified target URL and Agent_Config.
2. WHEN an agent executes a step, THE Agent_Runner SHALL log an Action_Trace entry containing: step number, timestamp, observation (Accessibility_Tree text or screenshot depending on Agent_Config), the agent's reasoning, the action taken, and the action result (success, failure, or error).
3. WHEN an agent completes a task, THE Agent_Runner SHALL record the overall task outcome (success, partial success, or failure) along with the total number of steps, elapsed time, and token usage.
4. THE Agent_Runner SHALL support Text-Only agent configuration where the observation is the serialized Accessibility_Tree.
5. THE Agent_Runner SHALL support Vision agent configuration where the observation includes a screenshot of the current page state.
6. THE Agent_Runner SHALL support at least two LLM backends (Claude and GPT-4o) via LiteLLM.
7. IF an agent exceeds a configurable step limit (default 30 steps), THEN THE Agent_Runner SHALL terminate the task and record the outcome as a timeout failure.
8. IF the LLM API returns an error, THEN THE Agent_Runner SHALL retry the request up to a configurable number of times (default 3) with exponential backoff before recording the step as failed.

### Requirement 8: Experiment Matrix Execution

**User Story:** As a researcher, I want to execute the full Track A experiment matrix (apps × variants × tasks), so that I can collect data for the controlled study.

#### Acceptance Criteria

1. WHEN a Track A experiment is initiated, THE Agent_Runner SHALL execute all combinations in the matrix: 4 WebArena apps × 4 A11y variants × 3–5 tasks per app, producing 48–80 test cases per Agent_Config.
2. THE Agent_Runner SHALL execute each test case with a configurable number of repetitions (default 3) to account for LLM non-determinism.
3. THE Agent_Runner SHALL randomize the execution order of test cases within each experiment run to mitigate ordering effects.
4. WHEN a test case completes, THE Agent_Runner SHALL store the Action_Trace, task outcome, scan results, and Agent_Config as a single experiment record in structured JSON format.
5. THE Agent_Runner SHALL support resuming an interrupted experiment run from the last completed test case.
6. THE experiment design SHALL include the Vision agent as a control condition. The expected result pattern is: Text-Only agents show a strong positive gradient in task success across A11y variant levels (Low → High), while Vision agents show a weak or null gradient, because Vision agents bypass the Accessibility_Tree. The Analysis_Engine SHALL test for this interaction effect between observation modality and A11y variant level.

### Requirement 9: Failure Auto-Classification

**User Story:** As a researcher, I want agent failures to be automatically classified into a taxonomy, so that I can distinguish accessibility-caused failures from other failure types.

#### Acceptance Criteria

1. WHEN an agent task results in failure, THE Failure_Classifier SHALL analyze the Action_Trace and classify the failure into one of 11 failure types across 4 domains: Accessibility (element not found due to missing label, keyboard trap, focus management failure), Model (hallucinated action, reasoning error, instruction misinterpretation), Environmental (page load timeout, dynamic content change, network error), and Task Design (ambiguous instruction, impossible task).
2. THE Failure_Classifier SHALL use pattern matching on Action_Trace entries to identify failure indicators: repeated failed selectors suggesting missing accessible names, tab-key loops suggesting keyboard traps, and actions on non-existent elements suggesting hallucination.
3. WHEN a failure matches patterns from multiple domains, THE Failure_Classifier SHALL assign a primary classification and list secondary contributing factors.
4. THE Failure_Classifier SHALL assign a confidence score (0.0–1.0) to each classification.
5. THE Failure_Classifier SHALL flag classifications with confidence below 0.7 for manual review.
6. THE Failure_Classifier SHALL support dual reporting: conservative mode (only Accessibility-domain failures counted) and inclusive mode (all failures counted).

### Requirement 10: Manual Review Workflow

**User Story:** As a researcher, I want to manually review a sample of auto-classified failures, so that I can validate the classifier's accuracy and compute inter-rater reliability.

#### Acceptance Criteria

1. THE Failure_Classifier SHALL randomly select 10% of classified failures for manual review.
2. WHEN a failure is selected for review, THE Failure_Classifier SHALL present the Action_Trace, the auto-classification, the confidence score, and the page state (screenshot and Accessibility_Tree snapshot) to the reviewer.
3. WHEN a reviewer submits a manual classification, THE Failure_Classifier SHALL store both the auto-classification and manual classification for inter-rater reliability computation.
4. THE Failure_Classifier SHALL compute Cohen's kappa between auto-classifications and manual classifications after each review batch.

### Requirement 11: HAR Recording for Track B

**User Story:** As a researcher, I want to record HAR archives of real-world websites, so that I can replay them for ecological validity testing in Track B.

#### Acceptance Criteria

1. WHEN a list of target URLs is provided, THE HAR_Recorder SHALL navigate to each URL using Playwright, capture the full HTTP transaction log, and save the result as a HAR file.
2. THE HAR_Recorder SHALL capture all sub-resource requests (scripts, stylesheets, images, fonts, API calls) in the HAR archive.
3. WHEN recording, THE HAR_Recorder SHALL execute page JavaScript to capture dynamically loaded content up to a configurable wait time (default 10 seconds after load event).
4. THE HAR_Recorder SHALL store metadata alongside each HAR file: recording timestamp, target URL, geographic region of the recording proxy, website sector classification, and page language.
5. IF a target URL fails to load or times out, THEN THE HAR_Recorder SHALL log the error and continue recording remaining URLs.
6. THE HAR_Recorder SHALL support recording at least 50 websites across multiple sectors and geographies for Track B.

### Requirement 12: HAR Replay for Consistent Testing

**User Story:** As a researcher, I want to replay HAR archives so that agents interact with a frozen snapshot of each website, ensuring reproducible results.

#### Acceptance Criteria

1. WHEN a HAR file is provided, THE HAR_Recorder SHALL serve the recorded HTTP responses via a local proxy, allowing Playwright to load the page as it appeared at recording time.
2. WHEN replaying, THE HAR_Recorder SHALL intercept all network requests from the browser and match them to recorded HAR entries by URL and method.
3. IF a network request during replay has no matching HAR entry, THEN THE HAR_Recorder SHALL return a 404 response and log the unmatched request.
4. THE HAR_Recorder SHALL support running the Scanner and Agent_Runner against replayed HAR pages identically to live pages.
5. WHEN replaying a HAR file, THE HAR_Recorder SHALL compute a coverage gap metric as the proportion of browser network requests that had no matching HAR entry. IF more than 20% of requests are unmatched, THE HAR_Recorder SHALL flag the recording as "low fidelity" and exclude it from primary analysis.

### Requirement 13: Statistical Analysis for Primary Research Question

**User Story:** As a researcher, I want to run CLMM and GEE models on the collected data, so that I can determine whether accessibility is a statistically significant predictor of agent success.

#### Acceptance Criteria

1. WHEN experiment data is provided, THE Analysis_Engine SHALL fit a Cumulative Link Mixed Model (CLMM) with ordinal accessibility level as the predictor and agent task success as the outcome, controlling for site complexity, sector, and agent architecture.
2. WHEN experiment data is provided, THE Analysis_Engine SHALL fit a GEE model with binary success as the outcome, including random intercepts for LLM backend and website.
3. THE Analysis_Engine SHALL report model coefficients, confidence intervals, p-values, and effect sizes for all predictors.
4. THE Analysis_Engine SHALL use criterion-level Tier 1+2 feature vectors as the primary independent variables for Track B analysis. THE Analysis_Engine SHALL perform sensitivity analysis by fitting models with Tier 1 metrics only, Tier 2 metrics only, and the supplementary Composite_Score.
5. THE Analysis_Engine SHALL perform post-hoc power analysis after the pilot phase and report whether the sample size is sufficient for the target effect size.

### Requirement 14: Secondary Research Question Analysis

**User Story:** As a researcher, I want to identify which specific WCAG 2.2 criteria are most predictive of agent success, so that I can provide actionable guidance for web developers.

#### Acceptance Criteria

1. WHEN criterion-level accessibility vectors are provided, THE Analysis_Engine SHALL train a Random Forest model with individual WCAG criterion pass/fail indicators as features and agent success as the outcome.
2. THE Analysis_Engine SHALL compute SHAP values for each WCAG criterion to quantify feature importance.
3. THE Analysis_Engine SHALL rank WCAG criteria by their SHAP importance and output the top predictors with their importance scores.
4. THE Analysis_Engine SHALL generate partial dependence plots for the top 10 most important WCAG criteria.

### Requirement 15: Experiment Data Export and Reproducibility

**User Story:** As a researcher, I want all experiment data to be exported in a structured, reproducible format, so that other researchers can verify and replicate the study.

#### Acceptance Criteria

1. THE Platform SHALL store all experiment records (scan results, Action_Traces, task outcomes, failure classifications) in a structured JSON format with a documented schema.
2. THE Platform SHALL generate a manifest file for each experiment run listing: all test cases executed, their outcomes, the software versions used (axe-core, Lighthouse, Playwright, LLM model versions), and configuration parameters.
3. THE Platform SHALL support exporting experiment data as CSV files suitable for import into R or Python statistical packages.
4. WHEN exporting data, THE Platform SHALL anonymize any personally identifiable information from HAR recordings (cookies, authentication tokens, user-specific URLs).

### Requirement 16: Scan Result Serialization and Deserialization

**User Story:** As a researcher, I want scan results to be reliably serialized to JSON and deserialized back, so that I can store, transfer, and reload results without data loss.

#### Acceptance Criteria

1. THE Scanner SHALL serialize scan results (Tier_1_Metrics, Tier_2_Metrics, Composite_Score, Accessibility_Tree snapshot) to JSON format.
2. THE Scanner SHALL deserialize JSON scan results back into structured objects.
3. FOR ALL valid scan result objects, serializing then deserializing SHALL produce an object equivalent to the original (round-trip property).
4. WHEN invalid JSON is provided for deserialization, THE Scanner SHALL return a descriptive error identifying the location and nature of the parsing failure.

### Requirement 17: Action Trace Serialization and Deserialization

**User Story:** As a researcher, I want action traces to be reliably serialized and deserialized, so that I can store and replay agent behavior for analysis.

#### Acceptance Criteria

1. THE Agent_Runner SHALL serialize Action_Trace records to JSON format, preserving step order, timestamps, observations, reasoning, actions, and results.
2. THE Agent_Runner SHALL deserialize JSON Action_Trace records back into structured objects.
3. FOR ALL valid Action_Trace objects, serializing then deserializing SHALL produce an object equivalent to the original (round-trip property).
4. WHEN invalid JSON is provided for deserialization, THE Agent_Runner SHALL return a descriptive error identifying the parsing failure.

### Requirement 18: Configuration Management

**User Story:** As a researcher, I want to manage experiment configurations centrally, so that I can reproduce experiments with identical parameters.

#### Acceptance Criteria

1. THE Platform SHALL load experiment configuration from a YAML or JSON configuration file specifying: target URLs, variant levels, agent configurations, LLM backends, step limits, retry counts, scan parameters, and output directories.
2. WHEN a configuration file is loaded, THE Platform SHALL validate all required fields and report specific validation errors for missing or invalid values.
3. THE Platform SHALL include the full configuration file content in the experiment manifest for reproducibility.
4. IF a configuration value is not specified, THEN THE Platform SHALL use documented default values.

### Requirement 19: Concurrent Execution and Resource Management

**User Story:** As a researcher, I want the platform to execute scans and agent runs concurrently where possible, so that I can complete large experiment matrices in a reasonable time.

#### Acceptance Criteria

1. THE Scanner SHALL support concurrent scanning of multiple URLs with a configurable concurrency limit (default 5).
2. THE Agent_Runner SHALL support concurrent execution of multiple test cases with a configurable concurrency limit (default 3).
3. WHILE executing concurrently, THE Platform SHALL isolate each browser context to prevent cross-contamination between test cases.
4. THE Platform SHALL log resource utilization (memory, CPU) at configurable intervals during experiment execution.

### Requirement 20: WebArena Docker Deployment Integration

**User Story:** As a researcher, I want the platform to integrate with WebArena's Docker deployment, so that I can programmatically manage the four self-hosted apps.

#### Acceptance Criteria

1. THE Platform SHALL provide configuration for connecting to WebArena's four Docker-hosted applications (Reddit, GitLab, CMS, E-commerce) via their respective URLs.
2. WHEN an experiment starts, THE Platform SHALL verify that all required WebArena services are reachable and report any connectivity failures before proceeding.
3. THE Platform SHALL support resetting WebArena app state between experiment runs to ensure a clean starting condition.

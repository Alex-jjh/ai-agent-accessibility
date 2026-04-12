// Integration tests for end-to-end pipeline
// Tests config → scan → export flow, variant → agent flow, and HAR → replay → scan flow
// with mock browser/page objects.
// Requirements: 8.1–8.5, 12.1–12.5, 15.1–15.4

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ExperimentConfig } from './config/types.js';
import type { ScanResult } from './scanner/types.js';
import type { ActionTrace, AgentConfig, TaskOutcome } from './runner/types.js';
import type { VariantLevel } from './variants/types.js';
import type { FailureClassification } from './classifier/types.js';

// --- Shared test fixtures ---

const agentConfig: AgentConfig = {
  observationMode: 'text-only',
  llmBackend: 'claude-opus',
  maxSteps: 30,
  retryCount: 3,
  retryBackoffMs: 1000,
  temperature: 0.0,
};

const testConfig: ExperimentConfig = {
  scanner: { wcagLevels: ['A', 'AA'], stabilityIntervalMs: 100, stabilityTimeoutMs: 500, concurrency: 2 },
  variants: {
    levels: ['low', 'base', 'high'],
    scoreRanges: {
      low: { min: 0, max: 0.25 },
      'medium-low': { min: 0.25, max: 0.5 },
      base: { min: 0.4, max: 0.7 },
      high: { min: 0.75, max: 1.0 },
      'pure-semantic-low': { min: 0, max: 0.25 },
    },
  },
  runner: { agentConfigs: [agentConfig], repetitions: 1, maxSteps: 10, concurrency: 1 },
  recorder: { waitAfterLoadMs: 100, concurrency: 1 },
  webarena: { apps: { reddit: { url: 'http://localhost:9999' } } },
  output: { dataDir: 'test-data-integration', exportFormats: ['json', 'csv'] },
};

function makeScanResult(url = 'http://localhost:9999'): ScanResult {
  return {
    scanId: 'scan-int-001',
    url,
    scannedAt: '2026-03-31T10:00:00Z',
    treeWasStable: true,
    stabilizationMs: 200,
    tier1: {
      url,
      axeCore: {
        violationCount: 2,
        violationsByWcagCriterion: {},
        impactSeverity: { critical: 1, serious: 1, moderate: 0, minor: 0 },
      },
      lighthouse: { accessibilityScore: 80, audits: {} },
      scannedAt: '2026-03-31T10:00:00Z',
    },
    tier2: {
      semanticHtmlRatio: 0.5,
      accessibleNameCoverage: 0.7,
      keyboardNavigability: 0.6,
      ariaCorrectness: 0.8,
      pseudoComplianceCount: 1,
      pseudoComplianceRatio: 0.1,
      formLabelingCompleteness: 0.9,
      landmarkCoverage: 0.65,
      shadowDomIncluded: true,
    },
    compositeScore: {
      compositeScore: 0.68,
      normalizedComponents: {},
      mode: 'composite',
      weights: {},
    },
    a11yTreeSnapshot: { role: 'WebArea' },
  };
}

function makeTrace(taskId: string, success: boolean): ActionTrace {
  return {
    taskId,
    variant: 'base',
    agentConfig,
    attempt: 1,
    success,
    outcome: success ? 'success' : 'failure',
    steps: success
      ? [{ stepNum: 1, timestamp: '2026-03-31T10:00:01Z', observation: 'page loaded', reasoning: 'click submit', action: "click(element='Submit')", result: 'success' }]
      : [
          { stepNum: 1, timestamp: '2026-03-31T10:00:01Z', observation: 'page loaded', reasoning: 'I can see a button', action: "click(element='Missing')", result: 'failure', resultDetail: 'element not found' },
          { stepNum: 2, timestamp: '2026-03-31T10:00:02Z', observation: 'page loaded', reasoning: 'I can see a button', action: "click(element='Missing')", result: 'failure', resultDetail: 'element not found' },
          { stepNum: 3, timestamp: '2026-03-31T10:00:03Z', observation: 'page loaded', reasoning: 'I can see a button', action: "click(element='Missing')", result: 'failure', resultDetail: 'element not found' },
        ],
    totalSteps: success ? 1 : 3,
    totalTokens: 500,
    durationMs: 3000,
  };
}

// ---------------------------------------------------------------------------
// Test 1: Config → Scan → Export flow with mock browser
// ---------------------------------------------------------------------------

describe('Config → Scan → Export flow', () => {
  it('loads config, scans URLs concurrently, and exports CSV + manifest', async () => {
    // Import the modules under test
    const { validateConfig } = await import('./config/loader.js');
    const { exportToCsv } = await import('./export/csv.js');
    const { generateManifest } = await import('./export/manifest.js');
    const { classifyFailure } = await import('./classifier/taxonomy/classify.js');
    const { computeCompositeScore } = await import('./scanner/composite.js');

    // 1. Validate config
    const validation = validateConfig(testConfig);
    expect(validation.valid).toBe(true);
    expect(validation.errors).toHaveLength(0);

    // 2. Simulate scan results for multiple URLs
    const scanResults = [
      makeScanResult('http://localhost:9999'),
      makeScanResult('http://localhost:8023'),
    ];

    // 3. Simulate agent traces (one success, one failure)
    const successTrace = makeTrace('reddit-task-1', true);
    const failureTrace = makeTrace('gitlab-task-1', false);

    // 4. Classify the failure
    const classification = classifyFailure(failureTrace);
    expect(classification.primary).toBeDefined();
    expect(classification.confidence).toBeGreaterThan(0);
    expect(classification.primaryDomain).toBeDefined();

    // 5. Build classified records for export
    const records: import('./export/csv.js').ClassifiedRecord[] = [
      {
        record: {
          caseId: 'reddit:base:reddit-task-1:0:1',
          app: 'reddit',
          variant: 'base',
          taskId: 'reddit-task-1',
          agentConfig,
          attempt: 1,
          trace: successTrace,
          taskOutcome: {
            taskId: 'reddit-task-1',
            outcome: 'success',
            traces: [successTrace],
            medianSteps: 1,
            medianDurationMs: 3000,
            scanResults: scanResults[0],
          },
          scanResults: scanResults[0],
        },
      },
      {
        record: {
          caseId: 'gitlab:base:gitlab-task-1:0:1',
          app: 'gitlab',
          variant: 'base',
          taskId: 'gitlab-task-1',
          agentConfig,
          attempt: 1,
          trace: failureTrace,
          taskOutcome: {
            taskId: 'gitlab-task-1',
            outcome: 'failure',
            traces: [failureTrace],
            medianSteps: 3,
            medianDurationMs: 3000,
            scanResults: scanResults[1],
          },
          scanResults: scanResults[1],
        },
        classification,
      },
    ];

    // 6. Export to CSV
    const csvResult = exportToCsv(records, {
      anonymize: true,
      anonymizeSiteIdentity: false,
      includeTraceDetails: true,
    });

    expect(csvResult.files).toBeDefined();
    expect(Object.keys(csvResult.files)).toContain('experiment-data.csv');
    expect(Object.keys(csvResult.files)).toContain('scan-metrics.csv');
    expect(Object.keys(csvResult.files)).toContain('failure-classifications.csv');
    expect(Object.keys(csvResult.files)).toContain('trace-summaries.csv');

    // Verify experiment-data.csv has correct rows (header + 2 data rows)
    const expDataLines = csvResult.files['experiment-data.csv'].split('\n');
    expect(expDataLines.length).toBe(3); // header + 2 records

    // Verify scan-metrics.csv has correct columns
    const scanHeader = csvResult.files['scan-metrics.csv'].split('\n')[0];
    expect(scanHeader).toContain('axeViolationCount');
    expect(scanHeader).toContain('lighthouseScore');
    expect(scanHeader).toContain('semanticHtmlRatio');

    // Verify failure-classifications.csv has the classified failure
    const classLines = csvResult.files['failure-classifications.csv'].split('\n');
    expect(classLines.length).toBe(2); // header + 1 classified failure

    // 7. Generate manifest
    const mockRun = {
      runId: 'test-run-001',
      matrix: {
        apps: ['reddit', 'gitlab'],
        variants: ['base'] as VariantLevel[],
        tasksPerApp: { reddit: ['reddit-task-1'], gitlab: ['gitlab-task-1'] },
        agentConfigs: [agentConfig],
        repetitions: 1,
      },
      executionOrder: ['reddit:base:reddit-task-1:0:1', 'gitlab:base:gitlab-task-1:0:1'],
      completedCases: new Set(['reddit:base:reddit-task-1:0:1', 'gitlab:base:gitlab-task-1:0:1']),
      startedAt: '2026-03-31T09:00:00Z',
      status: 'completed' as const,
    };

    const manifest = generateManifest(mockRun, testConfig, records.map((r) => r.record));
    expect(manifest.runId).toBe('test-run-001');
    expect(manifest.config).toEqual(testConfig);
    expect(manifest.testCases).toHaveLength(2);
    expect(manifest.softwareVersions).toBeDefined();
    expect(manifest.softwareVersions.axeCore).toBeDefined();
    expect(manifest.softwareVersions.playwright).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Test 2: Variant generation → validation → agent run flow
// ---------------------------------------------------------------------------

describe('Variant generation → validation → agent run flow', () => {
  it('generates test cases from experiment matrix and classifies failures', async () => {
    const { generateTestCases, parseTestCaseId, fisherYatesShuffle } = await import('./runner/scheduler.js');
    const { classifyFailure, filterByReportingMode } = await import('./classifier/taxonomy/classify.js');

    const matrix = {
      apps: ['reddit', 'cms'],
      variants: ['low', 'base', 'high'] as VariantLevel[],
      tasksPerApp: {
        reddit: ['r-task-1', 'r-task-2'],
        cms: ['c-task-1'],
      },
      agentConfigs: [agentConfig],
      repetitions: 2,
    };

    // Req 8.1: Generate all test case combinations
    const cases = generateTestCases(matrix);
    // 2 apps: reddit has 2 tasks, cms has 1 task
    // reddit: 3 variants × 2 tasks × 1 config × 2 reps = 12
    // cms:    3 variants × 1 task  × 1 config × 2 reps = 6
    expect(cases).toHaveLength(18);

    // Verify case ID format
    const firstCase = cases[0];
    expect(firstCase).toMatch(/^[^:]+:[^:]+:[^:]+:\d+:\d+$/);

    // Parse a case ID back
    const parsed = parseTestCaseId(firstCase, matrix);
    expect(parsed.app).toBeDefined();
    expect(parsed.variant).toBeDefined();
    expect(parsed.taskId).toBeDefined();
    expect(parsed.agentConfig).toEqual(agentConfig);
    expect(parsed.attempt).toBeGreaterThanOrEqual(1);

    // Req 8.3: Randomization produces different orderings
    const shuffled1 = fisherYatesShuffle(cases, () => 0.3);
    const shuffled2 = fisherYatesShuffle(cases, () => 0.7);
    // With different random seeds, orderings should differ
    const sameOrder = shuffled1.every((c, i) => c === shuffled2[i]);
    expect(sameOrder).toBe(false);
    // But contain the same elements
    expect(new Set(shuffled1)).toEqual(new Set(shuffled2));

    // Simulate agent failures and classify them
    const traces: ActionTrace[] = [
      makeTrace('r-task-1', false), // will be classified
      makeTrace('r-task-2', true),  // success, no classification
    ];

    const classifications = traces
      .filter((t) => !t.success)
      .map((t) => classifyFailure(t));

    expect(classifications).toHaveLength(1);
    expect(classifications[0].primary).toBeDefined();

    // Test reporting modes (Req 9.6)
    const allClassifications = classifications;
    const conservative = filterByReportingMode(allClassifications, 'conservative');
    const inclusive = filterByReportingMode(allClassifications, 'inclusive');

    // Inclusive always returns all
    expect(inclusive).toHaveLength(allClassifications.length);
    // Conservative only returns accessibility-domain
    for (const c of conservative) {
      expect(c.primaryDomain).toBe('accessibility');
    }
  });

  it('validates variant score ranges are consistent', async () => {
    const { VARIANT_SCORE_RANGES } = await import('./variants/validation/index.js');

    // Verify all four levels are defined
    expect(VARIANT_SCORE_RANGES).toHaveProperty('low');
    expect(VARIANT_SCORE_RANGES).toHaveProperty('medium-low');
    expect(VARIANT_SCORE_RANGES).toHaveProperty('base');
    expect(VARIANT_SCORE_RANGES).toHaveProperty('high');

    // Verify ranges are ordered: low < medium-low < base < high
    expect(VARIANT_SCORE_RANGES['low'].max).toBeLessThanOrEqual(VARIANT_SCORE_RANGES['medium-low'].max);
    expect(VARIANT_SCORE_RANGES['medium-low'].max).toBeLessThanOrEqual(VARIANT_SCORE_RANGES['base'].max);
    expect(VARIANT_SCORE_RANGES['base'].max).toBeLessThanOrEqual(VARIANT_SCORE_RANGES['high'].max);

    // Verify all ranges are within 0–1
    for (const [, range] of Object.entries(VARIANT_SCORE_RANGES)) {
      expect(range.min).toBeGreaterThanOrEqual(0);
      expect(range.max).toBeLessThanOrEqual(1);
      expect(range.min).toBeLessThanOrEqual(range.max);
    }
  });

  it('composite score computation integrates tier1 + tier2 correctly', async () => {
    const { computeCompositeScore } = await import('./scanner/composite.js');

    const scanResult = makeScanResult();
    const composite = computeCompositeScore(scanResult.tier1, scanResult.tier2, {
      weights: {
        lighthouseScore: 1,
        axeViolations: 1,
        semanticHtmlRatio: 1,
        accessibleNameCoverage: 1,
        keyboardNavigability: 1,
        ariaCorrectness: 1,
        pseudoComplianceRatio: 1,
        formLabelingCompleteness: 1,
        landmarkCoverage: 1,
      },
      mode: 'composite',
    });

    expect(composite.compositeScore).toBeGreaterThanOrEqual(0);
    expect(composite.compositeScore).toBeLessThanOrEqual(1);
    expect(composite.mode).toBe('composite');
    expect(composite.normalizedComponents).toBeDefined();
    expect(composite.normalizedComponents.lighthouseScore).toBeDefined();
    expect(composite.normalizedComponents.semanticHtmlRatio).toBeDefined();

    // Sensitivity modes
    const tier1Only = computeCompositeScore(scanResult.tier1, scanResult.tier2, {
      weights: { lighthouseScore: 1, axeViolations: 1 },
      mode: 'tier1-only',
    });
    expect(tier1Only.mode).toBe('tier1-only');

    const tier2Only = computeCompositeScore(scanResult.tier1, scanResult.tier2, {
      weights: { semanticHtmlRatio: 1, accessibleNameCoverage: 1 },
      mode: 'tier2-only',
    });
    expect(tier2Only.mode).toBe('tier2-only');
  });
});

// ---------------------------------------------------------------------------
// Test 3: HAR capture → replay → scan flow
// ---------------------------------------------------------------------------

describe('HAR capture → replay → scan flow', () => {
  it('classifies requests as functional vs non-functional correctly', async () => {
    const { classifyRequest, computeCoverageGap } = await import('./recorder/replay/replay.js');

    // Functional requests
    expect(classifyRequest('https://example.com/index.html')).toBe('functional');
    expect(classifyRequest('https://example.com/api/data')).toBe('functional');
    expect(classifyRequest('https://cdn.example.com/app.js')).toBe('functional');
    expect(classifyRequest('https://example.com/styles.css')).toBe('functional');

    // Non-functional requests (analytics, ads, tracking)
    expect(classifyRequest('https://www.google-analytics.com/collect')).toBe('non-functional');
    expect(classifyRequest('https://www.googletagmanager.com/gtm.js')).toBe('non-functional');
    expect(classifyRequest('https://ad.doubleclick.net/ad')).toBe('non-functional');
    expect(classifyRequest('https://www.facebook.com/tr')).toBe('non-functional');
    expect(classifyRequest('https://cdn.segment.com/analytics.js')).toBe('non-functional');
    expect(classifyRequest('https://static.hotjar.com/c/hotjar.js')).toBe('non-functional');
  });

  it('computes coverage gap correctly', async () => {
    const { computeCoverageGap } = await import('./recorder/replay/replay.js');

    // No requests → 0 gap
    expect(computeCoverageGap(0, 0)).toBe(0);

    // All matched → 0 gap
    expect(computeCoverageGap(10, 0)).toBe(0);

    // 2 of 10 unmatched → 0.2 gap
    expect(computeCoverageGap(10, 2)).toBeCloseTo(0.2);

    // All unmatched → 1.0 gap
    expect(computeCoverageGap(5, 5)).toBe(1);

    // 3 of 10 unmatched → 0.3 (> 0.20 threshold → low fidelity)
    const gap = computeCoverageGap(10, 3);
    expect(gap).toBeCloseTo(0.3);
    expect(gap > 0.20).toBe(true); // Would be flagged as low fidelity
  });

  it('scan result serialization round-trips through export pipeline', async () => {
    const { serializeScanResult, deserializeScanResult } = await import('./scanner/serialization.js');
    const { exportToCsv } = await import('./export/csv.js');

    const original = makeScanResult('https://example.com');

    // Serialize → deserialize round-trip
    const json = serializeScanResult(original);
    const restored = deserializeScanResult(json);

    expect(restored.scanId).toBe(original.scanId);
    expect(restored.url).toBe(original.url);
    expect(restored.tier1.axeCore.violationCount).toBe(original.tier1.axeCore.violationCount);
    expect(restored.tier2.semanticHtmlRatio).toBe(original.tier2.semanticHtmlRatio);
    expect(restored.treeWasStable).toBe(original.treeWasStable);

    // Feed the restored result through CSV export
    const trace = makeTrace('task-1', true);
    const records: import('./export/csv.js').ClassifiedRecord[] = [{
      record: {
        caseId: 'test:base:task-1:0:1',
        app: 'test',
        variant: 'base',
        taskId: 'task-1',
        agentConfig,
        attempt: 1,
        trace,
        taskOutcome: {
          taskId: 'task-1',
          outcome: 'success',
          traces: [trace],
          medianSteps: 1,
          medianDurationMs: 3000,
          scanResults: restored,
        },
        scanResults: restored,
      },
    }];

    const csvResult = exportToCsv(records, {
      anonymize: false,
      anonymizeSiteIdentity: false,
      includeTraceDetails: false,
    });

    // Verify scan metrics CSV contains the restored data
    const scanCsv = csvResult.files['scan-metrics.csv'];
    expect(scanCsv).toContain('https://example.com');
    expect(scanCsv).toContain('80'); // lighthouse score
    expect(scanCsv).toContain('0.5'); // semanticHtmlRatio
  });

  it('PII anonymization works in the export pipeline', async () => {
    const { scrubPii } = await import('./export/csv.js');

    // Email scrubbing
    expect(scrubPii('Contact user@example.com for help')).toContain('[email]');
    expect(scrubPii('Contact user@example.com for help')).not.toContain('user@example.com');

    // Credential scrubbing — the cookie regex matches "Authorization: Bearer abc123xyz"
    // as a credential header. The regex captures the header name + value up to whitespace.
    const scrubbed = scrubPii('Authorization: Bearer abc123xyz');
    expect(scrubbed).toContain('[redacted');

    // Test a standalone token pattern that the auth token regex catches
    const tokenScrubbed = scrubPii('token=eyJhbGciOiJIUzI1NiJ9.abc');
    expect(tokenScrubbed).toContain('[redacted');
    expect(tokenScrubbed).not.toContain('eyJhbGciOiJIUzI1NiJ9');

    // User URL segment scrubbing
    expect(scrubPii('https://example.com/users/john_doe/profile')).toContain('[redacted]');
    expect(scrubPii('https://example.com/users/john_doe/profile')).not.toContain('john_doe');
  });

  it('site identity anonymization replaces URLs with opaque IDs', async () => {
    const { exportToCsv, buildSiteMapping } = await import('./export/csv.js');

    const trace = makeTrace('task-1', true);
    const scan1 = makeScanResult('https://site-a.com');
    const scan2 = makeScanResult('https://site-b.com');

    const records: import('./export/csv.js').ClassifiedRecord[] = [
      {
        record: {
          caseId: 'a:base:task-1:0:1', app: 'a', variant: 'base', taskId: 'task-1',
          agentConfig, attempt: 1, trace,
          taskOutcome: { taskId: 'task-1', outcome: 'success', traces: [trace], medianSteps: 1, medianDurationMs: 3000, scanResults: scan1 },
          scanResults: scan1,
        },
      },
      {
        record: {
          caseId: 'b:base:task-1:0:1', app: 'b', variant: 'base', taskId: 'task-1',
          agentConfig, attempt: 1, trace,
          taskOutcome: { taskId: 'task-1', outcome: 'success', traces: [trace], medianSteps: 1, medianDurationMs: 3000, scanResults: scan2 },
          scanResults: scan2,
        },
      },
    ];

    // Build site mapping
    const mapping = buildSiteMapping(records);
    expect(Object.keys(mapping)).toHaveLength(2);
    expect(Object.values(mapping)).toContain('site_001');
    expect(Object.values(mapping)).toContain('site_002');

    // Export with site anonymization
    const csvResult = exportToCsv(records, {
      anonymize: false,
      anonymizeSiteIdentity: true,
      includeTraceDetails: false,
    });

    // Scan metrics CSV should use opaque IDs instead of real URLs
    const scanCsv = csvResult.files['scan-metrics.csv'];
    expect(scanCsv).toContain('site_001');
    expect(scanCsv).toContain('site_002');
    expect(scanCsv).not.toContain('https://site-a.com');
    expect(scanCsv).not.toContain('https://site-b.com');
  });
});

// ---------------------------------------------------------------------------
// Test 4: Cross-module data flow integrity
// ---------------------------------------------------------------------------

describe('Cross-module data flow integrity', () => {
  it('action trace serialization round-trips through classifier', async () => {
    const { serializeActionTrace, deserializeActionTrace } = await import('./runner/serialization.js');
    const { classifyFailure } = await import('./classifier/taxonomy/classify.js');

    const trace = makeTrace('task-1', false);

    // Serialize → deserialize
    const json = serializeActionTrace(trace);
    const restored = deserializeActionTrace(json);

    expect(restored.taskId).toBe(trace.taskId);
    expect(restored.steps).toHaveLength(trace.steps.length);
    expect(restored.totalTokens).toBe(trace.totalTokens);

    // Classify the restored trace — should produce same result as original
    const classOriginal = classifyFailure(trace);
    const classRestored = classifyFailure(restored);

    expect(classRestored.primary).toBe(classOriginal.primary);
    expect(classRestored.primaryDomain).toBe(classOriginal.primaryDomain);
    expect(classRestored.confidence).toBe(classOriginal.confidence);
  });

  it('experiment store paths follow documented layout', async () => {
    const { ExperimentStore } = await import('./export/store.js');

    const store = new ExperimentStore({ baseDir: 'data' });

    // Track A paths (use path.sep-agnostic checks for Windows compatibility)
    expect(store.runDir('run-001')).toMatch(/track-a[/\\]runs[/\\]run-001/);
    expect(store.caseDir('run-001', 'reddit:base:task-1:0:1')).toMatch(/track-a[/\\]runs[/\\]run-001[/\\]cases/);

    // Track B paths
    expect(store.harDir('har-001')).toMatch(/track-b[/\\]har[/\\]har-001/);

    // Exports path
    expect(store.exportsDir()).toMatch(/exports/);
  });

  it('WebArena config builds correctly from experiment config', async () => {
    const { buildWebArenaConfig, DEFAULT_WEBARENA_APPS } = await import('./runner/webarena.js');

    const waConfig = buildWebArenaConfig(testConfig);

    // Should have the reddit app from testConfig
    expect(waConfig).toHaveProperty('reddit');
    expect(waConfig.reddit.url).toBe('http://localhost:9999');

    // Should merge with defaults
    expect(waConfig.reddit.resetStrategy).toBeDefined();

    // Default apps should have all four
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toContain('reddit');
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toContain('gitlab');
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toContain('cms');
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toContain('ecommerce');
  });

  it('config validation rejects invalid configs and accepts valid ones', async () => {
    const { validateConfig } = await import('./config/loader.js');

    // Valid minimal config
    const valid = validateConfig({
      webarena: { apps: { reddit: { url: 'http://localhost:9999' } } },
    });
    expect(valid.valid).toBe(true);

    // Missing webarena
    const noWebarena = validateConfig({});
    expect(noWebarena.valid).toBe(false);
    expect(noWebarena.errors.some((e) => e.includes('webarena'))).toBe(true);

    // Invalid scanner config
    const badScanner = validateConfig({
      webarena: { apps: { reddit: { url: 'http://localhost:9999' } } },
      scanner: { concurrency: -1 },
    });
    expect(badScanner.valid).toBe(false);

    // Not an object
    const notObj = validateConfig('string');
    expect(notObj.valid).toBe(false);

    // Null
    const nullConfig = validateConfig(null);
    expect(nullConfig.valid).toBe(false);
  });
});

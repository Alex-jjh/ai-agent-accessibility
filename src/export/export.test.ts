// Unit tests for Data Export: manifest, CSV, and JSON store
// Requirements: 15.1–15.4

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import { generateManifest, collectSoftwareVersions } from './manifest.js';
import { exportToCsv, scrubPii, buildSiteMapping } from './csv.js';
import type { ClassifiedRecord } from './csv.js';
import { ExperimentStore } from './store.js';
import type { ExperimentConfig } from '../config/types.js';
import type { ExperimentRun, ActionTrace, AgentConfig } from '../runner/types.js';
import type { ExperimentRecord } from '../runner/scheduler.js';
import type { ScanResult } from '../scanner/types.js';
import type { FailureClassification } from '../classifier/types.js';
import type { HarMetadata } from '../recorder/types.js';

// --- Test fixtures ---

const agentConfig: AgentConfig = {
  observationMode: 'text-only',
  llmBackend: 'claude-opus',
  maxSteps: 30,
  retryCount: 3,
  retryBackoffMs: 1000,
  temperature: 0.0,
};

const experimentConfig: ExperimentConfig = {
  scanner: { wcagLevels: ['A', 'AA'], stabilityIntervalMs: 2000, stabilityTimeoutMs: 30000, concurrency: 5 },
  variants: {
    levels: ['low', 'medium-low', 'base', 'high'],
    scoreRanges: {
      low: { min: 0, max: 0.25 },
      'medium-low': { min: 0.25, max: 0.5 },
      base: { min: 0.4, max: 0.7 },
      high: { min: 0.75, max: 1.0 },
      'pure-semantic-low': { min: 0, max: 0.25 },
    },
  },
  runner: { agentConfigs: [agentConfig], repetitions: 3, maxSteps: 30, concurrency: 3 },
  recorder: { waitAfterLoadMs: 10000, concurrency: 5 },
  webarena: { apps: { reddit: { url: 'http://localhost:9999' } } },
  output: { dataDir: 'data', exportFormats: ['json', 'csv'] },
};

function makeScanResult(url = 'https://example.com/page1'): ScanResult {
  return {
    scanId: 'scan-001',
    url,
    scannedAt: '2026-01-15T10:00:00Z',
    treeWasStable: true,
    stabilizationMs: 4000,
    tier1: {
      url,
      axeCore: {
        violationCount: 5,
        violationsByWcagCriterion: { '4.1.2': [{ id: 'button-name', impact: 'critical', description: 'Buttons must have discernible text', nodes: 2 }] },
        impactSeverity: { critical: 2, serious: 1, moderate: 1, minor: 1 },
      },
      lighthouse: { accessibilityScore: 78, audits: { 'button-name': { pass: false } } },
      scannedAt: '2026-01-15T10:00:00Z',
    },
    tier2: {
      semanticHtmlRatio: 0.45,
      accessibleNameCoverage: 0.8,
      keyboardNavigability: 0.6,
      ariaCorrectness: 0.75,
      pseudoComplianceCount: 3,
      pseudoComplianceRatio: 0.15,
      formLabelingCompleteness: 0.9,
      landmarkCoverage: 0.7,
      shadowDomIncluded: true,
    },
    compositeScore: { compositeScore: 0.65, normalizedComponents: { lighthouse: 0.78 }, mode: 'composite', weights: { lighthouse: 0.5 } },
    a11yTreeSnapshot: { role: 'WebArea', name: 'Test' },
  };
}

function makeTrace(taskId = 'task-1', success = false): ActionTrace {
  return {
    taskId,
    variant: 'base',
    agentConfig,
    attempt: 1,
    success,
    outcome: success ? 'success' : 'failure',
    steps: [
      { stepNum: 1, timestamp: '2026-01-15T10:01:00Z', observation: 'a11y tree text', reasoning: 'Click submit', action: "click(element='Submit')", result: 'success' },
      { stepNum: 2, timestamp: '2026-01-15T10:01:05Z', observation: 'a11y tree text', reasoning: 'Check result', action: "click(element='Confirm')", result: success ? 'success' : 'error', resultDetail: success ? undefined : 'Element not found' },
    ],
    totalSteps: 2,
    totalTokens: 1500,
    durationMs: 5000,
    failureType: success ? undefined : 'F_ENF',
    failureConfidence: success ? undefined : 0.85,
  };
}

function makeRecord(caseId = 'reddit:base:task-1:0:1', url = 'https://example.com/page1'): ExperimentRecord {
  const trace = makeTrace('task-1', false);
  return {
    caseId,
    app: 'reddit',
    variant: 'base',
    taskId: 'task-1',
    agentConfig,
    attempt: 1,
    trace,
    taskOutcome: {
      taskId: 'task-1',
      outcome: 'failure',
      traces: [trace],
      medianSteps: 2,
      medianDurationMs: 5000,
      scanResults: makeScanResult(url),
    },
    scanResults: makeScanResult(url),
  };
}

function makeClassification(): FailureClassification {
  return {
    primary: 'F_ENF',
    primaryDomain: 'accessibility',
    secondaryFactors: ['F_PCT'],
    confidence: 0.85,
    flaggedForReview: false,
    evidence: ['Step 2: Element not found after 3 attempts targeting Submit button'],
  };
}

function makeClassifiedRecords(): ClassifiedRecord[] {
  return [
    { record: makeRecord('reddit:base:task-1:0:1', 'https://example.com/page1'), classification: makeClassification() },
    { record: makeRecord('reddit:low:task-2:0:1', 'https://other-site.org/app'), classification: undefined },
  ];
}

// --- Manifest tests ---

describe('generateManifest', () => {
  it('includes all required software versions', () => {
    const run: ExperimentRun = {
      runId: 'run-001',
      matrix: { apps: ['reddit'], variants: ['base'], tasksPerApp: { reddit: ['task-1'] }, agentConfigs: [agentConfig], repetitions: 1 },
      executionOrder: ['reddit:base:task-1:0:1'],
      completedCases: new Set(['reddit:base:task-1:0:1']),
      startedAt: '2026-01-15T09:00:00Z',
      status: 'completed',
    };
    const records = [makeRecord()];
    const manifest = generateManifest(run, experimentConfig, records);

    expect(manifest.runId).toBe('run-001');
    expect(manifest.startedAt).toBe('2026-01-15T09:00:00Z');
    expect(manifest.completedAt).toBeTruthy();
    expect(manifest.softwareVersions).toHaveProperty('axeCore');
    expect(manifest.softwareVersions).toHaveProperty('lighthouse');
    expect(manifest.softwareVersions).toHaveProperty('playwright');
    expect(manifest.softwareVersions).toHaveProperty('llmModels');
    expect(manifest.softwareVersions).toHaveProperty('platform');
    expect(manifest.softwareVersions.llmModels).toHaveProperty('claude-opus');
  });

  it('includes full config for reproducibility', () => {
    const run: ExperimentRun = {
      runId: 'run-002',
      matrix: { apps: ['reddit'], variants: ['base'], tasksPerApp: { reddit: ['task-1'] }, agentConfigs: [agentConfig], repetitions: 1 },
      executionOrder: [],
      completedCases: new Set(),
      startedAt: '2026-01-15T09:00:00Z',
      status: 'completed',
    };
    const manifest = generateManifest(run, experimentConfig, []);

    expect(manifest.config).toEqual(experimentConfig);
    expect(manifest.config.scanner.wcagLevels).toEqual(['A', 'AA']);
    expect(manifest.config.webarena.apps.reddit.url).toBe('http://localhost:9999');
  });

  it('lists test cases with outcomes', () => {
    const run: ExperimentRun = {
      runId: 'run-003',
      matrix: { apps: ['reddit'], variants: ['base'], tasksPerApp: { reddit: ['task-1'] }, agentConfigs: [agentConfig], repetitions: 1 },
      executionOrder: ['reddit:base:task-1:0:1'],
      completedCases: new Set(['reddit:base:task-1:0:1']),
      startedAt: '2026-01-15T09:00:00Z',
      status: 'completed',
    };
    const records = [makeRecord()];
    const manifest = generateManifest(run, experimentConfig, records);

    expect(manifest.testCases).toHaveLength(1);
    expect(manifest.testCases[0].caseId).toBe('reddit:base:task-1:0:1');
    expect(manifest.testCases[0].outcome).toBe('failure');
    expect(manifest.testCases[0].traces).toBe(1);
  });
});

// --- CSV export tests ---

describe('exportToCsv', () => {
  it('produces valid CSV with correct columns for all four files', () => {
    const data = makeClassifiedRecords();
    const result = exportToCsv(data, { anonymize: false, anonymizeSiteIdentity: false, includeTraceDetails: false });

    expect(Object.keys(result.files)).toEqual([
      'experiment-data.csv',
      'scan-metrics.csv',
      'failure-classifications.csv',
      'trace-summaries.csv',
    ]);

    // experiment-data.csv
    const expLines = result.files['experiment-data.csv'].split('\n');
    expect(expLines[0]).toContain('caseId');
    expect(expLines[0]).toContain('outcome');
    expect(expLines[0]).toContain('llmBackend');
    expect(expLines).toHaveLength(3); // header + 2 data rows

    // scan-metrics.csv
    const scanLines = result.files['scan-metrics.csv'].split('\n');
    expect(scanLines[0]).toContain('axeViolationCount');
    expect(scanLines[0]).toContain('semanticHtmlRatio');
    expect(scanLines[0]).toContain('compositeScore');
    expect(scanLines).toHaveLength(3);

    // failure-classifications.csv — only 1 classified record
    const failLines = result.files['failure-classifications.csv'].split('\n');
    expect(failLines[0]).toContain('primaryType');
    expect(failLines[0]).toContain('confidence');
    expect(failLines).toHaveLength(2); // header + 1 classified

    // trace-summaries.csv
    const traceLines = result.files['trace-summaries.csv'].split('\n');
    expect(traceLines[0]).toContain('totalSteps');
    expect(traceLines[0]).toContain('failureType');
    expect(traceLines).toHaveLength(3);
  });

  it('includes trace detail columns when includeTraceDetails is true', () => {
    const data = makeClassifiedRecords();
    const result = exportToCsv(data, { anonymize: false, anonymizeSiteIdentity: false, includeTraceDetails: true });

    const traceLines = result.files['trace-summaries.csv'].split('\n');
    expect(traceLines[0]).toContain('firstAction');
    expect(traceLines[0]).toContain('lastAction');
    expect(traceLines[0]).toContain('errorCount');
  });
});

// --- PII anonymization tests ---

describe('scrubPii', () => {
  it('removes email addresses', () => {
    const input = 'User john.doe@example.com submitted a form';
    expect(scrubPii(input)).toBe('User [email] submitted a form');
  });

  it('removes cookie values', () => {
    const input = 'cookie: session=abc123def456';
    expect(scrubPii(input)).toBe('[redacted-credential]');
  });

  it('removes auth tokens', () => {
    const input = 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc';
    const result = scrubPii(input);
    expect(result).not.toContain('eyJhbGciOiJIUzI1NiJ9');
    expect(result).toContain('[redacted-token]');
  });

  it('removes user-specific URL segments', () => {
    const input = 'Navigated to /users/john_doe/profile';
    expect(scrubPii(input)).toBe('Navigated to /users/[redacted]/profile');
  });

  it('handles multiple PII types in one string', () => {
    const input = 'User admin@test.com at /users/admin123 with Authorization: Bearer tok123';
    const result = scrubPii(input);
    expect(result).not.toContain('admin@test.com');
    expect(result).not.toContain('/users/admin123');
  });
});

// --- Site identity anonymization tests ---

describe('site identity anonymization', () => {
  it('replaces URLs with opaque IDs when enabled', () => {
    const data = makeClassifiedRecords();
    const result = exportToCsv(data, { anonymize: false, anonymizeSiteIdentity: true, includeTraceDetails: false });

    expect(result.siteMapping).toBeDefined();
    const mapping = result.siteMapping!;

    // Should have two unique URLs mapped
    expect(Object.keys(mapping)).toHaveLength(2);
    expect(mapping['https://example.com/page1']).toMatch(/^site_\d{3}$/);
    expect(mapping['https://other-site.org/app']).toMatch(/^site_\d{3}$/);

    // scan-metrics.csv should contain opaque IDs, not real URLs
    const scanCsv = result.files['scan-metrics.csv'];
    expect(scanCsv).not.toContain('https://example.com/page1');
    expect(scanCsv).not.toContain('https://other-site.org/app');
    expect(scanCsv).toContain('site_001');
  });

  it('does not anonymize URLs when disabled', () => {
    const data = makeClassifiedRecords();
    const result = exportToCsv(data, { anonymize: false, anonymizeSiteIdentity: false, includeTraceDetails: false });

    expect(result.siteMapping).toBeUndefined();
    const scanCsv = result.files['scan-metrics.csv'];
    expect(scanCsv).toContain('https://example.com/page1');
  });
});

// --- JSON store tests ---

describe('ExperimentStore', () => {
  const testDir = join('test-tmp', 'store-tests');
  let store: ExperimentStore;

  beforeEach(() => {
    store = new ExperimentStore({ baseDir: testDir });
  });

  afterEach(async () => {
    await rm(testDir, { recursive: true, force: true });
  });

  it('stores and loads manifest', async () => {
    const run: ExperimentRun = {
      runId: 'run-store-1',
      matrix: { apps: ['reddit'], variants: ['base'], tasksPerApp: { reddit: ['task-1'] }, agentConfigs: [agentConfig], repetitions: 1 },
      executionOrder: [],
      completedCases: new Set(),
      startedAt: '2026-01-15T09:00:00Z',
      status: 'completed',
    };
    const manifest = generateManifest(run, experimentConfig, []);

    await store.storeManifest('run-store-1', manifest);
    const loaded = await store.loadManifest('run-store-1');

    expect(loaded.runId).toBe('run-store-1');
    expect(loaded.config).toEqual(experimentConfig);
    expect(loaded.softwareVersions).toHaveProperty('axeCore');
  });

  it('stores and loads scan results', async () => {
    const scan = makeScanResult();
    await store.storeScanResult('run-1', 'case:1', scan);
    const loaded = await store.loadScanResult('run-1', 'case:1');

    expect(loaded.scanId).toBe('scan-001');
    expect(loaded.tier2.semanticHtmlRatio).toBe(0.45);
  });

  it('stores and loads action traces', async () => {
    const trace = makeTrace('task-1', true);
    await store.storeTrace('run-1', 'case:1', 1, trace);
    const loaded = await store.loadTrace('run-1', 'case:1', 1);

    expect(loaded.taskId).toBe('task-1');
    expect(loaded.success).toBe(true);
    expect(loaded.steps).toHaveLength(2);
  });

  it('stores and loads failure classifications', async () => {
    const classification = makeClassification();
    await store.storeClassification('run-1', 'case:1', classification);
    const loaded = await store.loadClassification('run-1', 'case:1');

    expect(loaded.primary).toBe('F_ENF');
    expect(loaded.confidence).toBe(0.85);
  });

  it('stores HAR metadata in track-b directory', async () => {
    const metadata: HarMetadata = {
      recordingTimestamp: '2026-01-15T10:00:00Z',
      targetUrl: 'https://example.com',
      geoRegion: 'us-east-1',
      sectorClassification: 'e-commerce',
      pageLanguage: 'en',
    };
    const path = await store.storeHarMetadata('har-001', metadata);
    expect(path).toContain('track-b');
    expect(path).toContain('har-001');

    const loaded = await store.loadHarMetadata('har-001');
    expect(loaded.targetUrl).toBe('https://example.com');
    expect(loaded.sectorClassification).toBe('e-commerce');
  });

  it('writes CSV exports to exports directory', async () => {
    const csvContent = 'caseId,outcome\ncase-1,success';
    const path = await store.writeCsvExport('experiment-data.csv', csvContent);
    expect(path).toContain('exports');
    expect(path).toContain('experiment-data.csv');
  });
});

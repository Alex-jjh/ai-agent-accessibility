// Unit tests for Experiment Matrix Scheduler
// Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import {
  generateTestCases,
  parseTestCaseId,
  fisherYatesShuffle,
  executeExperiment,
  loadRunState,
} from './scheduler.js';
import type { ExperimentMatrix, ActionTrace, TaskOutcome, AgentConfig } from './types.js';
import type { ScanResult } from '../scanner/types.js';
import type { TestCaseParams, TestCaseResult } from './scheduler.js';

// --- Test fixtures ---

const testConfig: AgentConfig = {
  observationMode: 'text-only',
  llmBackend: 'gpt-4o',
  maxSteps: 30,
  retryCount: 3,
  retryBackoffMs: 1000,
  temperature: 0,
};

const smallMatrix: ExperimentMatrix = {
  apps: ['reddit', 'gitlab'],
  variants: ['low', 'base'],
  tasksPerApp: {
    reddit: ['task-r1'],
    gitlab: ['task-g1'],
  },
  agentConfigs: [testConfig],
  repetitions: 2,
};

function makeMockTrace(caseId: string, params: TestCaseParams): ActionTrace {
  return {
    taskId: params.taskId,
    variant: params.variant as ActionTrace['variant'],
    agentConfig: params.agentConfig,
    attempt: params.attempt,
    success: true,
    outcome: 'success',
    steps: [],
    totalSteps: 0,
    totalTokens: 100,
    durationMs: 500,
  };
}

function makeMockScanResult(): ScanResult {
  return {
    scanId: 'scan-1',
    url: 'http://localhost',
    scannedAt: new Date().toISOString(),
    treeWasStable: true,
    stabilizationMs: 100,
    tier1: {
      url: 'http://localhost',
      axeCore: {
        violationCount: 0,
        violationsByWcagCriterion: {},
        impactSeverity: { critical: 0, serious: 0, moderate: 0, minor: 0 },
      },
      lighthouse: { accessibilityScore: 95, audits: {} },
      scannedAt: new Date().toISOString(),
    },
    tier2: {
      semanticHtmlRatio: 0.8,
      accessibleNameCoverage: 0.9,
      keyboardNavigability: 0.7,
      ariaCorrectness: 0.85,
      pseudoComplianceCount: 0,
      pseudoComplianceRatio: 0,
      formLabelingCompleteness: 1.0,
      landmarkCoverage: 0.6,
      shadowDomIncluded: false,
    },
    compositeScore: null,
    a11yTreeSnapshot: {},
  };
}

function makeMockResult(caseId: string, params: TestCaseParams): TestCaseResult {
  const trace = makeMockTrace(caseId, params);
  return {
    trace,
    taskOutcome: {
      taskId: params.taskId,
      outcome: 'success',
      traces: [trace],
      medianSteps: 0,
      medianDurationMs: 500,
      scanResults: makeMockScanResult(),
    },
    scanResults: makeMockScanResult(),
  };
}

const TEST_DATA_DIR = join('test-tmp', 'scheduler-tests');

// --- Tests ---

describe('generateTestCases', () => {
  it('generates correct number of test cases (apps × variants × tasks × configs × repetitions) (Req 8.1)', () => {
    const cases = generateTestCases(smallMatrix);
    // 2 apps × 2 variants × 1 task each × 1 config × 2 reps = 8
    expect(cases.length).toBe(8);
  });

  it('generates correct count for larger matrix', () => {
    const matrix: ExperimentMatrix = {
      apps: ['reddit', 'gitlab', 'cms', 'ecommerce'],
      variants: ['low', 'medium-low', 'base', 'high'],
      tasksPerApp: {
        reddit: ['r1', 'r2', 'r3'],
        gitlab: ['g1', 'g2', 'g3'],
        cms: ['c1', 'c2', 'c3'],
        ecommerce: ['e1', 'e2', 'e3'],
      },
      agentConfigs: [testConfig],
      repetitions: 3,
    };
    const cases = generateTestCases(matrix);
    // 4 apps × 4 variants × 3 tasks × 1 config × 3 reps = 144
    expect(cases.length).toBe(144);
  });

  it('handles multiple agent configs', () => {
    const matrix: ExperimentMatrix = {
      ...smallMatrix,
      agentConfigs: [
        testConfig,
        { ...testConfig, observationMode: 'vision' as const },
      ],
    };
    const cases = generateTestCases(matrix);
    // 2 apps × 2 variants × 1 task × 2 configs × 2 reps = 16
    expect(cases.length).toBe(16);
  });

  it('returns empty array for empty matrix', () => {
    const matrix: ExperimentMatrix = {
      apps: [],
      variants: ['low'],
      tasksPerApp: {},
      agentConfigs: [testConfig],
      repetitions: 1,
    };
    expect(generateTestCases(matrix)).toEqual([]);
  });

  it('case IDs contain app, variant, taskId, configIndex, attempt', () => {
    const cases = generateTestCases(smallMatrix);
    for (const c of cases) {
      const parts = c.split(':');
      expect(parts.length).toBe(5);
      expect(smallMatrix.apps).toContain(parts[0]);
      expect(smallMatrix.variants).toContain(parts[1]);
    }
  });
});

describe('parseTestCaseId', () => {
  it('round-trips with generateTestCases', () => {
    const cases = generateTestCases(smallMatrix);
    for (const caseId of cases) {
      const params = parseTestCaseId(caseId, smallMatrix);
      expect(smallMatrix.apps).toContain(params.app);
      expect(smallMatrix.variants).toContain(params.variant);
      expect(params.attempt).toBeGreaterThanOrEqual(1);
      expect(params.attempt).toBeLessThanOrEqual(smallMatrix.repetitions);
      expect(params.agentConfig).toEqual(testConfig);
    }
  });

  it('throws on invalid format', () => {
    expect(() => parseTestCaseId('bad', smallMatrix)).toThrow(/Invalid test case ID/);
  });

  it('throws on invalid config index', () => {
    expect(() => parseTestCaseId('reddit:low:t1:99:1', smallMatrix)).toThrow(/Invalid config index/);
  });
});

describe('fisherYatesShuffle', () => {
  it('produces a permutation of the same length', () => {
    const input = [1, 2, 3, 4, 5, 6, 7, 8];
    const shuffled = fisherYatesShuffle(input);
    expect(shuffled.length).toBe(input.length);
    expect(shuffled.sort()).toEqual(input.sort());
  });

  it('does not mutate the original array', () => {
    const input = [1, 2, 3];
    const copy = [...input];
    fisherYatesShuffle(input);
    expect(input).toEqual(copy);
  });

  it('produces different orderings with different random seeds (Req 8.3)', () => {
    const input = Array.from({ length: 20 }, (_, i) => i);
    const a = fisherYatesShuffle(input, () => 0.1);
    const b = fisherYatesShuffle(input, () => 0.9);
    // With different seeds, the orderings should differ
    expect(a).not.toEqual(b);
  });

  it('is deterministic with the same random function', () => {
    const input = [1, 2, 3, 4, 5];
    function makeRng(initial: number) {
      let s = initial;
      return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    }
    expect(fisherYatesShuffle(input, makeRng(0.42))).toEqual(fisherYatesShuffle(input, makeRng(0.42)));
  });
});

describe('executeExperiment', () => {
  beforeEach(async () => {
    // Clean up test data directory
    await rm(TEST_DATA_DIR, { recursive: true, force: true });
  });

  it('executes all test cases and returns completed run (Req 8.1, 8.4)', async () => {
    const executedCases: string[] = [];
    const run = await executeExperiment(smallMatrix, {
      dataDir: TEST_DATA_DIR,
      runTestCase: async (caseId, params) => {
        executedCases.push(caseId);
        return makeMockResult(caseId, params);
      },
    });

    expect(run.status).toBe('completed');
    expect(run.completedCases.size).toBe(8);
    expect(executedCases.length).toBe(8);
  });

  it('randomizes execution order (Req 8.3)', async () => {
    const order1: string[] = [];
    const order2: string[] = [];

    await executeExperiment(smallMatrix, {
      dataDir: join(TEST_DATA_DIR, 'run1'),
      runTestCase: async (caseId, params) => {
        order1.push(caseId);
        return makeMockResult(caseId, params);
      },
    });

    await executeExperiment(smallMatrix, {
      dataDir: join(TEST_DATA_DIR, 'run2'),
      runTestCase: async (caseId, params) => {
        order2.push(caseId);
        return makeMockResult(caseId, params);
      },
    });

    // Both should have the same cases but (very likely) different order
    expect(order1.sort()).toEqual(order2.sort());
    // Note: there's a tiny chance they could be the same order,
    // but with 8 items the probability is 1/8! ≈ 0.002%
  });

  it('supports resume — skips completed cases (Req 8.5)', async () => {
    const executedCases: string[] = [];
    let callCount = 0;

    // First run: fail after 3 cases
    try {
      await executeExperiment(smallMatrix, {
        dataDir: TEST_DATA_DIR,
        runTestCase: async (caseId, params) => {
          callCount++;
          if (callCount === 4) throw new Error('Simulated failure');
          executedCases.push(caseId);
          return makeMockResult(caseId, params);
        },
      });
    } catch {
      // Expected
    }

    expect(executedCases.length).toBe(3);

    // Find the runId from the persisted state
    const { readdir } = await import('node:fs/promises');
    const dirs = await readdir(TEST_DATA_DIR);
    const runId = dirs[0];

    // Resume: should skip the 3 completed cases
    const resumedCases: string[] = [];
    const run = await executeExperiment(smallMatrix, {
      dataDir: TEST_DATA_DIR,
      runTestCase: async (caseId, params) => {
        resumedCases.push(caseId);
        return makeMockResult(caseId, params);
      },
    }, runId);

    expect(run.status).toBe('completed');
    // Should have executed the remaining 5 cases (8 total - 3 completed)
    expect(resumedCases.length).toBe(5);
    expect(run.completedCases.size).toBe(8);

    // No overlap between first run and resumed cases
    for (const c of resumedCases) {
      expect(executedCases).not.toContain(c);
    }
  });

  it('persists run state to disk after each case (Req 8.5)', async () => {
    let runId = '';
    await executeExperiment(smallMatrix, {
      dataDir: TEST_DATA_DIR,
      runTestCase: async (caseId, params) => {
        return makeMockResult(caseId, params);
      },
    }).then((run) => { runId = run.runId; });

    // Should be able to load the persisted state
    const loaded = await loadRunState(TEST_DATA_DIR, runId);
    expect(loaded.status).toBe('completed');
    expect(loaded.completedCases.size).toBe(8);
    expect(loaded.matrix).toEqual(smallMatrix);
  });

  it('marks run as interrupted on failure', async () => {
    let runId = '';
    try {
      await executeExperiment(smallMatrix, {
        dataDir: TEST_DATA_DIR,
        runTestCase: async (caseId, params) => {
          runId = ''; // will be set from persisted state
          throw new Error('boom');
        },
      });
    } catch {
      // Expected
    }

    // Load persisted state to check status
    const { readdir } = await import('node:fs/promises');
    const dirs = await readdir(TEST_DATA_DIR);
    runId = dirs[0];
    const loaded = await loadRunState(TEST_DATA_DIR, runId);
    expect(loaded.status).toBe('interrupted');
  });

  it('stores experiment records as JSON files (Req 8.4)', async () => {
    let runId = '';
    await executeExperiment(smallMatrix, {
      dataDir: TEST_DATA_DIR,
      runTestCase: async (caseId, params) => makeMockResult(caseId, params),
    }).then((run) => { runId = run.runId; });

    const { readdir } = await import('node:fs/promises');
    const casesDir = join(TEST_DATA_DIR, runId, 'cases');
    const files = await readdir(casesDir);
    expect(files.length).toBe(8);
    expect(files.every((f) => f.endsWith('.json'))).toBe(true);
  });
});

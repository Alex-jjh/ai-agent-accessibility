// Unit tests for Concurrent Execution with Browser Context Isolation
// Requirements: 19.2, 19.3, 19.4

import { describe, it, expect, vi } from 'vitest';
import {
  Semaphore,
  captureResourceSnapshot,
  executeConcurrently,
} from './concurrency.js';
import type {
  ConcurrencyConfig,
  BrowserContextFactory,
} from './concurrency.js';
import type { TestCaseParams, TestCaseResult } from './scheduler.js';
import type { AgentConfig, ActionTrace } from './types.js';
import type { ScanResult } from '../scanner/types.js';

// --- Test fixtures ---

const testConfig: AgentConfig = {
  observationMode: 'text-only',
  llmBackend: 'gpt-4o',
  maxSteps: 30,
  retryCount: 3,
  retryBackoffMs: 1000,
  temperature: 0,
};

function makeParams(taskId: string): TestCaseParams {
  return {
    app: 'reddit',
    variant: 'base',
    taskId,
    agentConfig: testConfig,
    attempt: 1,
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


function makeMockResult(taskId: string): TestCaseResult {
  const trace: ActionTrace = {
    taskId,
    variant: 'base',
    agentConfig: testConfig,
    attempt: 1,
    success: true,
    steps: [],
    totalSteps: 0,
    totalTokens: 100,
    durationMs: 500,
  };
  return {
    trace,
    taskOutcome: {
      taskId,
      outcome: 'success',
      traces: [trace],
      medianSteps: 0,
      medianDurationMs: 500,
      scanResults: makeMockScanResult(),
    },
    scanResults: makeMockScanResult(),
  };
}

/** Creates a mock browser context factory that tracks create/cleanup calls */
function createMockContextFactory() {
  const created: string[] = [];
  const cleaned: string[] = [];
  let callIndex = 0;

  const factory: BrowserContextFactory = async () => {
    const id = `ctx-${callIndex++}`;
    created.push(id);
    return {
      cleanup: async () => {
        cleaned.push(id);
      },
    };
  };

  return { factory, created, cleaned };
}

// --- Semaphore tests ---

describe('Semaphore', () => {
  it('allows up to max concurrent acquisitions', async () => {
    const sem = new Semaphore(3);
    await sem.acquire();
    await sem.acquire();
    await sem.acquire();
    expect(sem.activeCount).toBe(3);
    expect(sem.waitingCount).toBe(0);
  });

  it('blocks when max is reached and unblocks on release', async () => {
    const sem = new Semaphore(1);
    await sem.acquire();

    let acquired = false;
    const pending = sem.acquire().then(() => { acquired = true; });

    // Should not have acquired yet
    await Promise.resolve();
    expect(acquired).toBe(false);
    expect(sem.waitingCount).toBe(1);

    sem.release();
    await pending;
    expect(acquired).toBe(true);
    expect(sem.activeCount).toBe(1);
  });

  it('throws on max < 1', () => {
    expect(() => new Semaphore(0)).toThrow('Semaphore max must be at least 1');
    expect(() => new Semaphore(-1)).toThrow('Semaphore max must be at least 1');
  });

  it('processes waiters in FIFO order', async () => {
    const sem = new Semaphore(1);
    await sem.acquire();

    const order: number[] = [];
    const p1 = sem.acquire().then(() => { order.push(1); });
    const p2 = sem.acquire().then(() => { order.push(2); });
    const p3 = sem.acquire().then(() => { order.push(3); });

    sem.release();
    await p1;
    sem.release();
    await p2;
    sem.release();
    await p3;

    expect(order).toEqual([1, 2, 3]);
  });
});

// --- captureResourceSnapshot tests ---

describe('captureResourceSnapshot', () => {
  it('returns a valid resource snapshot with memory and CPU data (Req 19.4)', () => {
    const snapshot = captureResourceSnapshot(2);
    expect(snapshot.timestamp).toBeTruthy();
    expect(snapshot.activeTasks).toBe(2);
    expect(snapshot.memoryMB.rss).toBeGreaterThan(0);
    expect(snapshot.memoryMB.heapUsed).toBeGreaterThan(0);
    expect(snapshot.memoryMB.heapTotal).toBeGreaterThan(0);
    expect(typeof snapshot.cpuUser).toBe('number');
    expect(typeof snapshot.cpuSystem).toBe('number');
  });

  it('accepts previous CPU usage for delta computation', () => {
    const prev = process.cpuUsage();
    const snapshot = captureResourceSnapshot(0, prev);
    expect(snapshot.cpuUser).toBeGreaterThanOrEqual(0);
    expect(snapshot.cpuSystem).toBeGreaterThanOrEqual(0);
  });
});

// --- executeConcurrently tests ---

describe('executeConcurrently', () => {
  it('executes all test cases and returns results (Req 19.2)', async () => {
    const { factory } = createMockContextFactory();
    const entries: Array<[string, TestCaseParams]> = [
      ['case-1', makeParams('t1')],
      ['case-2', makeParams('t2')],
      ['case-3', makeParams('t3')],
    ];

    const result = await executeConcurrently(
      entries,
      async (caseId) => makeMockResult(caseId),
      factory,
      { maxConcurrency: 3, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    expect(result.results.size).toBe(3);
    expect(result.errors.size).toBe(0);
    expect(result.results.has('case-1')).toBe(true);
    expect(result.results.has('case-2')).toBe(true);
    expect(result.results.has('case-3')).toBe(true);
    expect(result.totalDurationMs).toBeGreaterThanOrEqual(0);
  });

  it('respects concurrency limit (Req 19.2)', async () => {
    const { factory } = createMockContextFactory();
    let maxConcurrent = 0;
    let currentConcurrent = 0;

    const entries: Array<[string, TestCaseParams]> = Array.from(
      { length: 6 },
      (_, i) => [`case-${i}`, makeParams(`t${i}`)] as [string, TestCaseParams],
    );

    await executeConcurrently(
      entries,
      async (caseId) => {
        currentConcurrent++;
        maxConcurrent = Math.max(maxConcurrent, currentConcurrent);
        // Simulate some async work
        await new Promise((r) => setTimeout(r, 50));
        currentConcurrent--;
        return makeMockResult(caseId);
      },
      factory,
      { maxConcurrency: 2, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    expect(maxConcurrent).toBeLessThanOrEqual(2);
  });

  it('creates isolated browser context per test case (Req 19.3)', async () => {
    const { factory, created, cleaned } = createMockContextFactory();
    const entries: Array<[string, TestCaseParams]> = [
      ['case-1', makeParams('t1')],
      ['case-2', makeParams('t2')],
      ['case-3', makeParams('t3')],
    ];

    await executeConcurrently(
      entries,
      async (caseId) => makeMockResult(caseId),
      factory,
      { maxConcurrency: 3, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    // Each test case should get its own context
    expect(created.length).toBe(3);
    // All contexts should be cleaned up
    expect(cleaned.length).toBe(3);
  });

  it('cleans up context even when test case fails (Req 19.3)', async () => {
    const { factory, created, cleaned } = createMockContextFactory();
    const entries: Array<[string, TestCaseParams]> = [
      ['case-ok', makeParams('t1')],
      ['case-fail', makeParams('t2')],
    ];

    const result = await executeConcurrently(
      entries,
      async (caseId) => {
        if (caseId === 'case-fail') throw new Error('Simulated failure');
        return makeMockResult(caseId);
      },
      factory,
      { maxConcurrency: 2, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    expect(result.results.size).toBe(1);
    expect(result.errors.size).toBe(1);
    expect(result.errors.get('case-fail')?.message).toBe('Simulated failure');
    // Both contexts should still be cleaned up
    expect(created.length).toBe(2);
    expect(cleaned.length).toBe(2);
  });

  it('captures resource snapshots including initial and final (Req 19.4)', async () => {
    const { factory } = createMockContextFactory();
    const entries: Array<[string, TestCaseParams]> = [
      ['case-1', makeParams('t1')],
    ];

    const result = await executeConcurrently(
      entries,
      async (caseId) => makeMockResult(caseId),
      factory,
      { maxConcurrency: 1, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    // At minimum: initial + final snapshots
    expect(result.resourceSnapshots.length).toBeGreaterThanOrEqual(2);
    // First snapshot should have 0 active tasks (initial)
    expect(result.resourceSnapshots[0].activeTasks).toBe(0);
    // Last snapshot should have 0 active tasks (final)
    expect(result.resourceSnapshots[result.resourceSnapshots.length - 1].activeTasks).toBe(0);
  });

  it('logs resource utilization at configured intervals (Req 19.4)', async () => {
    const { factory } = createMockContextFactory();
    const logMessages: string[] = [];

    const entries: Array<[string, TestCaseParams]> = Array.from(
      { length: 3 },
      (_, i) => [`case-${i}`, makeParams(`t${i}`)] as [string, TestCaseParams],
    );

    await executeConcurrently(
      entries,
      async (caseId) => {
        // Each task takes ~120ms so the 50ms interval fires at least once
        await new Promise((r) => setTimeout(r, 120));
        return makeMockResult(caseId);
      },
      factory,
      { maxConcurrency: 1, resourceLogIntervalMs: 50 },
      (msg) => logMessages.push(msg),
    );

    // Should have logged at least one resource monitor message
    const monitorLogs = logMessages.filter((m) => m.includes('[Resource Monitor]'));
    expect(monitorLogs.length).toBeGreaterThanOrEqual(1);
    // Verify log format contains expected fields
    expect(monitorLogs[0]).toContain('active=');
    expect(monitorLogs[0]).toContain('mem=');
    expect(monitorLogs[0]).toContain('heap=');
  });

  it('handles empty input gracefully', async () => {
    const { factory, created } = createMockContextFactory();

    const result = await executeConcurrently(
      [],
      async (caseId) => makeMockResult(caseId),
      factory,
      { maxConcurrency: 3, resourceLogIntervalMs: 60_000 },
      () => {},
    );

    expect(result.results.size).toBe(0);
    expect(result.errors.size).toBe(0);
    expect(created.length).toBe(0);
  });

  it('uses default config values when not specified', async () => {
    const { factory } = createMockContextFactory();
    const entries: Array<[string, TestCaseParams]> = [
      ['case-1', makeParams('t1')],
    ];

    // Should not throw — uses defaults (maxConcurrency=3, resourceLogIntervalMs=10000)
    const result = await executeConcurrently(
      entries,
      async (caseId) => makeMockResult(caseId),
      factory,
      {},
      () => {},
    );

    expect(result.results.size).toBe(1);
  });
});

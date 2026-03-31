// Module 3: Agent Runner — Concurrent Execution with Browser Context Isolation
// Provides parallel test case execution with configurable concurrency limit,
// isolated browser contexts, and resource utilization logging.
// Requirements: 19.2, 19.3, 19.4

import type { TestCaseParams, TestCaseResult } from './scheduler.js';

/** Configuration for concurrent execution */
export interface ConcurrencyConfig {
  /** Maximum number of test cases to run in parallel (default 3) */
  maxConcurrency: number;
  /** Interval in ms for resource utilization logging (default 10000) */
  resourceLogIntervalMs: number;
}

/** Resource utilization snapshot */
export interface ResourceSnapshot {
  timestamp: string;
  memoryMB: {
    rss: number;
    heapUsed: number;
    heapTotal: number;
    external: number;
  };
  cpuUser: number;
  cpuSystem: number;
  activeTasks: number;
}

/** Result of a concurrent execution batch */
export interface ConcurrentExecutionResult {
  results: Map<string, TestCaseResult>;
  errors: Map<string, Error>;
  resourceSnapshots: ResourceSnapshot[];
  totalDurationMs: number;
}

/** Callback that runs a single test case */
export type RunTestCaseFn = (caseId: string, params: TestCaseParams) => Promise<TestCaseResult>;

/** Browser context factory — creates an isolated context and returns a cleanup function */
export type BrowserContextFactory = () => Promise<{ cleanup: () => Promise<void> }>;

const DEFAULT_CONFIG: ConcurrencyConfig = {
  maxConcurrency: 3,
  resourceLogIntervalMs: 10_000,
};

/**
 * Capture a resource utilization snapshot.
 * Logs memory via process.memoryUsage() and CPU via process.cpuUsage(). (Req 19.4)
 */
export function captureResourceSnapshot(
  activeTasks: number,
  previousCpuUsage?: NodeJS.CpuUsage,
): ResourceSnapshot {
  const mem = process.memoryUsage();
  const cpu = previousCpuUsage
    ? process.cpuUsage(previousCpuUsage)
    : process.cpuUsage();

  return {
    timestamp: new Date().toISOString(),
    memoryMB: {
      rss: Math.round((mem.rss / 1024 / 1024) * 100) / 100,
      heapUsed: Math.round((mem.heapUsed / 1024 / 1024) * 100) / 100,
      heapTotal: Math.round((mem.heapTotal / 1024 / 1024) * 100) / 100,
      external: Math.round((mem.external / 1024 / 1024) * 100) / 100,
    },
    cpuUser: cpu.user,
    cpuSystem: cpu.system,
    activeTasks,
  };
}


/**
 * Semaphore for limiting concurrency.
 * Implements a classic counting semaphore with acquire/release semantics.
 */
export class Semaphore {
  private current = 0;
  private readonly waitQueue: Array<() => void> = [];

  constructor(private readonly max: number) {
    if (max < 1) throw new Error('Semaphore max must be at least 1');
  }

  /** Acquire a slot. Resolves when a slot is available. */
  async acquire(): Promise<void> {
    if (this.current < this.max) {
      this.current++;
      return;
    }
    return new Promise<void>((resolve) => {
      this.waitQueue.push(() => {
        this.current++;
        resolve();
      });
    });
  }

  /** Release a slot, allowing the next waiter to proceed. */
  release(): void {
    this.current--;
    if (this.waitQueue.length > 0) {
      const next = this.waitQueue.shift()!;
      next();
    }
  }

  /** Current number of active slots */
  get activeCount(): number {
    return this.current;
  }

  /** Number of waiters in the queue */
  get waitingCount(): number {
    return this.waitQueue.length;
  }
}

/**
 * Execute test cases concurrently with browser context isolation and resource monitoring.
 *
 * - Limits parallelism via a semaphore (Req 19.2)
 * - Creates an isolated browser context per test case via the factory (Req 19.3)
 * - Logs resource utilization at configurable intervals (Req 19.4)
 *
 * @param caseEntries - Array of [caseId, params] tuples to execute
 * @param runTestCase - Callback that executes a single test case
 * @param contextFactory - Factory that creates isolated browser contexts
 * @param config - Concurrency and resource monitoring configuration
 * @param logger - Optional logger function (defaults to console.log)
 */
export async function executeConcurrently(
  caseEntries: Array<[string, TestCaseParams]>,
  runTestCase: RunTestCaseFn,
  contextFactory: BrowserContextFactory,
  config: Partial<ConcurrencyConfig> = {},
  logger: (message: string) => void = console.log,
): Promise<ConcurrentExecutionResult> {
  const cfg: ConcurrencyConfig = { ...DEFAULT_CONFIG, ...config };
  const semaphore = new Semaphore(cfg.maxConcurrency);
  const results = new Map<string, TestCaseResult>();
  const errors = new Map<string, Error>();
  const resourceSnapshots: ResourceSnapshot[] = [];
  const startTime = Date.now();
  let activeTasks = 0;
  let baseCpuUsage = process.cpuUsage();

  // Start resource monitoring interval (Req 19.4)
  const monitorInterval = setInterval(() => {
    const snapshot = captureResourceSnapshot(activeTasks, baseCpuUsage);
    resourceSnapshots.push(snapshot);
    baseCpuUsage = process.cpuUsage();
    logger(
      `[Resource Monitor] active=${snapshot.activeTasks} ` +
      `mem=${snapshot.memoryMB.rss}MB ` +
      `heap=${snapshot.memoryMB.heapUsed}/${snapshot.memoryMB.heapTotal}MB ` +
      `cpu_user=${snapshot.cpuUser}µs cpu_sys=${snapshot.cpuSystem}µs`,
    );
  }, cfg.resourceLogIntervalMs);

  // Capture initial snapshot
  resourceSnapshots.push(captureResourceSnapshot(0, baseCpuUsage));

  try {
    const tasks = caseEntries.map(async ([caseId, params]) => {
      await semaphore.acquire();
      activeTasks++;

      // Create isolated browser context (Req 19.3)
      let contextHandle: { cleanup: () => Promise<void> } | undefined;
      try {
        contextHandle = await contextFactory();
        const result = await runTestCase(caseId, params);
        results.set(caseId, result);
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        errors.set(caseId, error);
        logger(`[ConcurrentExecutor] Test case ${caseId} failed: ${error.message}`);
      } finally {
        // Clean up the isolated context
        if (contextHandle) {
          try {
            await contextHandle.cleanup();
          } catch (cleanupErr) {
            logger(`[ConcurrentExecutor] Context cleanup failed for ${caseId}: ${cleanupErr}`);
          }
        }
        activeTasks--;
        semaphore.release();
      }
    });

    await Promise.all(tasks);
  } finally {
    clearInterval(monitorInterval);
  }

  // Capture final snapshot
  resourceSnapshots.push(captureResourceSnapshot(0, baseCpuUsage));

  return {
    results,
    errors,
    resourceSnapshots,
    totalDurationMs: Date.now() - startTime,
  };
}

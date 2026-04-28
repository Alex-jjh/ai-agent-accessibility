// Module 3: Agent Runner — Experiment Matrix Scheduler
// Executes all combinations: apps × variants × tasks × repetitions
// with Fisher-Yates shuffle, resume support, and per-case persistence.
// Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

import { randomUUID } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import type {
  ExperimentMatrix,
  ExperimentRun,
  ActionTrace,
  TaskOutcome,
  AgentConfig,
} from './types.js';
import type { ScanResult } from '../scanner/types.js';

/** A single experiment record stored per test case */
export interface ExperimentRecord {
  caseId: string;
  app: string;
  variant: string;
  taskId: string;
  agentConfig: AgentConfig;
  attempt: number;
  trace: ActionTrace;
  taskOutcome: TaskOutcome;
  scanResults: ScanResult;
}

/** Options for controlling experiment execution */
export interface ExecuteExperimentOptions {
  /** Directory for persisting run state and records */
  dataDir: string;
  /** Callback invoked for each test case — performs the actual agent run + scan */
  runTestCase: (caseId: string, params: TestCaseParams) => Promise<TestCaseResult>;
  /** Optional callback fired after the run object is created but before execution starts.
   *  Useful for obtaining the runId in the caller's scope. */
  onRunCreated?: (runId: string) => void;
}

/** Parameters describing a single test case to execute */
export interface TestCaseParams {
  app: string;
  variant: string;
  taskId: string;
  agentConfig: AgentConfig;
  attempt: number;
  /** AMT individual-mode only: operator IDs for this case. */
  operatorIds?: string[];
}

/** Result returned by the runTestCase callback */
export interface TestCaseResult {
  trace: ActionTrace;
  taskOutcome: TaskOutcome;
  scanResults: ScanResult;
}

/** Persisted state for resume support */
interface PersistedRunState {
  runId: string;
  matrix: ExperimentMatrix;
  executionOrder: string[];
  completedCases: string[];
  startedAt: string;
  status: 'running' | 'completed' | 'interrupted';
}

/**
 * Generate all test case IDs from the experiment matrix.
 *
 * Composite-mode format: `{app}:{variant}:{taskId}:{configIndex}:{attempt}`
 * Individual-mode format: `{app}:individual:{taskId}:{configIndex}:{attempt}:{opId1+opId2+...}`
 *
 * The `+` separator in operator IDs is safe because operator IDs are
 * alphanumeric (L1..L13, ML1..ML3, H1..H8, H5a/b/c).
 * (Req 8.1)
 */
export function generateTestCases(matrix: ExperimentMatrix): string[] {
  const cases: string[] = [];

  // Composite variants (legacy)
  for (const app of matrix.apps) {
    const tasks = matrix.tasksPerApp[app] ?? [];
    for (const variant of matrix.variants) {
      for (const taskId of tasks) {
        for (let ci = 0; ci < matrix.agentConfigs.length; ci++) {
          for (let attempt = 1; attempt <= matrix.repetitions; attempt++) {
            cases.push(`${app}:${variant}:${taskId}:${ci}:${attempt}`);
          }
        }
      }
    }
  }

  // Individual variants (AMT Mode A / compositional study)
  if (matrix.individualVariants && matrix.individualVariants.length > 0) {
    for (const app of matrix.apps) {
      const tasks = matrix.tasksPerApp[app] ?? [];
      for (const opIds of matrix.individualVariants) {
        const opKey = opIds.join('+');
        for (const taskId of tasks) {
          for (let ci = 0; ci < matrix.agentConfigs.length; ci++) {
            for (let attempt = 1; attempt <= matrix.repetitions; attempt++) {
              cases.push(`${app}:individual:${taskId}:${ci}:${attempt}:${opKey}`);
            }
          }
        }
      }
    }
  }

  return cases;
}

/**
 * Parse a test case ID back into its component parameters.
 *
 * Composite format (5 parts): `{app}:{variant}:{taskId}:{ci}:{attempt}`
 * Individual format (6 parts): `{app}:individual:{taskId}:{ci}:{attempt}:{opIds}`
 */
export function parseTestCaseId(
  caseId: string,
  matrix: ExperimentMatrix,
): TestCaseParams {
  const parts = caseId.split(':');
  if (parts.length !== 5 && parts.length !== 6) {
    throw new Error(`Invalid test case ID format: ${caseId}`);
  }

  const [app, variant, taskId, configIndexStr, attemptStr] = parts;
  const configIndex = parseInt(configIndexStr, 10);
  const attempt = parseInt(attemptStr, 10);

  if (configIndex < 0 || configIndex >= matrix.agentConfigs.length) {
    throw new Error(`Invalid config index ${configIndex} in case ${caseId}`);
  }

  const params: TestCaseParams = {
    app,
    variant,
    taskId,
    agentConfig: matrix.agentConfigs[configIndex],
    attempt,
  };

  // Individual-mode: 6th part is operator IDs joined by '+'
  if (parts.length === 6 && variant === 'individual') {
    params.operatorIds = parts[5].split('+');
  }

  return params;
}

/**
 * Fisher-Yates shuffle for randomized execution order. (Req 8.3)
 * Accepts an optional random function for deterministic testing.
 */
export function fisherYatesShuffle<T>(
  array: T[],
  randomFn: () => number = Math.random,
): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(randomFn() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

/**
 * Persist the run state to disk for resume support. (Req 8.5)
 */
async function persistRunState(
  dataDir: string,
  run: ExperimentRun,
): Promise<void> {
  const statePath = join(dataDir, run.runId, 'run-state.json');
  await mkdir(dirname(statePath), { recursive: true });
  const state: PersistedRunState = {
    runId: run.runId,
    matrix: run.matrix,
    executionOrder: run.executionOrder,
    completedCases: [...run.completedCases],
    startedAt: run.startedAt,
    status: run.status,
  };
  await writeFile(statePath, JSON.stringify(state, null, 2));
}

/**
 * Persist a single experiment record to disk. (Req 8.4)
 */
async function persistRecord(
  dataDir: string,
  runId: string,
  record: ExperimentRecord,
): Promise<void> {
  const casesDir = join(dataDir, runId, 'cases');
  await mkdir(casesDir, { recursive: true });
  const safeCaseId = record.caseId.replace(/:/g, '_');
  const recordPath = join(casesDir, `${safeCaseId}.json`);
  await writeFile(recordPath, JSON.stringify(record, null, 2));
}

/**
 * Load a previously persisted run state for resume. (Req 8.5)
 */
export async function loadRunState(
  dataDir: string,
  runId: string,
): Promise<ExperimentRun> {
  const statePath = join(dataDir, runId, 'run-state.json');
  const raw = await readFile(statePath, 'utf-8');
  const state: PersistedRunState = JSON.parse(raw);
  return {
    runId: state.runId,
    matrix: state.matrix,
    executionOrder: state.executionOrder,
    completedCases: new Set(state.completedCases),
    startedAt: state.startedAt,
    status: state.status,
  };
}

/**
 * Execute the full experiment matrix.
 *
 * - Generates all test case combinations (Req 8.1)
 * - Applies configurable repetitions (Req 8.2)
 * - Randomizes execution order via Fisher-Yates (Req 8.3)
 * - Stores each record as JSON (Req 8.4)
 * - Supports resume from a previous interrupted run (Req 8.5)
 */
export async function executeExperiment(
  matrix: ExperimentMatrix,
  options: ExecuteExperimentOptions,
  resumeFrom?: string,
): Promise<ExperimentRun> {
  let run: ExperimentRun;

  if (resumeFrom) {
    run = await loadRunState(options.dataDir, resumeFrom);
    run.status = 'running';
  } else {
    const allCases = generateTestCases(matrix);
    const shuffled = fisherYatesShuffle(allCases);
    run = {
      runId: randomUUID(),
      matrix,
      executionOrder: shuffled,
      completedCases: new Set<string>(),
      startedAt: new Date().toISOString(),
      status: 'running',
    };
  }

  await persistRunState(options.dataDir, run);

  // Notify caller of the runId before execution starts
  options.onRunCreated?.(run.runId);

  for (const caseId of run.executionOrder) {
    // Skip already-completed cases (resume support, Req 8.5)
    if (run.completedCases.has(caseId)) continue;

    const params = parseTestCaseId(caseId, run.matrix);

    try {
      const result = await options.runTestCase(caseId, params);

      const record: ExperimentRecord = {
        caseId,
        app: params.app,
        variant: params.variant,
        taskId: params.taskId,
        agentConfig: params.agentConfig,
        attempt: params.attempt,
        trace: result.trace,
        taskOutcome: result.taskOutcome,
        scanResults: result.scanResults,
      };

      await persistRecord(options.dataDir, run.runId, record);
      // Mark complete BEFORE persisting state so crash recovery doesn't
      // re-execute a case whose record is already on disk. (Bug 3 fix)
      run.completedCases.add(caseId);
      await persistRunState(options.dataDir, run);
    } catch (err) {
      console.error(`[Scheduler] Test case ${caseId} failed:`, err);
      run.status = 'interrupted';
      await persistRunState(options.dataDir, run);
      throw err;
    }
  }

  run.status = 'completed';
  await persistRunState(options.dataDir, run);
  return run;
}

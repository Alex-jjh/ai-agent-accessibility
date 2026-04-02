// Module 3: Agent Runner — Action Trace Serialization/Deserialization
// Requirements: 17.1, 17.2, 17.3, 17.4

import type { ActionTrace, ActionTraceStep } from './types.js';

/**
 * Error thrown when Action Trace deserialization fails,
 * with location and nature of the parsing failure. (Req 17.4)
 */
export class ActionTraceParseError extends Error {
  constructor(
    public readonly location: string,
    public readonly nature: string,
  ) {
    super(`Action trace parse error at "${location}": ${nature}`);
    this.name = 'ActionTraceParseError';
  }
}

/**
 * Serialize an ActionTrace to JSON, preserving step order, timestamps,
 * observations, reasoning, actions, and results. (Req 17.1)
 */
export function serializeActionTrace(trace: ActionTrace): string {
  return JSON.stringify(trace);
}

/**
 * Deserialize a JSON string back into a structured ActionTrace object.
 * Returns a descriptive error on invalid JSON. (Req 17.2, 17.4)
 */
export function deserializeActionTrace(json: string): ActionTrace {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new ActionTraceParseError('root', `Invalid JSON: ${message}`);
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new ActionTraceParseError('root', 'Expected a JSON object');
  }

  const obj = parsed as Record<string, unknown>;

  // Validate required top-level fields
  validateString(obj, 'taskId');
  validateString(obj, 'variant');
  validateObject(obj, 'agentConfig');
  validateNumber(obj, 'attempt');
  validateBoolean(obj, 'success');
  validateNumber(obj, 'totalSteps');
  validateNumber(obj, 'totalTokens');
  validateNumber(obj, 'durationMs');

  // Validate outcome field (added for BUG-04+05 fix)
  if ('outcome' in obj) {
    const validOutcomes = ['success', 'partial_success', 'failure', 'timeout'];
    if (!validOutcomes.includes(obj.outcome as string)) {
      throw new ActionTraceParseError('outcome', `Expected one of ${validOutcomes.join(', ')}, got "${obj.outcome}"`);
    }
  }

  // Validate steps array
  if (!Array.isArray(obj.steps)) {
    throw new ActionTraceParseError('steps', `Expected array, got ${typeof obj.steps}`);
  }

  for (let i = 0; i < obj.steps.length; i++) {
    validateStep(obj.steps[i], i);
  }

  // Validate agentConfig structure
  validateAgentConfig(obj.agentConfig as Record<string, unknown>);

  return parsed as ActionTrace;
}

function validateString(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'string') {
    throw new ActionTraceParseError(field, `Expected string, got ${typeof obj[field]}`);
  }
}

function validateNumber(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'number') {
    throw new ActionTraceParseError(field, `Expected number, got ${typeof obj[field]}`);
  }
}

function validateBoolean(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'boolean') {
    throw new ActionTraceParseError(field, `Expected boolean, got ${typeof obj[field]}`);
  }
}

function validateObject(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'object' || obj[field] === null || Array.isArray(obj[field])) {
    throw new ActionTraceParseError(field, 'Expected an object');
  }
}

function validateStep(step: unknown, index: number): void {
  const prefix = `steps[${index}]`;
  if (typeof step !== 'object' || step === null || Array.isArray(step)) {
    throw new ActionTraceParseError(prefix, 'Expected an object');
  }
  const s = step as Record<string, unknown>;

  if (typeof s.stepNum !== 'number') {
    throw new ActionTraceParseError(`${prefix}.stepNum`, `Expected number, got ${typeof s.stepNum}`);
  }
  if (typeof s.timestamp !== 'string') {
    throw new ActionTraceParseError(`${prefix}.timestamp`, `Expected string, got ${typeof s.timestamp}`);
  }
  if (typeof s.observation !== 'string') {
    throw new ActionTraceParseError(`${prefix}.observation`, `Expected string, got ${typeof s.observation}`);
  }
  if (typeof s.reasoning !== 'string') {
    throw new ActionTraceParseError(`${prefix}.reasoning`, `Expected string, got ${typeof s.reasoning}`);
  }
  if (typeof s.action !== 'string') {
    throw new ActionTraceParseError(`${prefix}.action`, `Expected string, got ${typeof s.action}`);
  }
  const validResults = ['success', 'failure', 'error'];
  if (!validResults.includes(s.result as string)) {
    throw new ActionTraceParseError(`${prefix}.result`, `Expected one of ${validResults.join(', ')}, got "${s.result}"`);
  }
}

function validateAgentConfig(config: Record<string, unknown>): void {
  const prefix = 'agentConfig';
  if (typeof config.observationMode !== 'string') {
    throw new ActionTraceParseError(`${prefix}.observationMode`, `Expected string, got ${typeof config.observationMode}`);
  }
  if (typeof config.llmBackend !== 'string') {
    throw new ActionTraceParseError(`${prefix}.llmBackend`, `Expected string, got ${typeof config.llmBackend}`);
  }
  for (const numField of ['maxSteps', 'retryCount', 'retryBackoffMs', 'temperature']) {
    if (typeof config[numField] !== 'number') {
      throw new ActionTraceParseError(`${prefix}.${numField}`, `Expected number, got ${typeof config[numField]}`);
    }
  }
}

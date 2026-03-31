// Property-based test for Action Trace round-trip consistency
// Requirements: 17.1, 17.2, 17.3, 17.4

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  serializeActionTrace,
  deserializeActionTrace,
  ActionTraceParseError,
} from './serialization.js';
import type { ActionTrace, ActionTraceStep, AgentConfig } from './types.js';
import type { VariantLevel } from '../variants/types.js';

// --- Arbitraries ---

const arbObservationMode = fc.constantFrom('text-only' as const, 'vision' as const);
const arbLlmBackend = fc.constantFrom('claude-opus', 'gpt-4o');
const arbVariantLevel: fc.Arbitrary<VariantLevel> = fc.constantFrom(
  'low', 'medium-low', 'base', 'high',
);
const arbStepResult = fc.constantFrom('success' as const, 'failure' as const, 'error' as const);

const arbAgentConfig: fc.Arbitrary<AgentConfig> = fc.record({
  observationMode: arbObservationMode,
  llmBackend: arbLlmBackend,
  maxSteps: fc.integer({ min: 1, max: 100 }),
  retryCount: fc.integer({ min: 0, max: 10 }),
  retryBackoffMs: fc.integer({ min: 100, max: 10000 }),
  temperature: fc.double({ min: 0, max: 2, noNaN: true }),
});

const arbActionTraceStep: fc.Arbitrary<ActionTraceStep> = fc.record({
  stepNum: fc.integer({ min: 1, max: 100 }),
  timestamp: fc.integer({ min: 946684800000, max: 1893456000000 })
    .map((ts) => new Date(ts).toISOString()),
  observation: fc.string({ minLength: 1, maxLength: 200 }),
  reasoning: fc.string({ maxLength: 200 }),
  action: fc.string({ minLength: 1, maxLength: 100 }),
  result: arbStepResult,
  resultDetail: fc.option(fc.string({ maxLength: 100 }), { nil: undefined }),
});

const arbActionTrace: fc.Arbitrary<ActionTrace> = fc.record({
  taskId: fc.uuid(),
  variant: arbVariantLevel,
  agentConfig: arbAgentConfig,
  attempt: fc.integer({ min: 1, max: 10 }),
  success: fc.boolean(),
  steps: fc.array(arbActionTraceStep, { minLength: 0, maxLength: 5 }),
  totalSteps: fc.integer({ min: 0, max: 100 }),
  totalTokens: fc.integer({ min: 0, max: 500000 }),
  durationMs: fc.integer({ min: 0, max: 600000 }),
  failureType: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
  failureConfidence: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
});

// --- Tests ---

describe('serializeActionTrace / deserializeActionTrace', () => {
  // Property: round-trip produces equivalent object (Req 17.3)
  it('serialize → deserialize produces equivalent ActionTrace for all valid inputs', () => {
    fc.assert(
      fc.property(arbActionTrace, (trace) => {
        const json = serializeActionTrace(trace);
        const deserialized = deserializeActionTrace(json);
        expect(deserialized).toEqual(trace);
      }),
      { numRuns: 200 },
    );
  });

  // Property: serialization always produces valid JSON
  it('serializeActionTrace always produces parseable JSON', () => {
    fc.assert(
      fc.property(arbActionTrace, (trace) => {
        const json = serializeActionTrace(trace);
        expect(() => JSON.parse(json)).not.toThrow();
      }),
      { numRuns: 200 },
    );
  });

  // Property: step order is preserved (Req 17.1)
  it('deserialized trace preserves step order', () => {
    fc.assert(
      fc.property(arbActionTrace, (trace) => {
        const json = serializeActionTrace(trace);
        const deserialized = deserializeActionTrace(json);
        expect(deserialized.steps.length).toBe(trace.steps.length);
        for (let i = 0; i < trace.steps.length; i++) {
          expect(deserialized.steps[i].stepNum).toBe(trace.steps[i].stepNum);
          expect(deserialized.steps[i].timestamp).toBe(trace.steps[i].timestamp);
          expect(deserialized.steps[i].action).toBe(trace.steps[i].action);
        }
      }),
      { numRuns: 100 },
    );
  });

  // Property: identity fields preserved
  it('deserialized trace preserves taskId, variant, and attempt', () => {
    fc.assert(
      fc.property(arbActionTrace, (trace) => {
        const json = serializeActionTrace(trace);
        const deserialized = deserializeActionTrace(json);
        expect(deserialized.taskId).toBe(trace.taskId);
        expect(deserialized.variant).toBe(trace.variant);
        expect(deserialized.attempt).toBe(trace.attempt);
      }),
      { numRuns: 100 },
    );
  });
});

describe('deserializeActionTrace — error handling (Req 17.4)', () => {
  it('throws ActionTraceParseError on invalid JSON', () => {
    expect(() => deserializeActionTrace('not json')).toThrow(ActionTraceParseError);
    expect(() => deserializeActionTrace('not json')).toThrow(/Invalid JSON/);
  });

  it('throws ActionTraceParseError when root is not an object', () => {
    expect(() => deserializeActionTrace('"a string"')).toThrow(ActionTraceParseError);
    expect(() => deserializeActionTrace('[]')).toThrow(ActionTraceParseError);
    expect(() => deserializeActionTrace('42')).toThrow(ActionTraceParseError);
  });

  it('throws with location for missing taskId', () => {
    const bad = JSON.stringify({ variant: 'low' });
    try {
      deserializeActionTrace(bad);
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ActionTraceParseError);
      expect((err as ActionTraceParseError).location).toBe('taskId');
    }
  });

  it('throws with location for invalid steps', () => {
    const bad = JSON.stringify({
      taskId: 't1', variant: 'low',
      agentConfig: {
        observationMode: 'text-only', llmBackend: 'gpt-4o',
        maxSteps: 30, retryCount: 3, retryBackoffMs: 1000, temperature: 0,
      },
      attempt: 1, success: false, steps: 'not-an-array',
      totalSteps: 0, totalTokens: 0, durationMs: 0,
    });
    try {
      deserializeActionTrace(bad);
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ActionTraceParseError);
      expect((err as ActionTraceParseError).location).toBe('steps');
    }
  });

  it('throws with location for invalid step entry', () => {
    const bad = JSON.stringify({
      taskId: 't1', variant: 'low',
      agentConfig: {
        observationMode: 'text-only', llmBackend: 'gpt-4o',
        maxSteps: 30, retryCount: 3, retryBackoffMs: 1000, temperature: 0,
      },
      attempt: 1, success: false,
      steps: [{ stepNum: 'not-a-number' }],
      totalSteps: 0, totalTokens: 0, durationMs: 0,
    });
    try {
      deserializeActionTrace(bad);
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ActionTraceParseError);
      expect((err as ActionTraceParseError).location).toContain('steps[0]');
    }
  });

  it('throws with location for invalid agentConfig field', () => {
    const bad = JSON.stringify({
      taskId: 't1', variant: 'low',
      agentConfig: {
        observationMode: 123, llmBackend: 'gpt-4o',
        maxSteps: 30, retryCount: 3, retryBackoffMs: 1000, temperature: 0,
      },
      attempt: 1, success: false, steps: [],
      totalSteps: 0, totalTokens: 0, durationMs: 0,
    });
    try {
      deserializeActionTrace(bad);
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ActionTraceParseError);
      expect((err as ActionTraceParseError).location).toContain('agentConfig');
    }
  });
});

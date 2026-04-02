import { describe, it, expect } from 'vitest';
import { classifyFailure, filterByReportingMode } from './classify.js';
import type { ActionTrace, ActionTraceStep } from '../../runner/types.js';
import type { FailureClassification } from '../types.js';

/** Helper to build a minimal ActionTrace with given steps */
function makeTrace(
  steps: Partial<ActionTraceStep>[],
  overrides?: Partial<ActionTrace>,
): ActionTrace {
  return {
    taskId: 'test-task',
    variant: 'base',
    agentConfig: {
      observationMode: 'text-only',
      llmBackend: 'gpt-4o',
      maxSteps: 30,
      retryCount: 3,
      retryBackoffMs: 1000,
      temperature: 0,
    },
    attempt: 1,
    success: false,
    outcome: 'failure' as const,
    steps: steps.map((s, i) => ({
      stepNum: i + 1,
      timestamp: new Date().toISOString(),
      observation: s.observation ?? 'some observation',
      reasoning: s.reasoning ?? 'some reasoning',
      action: s.action ?? 'click(element=\'btn\')',
      result: s.result ?? 'failure',
      resultDetail: s.resultDetail,
    })),
    totalSteps: steps.length,
    totalTokens: overrides?.totalTokens ?? 1000,
    durationMs: overrides?.durationMs ?? 5000,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// F_ENF: Element not found (≥3 consecutive failed selectors)
// ---------------------------------------------------------------------------
describe('F_ENF detection', () => {
  it('detects ≥3 consecutive failed selectors', () => {
    const trace = makeTrace([
      { result: 'failure', action: 'click(element=\'Submit\')' },
      { result: 'failure', action: 'click(element=\'Submit btn\')' },
      { result: 'failure', action: 'click(element=\'Submit button\')' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_ENF');
    expect(result.primaryDomain).toBe('accessibility');
  });

  it('does not trigger with only 2 consecutive failures', () => {
    const trace = makeTrace([
      { result: 'failure' },
      { result: 'failure' },
      { result: 'success' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).not.toBe('F_ENF');
  });
});

// ---------------------------------------------------------------------------
// F_WEA: Wrong element actuation
// ---------------------------------------------------------------------------
describe('F_WEA detection', () => {
  it('detects wrong element actuation from resultDetail', () => {
    const trace = makeTrace([
      {
        result: 'success',
        resultDetail: 'clicked wrong element — unexpected target',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_WEA');
    expect(result.primaryDomain).toBe('accessibility');
  });
});

// ---------------------------------------------------------------------------
// F_KBT: Keyboard trap
// ---------------------------------------------------------------------------
describe('F_KBT detection', () => {
  it('detects keyboard trap from repeated tab with same observation', () => {
    const obs = 'focus: element#input1';
    const trace = makeTrace([
      { action: 'press(key=Tab)', observation: obs, result: 'success' },
      { action: 'press(key=Tab)', observation: obs, result: 'success' },
      { action: 'press(key=Tab)', observation: obs, result: 'success' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_KBT');
    expect(result.primaryDomain).toBe('accessibility');
  });

  it('does not trigger when observations differ', () => {
    const trace = makeTrace([
      { action: 'press(key=Tab)', observation: 'focus: el1', result: 'success' },
      { action: 'press(key=Tab)', observation: 'focus: el2', result: 'success' },
      { action: 'press(key=Tab)', observation: 'focus: el3', result: 'success' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).not.toBe('F_KBT');
  });
});

// ---------------------------------------------------------------------------
// F_PCT: Pseudo-compliance trap
// ---------------------------------------------------------------------------
describe('F_PCT detection', () => {
  it('detects pseudo-compliance from role-without-handler pattern', () => {
    const trace = makeTrace([
      {
        result: 'failure',
        resultDetail: 'element has role="button" but not interactive — no handler',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_PCT');
    expect(result.primaryDomain).toBe('accessibility');
  });
});

// ---------------------------------------------------------------------------
// F_SDI: Shadow DOM invisible
// ---------------------------------------------------------------------------
describe('F_SDI detection', () => {
  it('detects shadow DOM invisibility', () => {
    const trace = makeTrace([
      {
        result: 'failure',
        resultDetail: 'element inside shadow DOM — not in a11y tree',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_SDI');
    expect(result.primaryDomain).toBe('accessibility');
  });
});

// ---------------------------------------------------------------------------
// F_HAL: Hallucination
// ---------------------------------------------------------------------------
describe('F_HAL detection', () => {
  it('detects hallucination when action target not in observation', () => {
    const trace = makeTrace([
      {
        action: 'click("999")',
        observation: '[1] button "Save"\n[2] button "Cancel"\n[3] button "Help"',
        result: 'failure',
        resultDetail: 'element not found',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_HAL');
    expect(result.primaryDomain).toBe('model');
  });
});

// ---------------------------------------------------------------------------
// F_COF: Context overflow
// ---------------------------------------------------------------------------
describe('F_COF detection', () => {
  it('detects context overflow when tokens exceed model limit', () => {
    const trace = makeTrace(
      [{ result: 'error', resultDetail: 'token limit exceeded' }],
      { totalTokens: 200_001 },
    );
    // llmBackend is 'gpt-4o' (128k limit) — 200k exceeds it
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_COF');
    expect(result.primaryDomain).toBe('model');
    expect(result.confidence).toBeGreaterThanOrEqual(0.9);
  });

  it('does not trigger when tokens are within limit', () => {
    const trace = makeTrace(
      [{ result: 'failure' }],
      { totalTokens: 50_000 },
    );
    const result = classifyFailure(trace);
    expect(result.primary).not.toBe('F_COF');
  });
});

// ---------------------------------------------------------------------------
// F_REA: Reasoning error
// ---------------------------------------------------------------------------
describe('F_REA detection', () => {
  it('detects reasoning contradicting observation', () => {
    const trace = makeTrace([
      {
        reasoning: 'I can see the submit button, this should work',
        result: 'failure',
      },
      {
        reasoning: 'I see the form is ready, should work now',
        result: 'failure',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_REA');
    expect(result.primaryDomain).toBe('model');
  });
});

// ---------------------------------------------------------------------------
// F_ABB: Anti-bot block
// ---------------------------------------------------------------------------
describe('F_ABB detection', () => {
  it('detects HTTP 403 in result details', () => {
    const trace = makeTrace([
      { result: 'failure', resultDetail: 'HTTP 403 Forbidden' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_ABB');
    expect(result.primaryDomain).toBe('environmental');
  });

  it('detects HTTP 429 rate limiting', () => {
    const trace = makeTrace([
      { result: 'failure', resultDetail: '429 Too Many Requests' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_ABB');
  });
});

// ---------------------------------------------------------------------------
// F_NET: Network timeout
// ---------------------------------------------------------------------------
describe('F_NET detection', () => {
  it('detects timeout errors', () => {
    const trace = makeTrace([
      { result: 'error', resultDetail: 'Navigation timeout of 30000ms exceeded' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_NET');
    expect(result.primaryDomain).toBe('environmental');
  });

  it('detects connection refused', () => {
    const trace = makeTrace([
      { result: 'error', resultDetail: 'ECONNREFUSED 127.0.0.1:3000' },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_NET');
  });
});

// ---------------------------------------------------------------------------
// F_AMB: Task ambiguity
// ---------------------------------------------------------------------------
describe('F_AMB detection', () => {
  it('detects agent asking for clarification', () => {
    const trace = makeTrace([
      {
        reasoning: "I'm not sure what the task means — it's unclear which form to fill",
        result: 'failure',
      },
    ]);
    const result = classifyFailure(trace);
    expect(result.primary).toBe('F_AMB');
    expect(result.primaryDomain).toBe('task');
  });
});

// ---------------------------------------------------------------------------
// Multi-domain classification
// ---------------------------------------------------------------------------
describe('multi-domain classification', () => {
  it('assigns primary and secondary factors when multiple patterns match', () => {
    const trace = makeTrace([
      // F_ENF pattern (3 consecutive failures)
      { result: 'failure', action: 'click(element=\'btn\')' },
      { result: 'failure', action: 'click(element=\'btn\')' },
      { result: 'failure', action: 'click(element=\'btn\')' },
      // F_ABB pattern
      { result: 'failure', resultDetail: 'HTTP 403 Forbidden' },
    ]);
    const result = classifyFailure(trace);
    // Both should be detected; highest confidence wins primary
    const allTypes = [result.primary, ...result.secondaryFactors];
    expect(allTypes).toContain('F_ENF');
    expect(allTypes).toContain('F_ABB');
    expect(result.secondaryFactors.length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Confidence and review flagging
// ---------------------------------------------------------------------------
describe('confidence and review flagging', () => {
  it('flags low-confidence classifications for review', () => {
    // A trace with no strong patterns → fallback low confidence
    const trace = makeTrace([
      { result: 'success', reasoning: 'all good' },
      { result: 'failure', reasoning: 'hmm' },
    ]);
    const result = classifyFailure(trace);
    if (result.confidence < 0.7) {
      expect(result.flaggedForReview).toBe(true);
    }
  });

  it('does not flag high-confidence classifications', () => {
    const trace = makeTrace([
      { result: 'error', resultDetail: 'ECONNREFUSED' },
    ]);
    const result = classifyFailure(trace);
    expect(result.confidence).toBeGreaterThanOrEqual(0.7);
    expect(result.flaggedForReview).toBe(false);
  });

  it('confidence is between 0 and 1', () => {
    const trace = makeTrace([
      { result: 'failure' },
      { result: 'failure' },
      { result: 'failure' },
      { result: 'failure' },
      { result: 'failure' },
    ]);
    const result = classifyFailure(trace);
    expect(result.confidence).toBeGreaterThanOrEqual(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Reporting modes
// ---------------------------------------------------------------------------
describe('filterByReportingMode', () => {
  const accessibilityClassification: FailureClassification = {
    primary: 'F_ENF',
    primaryDomain: 'accessibility',
    secondaryFactors: [],
    confidence: 0.9,
    flaggedForReview: false,
    evidence: ['test'],
  };

  const modelClassification: FailureClassification = {
    primary: 'F_HAL',
    primaryDomain: 'model',
    secondaryFactors: [],
    confidence: 0.85,
    flaggedForReview: false,
    evidence: ['test'],
  };

  const envClassification: FailureClassification = {
    primary: 'F_NET',
    primaryDomain: 'environmental',
    secondaryFactors: [],
    confidence: 0.9,
    flaggedForReview: false,
    evidence: ['test'],
  };

  const all = [accessibilityClassification, modelClassification, envClassification];

  it('inclusive mode returns all classifications', () => {
    const filtered = filterByReportingMode(all, 'inclusive');
    expect(filtered).toHaveLength(3);
  });

  it('conservative mode returns only accessibility-domain classifications', () => {
    const filtered = filterByReportingMode(all, 'conservative');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].primaryDomain).toBe('accessibility');
  });
});

// ---------------------------------------------------------------------------
// Fallback when no pattern matches
// ---------------------------------------------------------------------------
describe('fallback classification', () => {
  it('returns a low-confidence fallback when no patterns match', () => {
    const trace = makeTrace([
      { result: 'success', reasoning: 'everything is fine' },
    ]);
    const result = classifyFailure(trace);
    expect(result.confidence).toBeLessThan(0.7);
    expect(result.flaggedForReview).toBe(true);
  });
});

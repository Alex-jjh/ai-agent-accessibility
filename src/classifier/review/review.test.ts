import { describe, it, expect } from 'vitest';
import { selectForReview, computeCohensKappa } from './index.js';
import type { FailureClassification, ManualReview } from '../types.js';
import type { ActionTrace } from '../../runner/types.js';

function makeClassification(
  primary: FailureClassification['primary'],
  domain: FailureClassification['primaryDomain'],
): FailureClassification {
  return {
    primary,
    primaryDomain: domain,
    secondaryFactors: [],
    confidence: 0.9,
    flaggedForReview: false,
    evidence: ['test evidence'],
  };
}

function makeTrace(taskId: string, attempt: number): ActionTrace {
  return {
    taskId,
    variant: 'base',
    agentConfig: {
      observationMode: 'text-only',
      llmBackend: 'gpt-4o',
      maxSteps: 30,
      retryCount: 3,
      retryBackoffMs: 1000,
      temperature: 0,
    },
    attempt,
    success: false,
    outcome: 'failure',
    steps: [],
    totalSteps: 0,
    totalTokens: 100,
    durationMs: 1000,
  };
}

function makeManualReview(
  traceId: string,
  classification: ManualReview['reviewerClassification'],
  domain: ManualReview['reviewerDomain'],
): ManualReview {
  return {
    traceId,
    reviewerClassification: classification,
    reviewerDomain: domain,
    reviewerNotes: '',
    reviewedAt: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// selectForReview
// ---------------------------------------------------------------------------
describe('selectForReview', () => {
  it('selects approximately sampleRate fraction of items', () => {
    const items = Array.from({ length: 100 }, (_, i) => ({
      trace: makeTrace(`task-${i}`, 1),
      classification: makeClassification('F_ENF', 'accessibility'),
    }));
    const selected = selectForReview(items, 0.10);
    expect(selected.length).toBe(10);
  });

  it('selects at least 1 item even for small lists', () => {
    const items = [
      {
        trace: makeTrace('task-0', 1),
        classification: makeClassification('F_HAL', 'model'),
      },
    ];
    const selected = selectForReview(items, 0.10);
    expect(selected.length).toBeGreaterThanOrEqual(1);
  });

  it('returns ReviewItem with correct structure', () => {
    const items = [
      {
        trace: makeTrace('task-0', 1),
        classification: makeClassification('F_NET', 'environmental'),
      },
    ];
    const selected = selectForReview(items, 1.0);
    expect(selected[0]).toHaveProperty('traceId');
    expect(selected[0]).toHaveProperty('actionTrace');
    expect(selected[0]).toHaveProperty('autoClassification');
  });
});

// ---------------------------------------------------------------------------
// computeCohensKappa
// ---------------------------------------------------------------------------
describe('computeCohensKappa', () => {
  it('returns kappa = 1.0 for perfect agreement', () => {
    const auto = [
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_HAL', 'model'),
      makeClassification('F_NET', 'environmental'),
      makeClassification('F_AMB', 'task'),
    ];
    const manual = [
      makeManualReview('t1', 'F_ENF', 'accessibility'),
      makeManualReview('t2', 'F_HAL', 'model'),
      makeManualReview('t3', 'F_NET', 'environmental'),
      makeManualReview('t4', 'F_AMB', 'task'),
    ];
    const result = computeCohensKappa(auto, manual);
    expect(result.cohensKappa).toBe(1.0);
    expect(result.agreementRate).toBe(1.0);
    expect(result.sampleSize).toBe(4);
  });

  it('returns kappa ≈ 0 for random/no agreement beyond chance', () => {
    // Construct a case where auto and manual systematically disagree
    // but marginals are balanced so p_e is high
    const auto = [
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_HAL', 'model'),
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_HAL', 'model'),
    ];
    const manual = [
      makeManualReview('t1', 'F_HAL', 'model'),
      makeManualReview('t2', 'F_ENF', 'accessibility'),
      makeManualReview('t3', 'F_HAL', 'model'),
      makeManualReview('t4', 'F_ENF', 'accessibility'),
    ];
    const result = computeCohensKappa(auto, manual);
    // Complete disagreement with balanced marginals → kappa ≈ -1
    // The key point: kappa should be well below 0.5
    expect(result.cohensKappa).toBeLessThan(0.5);
    expect(result.agreementRate).toBe(0);
  });

  it('builds correct confusion matrix', () => {
    const auto = [
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_HAL', 'model'),
    ];
    const manual = [
      makeManualReview('t1', 'F_ENF', 'accessibility'),
      makeManualReview('t2', 'F_HAL', 'model'),
      makeManualReview('t3', 'F_HAL', 'model'),
    ];
    const result = computeCohensKappa(auto, manual);

    // F_ENF auto → F_ENF manual: 1
    expect(result.confusionMatrix['F_ENF']['F_ENF']).toBe(1);
    // F_ENF auto → F_HAL manual: 1
    expect(result.confusionMatrix['F_ENF']['F_HAL']).toBe(1);
    // F_HAL auto → F_HAL manual: 1
    expect(result.confusionMatrix['F_HAL']['F_HAL']).toBe(1);
    // Everything else should be 0
    expect(result.confusionMatrix['F_HAL']['F_ENF']).toBe(0);
    expect(result.confusionMatrix['F_NET']['F_NET']).toBe(0);
  });

  it('handles empty inputs gracefully', () => {
    const result = computeCohensKappa([], []);
    expect(result.cohensKappa).toBe(0);
    expect(result.agreementRate).toBe(0);
    expect(result.sampleSize).toBe(0);
  });

  it('handles partial overlap (different array lengths)', () => {
    const auto = [
      makeClassification('F_ENF', 'accessibility'),
      makeClassification('F_HAL', 'model'),
      makeClassification('F_NET', 'environmental'),
    ];
    const manual = [
      makeManualReview('t1', 'F_ENF', 'accessibility'),
      makeManualReview('t2', 'F_HAL', 'model'),
    ];
    const result = computeCohensKappa(auto, manual);
    // Should only compare first 2 pairs
    expect(result.sampleSize).toBe(2);
    expect(result.agreementRate).toBe(1.0);
    expect(result.cohensKappa).toBe(1.0);
  });
});

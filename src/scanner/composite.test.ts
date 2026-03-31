// Property-based test for Composite Score round-trip consistency
// Requirements: 4.1, 4.2, 4.3, 4.4, 16.3

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { computeCompositeScore } from './composite.js';
import type {
  Tier1Metrics,
  Tier2Metrics,
  CompositeScoreOptions,
  CompositeScoreResult,
  SensitivityMode,
} from './types.js';

// --- Arbitraries ---

const arbTier1Metrics: fc.Arbitrary<Tier1Metrics> = fc.record({
  url: fc.webUrl(),
  axeCore: fc.record({
    violationCount: fc.integer({ min: 0, max: 200 }),
    violationsByWcagCriterion: fc.constant({}),
    impactSeverity: fc.record({
      critical: fc.integer({ min: 0, max: 50 }),
      serious: fc.integer({ min: 0, max: 50 }),
      moderate: fc.integer({ min: 0, max: 50 }),
      minor: fc.integer({ min: 0, max: 50 }),
    }),
  }),
  lighthouse: fc.record({
    accessibilityScore: fc.integer({ min: 0, max: 100 }),
    audits: fc.constant({}),
  }),
  scannedAt: fc.integer({ min: 946684800000, max: 1893456000000 }).map((ts) => new Date(ts).toISOString()),
});

const arbTier2Metrics: fc.Arbitrary<Tier2Metrics> = fc.record({
  semanticHtmlRatio: fc.double({ min: 0, max: 1, noNaN: true }),
  accessibleNameCoverage: fc.double({ min: 0, max: 1, noNaN: true }),
  keyboardNavigability: fc.double({ min: 0, max: 1, noNaN: true }),
  ariaCorrectness: fc.double({ min: 0, max: 1, noNaN: true }),
  pseudoComplianceCount: fc.integer({ min: 0, max: 100 }),
  pseudoComplianceRatio: fc.double({ min: 0, max: 1, noNaN: true }),
  formLabelingCompleteness: fc.double({ min: 0, max: 1, noNaN: true }),
  landmarkCoverage: fc.double({ min: 0, max: 1, noNaN: true }),
  shadowDomIncluded: fc.boolean(),
});

const arbMode: fc.Arbitrary<SensitivityMode> = fc.constantFrom(
  'tier1-only', 'tier2-only', 'composite',
);

const arbWeights: fc.Arbitrary<Record<string, number>> = fc.record({
  lighthouseScore: fc.double({ min: 0, max: 10, noNaN: true }),
  axeViolations: fc.double({ min: 0, max: 10, noNaN: true }),
  semanticHtmlRatio: fc.double({ min: 0, max: 10, noNaN: true }),
  accessibleNameCoverage: fc.double({ min: 0, max: 10, noNaN: true }),
  keyboardNavigability: fc.double({ min: 0, max: 10, noNaN: true }),
  ariaCorrectness: fc.double({ min: 0, max: 10, noNaN: true }),
  pseudoComplianceRatio: fc.double({ min: 0, max: 10, noNaN: true }),
  formLabelingCompleteness: fc.double({ min: 0, max: 10, noNaN: true }),
  landmarkCoverage: fc.double({ min: 0, max: 10, noNaN: true }),
});

const arbOptions: fc.Arbitrary<CompositeScoreOptions> = fc.record({
  weights: arbWeights,
  mode: arbMode,
});

describe('computeCompositeScore', () => {
  // --- Property: Round-trip consistency (Req 16.3) ---
  it('serialize → deserialize produces equivalent CompositeScoreResult', () => {
    fc.assert(
      fc.property(arbTier1Metrics, arbTier2Metrics, arbOptions, (tier1, tier2, options) => {
        const result = computeCompositeScore(tier1, tier2, options);

        // Serialize to JSON and back
        const json = JSON.stringify(result);
        const deserialized: CompositeScoreResult = JSON.parse(json);

        // Round-trip must produce equivalent object
        expect(deserialized.compositeScore).toBeCloseTo(result.compositeScore, 10);
        expect(deserialized.mode).toBe(result.mode);
        expect(Object.keys(deserialized.weights)).toEqual(Object.keys(result.weights));
        expect(Object.keys(deserialized.normalizedComponents)).toEqual(
          Object.keys(result.normalizedComponents),
        );

        // Check each weight value
        for (const key of Object.keys(result.weights)) {
          expect(deserialized.weights[key]).toBeCloseTo(result.weights[key], 10);
        }

        // Check each normalized component
        for (const key of Object.keys(result.normalizedComponents)) {
          expect(deserialized.normalizedComponents[key]).toBeCloseTo(
            result.normalizedComponents[key], 10,
          );
        }
      }),
      { numRuns: 200 },
    );
  });

  // --- Property: Composite score is always in [0, 1] ---
  it('composite score is always between 0.0 and 1.0', () => {
    fc.assert(
      fc.property(arbTier1Metrics, arbTier2Metrics, arbOptions, (tier1, tier2, options) => {
        const result = computeCompositeScore(tier1, tier2, options);
        expect(result.compositeScore).toBeGreaterThanOrEqual(0);
        expect(result.compositeScore).toBeLessThanOrEqual(1);
      }),
      { numRuns: 200 },
    );
  });

  // --- Property: All normalized components are in [0, 1] ---
  it('all normalized components are between 0.0 and 1.0', () => {
    fc.assert(
      fc.property(arbTier1Metrics, arbTier2Metrics, arbOptions, (tier1, tier2, options) => {
        const result = computeCompositeScore(tier1, tier2, options);
        for (const [key, value] of Object.entries(result.normalizedComponents)) {
          expect(value).toBeGreaterThanOrEqual(0);
          expect(value).toBeLessThanOrEqual(1);
        }
      }),
      { numRuns: 200 },
    );
  });

  // --- Property: Mode determines which components affect the score ---
  it('tier1-only mode ignores tier2 metrics in score computation', () => {
    fc.assert(
      fc.property(arbTier1Metrics, arbTier2Metrics, arbTier2Metrics, arbWeights,
        (tier1, tier2a, tier2b, weights) => {
          const opts: CompositeScoreOptions = { weights, mode: 'tier1-only' };
          const resultA = computeCompositeScore(tier1, tier2a, opts);
          const resultB = computeCompositeScore(tier1, tier2b, opts);
          // Same tier1 + tier1-only mode → same composite score regardless of tier2
          expect(resultA.compositeScore).toBeCloseTo(resultB.compositeScore, 10);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('tier2-only mode ignores tier1 metrics in score computation', () => {
    fc.assert(
      fc.property(arbTier1Metrics, arbTier1Metrics, arbTier2Metrics, arbWeights,
        (tier1a, tier1b, tier2, weights) => {
          const opts: CompositeScoreOptions = { weights, mode: 'tier2-only' };
          const resultA = computeCompositeScore(tier1a, tier2, opts);
          const resultB = computeCompositeScore(tier1b, tier2, opts);
          // Same tier2 + tier2-only mode → same composite score regardless of tier1
          expect(resultA.compositeScore).toBeCloseTo(resultB.compositeScore, 10);
        },
      ),
      { numRuns: 100 },
    );
  });

  // --- Unit: deterministic output ---
  it('produces identical output for identical input', () => {
    const tier1: Tier1Metrics = {
      url: 'https://example.com',
      axeCore: { violationCount: 5, violationsByWcagCriterion: {}, impactSeverity: { critical: 1, serious: 2, moderate: 1, minor: 1 } },
      lighthouse: { accessibilityScore: 85, audits: {} },
      scannedAt: '2025-01-01T00:00:00Z',
    };
    const tier2: Tier2Metrics = {
      semanticHtmlRatio: 0.3, accessibleNameCoverage: 0.8, keyboardNavigability: 0.6,
      ariaCorrectness: 0.9, pseudoComplianceCount: 2, pseudoComplianceRatio: 0.1,
      formLabelingCompleteness: 0.7, landmarkCoverage: 0.5, shadowDomIncluded: true,
    };
    const opts: CompositeScoreOptions = {
      weights: { lighthouseScore: 1, axeViolations: 1, semanticHtmlRatio: 1 },
      mode: 'composite',
    };

    const a = computeCompositeScore(tier1, tier2, opts);
    const b = computeCompositeScore(tier1, tier2, opts);

    expect(a).toEqual(b);
  });
});

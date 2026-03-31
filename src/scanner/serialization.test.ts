// Property-based test for scan result round-trip consistency
// Requirements: 16.1, 16.2, 16.3, 16.4

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  serializeScanResult,
  deserializeScanResult,
  ScanResultParseError,
} from './serialization.js';
import type {
  ScanResult,
  Tier1Metrics,
  Tier2Metrics,
  CompositeScoreResult,
  SensitivityMode,
  AccessibilityTreeSnapshot,
} from './types.js';

// --- Arbitraries ---

const arbTier1Metrics: fc.Arbitrary<Tier1Metrics> = fc.record({
  url: fc.webUrl(),
  axeCore: fc.record({
    violationCount: fc.integer({ min: 0, max: 200 }),
    violationsByWcagCriterion: fc.dictionary(
      fc.stringMatching(/^[0-9]+\.[0-9]+\.[0-9]+$/),
      fc.array(
        fc.record({
          id: fc.string({ minLength: 1, maxLength: 30 }),
          impact: fc.constantFrom('critical', 'serious', 'moderate', 'minor') as fc.Arbitrary<'critical' | 'serious' | 'moderate' | 'minor'>,
          description: fc.string({ maxLength: 100 }),
          helpUrl: fc.option(fc.webUrl(), { nil: undefined }),
          nodes: fc.integer({ min: 0, max: 50 }),
        }),
        { minLength: 0, maxLength: 3 },
      ),
      { minKeys: 0, maxKeys: 5 },
    ),
    impactSeverity: fc.record({
      critical: fc.integer({ min: 0, max: 50 }),
      serious: fc.integer({ min: 0, max: 50 }),
      moderate: fc.integer({ min: 0, max: 50 }),
      minor: fc.integer({ min: 0, max: 50 }),
    }),
  }),
  lighthouse: fc.record({
    accessibilityScore: fc.integer({ min: 0, max: 100 }),
    audits: fc.dictionary(
      fc.string({ minLength: 1, maxLength: 20 }),
      fc.record({
        pass: fc.boolean(),
        details: fc.option(fc.string(), { nil: undefined }),
      }),
      { minKeys: 0, maxKeys: 5 },
    ),
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

const arbCompositeScore: fc.Arbitrary<CompositeScoreResult> = fc.record({
  compositeScore: fc.double({ min: 0, max: 1, noNaN: true }),
  normalizedComponents: fc.dictionary(
    fc.string({ minLength: 1, maxLength: 20 }),
    fc.double({ min: 0, max: 1, noNaN: true }),
    { minKeys: 1, maxKeys: 9 },
  ),
  mode: arbMode,
  weights: fc.dictionary(
    fc.string({ minLength: 1, maxLength: 20 }),
    fc.double({ min: 0, max: 10, noNaN: true }),
    { minKeys: 1, maxKeys: 9 },
  ),
});

const arbA11ySnapshot: fc.Arbitrary<AccessibilityTreeSnapshot> = fc.dictionary(
  fc.string({ minLength: 1, maxLength: 20 }),
  fc.oneof(fc.string(), fc.integer(), fc.boolean()),
  { minKeys: 0, maxKeys: 5 },
);

const arbScanResult: fc.Arbitrary<ScanResult> = fc.record({
  scanId: fc.uuid(),
  url: fc.webUrl(),
  scannedAt: fc.integer({ min: 946684800000, max: 1893456000000 }).map((ts) => new Date(ts).toISOString()),
  treeWasStable: fc.boolean(),
  stabilizationMs: fc.integer({ min: 0, max: 60000 }),
  tier1: arbTier1Metrics,
  tier2: arbTier2Metrics,
  compositeScore: fc.option(arbCompositeScore, { nil: null }),
  a11yTreeSnapshot: arbA11ySnapshot,
});

// --- Tests ---

describe('serializeScanResult / deserializeScanResult', () => {
  // Property: round-trip produces equivalent object (Req 16.3)
  it('serialize → deserialize produces equivalent ScanResult for all valid inputs', () => {
    fc.assert(
      fc.property(arbScanResult, (scanResult) => {
        const json = serializeScanResult(scanResult);
        const deserialized = deserializeScanResult(json);

        // Deep equality — JSON round-trip preserves all fields
        expect(deserialized).toEqual(scanResult);
      }),
      { numRuns: 200 },
    );
  });

  // Property: serialization always produces valid JSON
  it('serializeScanResult always produces parseable JSON', () => {
    fc.assert(
      fc.property(arbScanResult, (scanResult) => {
        const json = serializeScanResult(scanResult);
        expect(() => JSON.parse(json)).not.toThrow();
      }),
      { numRuns: 200 },
    );
  });

  // Property: deserialized result has all required fields
  it('deserialized result preserves scanId, url, and scannedAt', () => {
    fc.assert(
      fc.property(arbScanResult, (scanResult) => {
        const json = serializeScanResult(scanResult);
        const deserialized = deserializeScanResult(json);
        expect(deserialized.scanId).toBe(scanResult.scanId);
        expect(deserialized.url).toBe(scanResult.url);
        expect(deserialized.scannedAt).toBe(scanResult.scannedAt);
      }),
      { numRuns: 100 },
    );
  });
});

describe('deserializeScanResult — error handling (Req 16.4)', () => {
  it('throws ScanResultParseError on invalid JSON', () => {
    expect(() => deserializeScanResult('not json')).toThrow(ScanResultParseError);
    expect(() => deserializeScanResult('not json')).toThrow(/Invalid JSON/);
  });

  it('throws ScanResultParseError when root is not an object', () => {
    expect(() => deserializeScanResult('"a string"')).toThrow(ScanResultParseError);
    expect(() => deserializeScanResult('[]')).toThrow(ScanResultParseError);
    expect(() => deserializeScanResult('42')).toThrow(ScanResultParseError);
  });

  it('throws ScanResultParseError with field location for missing scanId', () => {
    const bad = JSON.stringify({ url: 'x', scannedAt: 'x' });
    try {
      deserializeScanResult(bad);
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ScanResultParseError);
      expect((err as ScanResultParseError).location).toBe('scanId');
    }
  });

  it('throws ScanResultParseError with field location for missing tier1', () => {
    const partial = {
      scanId: 'id', url: 'u', scannedAt: 's',
      treeWasStable: true, stabilizationMs: 0,
    };
    try {
      deserializeScanResult(JSON.stringify(partial));
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ScanResultParseError);
      expect((err as ScanResultParseError).location).toBe('tier1');
    }
  });

  it('throws ScanResultParseError with field location for invalid tier2 metric', () => {
    const partial = {
      scanId: 'id', url: 'u', scannedAt: 's',
      treeWasStable: true, stabilizationMs: 0,
      tier1: {
        url: 'u', scannedAt: 's',
        axeCore: { violationCount: 0, violationsByWcagCriterion: {}, impactSeverity: { critical: 0, serious: 0, moderate: 0, minor: 0 } },
        lighthouse: { accessibilityScore: 90, audits: {} },
      },
      tier2: { semanticHtmlRatio: 'not a number' },
      a11yTreeSnapshot: {},
    };
    try {
      deserializeScanResult(JSON.stringify(partial));
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ScanResultParseError);
      expect((err as ScanResultParseError).location).toContain('tier2');
    }
  });
});

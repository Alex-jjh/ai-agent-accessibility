// Tests for Variant Validator
// Requirements: 5.5, 5.6

import { describe, it, expect, vi } from 'vitest';
import { validateVariant, VARIANT_SCORE_RANGES } from './index.js';
import type { Scanner } from './index.js';
import type { VariantLevel } from '../types.js';
import type {
  Tier1Metrics,
  Tier2Metrics,
  CompositeScoreResult,
} from '../../scanner/types.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTier1(overrides?: Partial<Tier1Metrics>): Tier1Metrics {
  return {
    url: 'http://localhost:3000',
    axeCore: {
      violationCount: 5,
      violationsByWcagCriterion: {},
      impactSeverity: { critical: 0, serious: 1, moderate: 2, minor: 2 },
    },
    lighthouse: { accessibilityScore: 70, audits: {} },
    scannedAt: new Date().toISOString(),
    ...overrides,
  };
}

function makeTier2(overrides?: Partial<Tier2Metrics>): Tier2Metrics {
  return {
    semanticHtmlRatio: 0.5,
    accessibleNameCoverage: 0.6,
    keyboardNavigability: 0.7,
    ariaCorrectness: 0.8,
    pseudoComplianceCount: 2,
    pseudoComplianceRatio: 0.1,
    formLabelingCompleteness: 0.9,
    landmarkCoverage: 0.5,
    shadowDomIncluded: true,
    ...overrides,
  };
}

function makeCompositeResult(score: number): CompositeScoreResult {
  return {
    compositeScore: score,
    normalizedComponents: {},
    mode: 'composite',
    weights: {},
  };
}

/** Create a mock Scanner that returns a predetermined composite score. */
function createMockScanner(compositeScore: number): Scanner {
  const tier1 = makeTier1();
  const tier2 = makeTier2();
  return {
    scanTier1: vi.fn().mockResolvedValue(tier1),
    scanTier2: vi.fn().mockResolvedValue(tier2),
    computeCompositeScore: vi.fn().mockReturnValue(makeCompositeResult(compositeScore)),
  };
}

/** Create a minimal mock Playwright Page. */
function createMockPage(url = 'http://localhost:3000') {
  const mockCdpSession = { detach: vi.fn().mockResolvedValue(undefined) } as any;
  return {
    url: () => url,
    context: () => ({
      newCDPSession: vi.fn().mockResolvedValue(mockCdpSession),
    }),
  } as any;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('VARIANT_SCORE_RANGES', () => {
  it('defines ranges for all four variant levels', () => {
    const levels: VariantLevel[] = ['low', 'medium-low', 'base', 'high'];
    for (const level of levels) {
      expect(VARIANT_SCORE_RANGES[level]).toBeDefined();
      expect(VARIANT_SCORE_RANGES[level].min).toBeLessThanOrEqual(VARIANT_SCORE_RANGES[level].max);
    }
  });

  it('has correct expected ranges', () => {
    expect(VARIANT_SCORE_RANGES['low']).toEqual({ min: 0.0, max: 0.25 });
    expect(VARIANT_SCORE_RANGES['medium-low']).toEqual({ min: 0.25, max: 0.50 });
    expect(VARIANT_SCORE_RANGES['base']).toEqual({ min: 0.40, max: 0.70 });
    expect(VARIANT_SCORE_RANGES['high']).toEqual({ min: 0.75, max: 1.0 });
  });
});

describe('validateVariant', () => {
  it('returns inExpectedRange=true when score is within range for low variant', async () => {
    const scanner = createMockScanner(0.15);
    const page = createMockPage();

    const result = await validateVariant(page, 'low', scanner);

    expect(result.variantLevel).toBe('low');
    expect(result.inExpectedRange).toBe(true);
    expect(result.expectedRange).toEqual({ min: 0.0, max: 0.25 });
    expect(result.compositeScore.compositeScore).toBe(0.15);
  });

  it('returns inExpectedRange=true when score is within range for medium-low variant', async () => {
    const scanner = createMockScanner(0.35);
    const page = createMockPage();

    const result = await validateVariant(page, 'medium-low', scanner);

    expect(result.variantLevel).toBe('medium-low');
    expect(result.inExpectedRange).toBe(true);
    expect(result.expectedRange).toEqual({ min: 0.25, max: 0.50 });
  });

  it('returns inExpectedRange=true when score is within range for base variant', async () => {
    const scanner = createMockScanner(0.55);
    const page = createMockPage();

    const result = await validateVariant(page, 'base', scanner);

    expect(result.variantLevel).toBe('base');
    expect(result.inExpectedRange).toBe(true);
    expect(result.expectedRange).toEqual({ min: 0.40, max: 0.70 });
  });

  it('returns inExpectedRange=true when score is within range for high variant', async () => {
    const scanner = createMockScanner(0.90);
    const page = createMockPage();

    const result = await validateVariant(page, 'high', scanner);

    expect(result.variantLevel).toBe('high');
    expect(result.inExpectedRange).toBe(true);
    expect(result.expectedRange).toEqual({ min: 0.75, max: 1.0 });
  });

  it('returns inExpectedRange=false when score is below range', async () => {
    const scanner = createMockScanner(0.10); // below base range 0.40–0.70
    const page = createMockPage();

    const result = await validateVariant(page, 'base', scanner);

    expect(result.inExpectedRange).toBe(false);
  });

  it('returns inExpectedRange=false when score is above range', async () => {
    const scanner = createMockScanner(0.60); // above low range 0.0–0.25
    const page = createMockPage();

    const result = await validateVariant(page, 'low', scanner);

    expect(result.inExpectedRange).toBe(false);
  });

  it('returns inExpectedRange=true at exact boundary min', async () => {
    const scanner = createMockScanner(0.25); // exact min of medium-low
    const page = createMockPage();

    const result = await validateVariant(page, 'medium-low', scanner);

    expect(result.inExpectedRange).toBe(true);
  });

  it('returns inExpectedRange=true at exact boundary max', async () => {
    const scanner = createMockScanner(0.70); // exact max of base
    const page = createMockPage();

    const result = await validateVariant(page, 'base', scanner);

    expect(result.inExpectedRange).toBe(true);
  });

  it('calls scanner.scanTier1 with correct options', async () => {
    const scanner = createMockScanner(0.50);
    const page = createMockPage('http://reddit.local:8080');

    await validateVariant(page, 'base', scanner);

    expect(scanner.scanTier1).toHaveBeenCalledWith(page, {
      url: 'http://reddit.local:8080',
      wcagLevels: ['A', 'AA'],
    });
  });

  it('calls scanner.scanTier2 with page and CDP session', async () => {
    const scanner = createMockScanner(0.50);
    const page = createMockPage();

    await validateVariant(page, 'base', scanner);

    expect(scanner.scanTier2).toHaveBeenCalledTimes(1);
    expect(scanner.scanTier2).toHaveBeenCalledWith(page, expect.anything());
  });

  it('calls scanner.computeCompositeScore in composite mode', async () => {
    const scanner = createMockScanner(0.50);
    const page = createMockPage();

    await validateVariant(page, 'base', scanner);

    expect(scanner.computeCompositeScore).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ mode: 'composite' }),
    );
  });

  it('works for all 4 WebArena app URLs', async () => {
    const appUrls = [
      'http://reddit.local:8080',
      'http://gitlab.local:8081',
      'http://cms.local:8082',
      'http://ecommerce.local:8083',
    ];

    for (const url of appUrls) {
      const scanner = createMockScanner(0.55);
      const page = createMockPage(url);

      const result = await validateVariant(page, 'base', scanner);

      expect(result.inExpectedRange).toBe(true);
      expect(scanner.scanTier1).toHaveBeenCalledWith(
        page,
        expect.objectContaining({ url }),
      );
    }
  });
});

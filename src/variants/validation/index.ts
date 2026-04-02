// Module 2: Variant Generator — Variant Validator
// Requirements: 5.5, 5.6
//
// Validates that a variant's composite accessibility score falls within
// the expected range for its variant level. Applies to all 4 WebArena
// apps (Reddit, GitLab, CMS, E-commerce).

import type { Page, CDPSession } from 'playwright';
import type { VariantLevel, VariantValidationResult } from '../types.js';
import type {
  Tier1Metrics,
  Tier1ScanOptions,
  Tier2Metrics,
  CompositeScoreOptions,
  CompositeScoreResult,
} from '../../scanner/types.js';

/**
 * Minimal scanner interface required by the variant validator.
 * Accepts an object providing Tier 1 scan, Tier 2 scan, and composite
 * score computation — decoupled from the concrete scanner module.
 */
export interface Scanner {
  scanTier1(page: Page, options: Tier1ScanOptions): Promise<Tier1Metrics>;
  scanTier2(page: Page, cdpSession: CDPSession): Promise<Tier2Metrics>;
  computeCompositeScore(
    tier1: Tier1Metrics,
    tier2: Tier2Metrics,
    options: CompositeScoreOptions,
  ): CompositeScoreResult;
}

/**
 * Expected composite score ranges per variant level (Req 5.5, 5.6).
 *
 * - Low:        0.00 – 0.25  (heavily degraded accessibility)
 * - Medium-Low: 0.25 – 0.50  (pseudo-compliance, partial degradation)
 * - Base:       0.40 – 0.70  (unmodified WebArena app)
 * - High:       0.75 – 1.00  (enhanced accessibility)
 */
export const VARIANT_SCORE_RANGES: Record<VariantLevel, { min: number; max: number }> = {
  'low':        { min: 0.0, max: 0.25 },
  'medium-low': { min: 0.25, max: 0.50 },
  'base':       { min: 0.40, max: 0.70 },
  'high':       { min: 0.75, max: 1.0 },
};

/** Default weights used for composite score in validation (equal weighting). */
const DEFAULT_COMPOSITE_WEIGHTS: Record<string, number> = {
  lighthouseScore: 1,
  axeViolations: 1,
  semanticHtmlRatio: 1,
  accessibleNameCoverage: 1,
  keyboardNavigability: 1,
  ariaCorrectness: 1,
  pseudoComplianceRatio: 1,
  formLabelingCompleteness: 1,
  landmarkCoverage: 1,
};

/**
 * Validate a variant by running the Scanner on the current page and
 * checking that the composite score falls within the expected range
 * for the given variant level.
 *
 * Steps:
 * 1. Run Tier 1 and Tier 2 scans on the page
 * 2. Compute composite score using default weights in 'composite' mode
 * 3. Check if the score falls within the expected range
 * 4. Return a VariantValidationResult
 *
 * @param page - Playwright Page with the variant already applied
 * @param level - The variant level to validate against
 * @param scanner - Scanner interface providing scan and score functions
 * @returns VariantValidationResult with score and range check
 */
export async function validateVariant(
  page: Page,
  level: VariantLevel,
  scanner: Scanner,
): Promise<VariantValidationResult> {
  const url = page.url();

  // 1. Run Tier 1 scan
  const tier1 = await scanner.scanTier1(page, {
    url,
    wcagLevels: ['A', 'AA'],
  });

  // 2. Run Tier 2 scan (requires a CDP session from the page's browser context)
  const cdpSession = await (page.context() as any).newCDPSession(page);
  try {
    const tier2 = await scanner.scanTier2(page, cdpSession);

    // 3. Compute composite score in 'composite' mode with default weights
    const compositeOptions: CompositeScoreOptions = {
      weights: DEFAULT_COMPOSITE_WEIGHTS,
      mode: 'composite',
    };
    const compositeScore = scanner.computeCompositeScore(tier1, tier2, compositeOptions);

    // 4. Check if score falls within expected range for this variant level
    const expectedRange = VARIANT_SCORE_RANGES[level];
    const score = compositeScore.compositeScore;
    const inExpectedRange = score >= expectedRange.min && score <= expectedRange.max;

    return {
      variantLevel: level,
      compositeScore,
      inExpectedRange,
      expectedRange,
    };
  } finally {
    await cdpSession.detach();
  }
}

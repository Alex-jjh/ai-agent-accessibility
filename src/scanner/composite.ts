// Module 1: Scanner — Composite Score Calculator (Supplementary)
// Requirements: 4.1, 4.2, 4.3, 4.4
//
// This score is supplementary — primary statistical analysis uses
// criterion-level feature vectors, not this composite.

import type {
  Tier1Metrics,
  Tier2Metrics,
  CompositeScoreOptions,
  CompositeScoreResult,
  SensitivityMode,
} from './types.js';

/** Default max expected violations for normalization (axe inversion) */
const DEFAULT_MAX_VIOLATIONS = 50;

/**
 * Normalize Tier 1 metrics to 0–1 scale (Req 4.2).
 * - Lighthouse score: divide by 100
 * - Axe violations: inverted — 1 - min(count / maxExpected, 1)
 */
function normalizeTier1(
  tier1: Tier1Metrics,
  maxViolations = DEFAULT_MAX_VIOLATIONS,
): Record<string, number> {
  return {
    lighthouseScore: Math.max(0, Math.min(1, tier1.lighthouse.accessibilityScore / 100)),
    axeViolations: Math.max(0, 1 - Math.min(tier1.axeCore.violationCount / maxViolations, 1)),
  };
}

/**
 * Extract Tier 2 metrics as a flat record (already 0–1, Req 4.2).
 */
function normalizeTier2(tier2: Tier2Metrics): Record<string, number> {
  return {
    semanticHtmlRatio: tier2.semanticHtmlRatio,
    accessibleNameCoverage: tier2.accessibleNameCoverage,
    keyboardNavigability: tier2.keyboardNavigability,
    ariaCorrectness: tier2.ariaCorrectness,
    pseudoComplianceRatio: tier2.pseudoComplianceRatio,
    formLabelingCompleteness: tier2.formLabelingCompleteness,
    landmarkCoverage: tier2.landmarkCoverage,
  };
}

/**
 * Compute a weighted composite score from normalized components.
 * Only includes components present in the weights map.
 */
function weightedSum(
  components: Record<string, number>,
  weights: Record<string, number>,
): number {
  let sum = 0;
  let totalWeight = 0;

  for (const [key, weight] of Object.entries(weights)) {
    if (key in components && weight > 0) {
      sum += components[key] * weight;
      totalWeight += weight;
    }
  }

  if (totalWeight === 0) return 0;
  return Math.max(0, Math.min(1, sum / totalWeight));
}

/**
 * Compute a supplementary composite accessibility score combining
 * Tier 1 and Tier 2 metrics with configurable weights.
 *
 * Supports three sensitivity modes (Req 4.3):
 * - `tier1-only`: Only Tier 1 components (Lighthouse + axe)
 * - `tier2-only`: Only Tier 2 functional metrics
 * - `composite`: Both Tier 1 and Tier 2
 *
 * Outputs the composite score alongside all individual metric values
 * in a structured format (Req 4.4).
 *
 * @param tier1 - Tier 1 metrics (axe-core + Lighthouse)
 * @param tier2 - Tier 2 functional metrics
 * @param options - Weights and sensitivity mode
 * @returns CompositeScoreResult with score, components, mode, and weights
 */
export function computeCompositeScore(
  tier1: Tier1Metrics,
  tier2: Tier2Metrics,
  options: CompositeScoreOptions,
): CompositeScoreResult {
  const { weights, mode } = options;

  const tier1Components = normalizeTier1(tier1);
  const tier2Components = normalizeTier2(tier2);

  let activeComponents: Record<string, number>;

  switch (mode) {
    case 'tier1-only':
      activeComponents = tier1Components;
      break;
    case 'tier2-only':
      activeComponents = tier2Components;
      break;
    case 'composite':
    default:
      activeComponents = { ...tier1Components, ...tier2Components };
      break;
  }

  const compositeScore = weightedSum(activeComponents, weights);

  // Build full normalized components map for output (Req 4.4)
  const normalizedComponents = { ...tier1Components, ...tier2Components };

  return {
    compositeScore,
    normalizedComponents,
    mode,
    weights,
  };
}

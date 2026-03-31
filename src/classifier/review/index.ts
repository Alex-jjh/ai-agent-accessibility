// Module 4: Failure Classifier — Manual review and inter-rater reliability

import type { ActionTrace } from '../../runner/types.js';
import type {
  FailureClassification,
  FailureType,
  InterRaterResult,
  ManualReview,
  ReviewItem,
} from '../types.js';
import { FAILURE_TYPES } from '../types.js';

/** All failure types as a flat array for confusion matrix initialization */
const ALL_FAILURE_TYPES: FailureType[] = Object.values(FAILURE_TYPES).flat() as FailureType[];

/**
 * Randomly select a sample of classified failures for manual review.
 * Default sample rate is 10% (Req 10.1).
 */
export function selectForReview(
  classifications: Array<{ trace: ActionTrace; classification: FailureClassification }>,
  sampleRate = 0.10,
): ReviewItem[] {
  const count = Math.max(1, Math.round(classifications.length * sampleRate));

  // Fisher-Yates shuffle on indices
  const indices = classifications.map((_, i) => i);
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }

  return indices.slice(0, count).map((idx) => {
    const item = classifications[idx];
    return {
      traceId: item.trace.taskId + '-' + item.trace.attempt,
      actionTrace: item.trace,
      autoClassification: item.classification,
    };
  });
}

/**
 * Compute Cohen's kappa between auto-classifications and manual reviews.
 * Measures inter-rater reliability (Req 10.4).
 *
 * kappa = (p_o - p_e) / (1 - p_e)
 *   p_o = observed agreement rate
 *   p_e = expected agreement by chance
 */
export function computeCohensKappa(
  autoClassifications: FailureClassification[],
  manualReviews: ManualReview[],
): InterRaterResult {
  // Build lookup: traceId → manual classification
  const manualMap = new Map<string, FailureType>();
  for (const review of manualReviews) {
    manualMap.set(review.traceId, review.reviewerClassification);
  }

  // Pair auto + manual by traceId — we need the traceId on the auto side too,
  // so the caller must ensure the ordering matches. We pair by index as fallback
  // when traceIds aren't embedded in FailureClassification.
  // For this implementation, we pair by array index (auto[i] ↔ manual[i]).
  const n = Math.min(autoClassifications.length, manualReviews.length);
  if (n === 0) {
    return {
      cohensKappa: 0,
      agreementRate: 0,
      confusionMatrix: buildEmptyConfusionMatrix(),
      sampleSize: 0,
    };
  }

  const confusionMatrix = buildEmptyConfusionMatrix();
  let agreements = 0;

  // Count per-rater marginals
  const autoCount: Record<string, number> = {};
  const manualCount: Record<string, number> = {};

  for (let i = 0; i < n; i++) {
    const autoType = autoClassifications[i].primary;
    const manualType = manualReviews[i].reviewerClassification;

    confusionMatrix[autoType][manualType] = (confusionMatrix[autoType][manualType] ?? 0) + 1;
    autoCount[autoType] = (autoCount[autoType] ?? 0) + 1;
    manualCount[manualType] = (manualCount[manualType] ?? 0) + 1;

    if (autoType === manualType) agreements++;
  }

  const po = agreements / n; // observed agreement

  // Expected agreement by chance
  let pe = 0;
  for (const ft of ALL_FAILURE_TYPES) {
    const autoFrac = (autoCount[ft] ?? 0) / n;
    const manualFrac = (manualCount[ft] ?? 0) / n;
    pe += autoFrac * manualFrac;
  }

  const kappa = pe === 1 ? 1 : (po - pe) / (1 - pe);

  return {
    cohensKappa: kappa,
    agreementRate: po,
    confusionMatrix,
    sampleSize: n,
  };
}

/** Build an empty confusion matrix with all 11 failure types */
function buildEmptyConfusionMatrix(): Record<FailureType, Record<FailureType, number>> {
  const matrix = {} as Record<FailureType, Record<FailureType, number>>;
  for (const ft of ALL_FAILURE_TYPES) {
    matrix[ft] = {} as Record<FailureType, number>;
    for (const ft2 of ALL_FAILURE_TYPES) {
      matrix[ft][ft2] = 0;
    }
  }
  return matrix;
}

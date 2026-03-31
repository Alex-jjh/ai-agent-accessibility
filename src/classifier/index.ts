// Module 4: Failure Classifier — failure attribution across 11-type taxonomy
export { classifyFailure, filterByReportingMode } from './taxonomy/classify.js';
export { selectForReview, computeCohensKappa } from './review/index.js';
export type {
  FailureDomain,
  FailureType,
  FailureClassification,
  ReportingMode,
  ReviewItem,
  ManualReview,
  InterRaterResult,
} from './types.js';
export { FAILURE_DOMAINS, FAILURE_TYPES } from './types.js';

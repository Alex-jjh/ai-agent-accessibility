// Module 4: Failure Classifier — Type definitions for failure taxonomy

import type { ActionTrace } from '../runner/types.js';

/** Failure domain categories */
export type FailureDomain = 'accessibility' | 'model' | 'environmental' | 'task';

/** 11 failure types across 4 domains */
export type FailureType =
  // Accessibility domain
  | 'F_ENF'   // Element not found (missing label/name)
  | 'F_WEA'   // Wrong element actuation
  | 'F_KBT'   // Keyboard trap
  | 'F_PCT'   // Pseudo-compliance trap
  | 'F_SDI'   // Shadow DOM invisible
  // Model domain
  | 'F_HAL'   // Hallucination
  | 'F_COF'   // Context overflow
  | 'F_REA'   // Reasoning error
  // Environmental domain
  | 'F_ABB'   // Anti-bot block
  | 'F_NET'   // Network timeout
  // Task domain
  | 'F_AMB';  // Task ambiguity

/** Result of auto-classifying a failure */
export interface FailureClassification {
  primary: FailureType;
  primaryDomain: FailureDomain;
  secondaryFactors: FailureType[];
  confidence: number;
  flaggedForReview: boolean;
  evidence: string[];
}

/** Reporting mode for failure analysis */
export type ReportingMode = 'conservative' | 'inclusive';

/** An item selected for manual review */
export interface ReviewItem {
  traceId: string;
  actionTrace: ActionTrace;
  autoClassification: FailureClassification;
  pageScreenshot?: string;
  a11yTreeSnapshot?: string;
}

/** A manual review submitted by a researcher */
export interface ManualReview {
  traceId: string;
  reviewerClassification: FailureType;
  reviewerDomain: FailureDomain;
  reviewerNotes: string;
  reviewedAt: string;
}

/** Inter-rater reliability result */
export interface InterRaterResult {
  cohensKappa: number;
  agreementRate: number;
  confusionMatrix: Record<FailureType, Record<FailureType, number>>;
  sampleSize: number;
}

/** All failure domains */
export const FAILURE_DOMAINS: readonly FailureDomain[] = [
  'accessibility',
  'model',
  'environmental',
  'task',
] as const;

/** Mapping of failure domains to their failure types */
export const FAILURE_TYPES: Record<FailureDomain, readonly FailureType[]> = {
  accessibility: ['F_ENF', 'F_WEA', 'F_KBT', 'F_PCT', 'F_SDI'],
  model: ['F_HAL', 'F_COF', 'F_REA'],
  environmental: ['F_ABB', 'F_NET'],
  task: ['F_AMB'],
} as const;

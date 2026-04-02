// Module 4: Failure Classifier — Auto-classification via pattern matching on ActionTrace

import type { ActionTrace, ActionTraceStep } from '../../runner/types.js';
import type {
  FailureClassification,
  FailureDomain,
  FailureType,
  ReportingMode,
} from '../types.js';

/** Context-window limits per model family for F_COF detection */
const MODEL_TOKEN_LIMITS: Record<string, number> = {
  'claude': 200_000,
  'gpt-4o': 128_000,
};

/** Minimum confidence threshold — below this the classification is flagged for review */
const REVIEW_THRESHOLD = 0.7;

/** Internal detection result from a single detector */
interface DetectionResult {
  type: FailureType;
  domain: FailureDomain;
  confidence: number;
  evidence: string[];
}

// ---------------------------------------------------------------------------
// Individual failure-type detectors
// ---------------------------------------------------------------------------

/** F_ENF: Find the longest run of ≥3 consecutive failed selectors */
function detectENF(steps: ActionTraceStep[]): DetectionResult | null {
  let bestConsecutive = 0;
  let bestActions: string[] = [];
  let consecutiveFails = 0;
  let failedActions: string[] = [];

  for (const step of steps) {
    if (step.result === 'failure') {
      consecutiveFails++;
      failedActions.push(`step ${step.stepNum}: ${step.action}`);
    } else {
      if (consecutiveFails > bestConsecutive) {
        bestConsecutive = consecutiveFails;
        bestActions = [...failedActions];
      }
      consecutiveFails = 0;
      failedActions = [];
    }
  }
  // Check the final run
  if (consecutiveFails > bestConsecutive) {
    bestConsecutive = consecutiveFails;
    bestActions = [...failedActions];
  }

  if (bestConsecutive >= 3) {
    const confidence = Math.min(0.6 + bestConsecutive * 0.1, 1.0);
    return {
      type: 'F_ENF',
      domain: 'accessibility',
      confidence,
      evidence: bestActions.slice(0, 5),
    };
  }
  return null;
}

/** F_WEA: Wrong element actuation — action succeeds but on wrong target */
function detectWEA(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.result === 'success' &&
      step.resultDetail &&
      /wrong|unexpected|incorrect|unintended/i.test(step.resultDetail)
    ) {
      evidence.push(`step ${step.stepNum}: ${step.action} — ${step.resultDetail}`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_WEA',
      domain: 'accessibility',
      confidence: Math.min(0.5 + evidence.length * 0.15, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_KBT: Keyboard trap — tab cycles back to same element */
function detectKBT(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (let i = 1; i < steps.length; i++) {
    const prev = steps[i - 1];
    const curr = steps[i];
    if (
      /tab/i.test(prev.action) &&
      /tab/i.test(curr.action) &&
      prev.observation === curr.observation
    ) {
      evidence.push(`steps ${prev.stepNum}-${curr.stepNum}: tab cycle detected`);
    }
  }
  if (evidence.length >= 2) {
    return {
      type: 'F_KBT',
      domain: 'accessibility',
      confidence: Math.min(0.6 + evidence.length * 0.1, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_PCT: Pseudo-compliance trap — role present but interaction fails */
function detectPCT(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.result === 'failure' &&
      step.resultDetail &&
      /not interactive|not clickable|no handler|role.*but/i.test(step.resultDetail)
    ) {
      evidence.push(`step ${step.stepNum}: ${step.action} — ${step.resultDetail}`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_PCT',
      domain: 'accessibility',
      confidence: Math.min(0.6 + evidence.length * 0.15, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_SDI: Shadow DOM invisible — element visible in screenshot but not in a11y tree */
function detectSDI(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.result === 'failure' &&
      step.resultDetail &&
      /shadow.?dom|not in.*tree|invisible.*a11y|hidden.*accessibility/i.test(step.resultDetail)
    ) {
      evidence.push(`step ${step.stepNum}: ${step.action} — ${step.resultDetail}`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_SDI',
      domain: 'accessibility',
      confidence: Math.min(0.5 + evidence.length * 0.2, 0.9),
      evidence,
    };
  }
  return null;
}

/** F_HAL: Hallucination — agent acts on element that doesn't exist in observation */
function detectHAL(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.result === 'failure' &&
      step.resultDetail &&
      /not found|does not exist|no such element|element missing/i.test(step.resultDetail)
    ) {
      // Check if the action references something not in the observation
      const actionTarget = step.action.match(/element='([^']+)'/)?.[1] ?? '';
      if (actionTarget && !step.observation.includes(actionTarget)) {
        evidence.push(`step ${step.stepNum}: action on "${actionTarget}" not in observation`);
      }
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_HAL',
      domain: 'model',
      confidence: Math.min(0.7 + evidence.length * 0.1, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_COF: Context overflow — token usage exceeds model context window */
function detectCOF(trace: ActionTrace): DetectionResult | null {
  const backend = trace.agentConfig.llmBackend.toLowerCase();
  let limit = 128_000; // default
  for (const [prefix, tokenLimit] of Object.entries(MODEL_TOKEN_LIMITS)) {
    if (backend.includes(prefix)) {
      limit = tokenLimit;
      break;
    }
  }
  if (trace.totalTokens > limit) {
    return {
      type: 'F_COF',
      domain: 'model',
      confidence: 0.95,
      evidence: [`totalTokens ${trace.totalTokens} exceeds ${backend} limit ${limit}`],
    };
  }
  return null;
}

/** F_REA: Reasoning error — agent reasoning contradicts its observation */
function detectREA(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (step.result === 'failure' || step.result === 'error') {
      // Heuristic: reasoning mentions an element/state that contradicts the observation
      const reasoningLower = step.reasoning.toLowerCase();
      if (
        (reasoningLower.includes('i can see') || reasoningLower.includes('i see')) &&
        step.result === 'failure'
      ) {
        evidence.push(`step ${step.stepNum}: reasoning claims visibility but action failed`);
      }
      if (
        reasoningLower.includes('should work') &&
        step.result === 'failure'
      ) {
        evidence.push(`step ${step.stepNum}: reasoning expects success but action failed`);
      }
    }
  }
  if (evidence.length >= 2) {
    return {
      type: 'F_REA',
      domain: 'model',
      confidence: Math.min(0.5 + evidence.length * 0.1, 0.85),
      evidence,
    };
  }
  return null;
}

/** F_ABB: Anti-bot block — HTTP 403/429 in action results */
function detectABB(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.resultDetail &&
      /\b(403|429)\b|forbidden|too many requests|rate.?limit|blocked/i.test(step.resultDetail)
    ) {
      evidence.push(`step ${step.stepNum}: ${step.resultDetail}`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_ABB',
      domain: 'environmental',
      confidence: Math.min(0.8 + evidence.length * 0.05, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_NET: Network timeout / connection errors */
function detectNET(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    if (
      step.result === 'error' &&
      step.resultDetail &&
      /timeout|timed.?out|connection.?refused|ECONNREFUSED|ECONNRESET|network|ETIMEDOUT/i.test(
        step.resultDetail,
      )
    ) {
      evidence.push(`step ${step.stepNum}: ${step.resultDetail}`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_NET',
      domain: 'environmental',
      confidence: Math.min(0.8 + evidence.length * 0.05, 0.95),
      evidence,
    };
  }
  return null;
}

/** F_AMB: Task ambiguity — agent asks for clarification */
function detectAMB(steps: ActionTraceStep[]): DetectionResult | null {
  const evidence: string[] = [];
  for (const step of steps) {
    const r = step.reasoning.toLowerCase();
    if (
      /unclear|ambiguous|not sure what|clarif|which one|please specify|don't understand the task/i.test(r)
    ) {
      evidence.push(`step ${step.stepNum}: reasoning indicates confusion — "${step.reasoning.slice(0, 80)}"`);
    }
  }
  if (evidence.length > 0) {
    return {
      type: 'F_AMB',
      domain: 'task',
      confidence: Math.min(0.6 + evidence.length * 0.15, 0.9),
      evidence,
    };
  }
  return null;
}

// ---------------------------------------------------------------------------
// Domain lookup
// ---------------------------------------------------------------------------

const DOMAIN_FOR_TYPE: Record<FailureType, FailureDomain> = {
  F_ENF: 'accessibility',
  F_WEA: 'accessibility',
  F_KBT: 'accessibility',
  F_PCT: 'accessibility',
  F_SDI: 'accessibility',
  F_HAL: 'model',
  F_COF: 'model',
  F_REA: 'model',
  F_ABB: 'environmental',
  F_NET: 'environmental',
  F_AMB: 'task',
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Classify an agent failure by running all 11 pattern detectors against the
 * action trace. Returns the highest-confidence detection as primary, with
 * remaining detections as secondary factors.
 */
export function classifyFailure(trace: ActionTrace): FailureClassification {
  const detections: DetectionResult[] = [];

  // Run all detectors
  const stepDetectors = [
    detectENF,
    detectWEA,
    detectKBT,
    detectPCT,
    detectSDI,
    detectHAL,
    detectREA,
    detectABB,
    detectNET,
    detectAMB,
  ];

  for (const detector of stepDetectors) {
    const result = detector(trace.steps);
    if (result) detections.push(result);
  }

  // Trace-level detectors
  const cofResult = detectCOF(trace);
  if (cofResult) detections.push(cofResult);

  // Sort by confidence descending
  detections.sort((a, b) => b.confidence - a.confidence);

  // If no detections, fall back to a low-confidence generic classification
  if (detections.length === 0) {
    return {
      primary: 'F_REA',
      primaryDomain: 'model',
      secondaryFactors: [],
      confidence: 0.3,
      flaggedForReview: true,
      evidence: ['No specific failure pattern detected — defaulting to reasoning error'],
    };
  }

  const primary = detections[0];
  const secondaryFactors = detections
    .slice(1)
    .map((d) => d.type);

  const allEvidence = detections.flatMap((d) => d.evidence);

  return {
    primary: primary.type,
    primaryDomain: primary.domain,
    secondaryFactors,
    confidence: primary.confidence,
    flaggedForReview: primary.confidence < REVIEW_THRESHOLD,
    evidence: allEvidence,
  };
}

/**
 * Filter classifications by reporting mode.
 * - conservative: only accessibility-domain primary classifications
 * - inclusive: all classifications
 */
export function filterByReportingMode(
  classifications: FailureClassification[],
  mode: ReportingMode,
): FailureClassification[] {
  if (mode === 'inclusive') return classifications;
  return classifications.filter((c) => c.primaryDomain === 'accessibility');
}

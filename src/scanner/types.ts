// Module 1: Scanner — Type definitions for accessibility scanning

/** Individual axe-core violation entry */
export interface AxeViolation {
  id: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  description: string;
  helpUrl?: string;
  nodes: number;
}

/** Aggregated axe-core scan result */
export interface AxeCoreResult {
  violationCount: number;
  violationsByWcagCriterion: Record<string, AxeViolation[]>;
  impactSeverity: Record<'critical' | 'serious' | 'moderate' | 'minor', number>;
}

/** Lighthouse accessibility audit result */
export interface LighthouseResult {
  accessibilityScore: number; // 0–100
  audits: Record<string, { pass: boolean; details?: unknown }>;
}

/** Tier 1 metrics from axe-core + Lighthouse */
export interface Tier1Metrics {
  url: string;
  axeCore: AxeCoreResult;
  lighthouse: LighthouseResult;
  scannedAt: string; // ISO 8601
}

/** Options for Tier 1 scanning */
export interface Tier1ScanOptions {
  url: string;
  wcagLevels: ('A' | 'AA' | 'AAA')[];
  lighthouseFlags?: Record<string, unknown>;
}

/** Tier 2 functional accessibility metrics (all decimals 0.0–1.0 except counts/booleans) */
export interface Tier2Metrics {
  semanticHtmlRatio: number;
  accessibleNameCoverage: number;
  keyboardNavigability: number;
  ariaCorrectness: number;
  pseudoComplianceCount: number;
  pseudoComplianceRatio: number;
  formLabelingCompleteness: number;
  landmarkCoverage: number;
  shadowDomIncluded: boolean;
}

/** Options for A11y tree stability detection */
export interface StabilityOptions {
  intervalMs: number;    // default 2000
  timeoutMs: number;     // default 30000
  maxRetries: number;    // derived from timeout/interval
}

/** Result of waiting for A11y tree stability */
export interface StabilityResult {
  stable: boolean;
  snapshot: AccessibilityTreeSnapshot;
  stabilizationMs: number;
  attempts: number;
}

/** Sensitivity mode for composite score computation */
export type SensitivityMode = 'tier1-only' | 'tier2-only' | 'composite';

/** Options for composite score computation */
export interface CompositeScoreOptions {
  weights: Record<string, number>;
  mode: SensitivityMode;
}

/** Result of composite score computation */
export interface CompositeScoreResult {
  compositeScore: number; // 0.0–1.0
  normalizedComponents: Record<string, number>;
  mode: SensitivityMode;
  weights: Record<string, number>;
}

/** Serialized accessibility tree snapshot */
export type AccessibilityTreeSnapshot = Record<string, unknown>;

/** Combined scan result for a single URL */
export interface ScanResult {
  scanId: string;
  url: string;
  scannedAt: string;
  treeWasStable: boolean;
  stabilizationMs: number;
  tier1: Tier1Metrics;
  tier2: Tier2Metrics;
  compositeScore?: CompositeScoreResult | null;
  a11yTreeSnapshot: AccessibilityTreeSnapshot;
}

/**
 * Validates that a metric value is within the 0.0–1.0 range (inclusive).
 * Used for Tier 2 metrics and composite scores.
 */
export function isValidMetricValue(value: number): boolean {
  return typeof value === 'number' && !Number.isNaN(value) && value >= 0.0 && value <= 1.0;
}

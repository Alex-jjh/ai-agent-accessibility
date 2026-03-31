// Module 1: Scanner — Tier 1 + Tier 2 accessibility measurement
export { scanTier1 } from './tier1/scan.js';
export { scanTier2 } from './tier2/scan.js';
export { waitForA11yTreeStable } from './snapshot/stability.js';
export { computeCompositeScore } from './composite.js';
export { serializeScanResult, deserializeScanResult, ScanResultParseError } from './serialization.js';
export { scanUrlsConcurrently } from './concurrent.js';
export type {
  ConcurrentScanOptions,
  UrlScanOutcome,
  ConcurrentScanResult,
} from './concurrent.js';
export type {
  Tier1Metrics,
  Tier1ScanOptions,
  AxeCoreResult,
  AxeViolation,
  LighthouseResult,
  Tier2Metrics,
  StabilityOptions,
  StabilityResult,
  SensitivityMode,
  CompositeScoreOptions,
  CompositeScoreResult,
  AccessibilityTreeSnapshot,
  ScanResult,
} from './types.js';
export { isValidMetricValue } from './types.js';

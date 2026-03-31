// Module 1: Scanner — Scan Result Serialization/Deserialization
// Requirements: 16.1, 16.2, 16.3, 16.4

import type { ScanResult } from './types.js';

/**
 * Error thrown when deserialization fails, with location and nature of the failure.
 */
export class ScanResultParseError extends Error {
  constructor(
    public readonly location: string,
    public readonly nature: string,
  ) {
    super(`Scan result parse error at "${location}": ${nature}`);
    this.name = 'ScanResultParseError';
  }
}

/**
 * Serialize a ScanResult (Tier1, Tier2, CompositeScore, A11y snapshot) to JSON.
 * (Req 16.1)
 */
export function serializeScanResult(result: ScanResult): string {
  return JSON.stringify(result);
}

/**
 * Deserialize a JSON string back into a structured ScanResult object.
 * Returns a descriptive error with location and nature of parsing failure
 * on invalid JSON. (Req 16.2, 16.4)
 */
export function deserializeScanResult(json: string): ScanResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new ScanResultParseError('root', `Invalid JSON: ${message}`);
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new ScanResultParseError('root', 'Expected a JSON object');
  }

  const obj = parsed as Record<string, unknown>;

  // Validate required top-level fields
  validateString(obj, 'scanId');
  validateString(obj, 'url');
  validateString(obj, 'scannedAt');
  validateBoolean(obj, 'treeWasStable');
  validateNumber(obj, 'stabilizationMs');
  validateTier1(obj);
  validateTier2(obj);
  validateA11yTreeSnapshot(obj);

  // compositeScore is optional (may be null or absent)
  if ('compositeScore' in obj && obj.compositeScore !== null && obj.compositeScore !== undefined) {
    validateCompositeScore(obj.compositeScore, 'compositeScore');
  }

  return parsed as ScanResult;
}

function validateString(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'string') {
    throw new ScanResultParseError(field, `Expected string, got ${typeof obj[field]}`);
  }
}

function validateNumber(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'number') {
    throw new ScanResultParseError(field, `Expected number, got ${typeof obj[field]}`);
  }
}

function validateBoolean(obj: Record<string, unknown>, field: string): void {
  if (typeof obj[field] !== 'boolean') {
    throw new ScanResultParseError(field, `Expected boolean, got ${typeof obj[field]}`);
  }
}

function validateTier1(obj: Record<string, unknown>): void {
  if (typeof obj.tier1 !== 'object' || obj.tier1 === null) {
    throw new ScanResultParseError('tier1', 'Expected an object');
  }
  const tier1 = obj.tier1 as Record<string, unknown>;
  validateString(tier1, 'url');
  validateString(tier1, 'scannedAt');

  if (typeof tier1.axeCore !== 'object' || tier1.axeCore === null) {
    throw new ScanResultParseError('tier1.axeCore', 'Expected an object');
  }
  const axe = tier1.axeCore as Record<string, unknown>;
  if (typeof axe.violationCount !== 'number') {
    throw new ScanResultParseError('tier1.axeCore.violationCount', 'Expected number');
  }

  if (typeof tier1.lighthouse !== 'object' || tier1.lighthouse === null) {
    throw new ScanResultParseError('tier1.lighthouse', 'Expected an object');
  }
  const lh = tier1.lighthouse as Record<string, unknown>;
  if (typeof lh.accessibilityScore !== 'number') {
    throw new ScanResultParseError('tier1.lighthouse.accessibilityScore', 'Expected number');
  }
}

function validateTier2(obj: Record<string, unknown>): void {
  if (typeof obj.tier2 !== 'object' || obj.tier2 === null) {
    throw new ScanResultParseError('tier2', 'Expected an object');
  }
  const tier2 = obj.tier2 as Record<string, unknown>;
  const numericFields = [
    'semanticHtmlRatio', 'accessibleNameCoverage', 'keyboardNavigability',
    'ariaCorrectness', 'pseudoComplianceCount', 'pseudoComplianceRatio',
    'formLabelingCompleteness', 'landmarkCoverage',
  ];
  for (const field of numericFields) {
    if (typeof tier2[field] !== 'number') {
      throw new ScanResultParseError(`tier2.${field}`, `Expected number, got ${typeof tier2[field]}`);
    }
  }
  if (typeof tier2.shadowDomIncluded !== 'boolean') {
    throw new ScanResultParseError('tier2.shadowDomIncluded', 'Expected boolean');
  }
}

function validateA11yTreeSnapshot(obj: Record<string, unknown>): void {
  if (typeof obj.a11yTreeSnapshot !== 'object' || obj.a11yTreeSnapshot === null) {
    throw new ScanResultParseError('a11yTreeSnapshot', 'Expected an object');
  }
}

function validateCompositeScore(value: unknown, path: string): void {
  if (typeof value !== 'object' || value === null) {
    throw new ScanResultParseError(path, 'Expected an object');
  }
  const cs = value as Record<string, unknown>;
  if (typeof cs.compositeScore !== 'number') {
    throw new ScanResultParseError(`${path}.compositeScore`, 'Expected number');
  }
  if (typeof cs.mode !== 'string') {
    throw new ScanResultParseError(`${path}.mode`, 'Expected string');
  }
}

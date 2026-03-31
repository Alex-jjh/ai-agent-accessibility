// Cross-cutting: CSV Exporter
// Exports experiment data as CSV files for R/Python import.
// Generates: experiment-data.csv, scan-metrics.csv, failure-classifications.csv, trace-summaries.csv
// Supports PII anonymization and site identity anonymization.
// Requirements: 15.1, 15.3, 15.4

import type { CsvExportOptions } from '../config/types.js';
import type { ExperimentRecord } from '../runner/scheduler.js';
import type { FailureClassification } from '../classifier/types.js';

/** A classified record pairs an experiment record with its failure classification (if any) */
export interface ClassifiedRecord {
  record: ExperimentRecord;
  classification?: FailureClassification;
}

/** Result of CSV export including the site identity mapping when anonymization is enabled */
export interface CsvExportResult {
  files: Record<string, string>; // filename → CSV content
  siteMapping?: Record<string, string>; // original URL → opaque ID
}

// --- PII scrubbing regexes (Req 15.4) ---

const EMAIL_REGEX = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
const COOKIE_REGEX = /(?:cookie|set-cookie|authorization|x-auth-token|x-api-key)\s*[:=]\s*[^\s;,]+/gi;
const AUTH_TOKEN_REGEX = /(?:bearer|token|jwt|session[_-]?id|api[_-]?key)\s*[:=]?\s*[A-Za-z0-9\-_.~+/]+=*/gi;
const URL_USER_SEGMENT_REGEX = /\/users?\/[A-Za-z0-9_\-]+/gi;

/**
 * Scrub PII from a string value: emails, cookies, auth tokens, user-specific URL segments.
 */
export function scrubPii(value: string): string {
  let result = value;
  result = result.replace(EMAIL_REGEX, '[email]');
  result = result.replace(COOKIE_REGEX, '[redacted-credential]');
  result = result.replace(AUTH_TOKEN_REGEX, '[redacted-token]');
  result = result.replace(URL_USER_SEGMENT_REGEX, '/users/[redacted]');
  return result;
}

/**
 * Escape a value for CSV: wrap in quotes if it contains commas, quotes, or newlines.
 */
function csvEscape(value: string | number | boolean | undefined | null): string {
  if (value === undefined || value === null) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Convert an array of row objects to a CSV string.
 */
function toCsv(headers: string[], rows: Record<string, string | number | boolean | undefined | null>[]): string {
  const headerLine = headers.map(csvEscape).join(',');
  const dataLines = rows.map(row =>
    headers.map(h => csvEscape(row[h])).join(','),
  );
  return [headerLine, ...dataLines].join('\n');
}

/**
 * Build a site identity mapping: original URL → opaque ID (e.g. site_001).
 */
export function buildSiteMapping(records: ClassifiedRecord[]): Record<string, string> {
  const urls = new Set<string>();
  for (const { record } of records) {
    urls.add(record.scanResults.url);
  }
  const mapping: Record<string, string> = {};
  let counter = 1;
  for (const url of urls) {
    mapping[url] = `site_${String(counter).padStart(3, '0')}`;
    counter++;
  }
  return mapping;
}

/**
 * Optionally anonymize a URL using the site mapping.
 */
function anonymizeUrl(url: string, mapping: Record<string, string> | undefined): string {
  if (!mapping) return url;
  return mapping[url] ?? url;
}

/**
 * Apply PII and site anonymization to a string value based on options.
 */
function applyAnonymization(
  value: string,
  options: CsvExportOptions,
  siteMapping?: Record<string, string>,
): string {
  let result = value;
  if (options.anonymize) {
    result = scrubPii(result);
  }
  if (options.anonymizeSiteIdentity && siteMapping) {
    for (const [url, opaqueId] of Object.entries(siteMapping)) {
      result = result.replaceAll(url, opaqueId);
    }
  }
  return result;
}

/**
 * Generate experiment-data.csv: one row per experiment record.
 */
function generateExperimentDataCsv(
  data: ClassifiedRecord[],
  options: CsvExportOptions,
  siteMapping?: Record<string, string>,
): string {
  const headers = [
    'caseId', 'app', 'variant', 'taskId', 'observationMode', 'llmBackend',
    'attempt', 'outcome', 'success', 'totalSteps', 'totalTokens', 'durationMs',
  ];
  const rows = data.map(({ record: r }) => ({
    caseId: r.caseId,
    app: r.app,
    variant: r.variant,
    taskId: r.taskId,
    observationMode: r.agentConfig.observationMode,
    llmBackend: r.agentConfig.llmBackend,
    attempt: r.attempt,
    outcome: r.taskOutcome.outcome,
    success: r.trace.success,
    totalSteps: r.trace.totalSteps,
    totalTokens: r.trace.totalTokens,
    durationMs: r.trace.durationMs,
  }));
  return toCsv(headers, rows);
}

/**
 * Generate scan-metrics.csv: one row per scan result with all tier 1 + tier 2 metrics.
 */
function generateScanMetricsCsv(
  data: ClassifiedRecord[],
  options: CsvExportOptions,
  siteMapping?: Record<string, string>,
): string {
  const headers = [
    'caseId', 'url', 'scannedAt',
    'axeViolationCount', 'lighthouseScore',
    'impactCritical', 'impactSerious', 'impactModerate', 'impactMinor',
    'semanticHtmlRatio', 'accessibleNameCoverage', 'keyboardNavigability',
    'ariaCorrectness', 'pseudoComplianceCount', 'pseudoComplianceRatio',
    'formLabelingCompleteness', 'landmarkCoverage', 'shadowDomIncluded',
    'compositeScore', 'compositeMode',
  ];
  const rows = data.map(({ record: r }) => {
    const s = r.scanResults;
    const url = anonymizeUrl(s.url, options.anonymizeSiteIdentity ? siteMapping : undefined);
    return {
      caseId: r.caseId,
      url,
      scannedAt: s.scannedAt,
      axeViolationCount: s.tier1.axeCore.violationCount,
      lighthouseScore: s.tier1.lighthouse.accessibilityScore,
      impactCritical: s.tier1.axeCore.impactSeverity.critical,
      impactSerious: s.tier1.axeCore.impactSeverity.serious,
      impactModerate: s.tier1.axeCore.impactSeverity.moderate,
      impactMinor: s.tier1.axeCore.impactSeverity.minor,
      semanticHtmlRatio: s.tier2.semanticHtmlRatio,
      accessibleNameCoverage: s.tier2.accessibleNameCoverage,
      keyboardNavigability: s.tier2.keyboardNavigability,
      ariaCorrectness: s.tier2.ariaCorrectness,
      pseudoComplianceCount: s.tier2.pseudoComplianceCount,
      pseudoComplianceRatio: s.tier2.pseudoComplianceRatio,
      formLabelingCompleteness: s.tier2.formLabelingCompleteness,
      landmarkCoverage: s.tier2.landmarkCoverage,
      shadowDomIncluded: s.tier2.shadowDomIncluded,
      compositeScore: s.compositeScore?.compositeScore ?? '',
      compositeMode: s.compositeScore?.mode ?? '',
    };
  });
  return toCsv(headers, rows);
}

/**
 * Generate failure-classifications.csv: one row per classified failure.
 */
function generateFailureClassificationsCsv(
  data: ClassifiedRecord[],
  options: CsvExportOptions,
  siteMapping?: Record<string, string>,
): string {
  const headers = [
    'caseId', 'primaryType', 'primaryDomain', 'secondaryFactors',
    'confidence', 'flaggedForReview', 'evidence',
  ];
  const classified = data.filter(d => d.classification);
  const rows = classified.map(({ record: r, classification: c }) => {
    let evidence = c!.evidence.join('; ');
    evidence = applyAnonymization(evidence, options, siteMapping);
    return {
      caseId: r.caseId,
      primaryType: c!.primary,
      primaryDomain: c!.primaryDomain,
      secondaryFactors: c!.secondaryFactors.join(';'),
      confidence: c!.confidence,
      flaggedForReview: c!.flaggedForReview,
      evidence,
    };
  });
  return toCsv(headers, rows);
}

/**
 * Generate trace-summaries.csv: one row per action trace with summary stats.
 */
function generateTraceSummariesCsv(
  data: ClassifiedRecord[],
  options: CsvExportOptions,
  siteMapping?: Record<string, string>,
): string {
  const baseHeaders = [
    'caseId', 'taskId', 'variant', 'attempt', 'success',
    'totalSteps', 'totalTokens', 'durationMs',
    'failureType', 'failureConfidence',
  ];
  const detailHeaders = options.includeTraceDetails
    ? ['firstAction', 'lastAction', 'errorCount']
    : [];
  const headers = [...baseHeaders, ...detailHeaders];

  const rows = data.map(({ record: r }) => {
    const t = r.trace;
    const base: Record<string, string | number | boolean | undefined | null> = {
      caseId: r.caseId,
      taskId: t.taskId,
      variant: t.variant,
      attempt: t.attempt,
      success: t.success,
      totalSteps: t.totalSteps,
      totalTokens: t.totalTokens,
      durationMs: t.durationMs,
      failureType: t.failureType ?? '',
      failureConfidence: t.failureConfidence ?? '',
    };
    if (options.includeTraceDetails && t.steps.length > 0) {
      let firstAction = t.steps[0].action;
      let lastAction = t.steps[t.steps.length - 1].action;
      firstAction = applyAnonymization(firstAction, options, siteMapping);
      lastAction = applyAnonymization(lastAction, options, siteMapping);
      base.firstAction = firstAction;
      base.lastAction = lastAction;
      base.errorCount = t.steps.filter(s => s.result === 'error').length;
    }
    return base;
  });
  return toCsv(headers, rows);
}

/**
 * Export experiment data as CSV files for R/Python import.
 *
 * Returns a map of filename → CSV content, plus the site identity mapping
 * when anonymizeSiteIdentity is enabled.
 * (Req 15.1, 15.3, 15.4)
 */
export function exportToCsv(
  data: ClassifiedRecord[],
  options: CsvExportOptions,
): CsvExportResult {
  const siteMapping = options.anonymizeSiteIdentity ? buildSiteMapping(data) : undefined;

  const files: Record<string, string> = {
    'experiment-data.csv': generateExperimentDataCsv(data, options, siteMapping),
    'scan-metrics.csv': generateScanMetricsCsv(data, options, siteMapping),
    'failure-classifications.csv': generateFailureClassificationsCsv(data, options, siteMapping),
    'trace-summaries.csv': generateTraceSummariesCsv(data, options, siteMapping),
  };

  return { files, siteMapping };
}

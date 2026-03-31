// Cross-cutting: JSON Data Store
// Stores all experiment records in structured JSON following the documented file system layout:
//   data/track-a/runs/{runId}/cases/{caseId}/
//   data/track-b/har/{harId}/
//   data/exports/
// Requirements: 15.1

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import type { ExperimentManifest } from '../config/types.js';
import type { ExperimentRecord } from '../runner/scheduler.js';
import type { ScanResult } from '../scanner/types.js';
import type { ActionTrace } from '../runner/types.js';
import type { FailureClassification } from '../classifier/types.js';
import type { HarMetadata } from '../recorder/types.js';

/** Configuration for the JSON data store */
export interface StoreConfig {
  /** Root data directory (e.g. 'data') */
  baseDir: string;
}

/**
 * Ensure a directory exists, creating it recursively if needed.
 */
async function ensureDir(dirPath: string): Promise<void> {
  await mkdir(dirPath, { recursive: true });
}

/**
 * Write a JSON file atomically (write content, ensure parent dir exists).
 */
async function writeJson(filePath: string, data: unknown): Promise<void> {
  await ensureDir(dirname(filePath));
  await writeFile(filePath, JSON.stringify(data, null, 2));
}

/**
 * Read and parse a JSON file.
 */
async function readJson<T>(filePath: string): Promise<T> {
  const raw = await readFile(filePath, 'utf-8');
  return JSON.parse(raw) as T;
}

/**
 * JSON data store for experiment records.
 *
 * File system layout:
 *   {baseDir}/track-a/runs/{runId}/manifest.json
 *   {baseDir}/track-a/runs/{runId}/cases/{caseId}/scan-result.json
 *   {baseDir}/track-a/runs/{runId}/cases/{caseId}/trace-attempt-{n}.json
 *   {baseDir}/track-a/runs/{runId}/cases/{caseId}/classification.json
 *   {baseDir}/track-b/har/{harId}/metadata.json
 *   {baseDir}/track-b/har/{harId}/scan-result.json
 *   {baseDir}/exports/  (CSV files written here)
 */
export class ExperimentStore {
  private readonly baseDir: string;

  constructor(config: StoreConfig) {
    this.baseDir = config.baseDir;
  }

  // --- Track A: Controlled experiments ---

  /** Get the path for a Track A run directory */
  runDir(runId: string): string {
    return join(this.baseDir, 'track-a', 'runs', runId);
  }

  /** Get the path for a case directory within a run */
  caseDir(runId: string, caseId: string): string {
    // Replace colons with underscores for filesystem safety
    const safeCaseId = caseId.replace(/:/g, '_');
    return join(this.runDir(runId), 'cases', safeCaseId);
  }

  /** Store the experiment manifest for a run (Req 15.2) */
  async storeManifest(runId: string, manifest: ExperimentManifest): Promise<string> {
    const filePath = join(this.runDir(runId), 'manifest.json');
    await writeJson(filePath, manifest);
    return filePath;
  }

  /** Load the experiment manifest for a run */
  async loadManifest(runId: string): Promise<ExperimentManifest> {
    const filePath = join(this.runDir(runId), 'manifest.json');
    return readJson<ExperimentManifest>(filePath);
  }

  /** Store a scan result for a test case */
  async storeScanResult(runId: string, caseId: string, scanResult: ScanResult): Promise<string> {
    const filePath = join(this.caseDir(runId, caseId), 'scan-result.json');
    await writeJson(filePath, scanResult);
    return filePath;
  }

  /** Load a scan result for a test case */
  async loadScanResult(runId: string, caseId: string): Promise<ScanResult> {
    const filePath = join(this.caseDir(runId, caseId), 'scan-result.json');
    return readJson<ScanResult>(filePath);
  }

  /** Store an action trace for a specific attempt */
  async storeTrace(runId: string, caseId: string, attempt: number, trace: ActionTrace): Promise<string> {
    const filePath = join(this.caseDir(runId, caseId), `trace-attempt-${attempt}.json`);
    await writeJson(filePath, trace);
    return filePath;
  }

  /** Load an action trace for a specific attempt */
  async loadTrace(runId: string, caseId: string, attempt: number): Promise<ActionTrace> {
    const filePath = join(this.caseDir(runId, caseId), `trace-attempt-${attempt}.json`);
    return readJson<ActionTrace>(filePath);
  }

  /** Store a failure classification for a test case */
  async storeClassification(runId: string, caseId: string, classification: FailureClassification): Promise<string> {
    const filePath = join(this.caseDir(runId, caseId), 'classification.json');
    await writeJson(filePath, classification);
    return filePath;
  }

  /** Load a failure classification for a test case */
  async loadClassification(runId: string, caseId: string): Promise<FailureClassification> {
    const filePath = join(this.caseDir(runId, caseId), 'classification.json');
    return readJson<FailureClassification>(filePath);
  }

  /** Store a full experiment record (convenience: writes scan, trace, and classification) */
  async storeRecord(runId: string, record: ExperimentRecord, classification?: FailureClassification): Promise<void> {
    await this.storeScanResult(runId, record.caseId, record.scanResults);
    await this.storeTrace(runId, record.caseId, record.attempt, record.trace);
    if (classification) {
      await this.storeClassification(runId, record.caseId, classification);
    }
  }

  // --- Track B: HAR recordings ---

  /** Get the path for a HAR recording directory */
  harDir(harId: string): string {
    return join(this.baseDir, 'track-b', 'har', harId);
  }

  /** Store HAR metadata */
  async storeHarMetadata(harId: string, metadata: HarMetadata): Promise<string> {
    const filePath = join(this.harDir(harId), 'metadata.json');
    await writeJson(filePath, metadata);
    return filePath;
  }

  /** Load HAR metadata */
  async loadHarMetadata(harId: string): Promise<HarMetadata> {
    const filePath = join(this.harDir(harId), 'metadata.json');
    return readJson<HarMetadata>(filePath);
  }

  /** Store a scan result for a HAR recording */
  async storeHarScanResult(harId: string, scanResult: ScanResult): Promise<string> {
    const filePath = join(this.harDir(harId), 'scan-result.json');
    await writeJson(filePath, scanResult);
    return filePath;
  }

  /** Load a scan result for a HAR recording */
  async loadHarScanResult(harId: string): Promise<ScanResult> {
    const filePath = join(this.harDir(harId), 'scan-result.json');
    return readJson<ScanResult>(filePath);
  }

  // --- Exports directory ---

  /** Get the exports directory path */
  exportsDir(): string {
    return join(this.baseDir, 'exports');
  }

  /** Write a CSV export file to the exports directory */
  async writeCsvExport(filename: string, content: string): Promise<string> {
    const filePath = join(this.exportsDir(), filename);
    await ensureDir(this.exportsDir());
    await writeFile(filePath, content);
    return filePath;
  }
}

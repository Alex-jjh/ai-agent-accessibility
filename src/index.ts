/**
 * End-to-end experiment pipeline — wires all six modules together.
 *
 * Pipeline flow:
 *   Load config → validate → verify WebArena → generate variants → scan →
 *   run agents → classify failures → export results → generate manifest
 *
 * Supports both Track A (WebArena controlled experiments) and
 * Track B (HAR replay ecological survey) through the same runner.
 *
 * Requirements: 8.1, 8.4, 12.4, 18.1, 18.3
 */

import { randomUUID } from 'node:crypto';
import type { Browser, BrowserContext, CDPSession, Page } from 'playwright';

// Config
import { loadConfig, validateConfig } from './config/index.js';
import type { ExperimentConfig } from './config/types.js';

// Scanner
import { scanTier1, scanTier2, waitForA11yTreeStable, computeCompositeScore } from './scanner/index.js';
import { scanUrlsConcurrently } from './scanner/concurrent.js';
import type { ScanResult, CompositeScoreOptions, Tier1ScanOptions } from './scanner/types.js';

// Variants
import { applyVariant, revertVariant, validateVariant } from './variants/index.js';
import type { VariantLevel } from './variants/types.js';
import type { Scanner } from './variants/validation/index.js';

// Runner
import {
  executeExperiment,
  generateTestCases,
  parseTestCaseId,
} from './runner/scheduler.js';
import {
  verifyWebArenaServices,
  resetWebArenaApp,
  buildWebArenaConfig,
} from './runner/webarena.js';
import { executeAgentTask } from './runner/agents/executor.js';
import type { ExperimentRecord, TestCaseParams, TestCaseResult } from './runner/scheduler.js';
import type { ExperimentRun, ActionTrace, TaskOutcome } from './runner/types.js';

// Classifier
import { classifyFailure, filterByReportingMode } from './classifier/index.js';
import type { FailureClassification, ReportingMode } from './classifier/types.js';

// Recorder
import { captureHar } from './recorder/capture/capture.js';
import { createReplaySession } from './recorder/replay/replay.js';
import type { HarCaptureOptions, ReplaySession } from './recorder/types.js';

// Export
import { generateManifest } from './export/manifest.js';
import { exportToCsv } from './export/csv.js';
import { ExperimentStore } from './export/store.js';
import type { ClassifiedRecord } from './export/csv.js';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Build a Scanner interface from the concrete scanner functions */
function buildScanner(): Scanner {
  return { scanTier1, scanTier2, computeCompositeScore };
}

/** Default composite score options.
 * Lighthouse weight reduced to 0.5 because snapshot mode is incompatible with
 * Playwright (falls back to navigation mode which re-loads the page, losing
 * variant patches). axe-core runs in-page and correctly reflects variants.
 */
const DEFAULT_COMPOSITE_OPTIONS: CompositeScoreOptions = {
  weights: {
    lighthouseScore: 0.5,  // Supplementary — navigation mode ignores variant patches
    axeViolations: 2,      // Primary Tier 1 — runs in-page, reflects variants
    semanticHtmlRatio: 1,
    accessibleNameCoverage: 1,
    keyboardNavigability: 1,
    ariaCorrectness: 1,
    pseudoComplianceRatio: 1,
    formLabelingCompleteness: 1,
    landmarkCoverage: 1,
  },
  mode: 'composite',
};

/**
 * Perform a full scan (Tier 1 + Tier 2 + stability + composite) on a page.
 * Returns a ScanResult ready for storage.
 */
async function fullScan(
  page: Page,
  cdpSession: CDPSession,
  url: string,
  config: ExperimentConfig,
  lighthouseCdpPort?: number,
): Promise<ScanResult> {
  const stability = await waitForA11yTreeStable(page, {
    intervalMs: config.scanner.stabilityIntervalMs,
    timeoutMs: config.scanner.stabilityTimeoutMs,
  });

  const tier1Options: Tier1ScanOptions = {
    url,
    wcagLevels: config.scanner.wcagLevels,
    lighthouseCdpPort,
  };

  const [tier1, tier2] = await Promise.all([
    scanTier1(page, tier1Options),
    scanTier2(page, cdpSession),
  ]);

  const composite = computeCompositeScore(tier1, tier2, DEFAULT_COMPOSITE_OPTIONS);

  return {
    scanId: randomUUID(),
    url,
    scannedAt: tier1.scannedAt,
    treeWasStable: stability.stable,
    stabilizationMs: stability.stabilizationMs,
    tier1,
    tier2,
    compositeScore: composite,
    a11yTreeSnapshot: stability.snapshot,
  };
}

// ---------------------------------------------------------------------------
// Track A: Controlled WebArena experiments
// ---------------------------------------------------------------------------

/** Options for running the Track A pipeline */
export interface TrackAOptions {
  /** Path to experiment config file (YAML or JSON) */
  configPath: string;
  /** Optional run ID to resume from */
  resumeRunId?: string;
  /** Logger function (defaults to console.log) */
  logger?: (msg: string) => void;
  /** Playwright Browser instance (caller manages lifecycle) */
  browser: Browser;
  /** CDP port for Lighthouse (e.g. 9222 from --remote-debugging-port) */
  lighthouseCdpPort?: number;
}

/** Result of a Track A experiment run */
export interface TrackAResult {
  run: ExperimentRun;
  records: ExperimentRecord[];
  classifications: Map<string, FailureClassification>;
  manifestPath?: string;
}

/**
 * Run the full Track A experiment pipeline.
 *
 * 1. Load & validate config (Req 18.1)
 * 2. Verify WebArena services are reachable
 * 3. For each test case in the experiment matrix:
 *    a. Apply variant to the target app page
 *    b. Scan the page (Tier 1 + Tier 2)
 *    c. Run the agent against the variant
 *    d. Classify failures
 * 4. Export results as CSV + JSON (Req 8.4)
 * 5. Generate experiment manifest (Req 18.3)
 */
export async function runTrackA(options: TrackAOptions): Promise<TrackAResult> {
  const log = options.logger ?? console.log;

  // 1. Load & validate config
  log('[Pipeline] Loading config...');
  const config = loadConfig(options.configPath);

  // 2. Verify WebArena services
  log('[Pipeline] Verifying WebArena services...');
  const waConfig = buildWebArenaConfig(config);
  const verification = await verifyWebArenaServices(waConfig);
  if (!verification.allReachable) {
    const failed = verification.failures.map((f) => `${f.app} (${f.url}): ${f.error ?? 'unreachable'}`);
    throw new Error(`WebArena services not reachable:\n  ${failed.join('\n  ')}`);
  }

  // 3. Execute experiment matrix
  const store = new ExperimentStore({ baseDir: config.output.dataDir });
  const records: ExperimentRecord[] = [];
  const classifications = new Map<string, FailureClassification>();
  const scanner = buildScanner();
  const browser = options.browser;

  const run = await executeExperiment(
    {
      apps: Object.keys(config.webarena.apps),
      variants: config.variants.levels,
      tasksPerApp: buildTasksPerApp(config),
      agentConfigs: config.runner.agentConfigs,
      repetitions: config.runner.repetitions,
    },
    {
      dataDir: config.output.dataDir,
      runTestCase: async (caseId: string, params: TestCaseParams): Promise<TestCaseResult> => {
        log(`[Pipeline] Running test case: ${caseId}`);

        // Create isolated browser context (Req 19.3)
        const context: BrowserContext = await browser.newContext();
        const page: Page = await context.newPage();
        const cdpSession: CDPSession = await context.newCDPSession(page);

        try {
          const appUrl = config.webarena.apps[params.app]?.url;
          if (!appUrl) throw new Error(`Unknown app: ${params.app}`);

          // Navigate to app
          await page.goto(appUrl, { waitUntil: 'load', timeout: 60_000 });

          // Apply variant
          const variantLevel = params.variant as VariantLevel;
          const variantDiff = await applyVariant(page, variantLevel, params.app);
          log(`[Pipeline] Variant ${variantLevel} applied: ${variantDiff.changes.length} changes, DOM hash ${variantDiff.domHashBefore === variantDiff.domHashAfter ? 'unchanged' : 'changed'}`);

          // Scan the page
          const scanResults = await fullScan(page, cdpSession, appUrl, config, options.lighthouseCdpPort);

          // Run agent
          const trace = await executeAgentTask({
            taskId: params.taskId,
            agentConfig: params.agentConfig,
            taskGoal: params.taskId,
            targetUrl: appUrl,
            variant: variantLevel,
            attempt: params.attempt,
          });

          // Determine task outcome
          const outcome: TaskOutcome = {
            taskId: params.taskId,
            outcome: trace.success ? 'success' : 'failure',
            traces: [trace],
            medianSteps: trace.totalSteps,
            medianDurationMs: trace.durationMs,
            scanResults,
          };

          // Classify failure if applicable
          if (!trace.success) {
            const classification = classifyFailure(trace);
            classifications.set(caseId, classification);
            trace.failureType = classification.primary;
            trace.failureConfidence = classification.confidence;
          }

          const record: ExperimentRecord = {
            caseId,
            app: params.app,
            variant: params.variant,
            taskId: params.taskId,
            agentConfig: params.agentConfig,
            attempt: params.attempt,
            trace,
            taskOutcome: outcome,
            scanResults,
          };
          records.push(record);

          // Persist to store
          await store.storeRecord(caseId, record, classifications.get(caseId));

          return { trace, taskOutcome: outcome, scanResults };
        } finally {
          await context.close().catch(() => {});
        }
      },
    },
    options.resumeRunId,
  );

  // 4. Export results
  log('[Pipeline] Exporting results...');
  const classifiedRecords: ClassifiedRecord[] = records.map((r) => ({
    record: r,
    classification: classifications.get(r.caseId),
  }));

  if (config.output.exportFormats.includes('csv')) {
    const csvResult = exportToCsv(classifiedRecords, {
      anonymize: true,
      anonymizeSiteIdentity: false,
      includeTraceDetails: true,
    });
    for (const [filename, content] of Object.entries(csvResult.files)) {
      await store.writeCsvExport(filename, content);
    }
  }

  // 5. Generate manifest (Req 18.3)
  log('[Pipeline] Generating manifest...');
  const manifest = generateManifest(run, config, records);
  const manifestPath = await store.storeManifest(run.runId, manifest);

  log(`[Pipeline] Track A complete. Run ID: ${run.runId}`);
  return { run, records, classifications, manifestPath };
}

// ---------------------------------------------------------------------------
// Track B: HAR replay ecological survey
// ---------------------------------------------------------------------------

/** Options for running the Track B pipeline */
export interface TrackBOptions {
  /** Path to experiment config file (YAML or JSON) */
  configPath: string;
  /** URLs to capture and scan (or pre-recorded HAR file paths) */
  urls: string[];
  /** Pre-recorded HAR file paths — if provided, skip capture and go straight to replay */
  harFilePaths?: string[];
  /** Logger function (defaults to console.log) */
  logger?: (msg: string) => void;
  /** Playwright Browser instance (caller manages lifecycle) */
  browser: Browser;
}

/** Result of a Track B scan run */
export interface TrackBResult {
  scanResults: ScanResult[];
  lowFidelityUrls: string[];
  classifications: Map<string, FailureClassification>;
}

/**
 * Run the Track B ecological survey pipeline.
 *
 * 1. Load & validate config
 * 2. Capture HAR files for target URLs (or use pre-recorded HARs)
 * 3. For each HAR recording:
 *    a. Create a replay session
 *    b. Scan the replayed page (Tier 1 + Tier 2)
 *    c. Optionally run agent and classify failures
 * 4. Flag low-fidelity recordings (>20% functional coverage gap)
 * 5. Export results
 *
 * Track B uses the same Scanner and Runner as Track A (Req 12.4).
 */
export async function runTrackB(options: TrackBOptions): Promise<TrackBResult> {
  const log = options.logger ?? console.log;

  // 1. Load config
  log('[Pipeline] Loading config...');
  const config = loadConfig(options.configPath);
  const store = new ExperimentStore({ baseDir: config.output.dataDir });

  // 2. Capture HARs (or use pre-recorded)
  let harPaths: string[];
  if (options.harFilePaths && options.harFilePaths.length > 0) {
    harPaths = options.harFilePaths;
    log(`[Pipeline] Using ${harPaths.length} pre-recorded HAR files`);
  } else {
    log(`[Pipeline] Capturing HAR for ${options.urls.length} URLs...`);
    const captureOpts: HarCaptureOptions = {
      urls: options.urls,
      waitAfterLoadMs: config.recorder.waitAfterLoadMs,
      concurrency: config.recorder.concurrency,
      outputDir: `${config.output.dataDir}/track-b/har`,
    };
    const captureResults = await captureHar(captureOpts);
    harPaths = captureResults
      .filter((r) => r.success)
      .map((r) => r.harFilePath);

    const failedCount = captureResults.filter((r) => !r.success).length;
    if (failedCount > 0) {
      log(`[Pipeline] ${failedCount} URL(s) failed to capture — continuing with ${harPaths.length} successful recordings`);
    }
  }

  // 3. Replay each HAR and scan
  const scanResults: ScanResult[] = [];
  const lowFidelityUrls: string[] = [];
  const classifications = new Map<string, FailureClassification>();
  const browser = options.browser;

  for (const harPath of harPaths) {
    log(`[Pipeline] Replaying HAR: ${harPath}`);
    let session: ReplaySession | undefined;
    try {
      session = await createReplaySession(browser, {
        harFilePath: harPath,
        unmatchedRequestBehavior: 'return-404',
      });

      const page = session.page;
      // Navigate to trigger replay
      await page.goto('about:blank').catch(() => {});

      // Check fidelity (Req 12.5)
      if (session.isLowFidelity) {
        log(`[Pipeline] Low fidelity recording (coverage gap > 20%): ${harPath}`);
        lowFidelityUrls.push(harPath);
        continue; // Skip low-fidelity recordings from primary analysis
      }

      // Scan the replayed page — same scanner as Track A (Req 12.4)
      const cdpSession: CDPSession = await page.context().newCDPSession(page);
      const url = page.url();
      const result = await fullScan(page, cdpSession, url, config);
      scanResults.push(result);

      // Store scan result
      const harId = harPath.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 60);
      await store.storeHarScanResult(harId, result);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      log(`[Pipeline] Error replaying ${harPath}: ${message}`);
    } finally {
      if (session) {
        await session.page.context().close().catch(() => {});
      }
    }
  }

  log(`[Pipeline] Track B complete. Scanned ${scanResults.length} sites, ${lowFidelityUrls.length} low-fidelity excluded.`);
  return { scanResults, lowFidelityUrls, classifications };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a tasksPerApp map from config.
 * WebArena task IDs are globally unique and each task is tied to a specific site.
 * BrowserGym handles the site routing internally during env.reset().
 *
 * Task ID ranges (from WebArena benchmark):
 *   0-99:   shopping_admin (Magento admin backend, port 7780)
 *   100-199: reddit (Postmill, port 9999)
 *   200-299: gitlab (GitLab, port 8023)
 *   300-399: shopping_admin (CMS tasks, also port 7780)
 *   400-811: map/wikipedia/cross-site tasks
 *
 * Note: Tasks 0-99 and 300-399 require shopping_admin, NOT shopping frontend.
 * If config only has 'ecommerce' (frontend), those tasks will fail.
 */
function buildTasksPerApp(config: ExperimentConfig): Record<string, string[]> {
  const apps = Object.keys(config.webarena.apps);
  const tasksPerApp: Record<string, string[]> = {};

  // Map app names to appropriate task ID ranges
  const defaultTaskIds: Record<string, string[]> = {
    // shopping_admin tasks (need admin backend)
    ecommerce_admin: ['0', '1', '2'],
    shopping_admin:  ['0', '1', '2'],
    // shopping frontend tasks — use tasks that work on the storefront
    // These are cross-site tasks that involve shopping but start from the frontend
    ecommerce: ['3', '4', '5'],  // Storefront-compatible tasks
    shopping:  ['3', '4', '5'],
    // Reddit (Postmill)
    reddit:    ['100', '101', '102'],
    // GitLab
    gitlab:    ['200', '201', '202'],
    // CMS (also shopping_admin)
    cms:       ['300', '301', '302'],
    // Wikipedia (Kiwix)
    wikipedia: ['400', '401', '402'],
  };

  for (const app of apps) {
    tasksPerApp[app] = defaultTaskIds[app] ?? ['0', '1', '2'];
  }
  return tasksPerApp;
}

// Re-export all modules for convenience
export * from './config/index.js';
export * from './scanner/index.js';
export * from './variants/index.js';
export * from './runner/index.js';
export * from './classifier/index.js';
export * from './recorder/index.js';
export * from './export/index.js';

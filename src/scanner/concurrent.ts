// Module 1: Scanner — Concurrent URL scanning with browser context isolation
// Supports concurrent scanning of multiple URLs with configurable limit (default 5).
// Each scan runs in an isolated browser context to prevent cross-contamination.
// Requirements: 19.1, 19.3

import { randomUUID } from 'node:crypto';
import type { Browser, BrowserContext, CDPSession, Page } from 'playwright';
import { scanTier1 } from './tier1/scan.js';
import { scanTier2 } from './tier2/scan.js';
import { waitForA11yTreeStable } from './snapshot/stability.js';
import { computeCompositeScore } from './composite.js';
import type {
  ScanResult,
  Tier1ScanOptions,
  CompositeScoreOptions,
} from './types.js';

/** Options for concurrent scanning */
export interface ConcurrentScanOptions {
  /** URLs to scan */
  urls: string[];
  /** WCAG conformance levels for axe-core filtering */
  wcagLevels: ('A' | 'AA' | 'AAA')[];
  /** Maximum concurrent scans (default 5, Req 19.1) */
  concurrency?: number;
  /** Optional composite score options; omit to skip composite computation */
  compositeOptions?: CompositeScoreOptions;
  /** A11y tree stability interval in ms (default 2000) */
  stabilityIntervalMs?: number;
  /** A11y tree stability timeout in ms (default 30000) */
  stabilityTimeoutMs?: number;
}

/** Result of scanning a single URL (success or error) */
export interface UrlScanOutcome {
  url: string;
  result?: ScanResult;
  error?: string;
}

/** Result of the full concurrent scan batch */
export interface ConcurrentScanResult {
  outcomes: UrlScanOutcome[];
  totalDurationMs: number;
}

/**
 * Scan a single URL in an isolated browser context.
 * Creates its own context and CDP session, cleans up on completion or error.
 */
async function scanUrl(
  browser: Browser,
  url: string,
  options: ConcurrentScanOptions,
): Promise<ScanResult> {
  let context: BrowserContext | undefined;
  try {
    // Req 19.3: Isolate each browser context per scan
    context = await browser.newContext();
    const page: Page = await context.newPage();
    const cdpSession: CDPSession = await context.newCDPSession(page);

    await page.goto(url, { waitUntil: 'load', timeout: 60_000 });

    // Wait for A11y tree stability
    const stability = await waitForA11yTreeStable(page, {
      intervalMs: options.stabilityIntervalMs ?? 2000,
      timeoutMs: options.stabilityTimeoutMs ?? 30000,
    });

    // Run Tier 1 + Tier 2 scans
    const tier1Options: Tier1ScanOptions = { url, wcagLevels: options.wcagLevels };
    const [tier1, tier2] = await Promise.all([
      scanTier1(page, tier1Options),
      scanTier2(page, cdpSession),
    ]);

    // Optional composite score
    const composite = options.compositeOptions
      ? computeCompositeScore(tier1, tier2, options.compositeOptions)
      : null;

    const scanResult: ScanResult = {
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

    await context.close();
    context = undefined;
    return scanResult;
  } catch (err) {
    if (context) {
      await context.close().catch(() => {});
    }
    throw err;
  }
}

/**
 * Scan multiple URLs concurrently with browser context isolation.
 *
 * Processes URLs in batches of `concurrency` (default 5, Req 19.1).
 * Each URL gets its own isolated browser context (Req 19.3).
 * Errors on individual URLs are logged and do not block remaining scans.
 *
 * @param browser - Playwright Browser instance (caller manages lifecycle)
 * @param options - Scan configuration including URLs and concurrency limit
 * @returns ConcurrentScanResult with per-URL outcomes and total duration
 */
export async function scanUrlsConcurrently(
  browser: Browser,
  options: ConcurrentScanOptions,
): Promise<ConcurrentScanResult> {
  const concurrency = options.concurrency ?? 5;
  const startTime = Date.now();
  const outcomes: UrlScanOutcome[] = [];

  // Process in batches to respect concurrency limit
  for (let i = 0; i < options.urls.length; i += concurrency) {
    const batch = options.urls.slice(i, i + concurrency);
    const settled = await Promise.allSettled(
      batch.map((url) => scanUrl(browser, url, options)),
    );

    for (let j = 0; j < settled.length; j++) {
      const url = batch[j];
      const entry = settled[j];
      if (entry.status === 'fulfilled') {
        outcomes.push({ url, result: entry.value });
      } else {
        const message = entry.reason instanceof Error
          ? entry.reason.message
          : String(entry.reason);
        console.error(`[Scanner] Concurrent scan failed for "${url}": ${message}`);
        outcomes.push({ url, error: message });
      }
    }
  }

  return {
    outcomes,
    totalDurationMs: Date.now() - startTime,
  };
}

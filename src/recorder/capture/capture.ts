/**
 * HAR Capture — navigates to URLs via Playwright, captures full HTTP transaction logs as HAR files.
 * Supports concurrent capture with configurable limit, metadata sidecar generation,
 * and graceful error handling (log and continue on failure).
 *
 * Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 19.1
 */

import { chromium } from 'playwright';
import type { Browser, BrowserContext, Page } from 'playwright';
import * as path from 'node:path';
import * as fs from 'node:fs/promises';
import type { HarCaptureOptions, HarCaptureResult, HarMetadata } from '../types.js';

/** Default options applied when not specified by the caller */
const DEFAULTS = {
  waitAfterLoadMs: 10_000,
  concurrency: 5,
} as const;

/**
 * Capture a single URL as a HAR file with metadata sidecar.
 * Uses Playwright's `routeFromHAR` in recording mode to capture all sub-resource requests.
 */
async function captureSingleUrl(
  browser: Browser,
  url: string,
  outputDir: string,
  waitAfterLoadMs: number,
): Promise<HarCaptureResult> {
  const sanitized = url.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 80);
  const timestamp = new Date().toISOString();
  const harFileName = `${sanitized}_${Date.now()}.har`;
  const harFilePath = path.join(outputDir, harFileName);

  let context: BrowserContext | undefined;
  try {
    context = await browser.newContext();
    const page: Page = await context.newPage();

    // Req 11.1, 11.2: Record all HTTP transactions including sub-resources
    await page.routeFromHAR(harFilePath, { update: true });

    // Navigate and wait for load event
    await page.goto(url, { waitUntil: 'load', timeout: 60_000 });

    // Req 11.3: Wait for dynamic content after load
    await page.waitForTimeout(waitAfterLoadMs);

    // Req 11.4: Extract metadata from response headers
    const pageLanguage = await page.evaluate(() => {
      const meta = document.querySelector('meta[http-equiv="Content-Language"]');
      return meta?.getAttribute('content') ?? document.documentElement.lang ?? '';
    });

    const metadata: HarMetadata = {
      recordingTimestamp: timestamp,
      targetUrl: url,
      geoRegion: '',              // Set by caller or external config
      sectorClassification: '',   // Set by caller or external config
      pageLanguage,
    };

    // Write metadata sidecar JSON
    const metadataPath = harFilePath.replace(/\.har$/, '.metadata.json');
    await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8');

    await context.close();
    context = undefined;

    return { harFilePath, metadata, success: true };
  } catch (err) {
    // Req 11.5: Log error and continue
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[HAR Capture] Failed to capture ${url}: ${message}`);

    if (context) {
      await context.close().catch(() => {});
    }

    return {
      harFilePath: '',
      metadata: {
        recordingTimestamp: new Date().toISOString(),
        targetUrl: url,
        geoRegion: '',
        sectorClassification: '',
        pageLanguage: '',
      },
      success: false,
      error: message,
    };
  }
}

/**
 * Capture HAR files for a list of URLs with concurrent execution.
 *
 * Req 11.6, 19.1: Supports at least 50 websites with configurable concurrency (default 5).
 * Errors on individual URLs are logged and do not block remaining captures.
 */
export async function captureHar(options: HarCaptureOptions): Promise<HarCaptureResult[]> {
  const waitAfterLoadMs = options.waitAfterLoadMs ?? DEFAULTS.waitAfterLoadMs;
  const concurrency = options.concurrency ?? DEFAULTS.concurrency;
  const outputDir = options.outputDir;

  // Ensure output directory exists
  await fs.mkdir(outputDir, { recursive: true });

  // Use caller-provided browser if available, otherwise launch our own
  const ownBrowser = !options.browser;
  const browser = options.browser ?? await chromium.launch({ headless: true });
  const results: HarCaptureResult[] = [];

  // Process URLs in batches of `concurrency`
  const urls = [...options.urls];
  for (let i = 0; i < urls.length; i += concurrency) {
    const batch = urls.slice(i, i + concurrency);
    const batchResults = await Promise.allSettled(
      batch.map((url) => captureSingleUrl(browser, url, outputDir, waitAfterLoadMs)),
    );

    for (const settled of batchResults) {
      if (settled.status === 'fulfilled') {
        results.push(settled.value);
      } else {
        // Should not happen since captureSingleUrl catches internally, but be safe
        console.error(`[HAR Capture] Unexpected batch error: ${settled.reason}`);
        results.push({
          harFilePath: '',
          metadata: {
            recordingTimestamp: new Date().toISOString(),
            targetUrl: '',
            geoRegion: '',
            sectorClassification: '',
            pageLanguage: '',
          },
          success: false,
          error: String(settled.reason),
        });
      }
    }
  }

  // Only close the browser if we launched it ourselves
  if (ownBrowser) {
    await browser.close();
  }
  return results;
}

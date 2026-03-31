// Module 1: Scanner — A11y Tree Stability Detector
// Requirements: 3.1, 3.2, 3.3, 3.4

import { createHash } from 'node:crypto';
import type { Page } from 'playwright';
import type {
  StabilityOptions,
  StabilityResult,
  AccessibilityTreeSnapshot,
} from '../types.js';

/** Default stability detection options */
const DEFAULT_OPTIONS: StabilityOptions = {
  intervalMs: 2000,
  timeoutMs: 30000,
  maxRetries: 15, // 30000 / 2000
};

/**
 * Compute SHA-256 hash of a string.
 */
function sha256(data: string): string {
  return createHash('sha256').update(data).digest('hex');
}

/**
 * Take an accessibility tree snapshot from the page using Playwright's
 * `locator.ariaSnapshot()` API. Returns the raw YAML string for hashing
 * and a parsed object for the StabilityResult snapshot field.
 *
 * Returns empty results if the snapshot fails (log and continue).
 */
async function takeSnapshot(
  page: Page,
): Promise<{ raw: string; parsed: AccessibilityTreeSnapshot }> {
  try {
    const raw = await page.locator('body').ariaSnapshot();
    // Store the raw YAML as a structured snapshot object
    const parsed: AccessibilityTreeSnapshot = { ariaTree: raw };
    return { raw, parsed };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[Scanner] Failed to take A11y tree snapshot: ${message}`);
    return { raw: '', parsed: {} };
  }
}

/**
 * Wait for the Accessibility Tree to stabilize by polling at a configurable
 * interval and comparing SHA-256 hashes of consecutive serialized snapshots.
 *
 * Returns stable when two consecutive snapshots match (Req 3.2).
 * Logs a warning and proceeds with the latest snapshot on timeout (Req 3.3).
 * Serializes the snapshot used for measurement alongside results (Req 3.4).
 *
 * @param page - Playwright Page object (must be navigated to the target URL)
 * @param options - Partial stability options; unspecified fields use defaults
 * @returns StabilityResult with stability status, snapshot, timing, and attempt count
 */
export async function waitForA11yTreeStable(
  page: Page,
  options?: Partial<StabilityOptions>,
): Promise<StabilityResult> {
  const intervalMs = options?.intervalMs ?? DEFAULT_OPTIONS.intervalMs;
  const timeoutMs = options?.timeoutMs ?? DEFAULT_OPTIONS.timeoutMs;
  const maxRetries = options?.maxRetries ?? Math.floor(timeoutMs / intervalMs);

  const startTime = Date.now();
  let attempts = 0;
  let previousHash: string | null = null;
  let latestSnapshot: AccessibilityTreeSnapshot = {};

  while (Date.now() - startTime < timeoutMs && attempts < maxRetries) {
    const { raw, parsed } = await takeSnapshot(page);
    latestSnapshot = parsed;
    attempts++;

    const currentHash = sha256(raw);

    if (previousHash !== null && currentHash === previousHash) {
      // Two consecutive snapshots match — tree is stable (Req 3.2)
      return {
        stable: true,
        snapshot: latestSnapshot,
        stabilizationMs: Date.now() - startTime,
        attempts,
      };
    }

    previousHash = currentHash;

    // Wait before next poll (Req 3.1), but only if we haven't exceeded timeout
    const elapsed = Date.now() - startTime;
    if (elapsed + intervalMs < timeoutMs) {
      await new Promise<void>((resolve) => setTimeout(resolve, intervalMs));
    }
  }

  // Timeout reached — log warning and proceed with latest snapshot (Req 3.3)
  const url = page.url();
  console.warn(
    `[Scanner] A11y tree did not stabilize within ${timeoutMs}ms for URL "${url}". ` +
    `Proceeding with latest snapshot after ${attempts} attempt(s).`,
  );

  return {
    stable: false,
    snapshot: latestSnapshot,
    stabilizationMs: Date.now() - startTime,
    attempts,
  };
}

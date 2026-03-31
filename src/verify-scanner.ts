/**
 * Local Scanner verification script.
 * Scans real websites with Tier 1 + Tier 2 to verify the pipeline.
 *
 * Usage: npm run build && node dist/verify-scanner.js
 */

import { chromium } from 'playwright';
import { scanTier1 } from './scanner/tier1/scan.js';
import { scanTier2 } from './scanner/tier2/scan.js';
import { waitForA11yTreeStable } from './scanner/snapshot/stability.js';
import { computeCompositeScore } from './scanner/composite.js';
import type { CompositeScoreOptions } from './scanner/types.js';

const URLS = [
  'https://example.com',
  'https://www.w3.org',
  'https://developer.mozilla.org/en-US/',
];

const COMPOSITE_OPTIONS: CompositeScoreOptions = {
  weights: {
    lighthouseScore: 1, axeViolations: 1, semanticHtmlRatio: 1,
    accessibleNameCoverage: 1, keyboardNavigability: 1, ariaCorrectness: 1,
    pseudoComplianceRatio: 1, formLabelingCompleteness: 1, landmarkCoverage: 1,
  },
  mode: 'composite',
};

async function main() {
  console.log('=== Scanner Verification ===\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--remote-debugging-port=9222'],
  });

  for (const url of URLS) {
    console.log(`--- ${url} ---`);
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      await page.goto(url, { waitUntil: 'load', timeout: 30_000 });

      const stability = await waitForA11yTreeStable(page, {
        intervalMs: 1500, timeoutMs: 10_000,
      });
      console.log(`  Stability: ${stability.stable ? 'stable' : 'timeout'} (${stability.stabilizationMs}ms)`);

      const tier1 = await scanTier1(page, { url, wcagLevels: ['A', 'AA'], lighthouseCdpPort: 9222 });
      console.log(`  Tier 1: axe violations=${tier1.axeCore.violationCount}, Lighthouse=${tier1.lighthouse.accessibilityScore}`);

      const cdpSession = await context.newCDPSession(page);
      const tier2 = await scanTier2(page, cdpSession);
      console.log(`  Tier 2:`);
      console.log(`    semanticHtmlRatio:        ${tier2.semanticHtmlRatio.toFixed(3)}`);
      console.log(`    accessibleNameCoverage:   ${tier2.accessibleNameCoverage.toFixed(3)}`);
      console.log(`    keyboardNavigability:     ${tier2.keyboardNavigability.toFixed(3)}`);
      console.log(`    ariaCorrectness:          ${tier2.ariaCorrectness.toFixed(3)}`);
      console.log(`    pseudoComplianceCount:    ${tier2.pseudoComplianceCount}`);
      console.log(`    formLabelingCompleteness: ${tier2.formLabelingCompleteness.toFixed(3)}`);
      console.log(`    landmarkCoverage:         ${tier2.landmarkCoverage.toFixed(3)}`);

      const composite = computeCompositeScore(tier1, tier2, COMPOSITE_OPTIONS);
      console.log(`  Composite: ${composite.compositeScore.toFixed(3)}`);
    } catch (err) {
      console.log(`  ERROR: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      await context.close();
    }
    console.log();
  }

  await browser.close();
  console.log('=== Done ===');
}

main().catch((err) => { console.error(err); process.exit(1); });

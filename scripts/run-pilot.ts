#!/usr/bin/env npx tsx
/**
 * Pilot experiment runner — minimal Track A run.
 *
 * Runs: 1 app (ecommerce) × 2 variants (low, high) × 3 tasks × 1 LLM × 3 reps = 18 cases
 * Estimated: ~2 hours, ~$11 LLM cost
 *
 * Usage: npx tsx scripts/run-pilot.ts
 */

import { chromium } from 'playwright';
import { runTrackA } from '../src/index.js';

async function main() {
  console.log('=== Pilot Experiment (Track A) ===\n');

  const browser = await chromium.launch({ headless: true });

  try {
    const result = await runTrackA({
      configPath: './config-pilot.yaml',
      browser,
      logger: (msg) => console.log(msg),
    });

    console.log(`\n=== Pilot Complete ===`);
    console.log(`Run ID: ${result.run.runId}`);
    console.log(`Records: ${result.records.length}`);
    console.log(`Classifications: ${result.classifications.size}`);
    if (result.manifestPath) {
      console.log(`Manifest: ${result.manifestPath}`);
    }

    // Summary stats
    const successes = result.records.filter((r) => r.trace.success).length;
    const failures = result.records.length - successes;
    console.log(`\nSuccess: ${successes}/${result.records.length} (${((successes / result.records.length) * 100).toFixed(1)}%)`);
    console.log(`Failures: ${failures}`);

    // Per-variant breakdown
    const byVariant = new Map<string, { total: number; success: number }>();
    for (const r of result.records) {
      const v = r.variant;
      const entry = byVariant.get(v) ?? { total: 0, success: 0 };
      entry.total++;
      if (r.trace.success) entry.success++;
      byVariant.set(v, entry);
    }
    console.log('\nPer-variant success rates:');
    for (const [variant, stats] of byVariant) {
      console.log(`  ${variant}: ${stats.success}/${stats.total} (${((stats.success / stats.total) * 100).toFixed(1)}%)`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

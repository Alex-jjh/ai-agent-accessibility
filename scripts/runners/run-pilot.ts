#!/usr/bin/env npx tsx
/**
 * Pilot experiment runner — Track A.
 *
 * Reads config from config-pilot.yaml which defines:
 *   - apps, variants, task IDs (via tasksPerApp or defaults)
 *   - agent configs (LLM backends, observation modes)
 *   - repetitions
 *
 * Total cases = apps × variants × tasks × agentConfigs × repetitions
 * (see config-pilot.yaml for current values)
 *
 * Usage:
 *   npx tsx scripts/run-pilot.ts
 *   npx tsx scripts/run-pilot.ts --resume <runId>
 *   npx tsx scripts/run-pilot.ts --config ./my-config.yaml
 *   npx tsx scripts/run-pilot.ts --cdp-port 9223
 */

import { chromium } from 'playwright';
import { runTrackA } from '../../src/index.js';

const args = process.argv.slice(2);
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './config-pilot.yaml';
const resumeRunId = args.find((_, i) => args[i - 1] === '--resume');
const cdpPort = parseInt(args.find((_, i) => args[i - 1] === '--cdp-port') ?? '9222');

async function main() {
  console.log('=== Pilot Experiment (Track A) ===');
  console.log(`Config: ${configPath}`);
  if (resumeRunId) console.log(`Resuming run: ${resumeRunId}`);
  console.log('');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', `--remote-debugging-port=${cdpPort}`],
  });

  try {
    const result = await runTrackA({
      configPath,
      browser,
      lighthouseCdpPort: cdpPort,
      resumeRunId,
      logger: (msg) => console.log(msg),
    });

    console.log(`\n=== Pilot Complete ===`);
    console.log(`Run ID: ${result.run.runId}`);
    console.log(`Records: ${result.records.length}`);
    console.log(`Classifications: ${result.classifications.size}`);
    if (result.manifestPath) {
      console.log(`Manifest: ${result.manifestPath}`);
    }

    if (result.records.length === 0) {
      console.log('\nNo records produced. Check config and WebArena connectivity.');
      return;
    }

    // Summary stats
    const successes = result.records.filter((r) => r.trace.success).length;
    const failures = result.records.length - successes;
    const pct = ((successes / result.records.length) * 100).toFixed(1);
    console.log(`\nSuccess: ${successes}/${result.records.length} (${pct}%)`);
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
      const varPct = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(1) : '0.0';
      console.log(`  ${variant}: ${stats.success}/${stats.total} (${varPct}%)`);
    }

    // Per-app breakdown
    const byApp = new Map<string, { total: number; success: number }>();
    for (const r of result.records) {
      const entry = byApp.get(r.app) ?? { total: 0, success: 0 };
      entry.total++;
      if (r.trace.success) entry.success++;
      byApp.set(r.app, entry);
    }
    console.log('\nPer-app success rates:');
    for (const [app, stats] of byApp) {
      const appPct = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(1) : '0.0';
      console.log(`  ${app}: ${stats.success}/${stats.total} (${appPct}%)`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

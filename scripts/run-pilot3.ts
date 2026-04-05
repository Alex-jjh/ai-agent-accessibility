#!/usr/bin/env npx tsx
/**
 * Pilot 3 experiment runner — Track A.
 *
 * Design: 6 tasks × 4 variants (low/medium-low/base/high) × 5 reps = 120 cases
 * Estimated time: ~6 hours
 *
 * Changes from Pilot 2:
 *   - Excluded ceiling/floor tasks (27, 47, 50)
 *   - Added medium-low variant for dose-response curve
 *   - Increased reps from 3 to 5 for better statistical power
 *   - send_msg_to_user bug fixed (balanced-paren extraction)
 *   - Variant patches more aggressive (wider composite score range)
 *   - F_UNK classifier for honest failure taxonomy
 *
 * Usage:
 *   npx tsx scripts/run-pilot3.ts
 *   npx tsx scripts/run-pilot3.ts --resume <runId>
 *   npx tsx scripts/run-pilot3.ts --dry-run
 */

import { chromium } from 'playwright';
import { runTrackA } from '../src/index.js';
import { loadConfig } from '../src/config/loader.js';
import * as fs from 'node:fs';
import * as path from 'node:path';

const args = process.argv.slice(2);
const CONFIG_PATH = args.find((_, i) => args[i - 1] === '--config') ?? './config-pilot3.yaml';
const resumeRunId = args.find((_, i) => args[i - 1] === '--resume');
const dryRun = args.includes('--dry-run');
const cdpPort = parseInt(args.find((_, i) => args[i - 1] === '--cdp-port') ?? '9222');

async function main() {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║     Pilot 3 Experiment — Track A         ║');
  console.log('╚══════════════════════════════════════════╝');
  console.log('');

  // Load and validate config
  const config = loadConfig(CONFIG_PATH);
  const variants = config.variants.levels;
  const tasks: string[] = [];
  for (const [app, ids] of Object.entries(config.webarena.tasksPerApp ?? {})) {
    for (const id of ids) {
      tasks.push(`${app}:${id}`);
    }
  }
  const reps = config.runner.repetitions;
  const agentCount = config.runner.agentConfigs?.length ?? 1;
  const totalCases = tasks.length * variants.length * reps * agentCount;

  console.log(`Config:     ${CONFIG_PATH}`);
  console.log(`Tasks:      ${tasks.length} (${tasks.join(', ')})`);
  console.log(`Variants:   ${variants.join(', ')}`);
  console.log(`Reps:       ${reps}`);
  console.log(`Agents:     ${agentCount} (${(config.runner.agentConfigs ?? []).map((a: any) => a.observationMode).join(', ')})`);
  console.log(`Total:      ${totalCases} cases`);
  console.log(`Est. time:  ~${Math.ceil(totalCases * 3 / 60)} hours`);
  console.log(`Output:     ${config.output.dataDir}`);
  if (resumeRunId) console.log(`Resuming:   ${resumeRunId}`);
  console.log('');

  // Pre-flight checks
  console.log('Pre-flight checks:');

  // 1. Check data directory
  const dataDir = config.output.dataDir;
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
    console.log(`  ✓ Created data directory: ${dataDir}`);
  } else {
    console.log(`  ✓ Data directory exists: ${dataDir}`);
  }

  // 2. Check variant inject scripts exist
  const injectDir = path.join('src', 'variants', 'patches', 'inject');
  for (const v of variants) {
    if (v === 'base') continue;
    const scriptName = `apply-${v}.js`;
    const scriptPath = path.join(injectDir, scriptName);
    if (fs.existsSync(scriptPath)) {
      console.log(`  ✓ Variant script: ${scriptName}`);
    } else {
      console.error(`  ✗ Missing variant script: ${scriptPath}`);
      process.exit(1);
    }
  }

  // 3. Check bridge script exists
  const bridgePath = path.join('src', 'runner', 'browsergym_bridge.py');
  if (fs.existsSync(bridgePath)) {
    console.log(`  ✓ Bridge script: ${bridgePath}`);
  } else {
    console.error(`  ✗ Missing bridge script: ${bridgePath}`);
    process.exit(1);
  }

  console.log('');

  if (dryRun) {
    console.log('Dry run — would execute the following matrix:');
    console.log('');
    let caseNum = 0;
    const agents = config.runner.agentConfigs ?? [{ observationMode: 'text-only' }];
    for (const agent of agents) {
      for (const task of tasks) {
        for (const variant of variants) {
          for (let rep = 1; rep <= reps; rep++) {
            caseNum++;
            const mode = (agent as any).observationMode ?? 'text-only';
            console.log(`  ${String(caseNum).padStart(3)}. [${mode}] ${task} × ${variant} × rep${rep}`);
          }
        }
      }
    }
    console.log(`\nTotal: ${caseNum} cases`);
    return;
  }

  // Launch browser and run
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', `--remote-debugging-port=${cdpPort}`],
  });

  const startTime = Date.now();

  try {
    const result = await runTrackA({
      configPath: CONFIG_PATH,
      browser,
      lighthouseCdpPort: cdpPort,
      resumeRunId,
      logger: (msg) => console.log(msg),
    });

    const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1);

    console.log('');
    console.log('╔══════════════════════════════════════════╗');
    console.log('║          Pilot 3 Complete                ║');
    console.log('╚══════════════════════════════════════════╝');
    console.log('');
    console.log(`Run ID:     ${result.run.runId}`);
    console.log(`Duration:   ${elapsed} min`);
    console.log(`Records:    ${result.records.length}`);
    if (result.manifestPath) {
      console.log(`Manifest:   ${result.manifestPath}`);
    }

    if (result.records.length === 0) {
      console.log('\nNo records produced. Check config and WebArena connectivity.');
      return;
    }

    // Overall stats
    const successes = result.records.filter((r) => r.trace.success).length;
    const pct = ((successes / result.records.length) * 100).toFixed(1);
    console.log(`\nOverall:    ${successes}/${result.records.length} (${pct}%)`);

    // Per-variant breakdown
    const byVariant = new Map<string, { total: number; success: number }>();
    for (const r of result.records) {
      const v = r.variant;
      const entry = byVariant.get(v) ?? { total: 0, success: 0 };
      entry.total++;
      if (r.trace.success) entry.success++;
      byVariant.set(v, entry);
    }
    console.log('\nPer-variant:');
    for (const v of variants) {
      const stats = byVariant.get(v) ?? { total: 0, success: 0 };
      const varPct = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(1) : '0.0';
      console.log(`  ${v.padEnd(12)} ${stats.success}/${stats.total} (${varPct}%)`);
    }

    // Per-task × variant matrix
    console.log('\nTask × Variant matrix:');
    const header = '  Task'.padEnd(28) + variants.map(v => v.padEnd(14)).join('');
    console.log(header);
    console.log('  ' + '─'.repeat(header.length - 2));

    const byTaskVariant = new Map<string, { total: number; success: number }>();
    for (const r of result.records) {
      const key = `${r.app}:${r.trace.taskId}|${r.variant}`;
      const entry = byTaskVariant.get(key) ?? { total: 0, success: 0 };
      entry.total++;
      if (r.trace.success) entry.success++;
      byTaskVariant.set(key, entry);
    }

    for (const task of tasks) {
      let line = `  ${task}`.padEnd(28);
      for (const v of variants) {
        // Task format in the map might differ — try both formats
        const key = `${task}|${v}`;
        const stats = byTaskVariant.get(key);
        if (stats) {
          const cellPct = ((stats.success / stats.total) * 100).toFixed(0);
          line += `${stats.success}/${stats.total} (${cellPct}%)`.padEnd(14);
        } else {
          line += '—'.padEnd(14);
        }
      }
      console.log(line);
    }

    // Failure classification summary
    if (result.classifications.size > 0) {
      const failureTypes = new Map<string, number>();
      for (const [, cls] of result.classifications) {
        const t = cls.primary;
        failureTypes.set(t, (failureTypes.get(t) ?? 0) + 1);
      }
      console.log('\nFailure taxonomy:');
      for (const [type, count] of [...failureTypes.entries()].sort((a, b) => b[1] - a[1])) {
        console.log(`  ${type}: ${count}`);
      }
    }

    // Token usage summary
    const tokensByVariant = new Map<string, number[]>();
    for (const r of result.records) {
      const v = r.variant;
      const arr = tokensByVariant.get(v) ?? [];
      arr.push(r.trace.totalTokens);
      tokensByVariant.set(v, arr);
    }
    console.log('\nAvg tokens per variant:');
    for (const v of variants) {
      const tokens = tokensByVariant.get(v) ?? [];
      const avg = tokens.length > 0 ? Math.round(tokens.reduce((a, b) => a + b, 0) / tokens.length) : 0;
      console.log(`  ${v.padEnd(12)} ${avg.toLocaleString()}`);
    }

    console.log(`\nData saved to: ${config.output.dataDir}`);
    console.log('Next: run scripts/sync-to-s3.sh to backup data');

  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error('Pilot 3 failed:', err);
  process.exit(1);
});

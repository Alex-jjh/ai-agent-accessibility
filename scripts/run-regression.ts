#!/usr/bin/env npx tsx
/**
 * Regression test — run specific WebArena tasks to verify bug fixes.
 *
 * Tests:
 * - reddit 102: previously successful, should still work
 * - reddit 100: previously failed with F_REA (agent gave up), might improve with better prompt
 * - reddit 101: previously failed with escape issues
 * - ecommerce 2: previously stuck on login loop (task design issue, expect fail)
 * - wikipedia 0: previously failed with noop loop
 * - wikipedia 1: previously failed with 30-step timeout
 *
 * Usage: npx tsx scripts/run-regression.ts
 */

import { chromium } from 'playwright';
import { loadConfig } from '../src/config/index.js';
import { executeAgentTask } from '../src/runner/agents/executor.js';
import { writeFileSync, mkdirSync } from 'node:fs';

// Targeted task list: app → task IDs
const TASKS: Record<string, string[]> = {
  reddit: ['100', '101', '102'],           // Reddit tasks (Postmill)
  ecommerce_admin: ['0', '1', '2'],        // Shopping admin tasks (Magento backend)
  ecommerce: ['3', '4', '5'],              // Shopping frontend tasks
  wikipedia: ['400', '401', '402'],         // Wikipedia tasks (Kiwix)
};

async function main() {
  console.log('=== Regression Test ===\n');

  const config = loadConfig('./config-regression.yaml');
  const results: Array<{
    app: string;
    taskId: string;
    success: boolean;
    steps: number;
    durationSec: number;
    failureType?: string;
    lastAction: string;
  }> = [];

  for (const [app, taskIds] of Object.entries(TASKS)) {
    const appUrl = config.webarena.apps[app]?.url;
    if (!appUrl) {
      console.log(`⚠️ App "${app}" not in config, skipping`);
      continue;
    }

    for (const taskId of taskIds) {
      console.log(`[${app}:${taskId}] Running...`);

      try {
        const trace = await executeAgentTask({
          taskId,
          targetUrl: appUrl,
          taskGoal: taskId,
          variant: 'base',
          agentConfig: config.runner.agentConfigs[0],
          attempt: 1,
        });

        const lastAction = trace.steps[trace.steps.length - 1]?.action ?? 'none';
        const status = trace.success ? '✅' : '❌';
        const durSec = Math.round(trace.durationMs / 1000);

        console.log(`  ${status} steps=${trace.totalSteps} dur=${durSec}s${trace.failureType ? ` fail=${trace.failureType}` : ''}`);
        console.log(`  last: ${lastAction.substring(0, 80)}`);

        results.push({
          app,
          taskId,
          success: trace.success,
          steps: trace.totalSteps,
          durationSec: durSec,
          failureType: trace.failureType,
          lastAction: lastAction.substring(0, 80),
        });

        // Persist full trace
        const outDir = './data/regression/cases';
        mkdirSync(outDir, { recursive: true });
        writeFileSync(`${outDir}/${app}_${taskId}.json`, JSON.stringify({
          app, taskId, trace, config: config.runner.agentConfigs[0],
        }, null, 2));
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.log(`  ⚠️ Error: ${msg.substring(0, 100)}`);
        results.push({
          app,
          taskId,
          success: false,
          steps: 0,
          durationSec: 0,
          failureType: 'ERROR',
          lastAction: msg.substring(0, 80),
        });
      }
      console.log('');
    }
  }

  // Summary
  const successes = results.filter((r) => r.success).length;
  console.log('=== Summary ===');
  console.log(`Success: ${successes}/${results.length} (${((successes / results.length) * 100).toFixed(0)}%)`);
  console.log('');
  for (const r of results) {
    const icon = r.success ? '✅' : '❌';
    console.log(`${icon} ${r.app}:${r.taskId} — ${r.steps} steps, ${r.durationSec}s${r.failureType ? `, ${r.failureType}` : ''}`);
  }

  // Save summary
  const outDir = './data/regression';
  mkdirSync(outDir, { recursive: true });
  writeFileSync(`${outDir}/summary.json`, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${outDir}/`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

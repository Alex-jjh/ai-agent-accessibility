#!/usr/bin/env npx tsx
/**
 * Regression test — run specific WebArena tasks to verify bug fixes.
 *
 * Validates fixes from pilot root cause analysis:
 * - Bracket stripping: ecommerce task 2 login loop (was [413] syntax bug)
 * - Task routing: wikipedia tasks now use 400+ IDs (was misrouted to ecommerce)
 * - System prompt: agents now instructed to use bare numeric bids
 *
 * Task mapping (must match WebArena global IDs):
 *   ecommerce_admin: 0-2   (admin backend at :7780)
 *   ecommerce:       3-99  (storefront at :7770)
 *   reddit:          100+  (Postmill at :9999)
 *   wikipedia:       400+  (Kiwix at :8888)
 *
 * Usage: npx tsx scripts/run-regression.ts
 *        npx tsx scripts/run-regression.ts --config ./my-config.yaml
 */

import { loadConfig } from '../src/config/index.js';
import { executeAgentTask } from '../src/runner/agents/executor.js';
import { writeFileSync, mkdirSync } from 'node:fs';

const args = process.argv.slice(2);
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './config-regression.yaml';

// Targeted task list — IDs must be in the correct WebArena range for each app
const TASKS: Record<string, string[]> = {
  reddit:          ['100', '101', '102'],
  ecommerce_admin: ['0', '1', '2'],
  ecommerce:       ['3', '4', '5'],
  wikipedia:       ['400', '401', '402'],
};

async function main() {
  console.log('=== Regression Test ===\n');

  const config = loadConfig(configPath);
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
          taskGoal: `webarena-task-${taskId}`,
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
  const total = results.length;
  const successes = results.filter((r) => r.success).length;
  const pct = total > 0 ? ((successes / total) * 100).toFixed(0) : '0';
  console.log('=== Summary ===');
  console.log(`Success: ${successes}/${total} (${pct}%)`);
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

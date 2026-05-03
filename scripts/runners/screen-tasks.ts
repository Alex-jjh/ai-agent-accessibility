#!/usr/bin/env npx tsx
/**
 * Task Screening — find WebArena tasks with 30-70% success rate.
 *
 * Loads task-to-site mapping from data/task-site-mapping.json (generated from
 * webarena/test.raw.json) and only runs tasks that belong to the specified app.
 * Automatically skips tasks belonging to other sites (e.g. map tasks in the
 * middle of a shopping_admin range).
 *
 * Usage:
 *   npx tsx scripts/screen-tasks.ts --app ecommerce_admin --start 0 --end 20 --maxSteps 30
 *   npx tsx scripts/screen-tasks.ts --app ecommerce --start 21 --end 50 --maxSteps 30
 *   npx tsx scripts/screen-tasks.ts --app reddit --start 27 --end 70 --maxSteps 30
 *   npx tsx scripts/screen-tasks.ts --app gitlab --start 44 --end 60 --maxSteps 30
 */

import { loadConfig } from '../../src/config/index.js';
import { executeAgentTask } from '../../src/runner/agents/executor.js';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';

const args = process.argv.slice(2);
const appArg = args.find((_, i) => args[i - 1] === '--app') ?? 'ecommerce_admin';
const startArg = parseInt(args.find((_, i) => args[i - 1] === '--start') ?? '0');
const endArg = parseInt(args.find((_, i) => args[i - 1] === '--end') ?? '20');
const maxStepsArg = parseInt(args.find((_, i) => args[i - 1] === '--maxSteps') ?? '30');
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './configs/archive/config-pilot.yaml';
const mappingPath = args.find((_, i) => args[i - 1] === '--mapping') ?? './task-site-mapping.json';

// App name aliases: our config uses ecommerce/ecommerce_admin,
// but test.raw.json uses shopping/shopping_admin
const APP_TO_SITE: Record<string, string> = {
  ecommerce_admin: 'shopping_admin',
  ecommerce: 'shopping',
  shopping_admin: 'shopping_admin',
  shopping: 'shopping',
  reddit: 'reddit',
  gitlab: 'gitlab',
  wikipedia: 'wikipedia',
};

interface ScreenResult {
  taskId: string;
  app: string;
  site: string;
  success: boolean;
  steps: number;
  durationMs: number;
  failureType?: string;
  error?: string;
}

/**
 * Load task-to-site mapping. Returns null if file not found (falls back to no filtering).
 */
function loadMapping(path: string): Record<string, string> | null {
  if (!existsSync(path)) {
    console.warn(`Warning: Mapping file not found at ${path}. Running without site filtering.`);
    console.warn(`Generate it on EC2: python3 -c "import json; ..."`);
    return null;
  }
  return JSON.parse(readFileSync(path, 'utf-8'));
}

async function main() {
  const siteName = APP_TO_SITE[appArg] ?? appArg;
  console.log(`=== Task Screening: ${appArg} (site=${siteName}) tasks ${startArg}-${endArg} (maxSteps=${maxStepsArg}) ===\n`);

  const config = loadConfig(configPath);
  const appUrl = config.webarena.apps[appArg]?.url;
  if (!appUrl) {
    console.error(`App "${appArg}" not found in config. Available: ${Object.keys(config.webarena.apps).join(', ')}`);
    process.exit(1);
  }

  // Load mapping and filter task IDs to only those belonging to this site
  const mapping = loadMapping(mappingPath);
  const taskIds: number[] = [];
  let skipped = 0;

  for (let id = startArg; id <= endArg; id++) {
    if (mapping) {
      const taskSite = mapping[String(id)];
      if (taskSite !== siteName) {
        if (taskSite) {
          console.log(`  [skip] Task ${id} belongs to "${taskSite}", not "${siteName}"`);
        } else {
          console.log(`  [skip] Task ${id} not found in mapping`);
        }
        skipped++;
        continue;
      }
    }
    taskIds.push(id);
  }

  console.log(`\nFiltered: ${taskIds.length} tasks to run, ${skipped} skipped\n`);

  if (taskIds.length === 0) {
    console.error('No valid tasks in range. Check --app and --start/--end values.');
    process.exit(1);
  }

  const results: ScreenResult[] = [];

  for (const taskId of taskIds) {
    const id = String(taskId);
    console.log(`[${results.length + 1}/${taskIds.length}] Testing task ${id} on ${appArg} (${siteName})...`);

    try {
      const trace = await executeAgentTask({
        taskId: id,
        targetUrl: appUrl,
        taskGoal: `webarena-task-${id}`,
        variant: 'base',
        agentConfig: {
          observationMode: 'text-only',
          llmBackend: 'claude-sonnet',
          maxSteps: maxStepsArg,
          retryCount: 2,
          retryBackoffMs: 1000,
          temperature: 0,
        },
        attempt: 1,
      });

      const result: ScreenResult = {
        taskId: id,
        app: appArg,
        site: siteName,
        success: trace.success,
        steps: trace.totalSteps,
        durationMs: trace.durationMs,
        failureType: trace.failureType,
      };
      results.push(result);

      // Save full trace for analysis
      const traceDir = './data/screening/traces';
      mkdirSync(traceDir, { recursive: true });
      writeFileSync(`${traceDir}/${appArg}_${id}.json`, JSON.stringify({
        app: appArg, taskId: id, trace, config: { maxSteps: maxStepsArg },
      }, null, 2));

      const status = trace.success ? '✅' : '❌';
      console.log(`  ${status} steps=${trace.totalSteps} dur=${Math.round(trace.durationMs / 1000)}s${trace.failureType ? ` fail=${trace.failureType}` : ''}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.log(`  ⚠️ Error: ${msg.substring(0, 100)}`);
      results.push({
        taskId: id,
        app: appArg,
        site: siteName,
        success: false,
        steps: 0,
        durationMs: 0,
        error: msg.substring(0, 200),
      });
    }
  }

  // Save results
  const outDir = './data/screening';
  mkdirSync(outDir, { recursive: true });
  const outFile = `${outDir}/${appArg}_${startArg}-${endArg}.json`;
  writeFileSync(outFile, JSON.stringify(results, null, 2));

  // Summary
  const successes = results.filter((r) => r.success);
  const total = results.length;
  console.log(`\n=== Screening Complete ===`);
  console.log(`Total: ${total} (${skipped} skipped), Success: ${successes.length} (${total > 0 ? ((successes.length / total) * 100).toFixed(1) : 0}%)`);
  console.log(`Saved to: ${outFile}`);

  if (successes.length > 0) {
    console.log(`\nSuccessful task IDs: ${successes.map((r) => r.taskId).join(', ')}`);
  }

  // Recommend tasks in the 30-70% sweet spot
  const sweetSpot = results.filter((r) => r.success && r.steps >= 3 && r.steps <= 25);
  if (sweetSpot.length > 0) {
    console.log(`\nRecommended (success + reasonable step count): ${sweetSpot.map((r) => r.taskId).join(', ')}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

#!/usr/bin/env npx tsx
/**
 * Task Screening — find WebArena tasks with 30-70% success rate.
 *
 * Runs each task once with base variant (no a11y modifications) to identify
 * tasks that are neither too easy nor too hard for the agent.
 *
 * WebArena task ID ranges (GLOBAL — determined by BrowserGym, not by app URL):
 *   Shopping admin:  0-2   (require admin login at :7780)
 *   Shopping frontend: 3-99  (storefront at :7770)
 *   Reddit:          100-199
 *   GitLab:          200-299
 *   CMS:             300-399
 *   Wikipedia:        400-811
 *
 * IMPORTANT: Task IDs must match the app. Running reddit task IDs (100+)
 * with --app ecommerce will route the agent to the wrong site.
 *
 * Usage:
 *   npx tsx scripts/screen-tasks.ts --app ecommerce --start 3 --end 20
 *   npx tsx scripts/screen-tasks.ts --app reddit --start 100 --end 130
 *   npx tsx scripts/screen-tasks.ts --app wikipedia --start 400 --end 420 --maxSteps 15
 */

import { loadConfig } from '../src/config/index.js';
import { executeAgentTask } from '../src/runner/agents/executor.js';
import { writeFileSync, mkdirSync } from 'node:fs';

const args = process.argv.slice(2);
const appArg = args.find((_, i) => args[i - 1] === '--app') ?? 'reddit';
const startArg = parseInt(args.find((_, i) => args[i - 1] === '--start') ?? '100');
const endArg = parseInt(args.find((_, i) => args[i - 1] === '--end') ?? '130');
const maxStepsArg = parseInt(args.find((_, i) => args[i - 1] === '--maxSteps') ?? '15');
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './config-pilot.yaml';

// Valid task ID ranges per app — from webarena/test.raw.json
// NOTE: These are approximate outer bounds. Task IDs are interleaved, not contiguous.
// The actual valid IDs within each range are sparse. Use --app with correct IDs.
const TASK_RANGES: Record<string, { min: number; max: number }> = {
  ecommerce_admin: { min: 0, max: 790 },
  ecommerce:       { min: 21, max: 798 },
  shopping_admin:  { min: 0, max: 790 },
  shopping:        { min: 21, max: 798 },
  reddit:          { min: 27, max: 791 },
  gitlab:          { min: 44, max: 811 },
  wikipedia:       { min: 97, max: 741 },
};

interface ScreenResult {
  taskId: string;
  app: string;
  success: boolean;
  steps: number;
  durationMs: number;
  failureType?: string;
  error?: string;
}

async function main() {
  console.log(`=== Task Screening: ${appArg} tasks ${startArg}-${endArg} (maxSteps=${maxStepsArg}) ===\n`);

  const config = loadConfig(configPath);
  const appUrl = config.webarena.apps[appArg]?.url;
  if (!appUrl) {
    console.error(`App "${appArg}" not found in config. Available: ${Object.keys(config.webarena.apps).join(', ')}`);
    process.exit(1);
  }

  // Validate task ID range matches the app
  const validRange = TASK_RANGES[appArg];
  if (validRange) {
    if (startArg < validRange.min || endArg > validRange.max) {
      console.error(
        `Task IDs ${startArg}-${endArg} are outside the valid range for "${appArg}" (${validRange.min}-${validRange.max}).\n` +
        `WebArena task IDs are global — using the wrong range will route the agent to the wrong site.\n` +
        `See: https://github.com/web-arena-x/webarena for task ID documentation.`
      );
      process.exit(1);
    }
  } else {
    console.warn(`Warning: No known task ID range for app "${appArg}". Proceeding without validation.`);
  }

  const results: ScreenResult[] = [];

  for (let taskId = startArg; taskId <= endArg; taskId++) {
    const id = String(taskId);
    console.log(`[${taskId}/${endArg}] Testing task ${id} on ${appArg}...`);

    try {
      const trace = await executeAgentTask({
        taskId: id,
        targetUrl: appUrl,
        // taskGoal is a placeholder — BrowserGym provides the real goal via env.reset()
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
        success: trace.success,
        steps: trace.totalSteps,
        durationMs: trace.durationMs,
        failureType: trace.failureType,
      };
      results.push(result);

      const status = trace.success ? '✅' : '❌';
      console.log(`  ${status} steps=${trace.totalSteps} dur=${Math.round(trace.durationMs / 1000)}s${trace.failureType ? ` fail=${trace.failureType}` : ''}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.log(`  ⚠️ Error: ${msg.substring(0, 100)}`);
      results.push({
        taskId: id,
        app: appArg,
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
  console.log(`Total: ${total}, Success: ${successes.length} (${((successes.length / total) * 100).toFixed(1)}%)`);
  console.log(`Saved to: ${outFile}`);

  if (successes.length > 0) {
    console.log(`\nSuccessful task IDs: ${successes.map((r) => r.taskId).join(', ')}`);
  }

  // Recommend tasks in the 30-70% sweet spot
  const sweetSpot = results.filter((r) => r.success && r.steps >= 3 && r.steps <= 20);
  if (sweetSpot.length > 0) {
    console.log(`\nRecommended (success + reasonable step count): ${sweetSpot.map((r) => r.taskId).join(', ')}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

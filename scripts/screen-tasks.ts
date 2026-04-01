#!/usr/bin/env npx tsx
/**
 * Task Screening — find WebArena tasks with 30-70% success rate.
 *
 * Runs each task once with base variant (no a11y modifications) to identify
 * tasks that are neither too easy nor too hard for the agent.
 *
 * WebArena task ID ranges:
 *   Shopping (ecommerce): 0-99
 *   Reddit: 100-199
 *   GitLab: 200-299
 *   CMS: 300-399
 *   Wikipedia: 400-811
 *
 * Usage:
 *   npx tsx scripts/screen-tasks.ts --app ecommerce --start 0 --end 20
 *   npx tsx scripts/screen-tasks.ts --app reddit --start 100 --end 130
 */

import { chromium } from 'playwright';
import { loadConfig } from '../src/config/index.js';
import { executeAgentTask } from '../src/runner/agents/executor.js';
import { writeFileSync, mkdirSync } from 'node:fs';

const args = process.argv.slice(2);
const appArg = args.find((_, i) => args[i - 1] === '--app') ?? 'reddit';
const startArg = parseInt(args.find((_, i) => args[i - 1] === '--start') ?? '100');
const endArg = parseInt(args.find((_, i) => args[i - 1] === '--end') ?? '130');
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './config-pilot.yaml';

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
  console.log(`=== Task Screening: ${appArg} tasks ${startArg}-${endArg} ===\n`);

  const config = loadConfig(configPath);
  const appUrl = config.webarena.apps[appArg]?.url;
  if (!appUrl) {
    console.error(`App "${appArg}" not found in config. Available: ${Object.keys(config.webarena.apps).join(', ')}`);
    process.exit(1);
  }

  const results: ScreenResult[] = [];

  for (let taskId = startArg; taskId <= endArg; taskId++) {
    const id = String(taskId);
    console.log(`[${taskId}/${endArg}] Testing task ${id} on ${appArg}...`);

    try {
      const trace = await executeAgentTask({
        taskId: id,
        targetUrl: appUrl,
        taskGoal: id,
        variant: 'base',
        agentConfig: {
          observationMode: 'text-only',
          llmBackend: 'claude-sonnet',
          maxSteps: 30,
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
      console.log(`  ${status} steps=${trace.steps.length} dur=${Math.round(trace.durationMs / 1000)}s${trace.failureType ? ` fail=${trace.failureType}` : ''}`);
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
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

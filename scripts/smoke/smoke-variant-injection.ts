#!/usr/bin/env npx tsx
/**
 * Smoke test: verify variant injection into BrowserGym bridge.
 *
 * Runs ecommerce task 3 with base and low variants (1 rep each).
 * Compares initial observations to confirm:
 *   1. env.unwrapped.page is accessible (bridge stderr shows DOM changes > 0)
 *   2. Observation re-capture works (low axtree lacks landmarks/ARIA)
 *   3. Causal link restored (low observation differs from base)
 *
 * Usage (on EC2 with WebArena running):
 *   npx tsx scripts/smoke-variant-injection.ts
 *   npx tsx scripts/smoke-variant-injection.ts --config ./config-regression.yaml
 */

import { loadConfig } from '../../src/config/index.js';
import { executeAgentTask } from '../../src/runner/agents/executor.js';
import { writeFileSync, mkdirSync } from 'node:fs';

const args = process.argv.slice(2);
const configPath = args.find((_, i) => args[i - 1] === '--config') ?? './config-regression.yaml';

const APP = 'ecommerce';
const TASK_ID = '3';

interface SmokeResult {
  variant: string;
  success: boolean;
  steps: number;
  initialObsLength: number;
  initialObsSnippet: string;
  hasLandmarks: boolean;
  hasAriaAttrs: boolean;
  error?: string;
}

async function runOneCase(variant: 'base' | 'low', appUrl: string, agentConfig: any): Promise<SmokeResult> {
  console.log(`\n--- Running ${APP} task ${TASK_ID} with variant="${variant}" ---`);

  try {
    const trace = await executeAgentTask({
      taskId: TASK_ID,
      targetUrl: appUrl,
      taskGoal: `webarena-task-${TASK_ID}`,
      variant,
      agentConfig: { ...agentConfig, maxSteps: 5 }, // short run, just need initial obs
      attempt: 1,
    });

    const initialObs = trace.steps[0]?.observation ?? '';
    const hasLandmarks = /\bnavigation\b|\bbanner\b|\bcontentinfo\b|\bmain\b/i.test(initialObs);
    const hasAriaAttrs = /aria-label|aria-expanded|aria-hidden/i.test(initialObs);

    return {
      variant,
      success: true,
      steps: trace.totalSteps,
      initialObsLength: initialObs.length,
      initialObsSnippet: initialObs.substring(0, 500),
      hasLandmarks,
      hasAriaAttrs,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`  Error: ${msg}`);
    return {
      variant,
      success: false,
      steps: 0,
      initialObsLength: 0,
      initialObsSnippet: '',
      hasLandmarks: false,
      hasAriaAttrs: false,
      error: msg.substring(0, 300),
    };
  }
}

async function main() {
  console.log('=== Smoke Test: Variant Injection into BrowserGym ===');
  console.log(`Config: ${configPath}`);
  console.log(`App: ${APP}, Task: ${TASK_ID}`);
  console.log('Watch bridge stderr for "[bridge] Applied variant" messages.\n');

  const config = loadConfig(configPath);
  const appUrl = config.webarena.apps[APP]?.url;
  if (!appUrl) {
    console.error(`App "${APP}" not found in config. Available: ${Object.keys(config.webarena.apps).join(', ')}`);
    process.exit(1);
  }

  const agentConfig = config.runner.agentConfigs[0];

  // Run base first, then low
  const baseResult = await runOneCase('base', appUrl, agentConfig);
  const lowResult = await runOneCase('low', appUrl, agentConfig);

  // Save raw results
  const outDir = './data/smoke-variant';
  mkdirSync(outDir, { recursive: true });
  writeFileSync(`${outDir}/results.json`, JSON.stringify({ base: baseResult, low: lowResult }, null, 2));

  // Verification report
  console.log('\n\n========================================');
  console.log('  VERIFICATION REPORT');
  console.log('========================================\n');

  // Check 1: Did bridge apply variant?
  const check1 = lowResult.success && !lowResult.error;
  console.log(`[Check 1] env.unwrapped.page accessible:`);
  console.log(`  ${check1 ? '✅' : '❌'} low variant case ${check1 ? 'completed' : 'FAILED'}`);
  console.log(`  (Check bridge stderr for "[bridge] Applied variant \'low\': N DOM changes" with N > 0)`);

  // Check 2: Observation re-capture — low should lack landmarks/ARIA
  const check2_landmarks = baseResult.hasLandmarks && !lowResult.hasLandmarks;
  const check2_aria = baseResult.hasAriaAttrs && !lowResult.hasAriaAttrs;
  const check2 = check2_landmarks || check2_aria;
  console.log(`\n[Check 2] Observation re-capture reflects patched DOM:`);
  console.log(`  Base: landmarks=${baseResult.hasLandmarks}, aria=${baseResult.hasAriaAttrs}`);
  console.log(`  Low:  landmarks=${lowResult.hasLandmarks}, aria=${lowResult.hasAriaAttrs}`);
  console.log(`  ${check2 ? '✅' : '⚠️'} ${check2 ? 'Low variant observation differs from base' : 'Observations may be identical — check manually'}`);

  // Check 3: Observations are different
  const obsDiffer = baseResult.initialObsSnippet !== lowResult.initialObsSnippet;
  console.log(`\n[Check 3] Causal link — observations differ between variants:`);
  console.log(`  Base obs length: ${baseResult.initialObsLength} chars`);
  console.log(`  Low obs length:  ${lowResult.initialObsLength} chars`);
  console.log(`  ${obsDiffer ? '✅' : '❌'} ${obsDiffer ? 'Observations are different' : 'Observations are IDENTICAL — variant not applied or re-capture failed'}`);

  // Overall
  const allPass = check1 && check2 && obsDiffer;
  console.log(`\n========================================`);
  console.log(`  OVERALL: ${allPass ? '✅ ALL CHECKS PASSED' : '⚠️ SOME CHECKS NEED ATTENTION'}`);
  console.log(`========================================`);
  console.log(`\nResults saved to ${outDir}/results.json`);

  // Print observation snippets for manual comparison
  console.log('\n--- Base initial observation (first 300 chars) ---');
  console.log(baseResult.initialObsSnippet.substring(0, 300));
  console.log('\n--- Low initial observation (first 300 chars) ---');
  console.log(lowResult.initialObsSnippet.substring(0, 300));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

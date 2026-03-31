// Cross-cutting: Experiment Manifest Generator
// Generates a manifest documenting all test cases, outcomes, software versions,
// and configuration parameters for reproducibility.
// Requirements: 15.2, 15.3, 18.3

import { createRequire } from 'node:module';
import type { ExperimentManifest, ExperimentConfig } from '../config/types.js';
import type { ExperimentRun } from '../runner/types.js';
import type { ExperimentRecord } from '../runner/scheduler.js';

/**
 * Resolve the installed version of a package, returning 'unknown' on failure.
 */
function getPackageVersion(packageName: string): string {
  try {
    const require = createRequire(import.meta.url);
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    const pkg = require(`${packageName}/package.json`) as { version?: string };
    return pkg.version ?? 'unknown';
  } catch {
    return 'unknown';
  }
}

/**
 * Collect software versions for axe-core, Lighthouse, Playwright, and the platform itself.
 * LLM model versions are extracted from the agent configs in the experiment matrix.
 */
export function collectSoftwareVersions(
  config: ExperimentConfig,
): ExperimentManifest['softwareVersions'] {
  const llmModels: Record<string, string> = {};
  for (const ac of config.runner.agentConfigs) {
    llmModels[ac.llmBackend] = ac.llmBackend; // version = model identifier
  }

  return {
    axeCore: getPackageVersion('@axe-core/playwright'),
    lighthouse: getPackageVersion('lighthouse'),
    playwright: getPackageVersion('playwright'),
    llmModels,
    platform: getPackageVersion('ai-agent-accessibility-platform'),
  };
}

/**
 * Generate an ExperimentManifest from a completed (or interrupted) experiment run.
 *
 * Lists all test cases with their outcomes, includes full config for reproducibility,
 * and records software versions of all key dependencies.
 * (Req 15.2, 15.3, 18.3)
 */
export function generateManifest(
  run: ExperimentRun,
  config: ExperimentConfig,
  records: ExperimentRecord[],
): ExperimentManifest {
  // Build per-case summary from experiment records
  const caseMap = new Map<string, { outcome: string; traces: number }>();
  for (const rec of records) {
    const existing = caseMap.get(rec.caseId);
    if (existing) {
      existing.traces += 1;
    } else {
      caseMap.set(rec.caseId, {
        outcome: rec.taskOutcome.outcome,
        traces: 1,
      });
    }
  }

  const testCases = Array.from(caseMap.entries()).map(([caseId, info]) => ({
    caseId,
    outcome: info.outcome,
    traces: info.traces,
  }));

  return {
    runId: run.runId,
    startedAt: run.startedAt,
    completedAt: new Date().toISOString(),
    config,
    softwareVersions: collectSoftwareVersions(config),
    testCases,
  };
}

// Configuration management — Type definitions

import type { VariantLevel } from '../variants/types.js';
import type { AgentConfig } from '../runner/types.js';

/** Central experiment configuration */
export interface ExperimentConfig {
  scanner: {
    wcagLevels: ('A' | 'AA' | 'AAA')[];
    stabilityIntervalMs: number;
    stabilityTimeoutMs: number;
    concurrency: number;
  };
  variants: {
    levels: VariantLevel[];
    scoreRanges: Record<VariantLevel, { min: number; max: number }>;
  };
  runner: {
    agentConfigs: AgentConfig[];
    repetitions: number;
    maxSteps: number;
    concurrency: number;
  };
  recorder: {
    waitAfterLoadMs: number;
    concurrency: number;
  };
  webarena: {
    apps: Record<string, { url: string; resetEndpoint?: string }>;
  };
  output: {
    dataDir: string;
    exportFormats: ('json' | 'csv')[];
  };
}

/** Manifest documenting a completed experiment run */
export interface ExperimentManifest {
  runId: string;
  startedAt: string;
  completedAt: string;
  config: ExperimentConfig;
  softwareVersions: {
    axeCore: string;
    lighthouse: string;
    playwright: string;
    llmModels: Record<string, string>;
    platform: string;
  };
  testCases: Array<{
    caseId: string;
    outcome: string;
    traces: number;
  }>;
}

/** Options for CSV data export */
export interface CsvExportOptions {
  anonymize: boolean;
  anonymizeSiteIdentity: boolean;
  includeTraceDetails: boolean;
}

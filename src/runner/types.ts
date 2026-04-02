// Module 3: Agent Runner — Type definitions for agent execution and experiment matrix

import type { VariantLevel } from '../variants/types.js';
import type { ScanResult } from '../scanner/types.js';

/** Agent observation mode */
export type ObservationMode = 'text-only' | 'vision';

/** LLM backend identifier */
export type LlmBackend = 'claude-opus' | 'gpt-4o' | (string & {});

/** Configuration for an AI agent run */
export interface AgentConfig {
  observationMode: ObservationMode;
  llmBackend: LlmBackend;
  maxSteps: number;
  retryCount: number;
  retryBackoffMs: number;
  temperature: number;
  /** Number of previous step messages to include in LLM context (default 6) */
  maxHistorySteps?: number;
}

/** A single step in an agent's action trace */
export interface ActionTraceStep {
  stepNum: number;
  timestamp: string;
  observation: string;
  reasoning: string;
  action: string;
  result: 'success' | 'failure' | 'error';
  resultDetail?: string;
}

/** Complete action trace for one agent attempt */
export interface ActionTrace {
  taskId: string;
  variant: VariantLevel;
  agentConfig: AgentConfig;
  attempt: number;
  success: boolean;
  steps: ActionTraceStep[];
  totalSteps: number;
  totalTokens: number;
  durationMs: number;
  failureType?: string;
  failureConfidence?: number;
}

/** Outcome of a task across multiple agent attempts */
export interface TaskOutcome {
  taskId: string;
  outcome: 'success' | 'partial_success' | 'failure' | 'timeout';
  traces: ActionTrace[];
  medianSteps: number;
  medianDurationMs: number;
  scanResults: ScanResult;
}

/** LLM API request */
export interface LlmRequest {
  model: string;
  messages: Array<{ role: string; content: string | object[] }>;
  temperature: number;
  maxTokens: number;
}

/** LLM API response */
export interface LlmResponse {
  content: string;
  tokensUsed: { prompt: number; completion: number };
  model: string;
  latencyMs: number;
}

/** Experiment matrix defining all test case combinations */
export interface ExperimentMatrix {
  apps: string[];
  variants: VariantLevel[];
  tasksPerApp: Record<string, string[]>;
  agentConfigs: AgentConfig[];
  repetitions: number;
}

/** State of an experiment run */
export interface ExperimentRun {
  runId: string;
  matrix: ExperimentMatrix;
  executionOrder: string[];
  completedCases: Set<string>;
  startedAt: string;
  status: 'running' | 'completed' | 'interrupted';
}

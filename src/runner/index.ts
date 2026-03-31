// Module 3: Agent Runner — agent execution with action trace logging

export { callLlm } from './backends/llm.js';
export type { RetryConfig } from './backends/llm.js';

export { executeAgentTask, parseLlmResponse } from './agents/executor.js';
export type {
  BrowserGymObservation,
  ExecuteTaskOptions,
  BridgeSpawner,
  BridgeTaskConfig,
  BridgeProcess,
} from './agents/executor.js';

export type {
  ObservationMode,
  LlmBackend,
  AgentConfig,
  ActionTraceStep,
  ActionTrace,
  TaskOutcome,
  LlmRequest,
  LlmResponse,
  ExperimentMatrix,
  ExperimentRun,
} from './types.js';

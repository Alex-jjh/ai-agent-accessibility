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

export {
  executeExperiment,
  generateTestCases,
  parseTestCaseId,
  fisherYatesShuffle,
  loadRunState,
} from './scheduler.js';
export type {
  ExperimentRecord,
  ExecuteExperimentOptions,
  TestCaseParams,
  TestCaseResult,
} from './scheduler.js';

export {
  serializeActionTrace,
  deserializeActionTrace,
  ActionTraceParseError,
} from './serialization.js';

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

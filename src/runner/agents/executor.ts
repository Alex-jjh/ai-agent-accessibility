// Module 3: Agent Runner — Agent Executor
// Executes AI agents against target websites via BrowserGym bridge,
// capturing detailed action traces per step. (Req 7.1–7.5, 7.7)

import { spawn, type ChildProcess } from 'node:child_process';
import { createInterface, type Interface as ReadlineInterface } from 'node:readline';
import type {
  AgentConfig,
  ActionTrace,
  ActionTraceStep,
  LlmRequest,
} from '../types.js';
import type { VariantLevel } from '../../variants/types.js';
import { callLlm } from '../backends/llm.js';

/** Observation received from the BrowserGym bridge */
export interface BrowserGymObservation {
  goal: string;
  axtree_txt: string;
  screenshot_base64?: string;
  url: string;
  last_action_error: string;
  terminated: boolean;
  truncated: boolean;
  reward: number;
  step: number;
}

/** Configuration for a single agent task execution */
export interface ExecuteTaskOptions {
  taskId: string;
  targetUrl: string;
  taskGoal: string;
  variant: VariantLevel;
  agentConfig: AgentConfig;
  attempt: number;
  /** Path to the BrowserGym bridge Python script */
  bridgeScriptPath?: string;
  /** Override for testing: inject a custom LLM caller */
  llmCaller?: typeof callLlm;
  /** Override for testing: inject a custom bridge spawner */
  bridgeSpawner?: BridgeSpawner;
}

/** Function signature for spawning the BrowserGym bridge process */
export type BridgeSpawner = (scriptPath: string, taskConfig: BridgeTaskConfig) => BridgeProcess;

/** Config sent to the Python bridge on startup */
export interface BridgeTaskConfig {
  taskId: string;
  targetUrl: string;
  taskGoal: string;
}

/** Abstraction over the bridge subprocess for testability */
export interface BridgeProcess {
  sendAction(action: string): void;
  readObservation(): Promise<BrowserGymObservation | null>;
  close(): Promise<void>;
}

/**
 * Build the system prompt for the agent LLM call.
 */
function buildSystemPrompt(goal: string, observationMode: 'text-only' | 'vision'): string {
  const modeNote = observationMode === 'vision'
    ? 'You receive both the accessibility tree and a screenshot of the page.'
    : 'You receive the accessibility tree text representation of the page.';

  return [
    'You are a web navigation agent. Your goal is to complete the following task:',
    `Task: ${goal}`,
    '',
    modeNote,
    '',
    'Respond with a JSON object containing:',
    '- "reasoning": your step-by-step thinking',
    '- "action": the BrowserGym action to execute (e.g., click("bid"), fill("bid", "text"), send_msg_to_user("done"))',
    '',
    'If the task is complete, use send_msg_to_user("done") as your action.',
    'If you cannot proceed, use send_msg_to_user("cannot complete") as your action.',
  ].join('\n');
}

/**
 * Build the user message content for a single step.
 */
function buildUserMessage(
  obs: BrowserGymObservation,
  observationMode: 'text-only' | 'vision',
): string | object[] {
  const textContent = [
    `Current URL: ${obs.url}`,
    obs.last_action_error ? `Last action error: ${obs.last_action_error}` : '',
    '',
    'Accessibility Tree:',
    obs.axtree_txt,
  ].filter(Boolean).join('\n');

  if (observationMode === 'vision' && obs.screenshot_base64) {
    return [
      { type: 'text', text: textContent },
      {
        type: 'image_url',
        image_url: { url: `data:image/png;base64,${obs.screenshot_base64}` },
      },
    ];
  }

  return textContent;
}

/**
 * Parse the LLM response to extract reasoning and action.
 */
export function parseLlmResponse(content: string): { reasoning: string; action: string } {
  // Try JSON parse first
  try {
    const parsed = JSON.parse(content);
    if (typeof parsed.action === 'string') {
      return {
        reasoning: typeof parsed.reasoning === 'string' ? parsed.reasoning : '',
        action: parsed.action,
      };
    }
  } catch {
    // Fall through to regex extraction
  }

  // Extract action from code block or inline
  const actionMatch = content.match(/```(?:\w+)?\s*([\s\S]*?)```/) ??
    content.match(/((?:click|fill|type|hover|press|scroll|goto|go_back|go_forward|new_tab|tab_close|tab_focus|send_msg_to_user|noop|focus)\s*\([\s\S]*?\))/);

  const action = actionMatch?.[1]?.trim() ?? 'noop()';
  const reasoning = content.replace(actionMatch?.[0] ?? '', '').trim();

  return { reasoning, action };
}

/**
 * Determine task outcome from the action trace.
 */
function determineOutcome(
  steps: ActionTraceStep[],
  hitStepLimit: boolean,
): 'success' | 'partial_success' | 'failure' | 'timeout' {
  if (hitStepLimit) return 'timeout';

  const lastStep = steps[steps.length - 1];
  if (!lastStep) return 'failure';

  // Check if agent signaled completion
  if (lastStep.action.includes('send_msg_to_user')) {
    if (lastStep.action.includes('done')) return 'success';
    if (lastStep.action.includes('cannot complete')) return 'failure';
    return 'partial_success';
  }

  // If terminated by environment reward
  return 'failure';
}

/**
 * Execute an AI agent against a target website, capturing a full action trace.
 *
 * The executor:
 * 1. Initializes a BrowserGym environment via the Python bridge subprocess
 * 2. Runs the agent step loop: observe → reason (LLM) → act → log
 * 3. Enforces the configurable step limit (default 30)
 * 4. Records ActionTraceStep per step and returns a complete ActionTrace
 */
export async function executeAgentTask(options: ExecuteTaskOptions): Promise<ActionTrace> {
  const {
    taskId,
    targetUrl,
    taskGoal,
    variant,
    agentConfig,
    attempt,
    bridgeScriptPath = 'src/runner/browsergym_bridge.py',
    llmCaller = callLlm,
    bridgeSpawner = defaultBridgeSpawner,
  } = options;

  const startTime = Date.now();
  const steps: ActionTraceStep[] = [];
  let totalTokens = 0;

  const bridge = bridgeSpawner(bridgeScriptPath, { taskId, targetUrl, taskGoal });

  try {
    // Get initial observation from env.reset()
    let obs = await bridge.readObservation();
    if (!obs) {
      throw new Error('Bridge process terminated before sending initial observation');
    }

    const systemPrompt = buildSystemPrompt(obs.goal || taskGoal, agentConfig.observationMode);

    for (let stepNum = 1; stepNum <= agentConfig.maxSteps; stepNum++) {
      const stepTimestamp = new Date().toISOString();
      const userContent = buildUserMessage(obs, agentConfig.observationMode);

      // Call LLM
      const llmRequest: LlmRequest = {
        model: agentConfig.llmBackend,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userContent },
        ],
        temperature: agentConfig.temperature,
        maxTokens: 4096,
      };

      let reasoning = '';
      let action = 'noop()';
      let stepResult: 'success' | 'failure' | 'error' = 'success';
      let resultDetail: string | undefined;

      try {
        const llmResponse = await llmCaller(llmRequest, {
          maxRetries: agentConfig.retryCount,
          backoffMs: agentConfig.retryBackoffMs,
        });

        totalTokens += llmResponse.tokensUsed.prompt + llmResponse.tokensUsed.completion;
        const parsed = parseLlmResponse(llmResponse.content);
        reasoning = parsed.reasoning;
        action = parsed.action;
      } catch (err) {
        stepResult = 'error';
        resultDetail = err instanceof Error ? err.message : String(err);
        reasoning = 'LLM call failed';
        action = 'noop()';
      }

      // Execute action in BrowserGym
      if (stepResult !== 'error') {
        bridge.sendAction(action);
        const nextObs = await bridge.readObservation();

        if (!nextObs) {
          stepResult = 'error';
          resultDetail = 'Bridge process terminated unexpectedly';
        } else {
          if (nextObs.last_action_error) {
            stepResult = 'failure';
            resultDetail = nextObs.last_action_error;
          }
          obs = nextObs;
        }
      }

      const observationStr = agentConfig.observationMode === 'text-only'
        ? obs.axtree_txt
        : `[screenshot + axtree] ${obs.url}`;

      steps.push({
        stepNum,
        timestamp: stepTimestamp,
        observation: observationStr,
        reasoning,
        action,
        result: stepResult,
        resultDetail,
      });

      // Check termination conditions
      if (obs.terminated || obs.truncated) break;
      if (action.includes('send_msg_to_user')) break;
      if (stepResult === 'error' && !resultDetail?.includes('retry')) break;
    }
  } finally {
    await bridge.close();
  }

  const durationMs = Date.now() - startTime;
  const hitStepLimit = steps.length >= agentConfig.maxSteps &&
    !steps[steps.length - 1]?.action.includes('send_msg_to_user');
  const outcome = determineOutcome(steps, hitStepLimit);

  return {
    taskId,
    variant,
    agentConfig,
    attempt,
    success: outcome === 'success',
    steps,
    totalSteps: steps.length,
    totalTokens,
    durationMs,
  };
}


/**
 * Default bridge spawner: starts the Python BrowserGym bridge as a child process
 * communicating via JSON lines over stdin/stdout.
 */
function defaultBridgeSpawner(scriptPath: string, taskConfig: BridgeTaskConfig): BridgeProcess {
  const child: ChildProcess = spawn('python', [scriptPath, JSON.stringify(taskConfig)], {
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  const rl: ReadlineInterface = createInterface({ input: child.stdout! });
  const lineBuffer: string[] = [];
  let lineResolve: ((value: string | null) => void) | null = null;
  let closed = false;

  rl.on('line', (line: string) => {
    if (lineResolve) {
      const resolve = lineResolve;
      lineResolve = null;
      resolve(line);
    } else {
      lineBuffer.push(line);
    }
  });

  rl.on('close', () => {
    closed = true;
    if (lineResolve) {
      const resolve = lineResolve;
      lineResolve = null;
      resolve(null);
    }
  });

  child.stderr?.on('data', (data: Buffer) => {
    console.warn(`[BrowserGym bridge stderr] ${data.toString().trim()}`);
  });

  function nextLine(): Promise<string | null> {
    if (lineBuffer.length > 0) {
      return Promise.resolve(lineBuffer.shift()!);
    }
    if (closed) return Promise.resolve(null);
    return new Promise((resolve) => {
      lineResolve = resolve;
    });
  }

  return {
    sendAction(action: string): void {
      child.stdin!.write(JSON.stringify({ action }) + '\n');
    },

    async readObservation(): Promise<BrowserGymObservation | null> {
      const line = await nextLine();
      if (line === null) return null;
      try {
        return JSON.parse(line) as BrowserGymObservation;
      } catch {
        console.warn(`[BrowserGym bridge] Failed to parse observation: ${line}`);
        return null;
      }
    },

    async close(): Promise<void> {
      if (!closed) {
        child.stdin!.end();
        child.kill('SIGTERM');
      }
      rl.close();
    },
  };
}

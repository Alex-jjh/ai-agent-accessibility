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
  /** Variant level to apply in the BrowserGym environment after env.reset() */
  variantLevel: string;
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
    'The accessibility tree shows elements with their BrowserGym IDs (bid). Use these IDs in your actions.',
    '',
    'Available actions (use EXACTLY this syntax with regular double quotes):',
    '  click("bid")           - Click an element by its bid',
    '  fill("bid", "text")    - Fill a text field with the given text',
    '  scroll(x, y)           - Scroll by x,y pixels (e.g., scroll(0, 500))',
    '  hover("bid")           - Hover over an element',
    '  goto("url")            - Navigate to a URL',
    '  go_back()              - Go back in browser history',
    '  send_msg_to_user("msg") - Send a message (use "done" when task is complete)',
    '  noop()                 - Do nothing (wait for page to load)',
    '',
    'IMPORTANT:',
    '- Use regular double quotes " not escaped quotes \\" in your action strings',
    '- Use BARE NUMERIC bid values WITHOUT brackets: click("123") NOT click("[123]")',
    '- The accessibility tree shows [123] but you must use just "123" in actions',
    '- If the page is loading, use noop() and wait',
    '- If you cannot complete the task after trying, use send_msg_to_user("cannot complete")',
    '- If the task is complete, use send_msg_to_user("done")',
    '',
    'Respond with a JSON object: {"reasoning": "your thinking", "action": "the action to execute"}',
  ].join('\n');
}

/**
 * Build the user message content for a single step.
 */
function buildUserMessage(
  obs: BrowserGymObservation,
  observationMode: 'text-only' | 'vision',
  previousSteps?: ActionTraceStep[],
): string | object[] {
  const parts: string[] = [];

  parts.push(`Current URL: ${obs.url}`);

  if (obs.last_action_error) {
    parts.push(`Last action error: ${obs.last_action_error}`);
    parts.push('(Try a different approach or different element)');
  }

  // Include last 2 steps for context (helps agent avoid repeating failed actions)
  if (previousSteps && previousSteps.length > 0) {
    const recent = previousSteps.slice(-2);
    parts.push('');
    parts.push('Recent actions:');
    for (const step of recent) {
      const status = step.result === 'success' ? '✓' : '✗';
      parts.push(`  ${status} ${step.action.substring(0, 80)}${step.resultDetail ? ` — ${step.resultDetail.substring(0, 60)}` : ''}`);
    }
  }

  parts.push('');
  parts.push('Accessibility Tree:');
  parts.push(obs.axtree_txt || '[Page content not available]');

  const textContent = parts.join('\n');

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
 * Clean up action string for BrowserGym compatibility.
 * Fixes common issues from LLM output:
 * - Escaped quotes: fill(\"bid\", \"text\") → fill("bid", "text")
 * - Smart quotes: fill("bid") → fill("bid")
 * - Trailing/leading whitespace
 */
function cleanAction(raw: string): string {
  let action = raw.trim();

  // Remove escaped backslash-quotes: \" → "
  action = action.replace(/\\"/g, '"');
  // Remove escaped single quotes: \' → '
  action = action.replace(/\\'/g, "'");
  // Replace smart quotes
  action = action.replace(/[\u201C\u201D]/g, '"');
  action = action.replace(/[\u2018\u2019]/g, "'");

  // Strip brackets from bid references: fill("[413]", ...) → fill("413", ...)
  // LLMs copy [bid] notation from a11y tree but BrowserGym expects bare numeric IDs.
  // Handle both double and single quote variants: click("[413]"), click('[413]'), click([413])
  action = action.replace(/\(["']?\[(\d+)\]["']?/g, '("$1"');

  return action;
}

/**
 * Parse the LLM response to extract reasoning and action.
 */
export function parseLlmResponse(content: string): { reasoning: string; action: string } {
  // Strip markdown code blocks if present
  let cleaned = content.trim();
  const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    cleaned = codeBlockMatch[1].trim();
  }

  // Try JSON parse
  try {
    const parsed = JSON.parse(cleaned);
    if (typeof parsed.action === 'string') {
      return {
        reasoning: typeof parsed.reasoning === 'string' ? parsed.reasoning : '',
        action: cleanAction(parsed.action),
      };
    }
  } catch {
    // Fall through to regex extraction
  }

  // Try parsing the original content as JSON (in case code block stripping broke it)
  try {
    const parsed = JSON.parse(content.trim());
    if (typeof parsed.action === 'string') {
      return {
        reasoning: typeof parsed.reasoning === 'string' ? parsed.reasoning : '',
        action: cleanAction(parsed.action),
      };
    }
  } catch {
    // Fall through to regex extraction
  }

  // Extract action from inline function call patterns
  const actionMatch = content.match(/((?:click|fill|type|hover|press|scroll|goto|go_back|go_forward|new_tab|tab_close|tab_focus|select_option|send_msg_to_user|noop|focus)\s*\([\s\S]*?\))/);

  const action = actionMatch?.[1]?.trim() ?? 'noop()';
  const reasoning = content.replace(actionMatch?.[0] ?? '', '').trim();

  return { reasoning, action: cleanAction(action) };
}

/**
 * Determine task outcome from the action trace and environment signals.
 *
 * Priority order:
 * 1. BrowserGym reward > 0 → success (ground truth from environment)
 * 2. Step limit / truncation → timeout
 * 3. Agent self-report via send_msg_to_user (with "cannot complete" checked
 *    BEFORE "done" to avoid false positives like "cannot complete, done trying")
 * 4. Default → failure
 */
function determineOutcome(
  steps: ActionTraceStep[],
  hitStepLimit: boolean,
  lastReward: number,
): 'success' | 'partial_success' | 'failure' | 'timeout' {
  // BrowserGym reward is the ground truth — if the environment says the task
  // was completed successfully, trust it over the agent's self-report.
  if (lastReward > 0) return 'success';

  if (hitStepLimit) return 'timeout';

  const lastStep = steps[steps.length - 1];
  if (!lastStep) return 'failure';

  // Check if agent signaled completion.
  // IMPORTANT: check "cannot complete" BEFORE "done" — an LLM might output
  // "I cannot complete this task, done trying" which contains both strings.
  if (lastStep.action.includes('send_msg_to_user')) {
    if (lastStep.action.includes('cannot complete')) return 'failure';
    if (lastStep.action.includes('done')) return 'success';
    return 'partial_success';
  }

  // Terminated by environment without positive reward
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
  let envTruncated = false;
  let lastReward = 0;

  const bridge = bridgeSpawner(bridgeScriptPath, { taskId, targetUrl, taskGoal, variantLevel: variant });

  try {
    // Get initial observation from env.reset()
    let obs = await bridge.readObservation();
    if (!obs) {
      throw new Error('Bridge process terminated before sending initial observation');
    }

    const systemPrompt = buildSystemPrompt(obs.goal || taskGoal, agentConfig.observationMode);
    const maxHistory = agentConfig.maxHistorySteps ?? 6;
    // Accumulate conversation history for multi-turn context
    const messageHistory: Array<{ role: string; content: string | object[] }> = [];

    for (let stepNum = 1; stepNum <= agentConfig.maxSteps; stepNum++) {
      const stepTimestamp = new Date().toISOString();
      const userContent = buildUserMessage(obs, agentConfig.observationMode, steps);

      // Build messages: system + recent history + current observation
      const historyWindow = messageHistory.slice(-maxHistory * 2); // each turn = user + assistant
      const llmRequest: LlmRequest = {
        model: agentConfig.llmBackend,
        messages: [
          { role: 'system', content: systemPrompt },
          ...historyWindow,
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

        // Accumulate history for multi-turn context.
        // For vision mode, strip base64 screenshots from history to avoid
        // token explosion — only the current step gets the screenshot.
        let historyContent: string | object[] = userContent;
        if (Array.isArray(userContent)) {
          // Vision mode: keep only text entries, drop image_url
          historyContent = (userContent as Array<{ type: string; text?: string }>)
            .filter((part) => part.type === 'text')
            .map((part) => part.text ?? '')
            .join('\n');
        }
        messageHistory.push({ role: 'user', content: historyContent });
        messageHistory.push({ role: 'assistant', content: llmResponse.content });
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
        ? (obs.axtree_txt || `[No accessibility tree available] URL: ${obs.url}`)
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
      if (obs.terminated || obs.truncated) {
        if (obs.truncated) envTruncated = true;
        lastReward = obs.reward;
        break;
      }
      if (action.includes('send_msg_to_user')) {
        // Capture final reward before breaking — BrowserGym may signal
        // success on the same step the agent sends its completion message.
        lastReward = obs.reward;
        break;
      }
      if (stepResult === 'error' && !resultDetail?.includes('retry')) break;
    }
  } finally {
    await bridge.close();
  }

  const durationMs = Date.now() - startTime;
  // Detect timeout: either hit the agent step limit, or BrowserGym truncated the episode.
  // We track whether BrowserGym signaled truncation (obs.truncated) separately from
  // the agent's own step limit, since both should map to 'timeout' outcome.
  const lastStep = steps[steps.length - 1];
  const agentHitLimit = steps.length >= agentConfig.maxSteps &&
    !lastStep?.action.includes('send_msg_to_user');
  const hitStepLimit = agentHitLimit || envTruncated;
  const outcome = determineOutcome(steps, hitStepLimit, lastReward);

  return {
    taskId,
    variant,
    agentConfig,
    attempt,
    success: outcome === 'success',
    outcome,
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

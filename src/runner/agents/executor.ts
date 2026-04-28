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
  ObservationMode,
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
  /** AMT individual-mode only: operator IDs for this case. */
  operatorIds?: string[];
  /** Path to the BrowserGym bridge Python script */
  bridgeScriptPath?: string;
  /** Override for testing: inject a custom LLM caller */
  llmCaller?: typeof callLlm;
  /** Override for testing: inject a custom bridge spawner */
  bridgeSpawner?: BridgeSpawner;
  /** Wall-clock timeout in ms for the entire case. Default: 600000 (10 min).
   *  If exceeded, the case is terminated with outcome='timeout' and
   *  resultDetail='wall-clock timeout' for post-hoc review. */
  wallClockTimeoutMs?: number;
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
  /** Observation mode — 'vision-only' enables Set-of-Marks screenshot overlay */
  observationMode?: string;
  /** Override bridge read timeout in ms (default 120s). CUA mode needs longer. */
  bridgeReadTimeoutMs?: number;
  /** AMT individual-mode only: operator IDs to inject. */
  operatorIds?: string[];
}

/** Abstraction over the bridge subprocess for testability */
export interface BridgeProcess {
  sendAction(action: string): void;
  readObservation(): Promise<BrowserGymObservation | null>;
  close(): Promise<void>;
  /** Get accumulated stderr output from the bridge process (ISSUE-BR-7). */
  getStderrLog(): string;
}

/**
 * Build the system prompt for the agent LLM call.
 */
function buildSystemPrompt(goal: string, observationMode: ObservationMode): string {
  let modeNote: string;
  let actionNote: string;
  switch (observationMode) {
    case 'vision':
      modeNote = 'You receive both the accessibility tree and a screenshot of the page.';
      actionNote = [
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
      ].join('\n');
      break;
    case 'vision-only':
      modeNote = [
        'You receive ONLY a screenshot of the page. You do NOT have access to the accessibility tree.',
        'The screenshot has numbered labels overlaid on interactive elements (Set-of-Marks).',
        'Use these numeric labels as element IDs in your actions.',
      ].join('\n');
      actionNote = [
        'Use the numbered labels visible on the screenshot as element IDs.',
        '',
        'Available actions (use EXACTLY this syntax with regular double quotes):',
        '  click("id")            - Click the element with this label number',
        '  fill("id", "text")     - Fill a text field with the given text',
        '  scroll(x, y)           - Scroll by x,y pixels (e.g., scroll(0, 500))',
        '  hover("id")            - Hover over an element',
        '  goto("url")            - Navigate to a URL',
        '  go_back()              - Go back in browser history',
        '  send_msg_to_user("msg") - Send a message (use "done" when task is complete)',
        '  noop()                 - Do nothing (wait for page to load)',
      ].join('\n');
      break;
    default: // text-only
      modeNote = 'You receive the accessibility tree text representation of the page.';
      actionNote = [
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
      ].join('\n');
      break;
  }

  return [
    'You are a web navigation agent. Your goal is to complete the following task:',
    `Task: ${goal}`,
    '',
    modeNote,
    '',
    actionNote,
    '',
    'IMPORTANT:',
    '- Use regular double quotes " not escaped quotes \\" in your action strings',
    ...(observationMode !== 'vision-only' ? [
      '- Use BARE NUMERIC bid values WITHOUT brackets: click("123") NOT click("[123]")',
      '- The accessibility tree shows [123] but you must use just "123" in actions',
    ] : [
      '- Use the numeric labels from the screenshot: click("123")',
    ]),
    '- If the page is loading, use noop() and wait',
    '- If you cannot complete the task after trying, use send_msg_to_user("cannot complete")',
    '- When the task asks for information, respond with ONLY the direct answer:',
    '  send_msg_to_user("Luma")  — just the answer, no explanation',
    '  send_msg_to_user("$25.99")',
    '  send_msg_to_user("3")',
    '  Do NOT include long explanations. Do NOT use quotes inside the answer text.',
    '- If the task is an action (not a question), use send_msg_to_user("done") when complete',
    '',
    'Respond with a JSON object: {"reasoning": "your thinking", "action": "the action to execute"}',
  ].join('\n');
}

/**
 * Build the user message content for a single step.
 */
function buildUserMessage(
  obs: BrowserGymObservation,
  observationMode: ObservationMode,
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

  // For vision-only mode, do NOT include the accessibility tree — the agent
  // must rely solely on the screenshot. This is the control condition.
  if (observationMode !== 'vision-only') {
    parts.push('');
    parts.push('Accessibility Tree:');
    parts.push(obs.axtree_txt || '[Page content not available]');
  }

  const textContent = parts.join('\n');

  // Vision and vision-only modes: include screenshot as image content block
  if ((observationMode === 'vision' || observationMode === 'vision-only') && obs.screenshot_base64) {
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

  // Sanitize send_msg_to_user: BrowserGym exec()'s the action string as Python code.
  // Internal double quotes in the message text break the Python string literal,
  // causing "ValueError: Received an empty action". Extract the message between
  // the FIRST `("` and the LAST `")` to handle nested parens/quotes correctly.
  if (action.startsWith('send_msg_to_user(')) {
    // Find message content: everything between first `("` and last `")`
    const openIdx = action.indexOf('("');
    const closeIdx = action.lastIndexOf('")');
    let msg: string;
    if (openIdx !== -1 && closeIdx > openIdx) {
      msg = action.slice(openIdx + 2, closeIdx);
    } else {
      // Fallback: strip the function wrapper and any quotes
      msg = action.replace(/^send_msg_to_user\s*\(\s*"?/, '').replace(/"?\s*\)\s*$/, '');
    }
    // Replace internal double quotes with single quotes
    msg = msg.replace(/"/g, "'");
    // Remove newlines that break Python exec()
    msg = msg.replace(/[\r\n]+/g, ' ');
    // Remove backslashes that could break Python string
    msg = msg.replace(/\\/g, '');
    // Truncate to avoid token-explosion in BrowserGym's action parser
    if (msg.length > 500) msg = msg.substring(0, 500);
    action = `send_msg_to_user("${msg}")`;
  }

  return action;
}

/**
 * Extract a balanced-parenthesis function call starting at the given position.
 * Returns the full call string (e.g. `send_msg_to_user("text (with parens)")`)
 * or null if no balanced call is found.
 *
 * This replaces the old non-greedy regex `\([\s\S]*?\)` which truncated at the
 * first `)` inside the message — e.g. `send_msg_to_user("review (in German) is positive")`
 * was cut to `send_msg_to_user("review (in German)` losing the rest.
 */
export function extractBalancedCall(text: string, startIndex: number): string | null {
  // Find the opening paren
  const parenIdx = text.indexOf('(', startIndex);
  if (parenIdx === -1) return null;

  let depth = 0;
  // Track whether we're inside a string literal to avoid counting parens in strings
  let inDouble = false;
  let inSingle = false;

  for (let i = parenIdx; i < text.length; i++) {
    const ch = text[i];
    const prev = i > 0 ? text[i - 1] : '';

    // Handle string delimiters (skip escaped quotes)
    if (ch === '"' && !inSingle && prev !== '\\') {
      inDouble = !inDouble;
      continue;
    }
    if (ch === "'" && !inDouble && prev !== '\\') {
      inSingle = !inSingle;
      continue;
    }

    // Only count parens outside of string literals
    if (!inDouble && !inSingle) {
      if (ch === '(') depth++;
      if (ch === ')') depth--;
      if (depth === 0) {
        return text.slice(startIndex, i + 1);
      }
    }
  }

  // No balanced closing paren found — return best-effort up to end of text,
  // appending a closing `")` for send_msg_to_user so cleanAction can sanitize it.
  const partial = text.slice(startIndex);
  if (partial.startsWith('send_msg_to_user')) {
    // Unbalanced send_msg_to_user — close it so the message isn't lost
    return partial.replace(/\s*$/, '') + '")';
  }
  return null;
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

  // Extract action from inline function call patterns using balanced-paren matching.
  // The old regex `\([\s\S]*?\)` was non-greedy and truncated at the first `)` inside
  // the message text — e.g. `send_msg_to_user("review (in German)")` was cut at
  // `(in German)`. Now we use a depth counter that respects string literals.
  const ACTION_NAMES = /(?:click|fill|type|hover|press|scroll|goto|go_back|go_forward|new_tab|tab_close|tab_focus|select_option|send_msg_to_user|noop|focus)\s*\(/;
  const fnMatch = content.match(ACTION_NAMES);

  if (fnMatch && fnMatch.index !== undefined) {
    const call = extractBalancedCall(content, fnMatch.index);
    if (call) {
      const reasoning = content.replace(call, '').trim();
      return { reasoning, action: cleanAction(call) };
    }
  }

  return { reasoning: content.trim(), action: cleanAction('noop()') };
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
    operatorIds,
    bridgeScriptPath = 'src/runner/browsergym_bridge.py',
    llmCaller = callLlm,
    bridgeSpawner = defaultBridgeSpawner,
    wallClockTimeoutMs = 600_000, // 10 minutes default
  } = options;

  const startTime = Date.now();
  const steps: ActionTraceStep[] = [];
  let totalTokens = 0;
  let envTruncated = false;
  let lastReward = 0;

  const bridge = bridgeSpawner(bridgeScriptPath, {
    taskId, targetUrl, taskGoal, variantLevel: variant,
    observationMode: agentConfig.observationMode,
    // CUA mode: bridge runs its own agent loop (5-10 min), needs longer read timeout
    bridgeReadTimeoutMs: agentConfig.observationMode === 'cua' ? wallClockTimeoutMs + 30_000 : undefined,
    // AMT individual-mode: pass operator IDs to bridge
    operatorIds,
  });

  let bridgeLog = ''; // ISSUE-BR-7: will be populated from bridge stderr

  try {
    // Get initial observation from env.reset()
    let obs = await bridge.readObservation();
    if (!obs) {
      throw new Error('Bridge process terminated before sending initial observation');
    }

    const systemPrompt = buildSystemPrompt(obs.goal || taskGoal, agentConfig.observationMode);
    const maxHistory = agentConfig.maxHistorySteps ?? 6;

    // CUA mode: bridge runs its own agent loop internally.
    // We just wait for the final summary observation.
    if (agentConfig.observationMode === 'cua') {
      console.log(`[executor] CUA mode: waiting for bridge self-driven agent loop (up to ${wallClockTimeoutMs / 1000}s)...`);
      const finalObs = await bridge.readObservation();
      bridgeLog = bridge.getStderrLog();

      if (!finalObs) {
        throw new Error('CUA bridge terminated without sending result');
      }

      // Extract CUA-specific result from the observation
      const cuaResult = (finalObs as unknown as Record<string, unknown>).cua_result as Record<string, unknown> | undefined;
      const cuaOutcome = (cuaResult?.outcome as string) ?? 'failure';
      const cuaSteps = (cuaResult?.steps as Array<Record<string, unknown>>) ?? [];
      const cuaTotalTokens = (cuaResult?.totalTokens as number) ?? 0;
      const cuaDurationMs = (cuaResult?.durationMs as number) ?? (Date.now() - startTime);

      // Convert CUA steps to ActionTraceStep format
      for (const cs of cuaSteps) {
        steps.push({
          stepNum: (cs.step as number) ?? steps.length + 1,
          timestamp: new Date().toISOString(),
          observation: `[cua screenshot] ${finalObs.url}`,
          reasoning: (cs.reasoning as string) ?? '',
          action: `cua:${cs.action ?? 'unknown'}(${JSON.stringify(cs.input ?? {}).substring(0, 100)})`,
          result: cs.error ? 'failure' : 'success',
          resultDetail: (cs.error as string) ?? (cs.answer as string) ?? undefined,
        });
      }

      totalTokens = cuaTotalTokens;
      lastReward = finalObs.reward;

      // Map CUA outcome
      const outcomeMap: Record<string, 'success' | 'partial_success' | 'failure' | 'timeout'> = {
        success: 'success',
        failure: 'failure',
        timeout: 'timeout',
      };
      const mappedOutcome = outcomeMap[cuaOutcome] ?? 'failure';

      // BrowserGym reward is already evaluated by the CUA bridge (it calls
      // env.step(send_msg_to_user) before sending the summary). We don't
      // need to send another action — the bridge has already exited.

      return {
        taskId, variant, agentConfig, attempt,
        success: lastReward > 0 || mappedOutcome === 'success',
        outcome: lastReward > 0 ? 'success' : mappedOutcome,
        steps,
        totalSteps: steps.length,
        totalTokens,
        durationMs: cuaDurationMs,
        bridgeLog: bridgeLog || undefined,
      };
    }

    // --- Normal (non-CUA) agent loop below ---
    // Accumulate conversation history for multi-turn context
    const messageHistory: Array<{ role: string; content: string | object[] }> = [];

    for (let stepNum = 1; stepNum <= agentConfig.maxSteps; stepNum++) {
      // Wall-clock timeout: if the case has been running too long, abort.
      // This prevents a single hung case (e.g., BrowserGym intersection_observer
      // loop, Bedrock rate limit retry storm) from blocking the entire experiment.
      const elapsed = Date.now() - startTime;
      if (elapsed > wallClockTimeoutMs) {
        console.warn(`[executor] Case ${taskId}:${variant} wall-clock timeout after ${Math.round(elapsed / 1000)}s`);
        steps.push({
          stepNum,
          timestamp: new Date().toISOString(),
          observation: '[wall-clock timeout]',
          reasoning: `Case exceeded ${wallClockTimeoutMs / 1000}s wall-clock limit`,
          action: 'noop()',
          result: 'error',
          resultDetail: `wall-clock timeout after ${Math.round(elapsed / 1000)}s`,
        });
        break;
      }

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

      let observationStr: string;
      if (agentConfig.observationMode === 'vision-only') {
        observationStr = `[screenshot only] ${obs.url}`;
      } else if (agentConfig.observationMode === 'vision') {
        observationStr = `[screenshot + axtree] ${obs.url}`;
      } else {
        observationStr = obs.axtree_txt || `[No accessibility tree available] URL: ${obs.url}`;
      }

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
    bridgeLog = bridge.getStderrLog(); // ISSUE-BR-7: capture before close
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
    bridgeLog: bridgeLog || undefined, // ISSUE-BR-7: include bridge stderr in trace
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
  const stderrChunks: string[] = []; // ISSUE-BR-7: capture bridge stderr for trace

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
    const text = data.toString().trim();
    console.warn(`[BrowserGym bridge stderr] ${text}`);
    stderrChunks.push(text); // ISSUE-BR-7: buffer for trace
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
      // Timeout: if bridge doesn't respond within the configured timeout, it's hung.
      // Default 120s for normal mode; CUA mode passes a longer timeout since the
      // bridge runs its own agent loop (5-10 min).
      const BRIDGE_READ_TIMEOUT_MS = taskConfig.bridgeReadTimeoutMs ?? 120_000;
      let timer: ReturnType<typeof setTimeout>;
      const timeoutPromise = new Promise<null>((resolve) => {
        timer = setTimeout(() => {
          console.warn(`[BrowserGym bridge] readObservation timeout after ${BRIDGE_READ_TIMEOUT_MS / 1000}s — killing bridge`);
          try {
            child.kill('SIGKILL');
          } catch { /* already dead */ }
          closed = true;
          resolve(null);
        }, BRIDGE_READ_TIMEOUT_MS);
      });

      const line = await Promise.race([nextLine(), timeoutPromise]);
      clearTimeout(timer!); // ISSUE-BR-1 fix: prevent dangling timer leak
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

    getStderrLog(): string {
      // ISSUE-BR-7: return accumulated stderr, cap at 50KB to avoid trace bloat
      const full = stderrChunks.join('\n');
      return full.length > 50_000 ? full.slice(-50_000) : full;
    },
  };
}

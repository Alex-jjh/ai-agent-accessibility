// Unit tests for Agent Executor (Req 7.1–7.8)

import { describe, it, expect, vi } from 'vitest';
import {
  executeAgentTask,
  parseLlmResponse,
  type BrowserGymObservation,
  type BridgeProcess,
  type BridgeSpawner,
  type ExecuteTaskOptions,
} from './executor.js';
import type { AgentConfig, LlmRequest, LlmResponse } from '../types.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeObs(overrides: Partial<BrowserGymObservation> = {}): BrowserGymObservation {
  return {
    goal: 'Test task goal',
    axtree_txt: '[1] RootWebArea "Test Page"\n  [2] link "Home"\n  [3] button "Submit"',
    url: 'http://localhost:3000/test',
    last_action_error: '',
    terminated: false,
    truncated: false,
    reward: 0,
    step: 0,
    ...overrides,
  };
}

function makeAgentConfig(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    observationMode: 'text-only',
    llmBackend: 'gpt-4o',
    maxSteps: 30,
    retryCount: 3,
    retryBackoffMs: 1000,
    temperature: 0.0,
    ...overrides,
  };
}

/**
 * Create a mock bridge that feeds a sequence of observations
 * and records actions sent to it.
 */
function createMockBridge(observations: BrowserGymObservation[]): {
  bridge: BridgeProcess;
  sentActions: string[];
} {
  const sentActions: string[] = [];
  let obsIndex = 0;

  const bridge: BridgeProcess = {
    sendAction(action: string) {
      sentActions.push(action);
    },
    async readObservation(): Promise<BrowserGymObservation | null> {
      if (obsIndex >= observations.length) return null;
      return observations[obsIndex++];
    },
    async close(): Promise<void> {
      // no-op
    },
  };

  return { bridge, sentActions };
}

/**
 * Create a mock LLM caller that returns a sequence of responses.
 */
function createMockLlmCaller(responses: Array<Partial<LlmResponse> & { content: string }>) {
  let callIndex = 0;
  const calls: LlmRequest[] = [];

  const caller = async (request: LlmRequest): Promise<LlmResponse> => {
    calls.push(request);
    if (callIndex >= responses.length) {
      throw new Error('No more mock LLM responses');
    }
    const resp = responses[callIndex++];
    return {
      content: resp.content,
      tokensUsed: resp.tokensUsed ?? { prompt: 100, completion: 50 },
      model: resp.model ?? 'gpt-4o',
      latencyMs: resp.latencyMs ?? 200,
    };
  };

  return { caller, calls };
}

function makeTaskOptions(overrides: Partial<ExecuteTaskOptions> = {}): ExecuteTaskOptions {
  return {
    taskId: 'test-task-1',
    targetUrl: 'http://localhost:3000/test',
    taskGoal: 'Click the submit button',
    variant: 'base',
    agentConfig: makeAgentConfig(),
    attempt: 1,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// parseLlmResponse
// ---------------------------------------------------------------------------

describe('parseLlmResponse', () => {
  it('parses valid JSON with reasoning and action', () => {
    const content = JSON.stringify({
      reasoning: 'I see a submit button, I will click it.',
      action: 'click("3")',
    });
    const result = parseLlmResponse(content);
    expect(result.reasoning).toBe('I see a submit button, I will click it.');
    expect(result.action).toBe('click("3")');
  });

  it('extracts action from code block when JSON parse fails', () => {
    const content = 'I will click the button.\n```\nclick("3")\n```';
    const result = parseLlmResponse(content);
    expect(result.action).toBe('click("3")');
    expect(result.reasoning).toContain('I will click the button');
  });

  it('extracts inline action calls', () => {
    const content = 'Let me fill the search box: fill("7", "test query")';
    const result = parseLlmResponse(content);
    expect(result.action).toBe('fill("7", "test query")');
  });

  it('returns noop() when no action is found', () => {
    const content = 'I am not sure what to do here.';
    const result = parseLlmResponse(content);
    expect(result.action).toBe('noop()');
  });

  it('handles send_msg_to_user action', () => {
    const content = JSON.stringify({
      reasoning: 'Task is complete.',
      action: 'send_msg_to_user("done")',
    });
    const result = parseLlmResponse(content);
    expect(result.action).toBe('send_msg_to_user("done")');
  });
});


// ---------------------------------------------------------------------------
// executeAgentTask — Action trace logging (Req 7.2, 7.3)
// ---------------------------------------------------------------------------

describe('executeAgentTask', () => {
  it('captures all required fields in action trace steps', async () => {
    const initialObs = makeObs();
    const afterClickObs = makeObs({ step: 1 });
    const doneObs = makeObs({ step: 2, terminated: true, reward: 1 });

    const { bridge, sentActions } = createMockBridge([initialObs, afterClickObs, doneObs]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Click submit', action: 'click("3")' }) },
      { content: JSON.stringify({ reasoning: 'Task done', action: 'send_msg_to_user("done")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({ bridgeSpawner, llmCaller: caller }),
    );

    expect(trace.taskId).toBe('test-task-1');
    expect(trace.variant).toBe('base');
    expect(trace.attempt).toBe(1);
    expect(trace.steps.length).toBe(2);
    expect(trace.totalSteps).toBe(2);
    expect(trace.totalTokens).toBe(300); // 2 calls × (100 + 50)
    expect(trace.durationMs).toBeGreaterThanOrEqual(0);

    // Verify each step has all required fields
    for (const step of trace.steps) {
      expect(step).toHaveProperty('stepNum');
      expect(step).toHaveProperty('timestamp');
      expect(step).toHaveProperty('observation');
      expect(step).toHaveProperty('reasoning');
      expect(step).toHaveProperty('action');
      expect(step).toHaveProperty('result');
      expect(typeof step.stepNum).toBe('number');
      expect(typeof step.timestamp).toBe('string');
      expect(step.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO 8601
    }

    // First step: click action
    expect(trace.steps[0].action).toBe('click("3")');
    expect(trace.steps[0].reasoning).toBe('Click submit');
    expect(trace.steps[0].stepNum).toBe(1);

    // Second step: completion
    expect(trace.steps[1].action).toBe('send_msg_to_user("done")');
    expect(trace.steps[1].stepNum).toBe(2);

    // Actions were sent to bridge
    expect(sentActions).toEqual(['click("3")', 'send_msg_to_user("done")']);
  });

  it('records task outcome as success when agent sends done', async () => {
    const { bridge } = createMockBridge([
      makeObs(),
      makeObs({ step: 1 }),
    ]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Done', action: 'send_msg_to_user("done")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({ bridgeSpawner, llmCaller: caller }),
    );

    expect(trace.success).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // Step limit enforcement and timeout (Req 7.7)
  // ---------------------------------------------------------------------------

  it('enforces step limit and records timeout outcome', async () => {
    const maxSteps = 3;
    // Provide enough observations: 1 initial + 3 step results
    const observations = [
      makeObs(),
      makeObs({ step: 1 }),
      makeObs({ step: 2 }),
      makeObs({ step: 3 }),
    ];

    const { bridge } = createMockBridge(observations);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    // LLM always returns a non-terminal action
    const { caller } = createMockLlmCaller(
      Array.from({ length: maxSteps }, (_, i) => ({
        content: JSON.stringify({ reasoning: `Step ${i + 1}`, action: 'click("2")' }),
      })),
    );

    const trace = await executeAgentTask(
      makeTaskOptions({
        agentConfig: makeAgentConfig({ maxSteps }),
        bridgeSpawner,
        llmCaller: caller,
      }),
    );

    expect(trace.totalSteps).toBe(maxSteps);
    expect(trace.success).toBe(false);
    // The trace should have exactly maxSteps steps
    expect(trace.steps.length).toBe(maxSteps);
  });

  // ---------------------------------------------------------------------------
  // LLM error handling with retry (Req 7.8)
  // ---------------------------------------------------------------------------

  it('records error step when LLM call fails after retries', async () => {
    const { bridge } = createMockBridge([makeObs()]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const failingCaller = async (): Promise<LlmResponse> => {
      throw new Error('LLM API returned 503: Service Unavailable');
    };

    const trace = await executeAgentTask(
      makeTaskOptions({ bridgeSpawner, llmCaller: failingCaller }),
    );

    expect(trace.steps.length).toBe(1);
    expect(trace.steps[0].result).toBe('error');
    expect(trace.steps[0].resultDetail).toContain('503');
    expect(trace.steps[0].action).toBe('noop()');
    expect(trace.success).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Text-only vs Vision observation modes (Req 7.4, 7.5)
  // ---------------------------------------------------------------------------

  it('uses axtree_txt for text-only observation mode', async () => {
    const initialObs = makeObs({ axtree_txt: '[1] RootWebArea "Text Only Page"' });
    const afterActionObs = makeObs({ axtree_txt: '[1] RootWebArea "After Action"', terminated: true });
    const { bridge } = createMockBridge([initialObs, afterActionObs]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller, calls } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Done', action: 'send_msg_to_user("done")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({
        agentConfig: makeAgentConfig({ observationMode: 'text-only' }),
        bridgeSpawner,
        llmCaller: caller,
      }),
    );

    // The observation logged reflects the state after the action (obs is updated)
    expect(trace.steps[0].observation).toContain('After Action');

    // LLM message should be a plain string (not array with image)
    const userMsg = calls[0].messages.find((m) => m.role === 'user');
    expect(typeof userMsg?.content).toBe('string');
    // The LLM was called with the initial observation text
    expect(userMsg?.content).toContain('Text Only Page');
  });

  it('includes screenshot for vision observation mode', async () => {
    const obs = makeObs({
      axtree_txt: '[1] RootWebArea "Vision Page"',
      screenshot_base64: 'iVBORw0KGgoAAAANSUhEUg==',
    });
    const { bridge } = createMockBridge([obs, makeObs({ terminated: true })]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller, calls } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Done', action: 'send_msg_to_user("done")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({
        agentConfig: makeAgentConfig({ observationMode: 'vision' }),
        bridgeSpawner,
        llmCaller: caller,
      }),
    );

    // Observation logged should indicate screenshot mode
    expect(trace.steps[0].observation).toContain('[screenshot + axtree]');

    // LLM message should be an array with text and image_url
    const userMsg = calls[0].messages.find((m) => m.role === 'user');
    expect(Array.isArray(userMsg?.content)).toBe(true);
    const contentArr = userMsg?.content as object[];
    expect(contentArr.some((c: any) => c.type === 'image_url')).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // Token accumulation (Req 7.3)
  // ---------------------------------------------------------------------------

  it('accumulates token usage across steps', async () => {
    const { bridge } = createMockBridge([
      makeObs(),
      makeObs({ step: 1 }),
      makeObs({ step: 2, terminated: true }),
    ]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Step 1', action: 'click("2")' }), tokensUsed: { prompt: 200, completion: 80 } },
      { content: JSON.stringify({ reasoning: 'Done', action: 'send_msg_to_user("done")' }), tokensUsed: { prompt: 250, completion: 60 } },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({ bridgeSpawner, llmCaller: caller }),
    );

    expect(trace.totalTokens).toBe(200 + 80 + 250 + 60); // 590
  });

  // ---------------------------------------------------------------------------
  // Bridge termination handling
  // ---------------------------------------------------------------------------

  it('handles bridge termination before initial observation', async () => {
    const bridge: BridgeProcess = {
      sendAction: vi.fn(),
      readObservation: async () => null,
      close: async () => {},
    };
    const bridgeSpawner: BridgeSpawner = () => bridge;

    await expect(
      executeAgentTask(makeTaskOptions({ bridgeSpawner })),
    ).rejects.toThrow('Bridge process terminated before sending initial observation');
  });

  it('stops execution when environment signals terminated', async () => {
    const { bridge } = createMockBridge([
      makeObs(),
      makeObs({ step: 1, terminated: true, reward: 1 }),
    ]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Click', action: 'click("3")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({
        agentConfig: makeAgentConfig({ maxSteps: 10 }),
        bridgeSpawner,
        llmCaller: caller,
      }),
    );

    // Should stop after 1 step even though maxSteps is 10
    expect(trace.totalSteps).toBe(1);
  });

  it('records action error from bridge in step result', async () => {
    const { bridge } = createMockBridge([
      makeObs(),
      makeObs({ step: 1, last_action_error: 'Element bid="99" not found' }),
      makeObs({ step: 2, terminated: true }),
    ]);
    const bridgeSpawner: BridgeSpawner = () => bridge;

    const { caller } = createMockLlmCaller([
      { content: JSON.stringify({ reasoning: 'Click missing', action: 'click("99")' }) },
      { content: JSON.stringify({ reasoning: 'Give up', action: 'send_msg_to_user("cannot complete")' }) },
    ]);

    const trace = await executeAgentTask(
      makeTaskOptions({ bridgeSpawner, llmCaller: caller }),
    );

    expect(trace.steps[0].result).toBe('failure');
    expect(trace.steps[0].resultDetail).toContain('not found');
    expect(trace.success).toBe(false);
  });
});

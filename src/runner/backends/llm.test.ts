// Unit tests for LLM Backend Adapter (Req 7.6, 7.8)

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { callLlm } from './llm.js';
import type { LlmRequest } from '../types.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeLlmRequest(overrides: Partial<LlmRequest> = {}): LlmRequest {
  return {
    model: 'gpt-4o',
    messages: [{ role: 'user', content: 'Hello' }],
    temperature: 0.0,
    maxTokens: 1024,
    ...overrides,
  };
}

function makeSuccessResponse(content = 'Hello back') {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      id: 'chatcmpl-123',
      model: 'gpt-4o',
      choices: [{ index: 0, message: { role: 'assistant', content }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
    }),
    text: async () => '',
  } as unknown as Response;
}

function makeErrorResponse(status: number, body: string) {
  return {
    ok: false,
    status,
    json: async () => ({}),
    text: async () => body,
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('callLlm', () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('returns structured response on success', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(makeSuccessResponse('Test response'));

    const result = await callLlm(makeLlmRequest());

    expect(result.content).toBe('Test response');
    expect(result.tokensUsed.prompt).toBe(10);
    expect(result.tokensUsed.completion).toBe(5);
    expect(result.model).toBe('gpt-4o');
    expect(result.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it('sends correct request body to LiteLLM proxy', async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeSuccessResponse());
    globalThis.fetch = mockFetch;

    await callLlm(makeLlmRequest({ model: 'claude-3-opus-20240229', temperature: 0.5 }));

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:4000/v1/chat/completions');
    expect(options.method).toBe('POST');

    const body = JSON.parse(options.body);
    expect(body.model).toBe('claude-3-opus-20240229');
    expect(body.temperature).toBe(0.5);
    expect(body.messages).toEqual([{ role: 'user', content: 'Hello' }]);
  });

  it('retries with exponential backoff on failure', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce(makeErrorResponse(503, 'Service Unavailable'))
      .mockResolvedValueOnce(makeErrorResponse(429, 'Rate limited'))
      .mockResolvedValueOnce(makeSuccessResponse('Recovered'));

    globalThis.fetch = mockFetch;

    const result = await callLlm(makeLlmRequest(), { maxRetries: 3, backoffMs: 1 });

    expect(result.content).toBe('Recovered');
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('throws after exhausting all retries', async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeErrorResponse(500, 'Internal Server Error'));
    globalThis.fetch = mockFetch;

    await expect(
      callLlm(makeLlmRequest(), { maxRetries: 2, backoffMs: 1 }),
    ).rejects.toThrow(/failed after 3 attempts/);

    // 1 initial + 2 retries = 3 total calls
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('retries on network errors', async () => {
    const mockFetch = vi.fn()
      .mockRejectedValueOnce(new Error('fetch failed'))
      .mockResolvedValueOnce(makeSuccessResponse('OK'));

    globalThis.fetch = mockFetch;

    const result = await callLlm(makeLlmRequest(), { maxRetries: 2, backoffMs: 1 });
    expect(result.content).toBe('OK');
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('handles missing usage in response gracefully', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        model: 'gpt-4o',
        choices: [{ index: 0, message: { role: 'assistant', content: 'Hi' }, finish_reason: 'stop' }],
        // no usage field
      }),
      text: async () => '',
    } as unknown as Response);

    const result = await callLlm(makeLlmRequest());
    expect(result.content).toBe('Hi');
    expect(result.tokensUsed.prompt).toBe(0);
    expect(result.tokensUsed.completion).toBe(0);
  });

  it('handles empty choices gracefully', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        model: 'gpt-4o',
        choices: [],
        usage: { prompt_tokens: 5, completion_tokens: 0 },
      }),
      text: async () => '',
    } as unknown as Response);

    const result = await callLlm(makeLlmRequest());
    expect(result.content).toBe('');
  });
});

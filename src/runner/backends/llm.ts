// Module 3: Agent Runner — LLM Backend Adapter
// Calls LiteLLM proxy with exponential backoff retry (Req 7.6, 7.8)

import type { LlmRequest, LlmResponse } from '../types.js';

/** Retry configuration for LLM calls */
export interface RetryConfig {
  maxRetries: number;   // default 3
  backoffMs: number;    // default 1000 — delay = backoffMs * 2^attempt
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  backoffMs: 1000,
};

const LITELLM_BASE_URL = 'http://localhost:4000/v1/chat/completions';

/**
 * Call an LLM backend via the LiteLLM proxy with exponential backoff retry.
 * Supports Claude and GPT-4o backends via model name prefix.
 *
 * @param request - The LLM request payload
 * @param retryConfig - Optional retry configuration (defaults: 3 retries, 1s base backoff)
 * @returns Structured LLM response with content, token usage, model, and latency
 */
export async function callLlm(
  request: LlmRequest,
  retryConfig: Partial<RetryConfig> = {},
): Promise<LlmResponse> {
  const config: RetryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    if (attempt > 0) {
      const delayMs = config.backoffMs * Math.pow(2, attempt - 1);
      await sleep(delayMs);
    }

    const startMs = Date.now();
    try {
      const response = await fetch(LITELLM_BASE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: request.model,
          messages: request.messages,
          temperature: request.temperature,
          max_tokens: request.maxTokens,
        }),
      });

      if (!response.ok) {
        const body = await response.text().catch(() => '');
        throw new Error(`LLM API returned ${response.status}: ${body}`);
      }

      const data = await response.json() as OpenAIChatResponse;
      const latencyMs = Date.now() - startMs;

      const content = data.choices?.[0]?.message?.content ?? '';
      const usage = data.usage ?? { prompt_tokens: 0, completion_tokens: 0 };

      return {
        content,
        tokensUsed: {
          prompt: usage.prompt_tokens,
          completion: usage.completion_tokens,
        },
        model: data.model ?? request.model,
        latencyMs,
      };
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      if (attempt < config.maxRetries) {
        console.warn(
          `LLM call attempt ${attempt + 1}/${config.maxRetries + 1} failed: ${lastError.message}. Retrying...`,
        );
      }
    }
  }

  throw new Error(
    `LLM call failed after ${config.maxRetries + 1} attempts: ${lastError?.message}`,
  );
}

/** Sleep for the given number of milliseconds */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** OpenAI-compatible chat completion response shape (subset) */
interface OpenAIChatResponse {
  id?: string;
  model?: string;
  choices?: Array<{
    index: number;
    message: { role: string; content: string };
    finish_reason: string;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens?: number;
  };
}

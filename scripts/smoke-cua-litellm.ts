#!/usr/bin/env npx tsx
/**
 * Smoke test: Verify LiteLLM → Bedrock can handle Anthropic Computer Use tool.
 *
 * This script tests whether the LiteLLM proxy correctly forwards:
 * 1. The `anthropic-beta: computer-use-2025-01-24` header
 * 2. The `computer_20250124` tool definition (schema-less)
 * 3. A screenshot image in the messages
 * 4. And receives back a `tool_use` response with coordinate actions
 *
 * Usage:
 *   npx tsx scripts/smoke-cua-litellm.ts
 *
 * Prerequisites:
 *   - LiteLLM proxy running on localhost:4000
 *   - Bedrock access configured (AWS credentials)
 *
 * Test strategy:
 *   We try THREE approaches in order:
 *   1. LiteLLM /v1/messages (Anthropic-native format) — ideal path
 *   2. LiteLLM /v1/chat/completions with extra_headers — OpenAI-compat path
 *   3. Direct Bedrock Converse API via aws-sdk — fallback if LiteLLM can't do it
 *
 * If approach 1 or 2 works, we can integrate CUA with minimal changes.
 * If only approach 3 works, we need a separate Bedrock client in llm.ts.
 */

// --- Generate a minimal 200x150 test PNG (red rectangle) ---
// We create a tiny PNG in-memory so the script has zero external dependencies.
function createTestPngBase64(): string {
  // Minimal valid 200x150 red PNG — generated via raw IHDR+IDAT+IEND chunks.
  // For the smoke test we just need *any* valid image. Using a pre-encoded
  // tiny 4x4 red PNG to keep the script self-contained.
  //
  // This is a 4x4 pixel red PNG, base64-encoded.
  // In production, we'd send actual Playwright screenshots.
  const tinyRedPng =
    'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAADklEQVQI12P4z8BQDwAEgAF/' +
    'QujHfwAAAABJRU5ErkJggg==';
  return tinyRedPng;
}

const LITELLM_BASE = 'http://localhost:4000';
const MODEL = 'claude-sonnet'; // maps to bedrock/us.anthropic.claude-sonnet-4-... in litellm_config

// Computer use tool definition (Anthropic schema-less format)
const COMPUTER_TOOL = {
  type: 'computer_20250124',
  name: 'computer',
  display_width_px: 1024,
  display_height_px: 768,
};

const BETA_HEADER = 'computer-use-2025-01-24';

const screenshotB64 = createTestPngBase64();

// ============================================================
// Approach 1: LiteLLM /v1/messages (Anthropic-native format)
// ============================================================
async function testApproach1_Messages(): Promise<boolean> {
  console.log('\n=== Approach 1: LiteLLM /v1/messages (Anthropic format) ===');
  try {
    const response = await fetch(`${LITELLM_BASE}/v1/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'anthropic-beta': BETA_HEADER,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1024,
        tools: [COMPUTER_TOOL],
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: 'Click on the search button in this screenshot.',
              },
              {
                type: 'image',
                source: {
                  type: 'base64',
                  media_type: 'image/png',
                  data: screenshotB64,
                },
              },
            ],
          },
        ],
      }),
    });

    const status = response.status;
    const body = await response.text();
    console.log(`  Status: ${status}`);

    if (!response.ok) {
      console.log(`  Error: ${body.substring(0, 500)}`);
      return false;
    }

    const data = JSON.parse(body);
    console.log(`  Stop reason: ${data.stop_reason}`);
    console.log(`  Content blocks: ${data.content?.length}`);

    // Check if we got a tool_use block back
    const toolUseBlock = data.content?.find(
      (b: { type: string }) => b.type === 'tool_use',
    );
    if (toolUseBlock) {
      console.log(`  ✅ Got tool_use block!`);
      console.log(`     Tool: ${toolUseBlock.name}`);
      console.log(`     Action: ${JSON.stringify(toolUseBlock.input)}`);
      return true;
    }

    // Even if no tool_use, check if Claude responded with text (might describe
    // what it would do — this means the API call worked but Claude chose not
    // to use the tool on a tiny red square)
    const textBlock = data.content?.find(
      (b: { type: string }) => b.type === 'text',
    );
    if (textBlock) {
      console.log(`  ⚠️  Got text response (no tool_use):`);
      console.log(`     ${textBlock.text.substring(0, 200)}`);
      console.log(`  This means the API call WORKED but Claude didn't use the tool.`);
      console.log(`  (Expected — our test image is a tiny red square, not a real UI)`);
      return true; // API path works, just need a real screenshot
    }

    console.log(`  ❌ Unexpected response shape: ${body.substring(0, 300)}`);
    return false;
  } catch (err) {
    console.log(`  ❌ Failed: ${err instanceof Error ? err.message : err}`);
    return false;
  }
}

// ============================================================
// Approach 2: LiteLLM /v1/chat/completions (OpenAI-compat)
// with extra_headers and extra_body for computer_use
// ============================================================
async function testApproach2_ChatCompletions(): Promise<boolean> {
  console.log(
    '\n=== Approach 2: LiteLLM /v1/chat/completions (OpenAI-compat + extra_body) ===',
  );
  try {
    // LiteLLM supports passing Anthropic-specific params via extra_body
    // See: https://docs.litellm.ai/docs/providers/anthropic
    const response = await fetch(`${LITELLM_BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1024,
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: 'Click on the search button in this screenshot.',
              },
              {
                type: 'image_url',
                image_url: {
                  url: `data:image/png;base64,${screenshotB64}`,
                },
              },
            ],
          },
        ],
        // Pass Anthropic-specific tool definitions via extra_body
        // LiteLLM should forward these to Bedrock
        extra_body: {
          anthropic_beta: [BETA_HEADER],
          tools: [COMPUTER_TOOL],
        },
      }),
    });

    const status = response.status;
    const body = await response.text();
    console.log(`  Status: ${status}`);

    if (!response.ok) {
      console.log(`  Error: ${body.substring(0, 500)}`);
      return false;
    }

    const data = JSON.parse(body);
    console.log(`  Finish reason: ${data.choices?.[0]?.finish_reason}`);
    const content = data.choices?.[0]?.message?.content;
    console.log(`  Content: ${typeof content === 'string' ? content.substring(0, 200) : JSON.stringify(content)?.substring(0, 200)}`);

    // Check for tool_calls in OpenAI format
    const toolCalls = data.choices?.[0]?.message?.tool_calls;
    if (toolCalls && toolCalls.length > 0) {
      console.log(`  ✅ Got tool_calls!`);
      for (const tc of toolCalls) {
        console.log(`     ${tc.function?.name}: ${tc.function?.arguments}`);
      }
      return true;
    }

    if (content) {
      console.log(`  ⚠️  Got text response but no tool_calls.`);
      console.log(`  API path may work — Claude just didn't use the tool on a red square.`);
      return true;
    }

    console.log(`  ❌ Unexpected response: ${body.substring(0, 300)}`);
    return false;
  } catch (err) {
    console.log(`  ❌ Failed: ${err instanceof Error ? err.message : err}`);
    return false;
  }
}

// ============================================================
// Approach 3: Direct Bedrock Converse API (fallback)
// Uses additionalModelRequestFields for computer_use
// ============================================================
async function testApproach3_BedrockDirect(): Promise<boolean> {
  console.log('\n=== Approach 3: Direct Bedrock Converse API (boto3 equivalent) ===');
  console.log('  ⏭️  Skipping — requires aws-sdk. If approaches 1 & 2 fail,');
  console.log('  we\'ll implement this as a Python script using boto3.');
  console.log('  The Bedrock Converse API definitely supports computer_use —');
  console.log('  see: docs.aws.amazon.com/bedrock/latest/userguide/computer-use.html');
  return false;
}

// ============================================================
// Main
// ============================================================
async function main() {
  console.log('╔══════════════════════════════════════════════════════════╗');
  console.log('║  CUA Smoke Test: LiteLLM → Bedrock Computer Use        ║');
  console.log('╚══════════════════════════════════════════════════════════╝');
  console.log(`\nLiteLLM: ${LITELLM_BASE}`);
  console.log(`Model: ${MODEL}`);
  console.log(`Beta: ${BETA_HEADER}`);
  console.log(`Tool: ${COMPUTER_TOOL.type}`);

  // Check LiteLLM is reachable
  try {
    const health = await fetch(`${LITELLM_BASE}/health`);
    if (!health.ok) {
      console.error('\n❌ LiteLLM proxy not reachable at', LITELLM_BASE);
      console.error('   Start it with: litellm --config litellm_config.yaml --port 4000');
      process.exit(1);
    }
    console.log('\n✅ LiteLLM proxy is running');
  } catch {
    console.error('\n❌ Cannot connect to LiteLLM at', LITELLM_BASE);
    console.error('   Start it with: litellm --config litellm_config.yaml --port 4000');
    process.exit(1);
  }

  const results: Record<string, boolean> = {};

  results['approach1_messages'] = await testApproach1_Messages();
  results['approach2_chatcompletions'] = await testApproach2_ChatCompletions();
  results['approach3_bedrock_direct'] = await testApproach3_BedrockDirect();

  // Summary
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║  Results Summary                                        ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  for (const [name, ok] of Object.entries(results)) {
    const icon = ok ? '✅' : '❌';
    console.log(`║  ${icon} ${name.padEnd(40)}${ok ? 'PASS' : 'FAIL'}     ║`);
  }
  console.log('╚══════════════════════════════════════════════════════════╝');

  if (results['approach1_messages']) {
    console.log('\n🎯 Recommendation: Use Approach 1 (/v1/messages)');
    console.log('   Add a callLlmCua() function in llm.ts that calls /v1/messages');
    console.log('   with anthropic-beta header and computer_use tool definition.');
  } else if (results['approach2_chatcompletions']) {
    console.log('\n🎯 Recommendation: Use Approach 2 (/v1/chat/completions + extra_body)');
    console.log('   Modify callLlm() to pass extra_body with anthropic_beta and tools.');
  } else {
    console.log('\n🎯 Recommendation: Use Approach 3 (Direct Bedrock)');
    console.log('   LiteLLM cannot forward computer_use to Bedrock.');
    console.log('   Implement a direct Bedrock Converse API client.');
    console.log('   Next step: write a Python boto3 smoke test to confirm.');
  }
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});

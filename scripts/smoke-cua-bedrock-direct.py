#!/usr/bin/env python3
"""
Smoke test: Direct Bedrock Converse API for Computer Use.

Fallback test if LiteLLM cannot forward computer_use tool definitions.
Uses boto3 directly to call Bedrock's Converse API with:
  - computer_20241022 tool type
  - anthropic_beta: ["computer-use-2024-10-22"]
  - A test screenshot image

Usage:
  python scripts/smoke-cua-bedrock-direct.py

Prerequisites:
  pip install boto3
  AWS credentials configured (via env vars, ~/.aws/credentials, or EC2 instance role)

Note on tool versions:
  Bedrock docs reference computer_20241022 (older version).
  Anthropic docs reference computer_20250124 (newer, for Claude 4 models).
  We test BOTH to see which Bedrock accepts for our model.
"""

import base64
import json
import sys

try:
    import boto3
except ImportError:
    print("❌ boto3 not installed. Run: pip install boto3")
    sys.exit(1)


# Minimal 4x4 red PNG for testing
TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAADklEQVQI12P4z8BQDwAEgAF/"
    "QujHfwAAAABJRU5ErkJggg=="
)

# Bedrock model ID — Claude Sonnet 4 (cross-region inference)
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = "us-east-2"


def test_converse_api(tool_version: str, beta_version: str) -> bool:
    """Test Bedrock Converse API with computer use tool."""
    print(f"\n--- Testing tool={tool_version}, beta={beta_version} ---")

    client = boto3.client("bedrock-runtime", region_name=REGION)
    png_bytes = base64.b64decode(TEST_PNG_B64)

    try:
        response = client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": "Click on the search button in this screenshot."},
                        {
                            "image": {
                                "format": "png",
                                "source": {"bytes": png_bytes},
                            }
                        },
                    ],
                }
            ],
            additionalModelRequestFields={
                "tools": [
                    {
                        "type": tool_version,
                        "name": "computer",
                        "display_height_px": 768,
                        "display_width_px": 1024,
                    }
                ],
                "anthropic_beta": [beta_version],
            },
            # Bedrock Converse requires at least one tool in toolConfig
            # even when using additionalModelRequestFields for Anthropic tools.
            # We add a dummy tool to satisfy the schema.
            toolConfig={
                "tools": [
                    {
                        "toolSpec": {
                            "name": "send_msg_to_user",
                            "description": "Send a message to the user when task is complete",
                            "inputSchema": {
                                "json": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string",
                                            "description": "Message to send",
                                        }
                                    },
                                    "required": ["message"],
                                }
                            },
                        }
                    }
                ]
            },
        )

        # Parse response
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        stop_reason = response.get("stopReason", "unknown")
        usage = response.get("usage", {})

        print(f"  Stop reason: {stop_reason}")
        print(f"  Tokens: input={usage.get('inputTokens', '?')}, output={usage.get('outputTokens', '?')}")
        print(f"  Content blocks: {len(content)}")

        for block in content:
            if "text" in block:
                print(f"  Text: {block['text'][:200]}")
            elif "toolUse" in block:
                tu = block["toolUse"]
                print(f"  ✅ Tool use: {tu.get('name')} → {json.dumps(tu.get('input', {}))}")
                return True

        # If we got a text response, the API call worked even if Claude
        # didn't use the tool (expected for a tiny red square)
        if any("text" in b for b in content):
            print("  ⚠️  API call succeeded but Claude didn't use the tool.")
            print("  (Expected — test image is a 4x4 red square, not a real UI)")
            return True

        print(f"  ❌ Unexpected response: {json.dumps(content)[:300]}")
        return False

    except client.exceptions.ValidationException as e:
        print(f"  ❌ ValidationException: {e}")
        return False
    except client.exceptions.ModelErrorException as e:
        print(f"  ❌ ModelErrorException: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
        return False


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  CUA Smoke Test: Direct Bedrock Converse API            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nModel: {MODEL_ID}")
    print(f"Region: {REGION}")

    results = {}

    # Test 1: Older tool version (documented in Bedrock docs)
    results["computer_20241022"] = test_converse_api(
        "computer_20241022", "computer-use-2024-10-22"
    )

    # Test 2: Newer tool version (documented in Anthropic docs for Claude 4)
    results["computer_20250124"] = test_converse_api(
        "computer_20250124", "computer-use-2025-01-24"
    )

    # Summary
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  Results Summary                                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        status = "PASS" if ok else "FAIL"
        print(f"║  {icon} {name:<40} {status:<8} ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if any(results.values()):
        working = [k for k, v in results.items() if v]
        print(f"\n🎯 Bedrock supports computer use with: {', '.join(working)}")
        print("   If LiteLLM can't forward this, we can call Bedrock directly")
        print("   from the executor using @aws-sdk/client-bedrock-runtime.")
    else:
        print("\n❌ Neither tool version worked with Bedrock Converse API.")
        print("   Check: 1) Model access enabled in Bedrock console")
        print("          2) AWS credentials have bedrock:InvokeModel permission")
        print("          3) Model supports computer use (Claude 3.5 Sonnet v2+)")


if __name__ == "__main__":
    main()

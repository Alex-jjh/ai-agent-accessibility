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


# Generate a proper-sized test PNG (1024x768) using PIL or raw bytes.
# Computer use requires a reasonably sized screenshot — tiny images get rejected.
def _generate_test_png() -> bytes:
    """Generate a 1024x768 test PNG with some UI-like elements."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1024, 768), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        # Draw a fake toolbar
        draw.rectangle([0, 0, 1024, 50], fill=(50, 50, 50))
        draw.text((20, 15), "File  Edit  View  Help", fill=(255, 255, 255))
        # Draw a fake search button
        draw.rectangle([800, 10, 900, 40], fill=(0, 120, 215))
        draw.text((820, 17), "Search", fill=(255, 255, 255))
        # Draw some content
        draw.text((50, 100), "Welcome to the test page", fill=(0, 0, 0))
        draw.rectangle([50, 150, 300, 180], outline=(0, 0, 0))
        draw.text((60, 155), "Username", fill=(128, 128, 128))
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: generate a minimal valid 64x64 PNG without PIL
        # (unlikely on EC2 since PIL is installed for BrowserGym)
        import struct, zlib
        width, height = 64, 64
        raw = b""
        for _ in range(height):
            raw += b"\x00" + b"\xc0\xc0\xc0" * width  # gray pixels
        compressed = zlib.compress(raw)
        def chunk(ctype, data):
            c = ctype + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", compressed)
        png += chunk(b"IEND", b"")
        return png

TEST_PNG_BYTES = _generate_test_png()
TEST_PNG_B64 = base64.b64encode(TEST_PNG_BYTES).decode("ascii")
print(f"Test image: {len(TEST_PNG_BYTES)} bytes, base64 length: {len(TEST_PNG_B64)}")

# Bedrock model ID — Claude Sonnet 4 (cross-region inference)
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = "us-east-2"


def test_converse_api(tool_version: str, beta_version: str) -> bool:
    """Test Bedrock Converse API with computer use tool."""
    print(f"\n--- Testing tool={tool_version}, beta={beta_version} ---")

    client = boto3.client("bedrock-runtime", region_name=REGION)
    png_bytes = TEST_PNG_BYTES

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

    # Skip computer_20241022 — Bedrock confirmed it's not supported for Sonnet 4:
    # "Did you mean one of bash_20250124, computer_20250124, text_editor_20250124..."
    print("\n  ⏭️  Skipping computer_20241022 (confirmed incompatible with Sonnet 4)")

    # Test: Correct tool version for Sonnet 4
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

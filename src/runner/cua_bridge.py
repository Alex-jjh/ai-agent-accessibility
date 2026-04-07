"""
CUA (Computer Use Agent) Bridge — Coordinate-based vision agent via Bedrock.

This module implements a self-driving agent loop that uses Anthropic's Computer Use
tool through AWS Bedrock Converse API. The agent sees only raw screenshots (no DOM,
no a11y tree, no SoM overlays) and interacts via pixel coordinates.

Architecture:
  - Called from browsergym_bridge.py when observationMode == "cua"
  - Runs its own agent loop internally (screenshot → Bedrock → execute action → repeat)
  - Communicates results back to the TS executor via the same JSON-line protocol
  - Uses Playwright page directly for actions (page.mouse.click, page.keyboard.type)
  - Does NOT use BrowserGym's env.step() for actions — zero DOM dependency

This is the "true vision" control condition: DOM mutations (variant patches) change
semantic structure but the agent never reads DOM. If CUA performance is unaffected
by accessibility degradation while text-only drops, the causal arrow points to the
a11y tree, not visual layout.
"""

import base64
import io
import json
import math
import sys
import time
import traceback

import boto3
import numpy as np

# Bedrock config — matches litellm_config.yaml
BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
BEDROCK_REGION = "us-east-2"
BETA_VERSION = "computer-use-2025-01-24"
TOOL_VERSION = "computer_20250124"

# Screenshot scaling: Anthropic limits to 1568px long edge, ~1.15MP total
MAX_LONG_EDGE = 1568
MAX_TOTAL_PIXELS = 1_150_000

# Agent loop limits
DEFAULT_MAX_STEPS = 30


def get_scale_factor(width: int, height: int) -> float:
    """Calculate scale factor to meet Anthropic's image size constraints."""
    long_edge = max(width, height)
    long_edge_scale = MAX_LONG_EDGE / long_edge
    total_pixels_scale = math.sqrt(MAX_TOTAL_PIXELS / (width * height))
    return min(1.0, long_edge_scale, total_pixels_scale)


def capture_screenshot_b64(page) -> tuple[str, int, int, float]:
    """Capture screenshot from Playwright page, scale it, return (base64, orig_w, orig_h, scale).

    Returns the screenshot as base64 PNG, plus dimensions and scale factor
    needed for coordinate mapping.
    """
    from PIL import Image

    # Get viewport size
    viewport = page.viewport_size
    orig_w = viewport["width"] if viewport else 1280
    orig_h = viewport["height"] if viewport else 720

    # Capture raw screenshot
    png_bytes = page.screenshot(type="png")
    img = Image.open(io.BytesIO(png_bytes))
    actual_w, actual_h = img.size

    # Calculate scale
    scale = get_scale_factor(actual_w, actual_h)

    if scale < 1.0:
        scaled_w = int(actual_w * scale)
        scaled_h = int(actual_h * scale)
        img = img.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Encode to base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return b64, actual_w, actual_h, scale


def call_bedrock_cua(
    client,
    messages: list,
    goal: str,
    display_w: int,
    display_h: int,
) -> dict:
    """Call Bedrock Converse API with computer_use tool.

    Returns the full response dict from Bedrock.
    """
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": (
            f"You are a web navigation agent. Complete this task: {goal}\n\n"
            "You can see the browser screenshot. Use the computer tool to interact.\n"
            "When the task is complete, respond with a text message starting with 'DONE:' "
            "followed by your answer.\n"
            "If you cannot complete the task, respond with 'CANNOT_COMPLETE: reason'.\n"
            "Be concise and efficient. Click precisely on UI elements."
        )}],
        messages=messages,
        additionalModelRequestFields={
            "tools": [
                {
                    "type": TOOL_VERSION,
                    "name": "computer",
                    "display_height_px": display_h,
                    "display_width_px": display_w,
                }
            ],
            "anthropic_beta": [BETA_VERSION],
        },
    )
    return response


def execute_cua_action(page, action: str, input_data: dict, scale: float) -> str | None:
    """Execute a computer use action on the Playwright page.

    Handles coordinate scaling: Claude returns coordinates in the scaled image space,
    we need to map them back to the original page space.

    Returns an error string if the action failed, None on success.
    """
    try:
        if action == "left_click":
            x, y = input_data["coordinate"]
            page.mouse.click(x / scale, y / scale)
        elif action == "right_click":
            x, y = input_data["coordinate"]
            page.mouse.click(x / scale, y / scale, button="right")
        elif action == "double_click":
            x, y = input_data["coordinate"]
            page.mouse.dblclick(x / scale, y / scale)
        elif action == "middle_click":
            x, y = input_data["coordinate"]
            page.mouse.click(x / scale, y / scale, button="middle")
        elif action == "mouse_move":
            x, y = input_data["coordinate"]
            page.mouse.move(x / scale, y / scale)
        elif action == "type":
            text = input_data.get("text", "")
            page.keyboard.type(text)
        elif action == "key":
            key_combo = input_data.get("text", "")
            # Anthropic uses "ctrl+a" format, Playwright uses "Control+a"
            key_combo = key_combo.replace("ctrl", "Control").replace("alt", "Alt")
            key_combo = key_combo.replace("shift", "Shift").replace("cmd", "Meta")
            key_combo = key_combo.replace("super", "Meta")
            page.keyboard.press(key_combo)
        elif action == "scroll":
            x, y = input_data.get("coordinate", [0, 0])
            direction = input_data.get("direction", "down")
            amount = input_data.get("amount", 3)
            # Playwright scroll: positive deltaY = scroll down
            delta_map = {"up": -120, "down": 120, "left": -120, "right": 120}
            delta = delta_map.get(direction, 120) * amount
            if direction in ("up", "down"):
                page.mouse.wheel(0, delta)
            else:
                page.mouse.wheel(delta, 0)
        elif action == "screenshot":
            pass  # No-op — we always take a screenshot after each step
        elif action == "wait":
            duration = input_data.get("duration", 1)
            time.sleep(min(duration, 5))  # Cap at 5s
        else:
            return f"Unknown action: {action}"
        return None
    except Exception as e:
        return f"Action {action} failed: {e}"


def run_cua_agent_loop(env, config: dict, send_fn) -> None:
    """Run the CUA agent loop: screenshot → Bedrock → execute → repeat.

    This is the main entry point called from browsergym_bridge.py.
    It runs the full agent loop internally and sends results via send_fn
    (the JSON-line protocol to the TS executor).

    Args:
        env: BrowserGym environment (already reset, with variant patches applied)
        config: Task config dict from the executor
        send_fn: Function to send JSON observations to stdout
    """
    goal = config.get("taskGoal", "")
    max_steps = config.get("maxSteps", DEFAULT_MAX_STEPS)
    page = env.unwrapped.page

    # Initialize Bedrock client
    client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    # Conversation history for multi-turn
    messages = []
    steps = []
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    print(f"[cua] Starting CUA agent loop: goal='{goal[:80]}', max_steps={max_steps}", file=sys.stderr)

    final_answer = ""
    outcome = "failure"

    for step_num in range(1, max_steps + 1):
        elapsed = time.time() - start_time
        if elapsed > 600:  # 10 min wall-clock timeout
            print(f"[cua] Wall-clock timeout after {elapsed:.0f}s", file=sys.stderr)
            outcome = "timeout"
            break

        # 1. Capture screenshot
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        time.sleep(0.5)  # Let page settle

        try:
            screenshot_b64, orig_w, orig_h, scale = capture_screenshot_b64(page)
        except Exception as e:
            print(f"[cua] Screenshot failed: {e}", file=sys.stderr)
            steps.append({"step": step_num, "action": "screenshot_error", "error": str(e)})
            continue

        # 2. Build message with screenshot
        user_content = [
            {"text": f"Step {step_num}. Current URL: {page.url}"},
            {
                "image": {
                    "format": "png",
                    "source": {"bytes": base64.b64decode(screenshot_b64)},
                }
            },
        ]
        messages.append({"role": "user", "content": user_content})

        # 3. Call Bedrock
        try:
            # Calculate display dimensions (what Claude sees after scaling)
            display_w = int(orig_w * scale)
            display_h = int(orig_h * scale)

            response = call_bedrock_cua(client, messages, goal, display_w, display_h)
        except Exception as e:
            print(f"[cua] Bedrock call failed: {e}", file=sys.stderr)
            steps.append({"step": step_num, "action": "llm_error", "error": str(e)})
            # Remove the user message we just added (so conversation stays valid)
            messages.pop()
            continue

        # 4. Parse response
        usage = response.get("usage", {})
        total_input_tokens += usage.get("inputTokens", 0)
        total_output_tokens += usage.get("outputTokens", 0)

        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])
        stop_reason = response.get("stopReason", "unknown")

        # Add assistant response to conversation
        messages.append({"role": "assistant", "content": content_blocks})

        # 5. Process content blocks
        text_response = ""
        tool_uses = []
        for block in content_blocks:
            if "text" in block:
                text_response = block["text"]
            elif "toolUse" in block:
                tool_uses.append(block["toolUse"])

        # Check for task completion via text response
        if text_response:
            if text_response.startswith("DONE:"):
                final_answer = text_response[5:].strip()
                outcome = "success"
                steps.append({"step": step_num, "action": "done", "answer": final_answer,
                              "reasoning": text_response})
                print(f"[cua] Task complete: {final_answer[:100]}", file=sys.stderr)
                break
            elif text_response.startswith("CANNOT_COMPLETE"):
                final_answer = text_response
                outcome = "failure"
                steps.append({"step": step_num, "action": "cannot_complete",
                              "reasoning": text_response})
                print(f"[cua] Cannot complete: {text_response[:100]}", file=sys.stderr)
                break

        # 6. Execute tool actions
        if not tool_uses and stop_reason != "tool_use":
            # Claude responded with text only, no tool use — might be thinking
            steps.append({"step": step_num, "action": "text_only",
                          "reasoning": text_response[:200]})
            print(f"[cua] Step {step_num}: text only (no tool_use)", file=sys.stderr)
            continue

        for tu in tool_uses:
            tool_name = tu.get("name", "")
            tool_input = tu.get("input", {})
            tool_id = tu.get("toolUseId", "")
            action = tool_input.get("action", "screenshot")

            print(f"[cua] Step {step_num}: {action} {json.dumps(tool_input)[:100]}", file=sys.stderr)

            error = execute_cua_action(page, action, tool_input, scale)

            step_record = {
                "step": step_num,
                "action": action,
                "input": tool_input,
                "error": error,
            }
            steps.append(step_record)

            # Build tool_result for next turn
            # After executing, take a fresh screenshot as the result
            try:
                time.sleep(0.3)  # Brief pause for page to react
                result_b64, _, _, _ = capture_screenshot_b64(page)
                tool_result_content = [
                    {
                        "image": {
                            "format": "png",
                            "source": {"bytes": base64.b64decode(result_b64)},
                        }
                    }
                ]
                if error:
                    tool_result_content.insert(0, {"text": f"Error: {error}"})
            except Exception:
                tool_result_content = [{"text": error or "Action executed"}]

            messages.append({
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": tool_result_content,
                        }
                    }
                ],
            })

    else:
        # Hit max_steps without completing
        outcome = "timeout"

    duration_ms = int((time.time() - start_time) * 1000)
    total_tokens = total_input_tokens + total_output_tokens

    print(f"[cua] Loop finished: outcome={outcome}, steps={len(steps)}, "
          f"tokens={total_tokens}, duration={duration_ms}ms", file=sys.stderr)

    # Send final result to executor via JSON-line protocol.
    # For CUA mode, we send a single summary observation that the executor
    # interprets as the complete run result.
    send_fn({
        "goal": goal,
        "axtree_txt": "",  # CUA mode: no a11y tree
        "screenshot_base64": None,
        "url": page.url,
        "last_action_error": "",
        "terminated": True,
        "truncated": outcome == "timeout",
        "reward": 0.0,  # BrowserGym evaluator will determine this
        "step": len(steps),
        # CUA-specific fields
        "cua_result": {
            "outcome": outcome,
            "answer": final_answer,
            "steps": steps,
            "totalSteps": len(steps),
            "totalTokens": total_tokens,
            "inputTokens": total_input_tokens,
            "outputTokens": total_output_tokens,
            "durationMs": duration_ms,
        },
    })

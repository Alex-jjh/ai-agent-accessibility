#!/usr/bin/env python3
"""
BrowserGym Bridge — JSON-line subprocess protocol for the TypeScript executor.

Protocol:
  1. Executor spawns: python browsergym_bridge.py '<task_config_json>'
  2. Bridge calls env.reset(), sends initial observation as JSON line to stdout.
  3. Executor reads observation, calls LLM, writes action as JSON line to stdin.
  4. Bridge calls env.step(action), sends next observation to stdout.
  5. Loop until terminated/truncated or stdin closes.

Observation JSON schema (stdout):
  {
    "goal": str,
    "axtree_txt": str,
    "screenshot_base64": str | null,
    "url": str,
    "last_action_error": str,
    "terminated": bool,
    "truncated": bool,
    "reward": float,
    "step": int
  }

Action JSON schema (stdin):
  { "action": str }
"""

import base64
import io
import json
import pathlib
import sys
import traceback

import gymnasium as gym
import numpy as np

# Register WebArena tasks
try:
    import browsergym.webarena  # noqa: F401
except ImportError:
    print(
        json.dumps({"error": "browsergym.webarena not installed"}),
        file=sys.stderr,
    )
    sys.exit(1)


def encode_screenshot(screenshot: np.ndarray | None) -> str | None:
    """Encode RGB numpy array to base64 PNG string."""
    if screenshot is None:
        return None
    try:
        from PIL import Image

        img = Image.fromarray(screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def flatten_axtree(axtree_object: dict | None) -> str:
    """Convert BrowserGym's axtree_object to text using BrowserGym's own utility."""
    if not axtree_object:
        return ""
    try:
        # Use BrowserGym's built-in flattener if available
        from browsergym.utils.obs import flatten_axtree_to_str
        return flatten_axtree_to_str(axtree_object)
    except ImportError:
        pass
    try:
        from browsergym.core.obs import flatten_axtree_to_str
        return flatten_axtree_to_str(axtree_object)
    except ImportError:
        pass
    # Fallback: simple extraction from CDP nodes
    try:
        nodes = axtree_object.get("nodes", [])
        lines = []
        for node in nodes:
            role_val = ""
            name_val = ""
            if isinstance(node.get("role"), dict):
                role_val = node["role"].get("value", "")
            if isinstance(node.get("name"), dict):
                name_val = node["name"].get("value", "")
            if role_val and role_val not in ("none", "generic", "InlineTextBox"):
                bid = node.get("browsergym_id", node.get("nodeId", ""))
                line = f'{role_val} "{name_val}"' if name_val else role_val
                if bid:
                    line += f" [bid={bid}]"
                lines.append(line)
        return "\n".join(lines[:200])  # Cap at 200 lines to avoid token explosion
    except Exception:
        return str(axtree_object)[:3000]


def extract_observation(obs: dict, step: int) -> dict:
    """Convert BrowserGym observation dict to our JSON protocol format."""
    # BrowserGym returns axtree_object (dict), not axtree_txt (string)
    axtree_txt = obs.get("axtree_txt", "")
    if not axtree_txt:
        axtree_txt = flatten_axtree(obs.get("axtree_object"))

    # URL: try direct 'url' key first, then open_pages_urls
    current_url = obs.get("url", "")
    if not current_url:
        urls = obs.get("open_pages_urls", None)
        active_idx = obs.get("active_page_index", 0)
        try:
            if urls is not None and len(urls) > 0:
                current_url = str(urls[int(active_idx)])
        except (IndexError, TypeError, ValueError):
            current_url = ""

    return {
        "goal": obs.get("goal", ""),
        "axtree_txt": axtree_txt,
        "screenshot_base64": encode_screenshot(obs.get("screenshot")),
        "url": current_url,
        "last_action_error": obs.get("last_action_error", ""),
        "terminated": False,
        "truncated": False,
        "reward": 0.0,
        "step": step,
    }


def send(obj: dict) -> None:
    """Write a JSON line to stdout and flush."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def recv() -> dict | None:
    """Read a JSON line from stdin. Returns None on EOF."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())


# ---------------------------------------------------------------------------
# Variant injection — shared JS files from src/variants/patches/inject/
# ---------------------------------------------------------------------------

INJECT_DIR = pathlib.Path(__file__).parent / ".." / "variants" / "patches" / "inject"

VARIANT_SCRIPTS = {
    "low": "apply-low.js",
    "medium-low": "apply-medium-low.js",
    "high": "apply-high.js",
}


def apply_variant(page, variant_level: str) -> list:
    """Apply variant DOM patches on the BrowserGym Playwright page.

    Reads the same JS files used by the TypeScript variant engine,
    ensuring the agent sees the same DOM state as the scanner.
    """
    if variant_level == "base":
        return []  # No-op for base variant

    script_file = VARIANT_SCRIPTS.get(variant_level)
    if not script_file:
        print(f"[bridge] Unknown variant level: {variant_level}", file=sys.stderr)
        return []

    js_path = INJECT_DIR / script_file
    if not js_path.exists():
        print(f"[bridge] Variant script not found: {js_path}", file=sys.stderr)
        return []

    js_code = js_path.read_text(encoding="utf-8")
    changes = page.evaluate(js_code)
    return changes or []


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: browsergym_bridge.py '<task_config_json>'", file=sys.stderr)
        sys.exit(1)

    config = json.loads(sys.argv[1])
    task_id = config.get("taskId", "browsergym/webarena.0")

    # Resolve BrowserGym task name
    # If taskId looks like a WebArena numeric ID, prefix it
    if task_id.isdigit():
        gym_task = f"browsergym/webarena.{task_id}"
    elif task_id.startswith("browsergym/"):
        gym_task = task_id
    else:
        # Fallback: use as-is (may be a custom task name)
        gym_task = f"browsergym/webarena.{task_id}"

    # Set Playwright default timeout to 60s (BrowserGym default is 10s which
    # is too short for Magento admin on t3a.xlarge instances)
    import os
    os.environ["PLAYWRIGHT_TIMEOUT"] = "60000"

    # Ensure all WA_* env vars are set (BrowserGym + webarena assert on import)
    # Use targetUrl as fallback base for missing services
    target_url = config.get("targetUrl", "http://localhost:7770")
    # Extract base IP:port pattern from targetUrl
    import re
    base_match = re.match(r'(https?://[^:/]+)', target_url)
    base_host = base_match.group(1) if base_match else "http://localhost"

    wa_defaults = {
        "WA_SHOPPING": f"{base_host}:7770",
        "WA_SHOPPING_ADMIN": f"{base_host}:7780",
        "WA_REDDIT": f"{base_host}:9999",
        "WA_GITLAB": f"{base_host}:8023",
        "WA_WIKIPEDIA": f"{base_host}:8888",
        "WA_MAP": f"{base_host}:3000",
        "WA_HOMEPAGE": f"{base_host}:7770",
    }
    for key, default in wa_defaults.items():
        os.environ.setdefault(key, default)

    # Monkey-patch BrowserGym's ui_login to increase timeout and handle failures gracefully
    # BrowserGym's default Playwright timeout is 10s which is too short for Magento on t3a.xlarge
    try:
        import browsergym.webarena.instance as wa_inst
        _original_ui_login = wa_inst.WebArenaInstance.ui_login

        def _patched_ui_login(self, site, page):
            """Fix BrowserGym's ui_login for WebArena AMI compatibility."""
            # map service doesn't exist in WebArena AMI — skip entirely
            if site == "map":
                print(f"[bridge] Skipping ui_login for map (service not available)", file=sys.stderr)
                return

            page.context.set_default_timeout(30000)

            if site == "shopping_admin":
                # BrowserGym navigates to storefront URL but admin login is at /admin/
                # Manually handle the admin login flow in a new tab, preserving the original page
                try:
                    url = self.urls[site]
                    username = self.credentials[site]["username"]
                    password = self.credentials[site]["password"]
                    # Remember current page count
                    pages_before = len(page.context.pages)
                    login_page = page.context.new_page()
                    login_page.goto(f"{url}/admin/", timeout=30000)
                    login_page.locator("#username").fill(username)
                    login_page.locator("#login").fill(password)
                    login_page.locator(".action-login").click()
                    login_page.wait_for_load_state("load", timeout=30000)
                    login_page.close()
                    # Ensure original page is still the active one
                    if len(page.context.pages) > 0:
                        page.context.pages[0].bring_to_front()
                    print(f"[bridge] ui_login for shopping_admin succeeded via /admin/", file=sys.stderr)
                except Exception as e:
                    print(f"[bridge] ui_login for shopping_admin failed (non-fatal): {e}", file=sys.stderr)
                return

            # All other sites: use original login with increased timeout
            try:
                _original_ui_login(self, site, page)
            except Exception as e:
                print(f"[bridge] ui_login for {site} failed (non-fatal): {e}", file=sys.stderr)

        wa_inst.WebArenaInstance.ui_login = _patched_ui_login
    except Exception:
        pass  # If patching fails, proceed with original behavior

    # Monkey-patch BrowserGym's action functions to increase the hardcoded 500ms
    # timeout to 3000ms. BrowserGym hardcodes timeout=500 in every action call
    # (click, fill, hover, etc.) in browsergym/core/action/functions.py.
    # Our set_default_timeout() calls have no effect because the explicit
    # timeout=500 parameter overrides the default. Magento on t3a.xlarge
    # needs more than 500ms for many DOM interactions.
    try:
        import browsergym.core.action.functions as _action_fns
        import inspect

        _ACTION_TIMEOUT_MS = 3000  # 3s instead of 500ms

        # Patch each function that has timeout=500 in its signature
        for name in dir(_action_fns):
            fn = getattr(_action_fns, name)
            if not callable(fn) or name.startswith('_'):
                continue
            try:
                sig = inspect.signature(fn)
                # Check if function has a 'timeout' parameter defaulting to 500
                for pname, param in sig.parameters.items():
                    if pname == 'timeout' and param.default == 500:
                        # Can't easily change default, so we wrap instead
                        break
            except (ValueError, TypeError):
                continue

        # Direct approach: replace the hardcoded 500 values in the source
        # by monkey-patching the specific action functions we care about
        _orig_click = _action_fns.click
        _orig_fill = _action_fns.fill
        _orig_hover = _action_fns.hover
        _orig_press = _action_fns.press
        _orig_focus = _action_fns.focus
        _orig_clear = _action_fns.clear
        _orig_dblclick = _action_fns.dblclick
        _orig_select_option = _action_fns.select_option
        _orig_check = _action_fns.check
        _orig_uncheck = _action_fns.uncheck
        _orig_drag_and_drop = _action_fns.drag_and_drop

        def _make_timeout_wrapper(orig_fn):
            """Wrap an action function to replace timeout=500 with our value."""
            sig = inspect.signature(orig_fn)
            def wrapper(*args, **kwargs):
                # If caller didn't explicitly set timeout, or set it to 500 (the default),
                # override with our higher value
                if 'timeout' not in kwargs or kwargs['timeout'] == 500:
                    kwargs['timeout'] = _ACTION_TIMEOUT_MS
                return orig_fn(*args, **kwargs)
            wrapper.__name__ = orig_fn.__name__
            wrapper.__doc__ = orig_fn.__doc__
            return wrapper

        for fn_name in ['click', 'fill', 'hover', 'press', 'focus', 'clear',
                        'dblclick', 'select_option', 'check', 'uncheck', 'drag_and_drop']:
            if hasattr(_action_fns, fn_name):
                setattr(_action_fns, fn_name, _make_timeout_wrapper(getattr(_action_fns, fn_name)))

        print(f"[bridge] Patched BrowserGym action timeout: 500ms -> {_ACTION_TIMEOUT_MS}ms", file=sys.stderr)
    except Exception as e:
        print(f"[bridge] WARNING: Failed to patch action timeout: {e}", file=sys.stderr)

    env = None
    try:
        env = gym.make(gym_task)

        # Patch Playwright default timeout before reset (ui_login uses 10s default)
        try:
            if hasattr(env, 'unwrapped') and hasattr(env.unwrapped, 'context'):
                env.unwrapped.context.set_default_timeout(60000)
        except Exception:
            pass

        obs, info = env.reset()

        # Increase page timeout after reset for subsequent actions
        # (supplementary to the action function monkey-patch above)
        try:
            if hasattr(env, 'unwrapped') and hasattr(env.unwrapped, 'page'):
                env.unwrapped.page.set_default_timeout(3000)  # 3s for actions
            if hasattr(env, 'unwrapped') and hasattr(env.unwrapped, 'context'):
                env.unwrapped.context.set_default_timeout(3000)
        except Exception:
            pass

        # Apply variant DOM patches after env.reset() so the agent sees
        # the same accessibility state as the scanner. (Bug 6 fix)
        variant_level = config.get("variantLevel", "base")
        if variant_level != "base":
            try:
                bg_page = env.unwrapped.page
                changes = apply_variant(bg_page, variant_level)
                print(f"[bridge] Applied variant '{variant_level}': {len(changes)} DOM changes", file=sys.stderr)
                # Wait for DOM to settle after patches
                bg_page.wait_for_timeout(500)
                # Re-capture observation so agent sees the patched a11y tree.
                # Try BrowserGym's internal _get_obs first, fall back to noop step.
                try:
                    if hasattr(env.unwrapped, '_get_obs'):
                        fresh_obs = env.unwrapped._get_obs()
                        if fresh_obs:
                            obs = {**obs, **fresh_obs}
                    else:
                        # Fallback: execute noop to trigger fresh observation cycle
                        obs, _, _, _, _ = env.step("noop()")
                except Exception as re_obs_err:
                    print(f"[bridge] Observation re-capture after variant failed (non-fatal): {re_obs_err}", file=sys.stderr)
            except Exception as variant_err:
                print(f"[bridge] WARNING: variant injection failed: {variant_err}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

        # Send initial observation
        obs_msg = extract_observation(obs, step=0)
        obs_msg["goal"] = obs.get("goal", config.get("taskGoal", ""))
        send(obs_msg)

        step = 0
        while True:
            # Read action from executor
            action_msg = recv()
            if action_msg is None:
                break  # stdin closed

            action = action_msg.get("action", "noop()")
            step += 1

            # Clean up action string — fix common LLM output issues
            # Remove escaped quotes that break Python eval
            action = action.replace('\\"', '"').replace("\\'", "'")
            # Remove leading/trailing whitespace
            action = action.strip()

            # Debug: log the action being sent to BrowserGym
            print(f"[bridge] Step {step}: executing action: {action[:200]}", file=sys.stderr)

            # Execute action in BrowserGym
            obs, reward, terminated, truncated, info = env.step(action)

            obs_msg = extract_observation(obs, step=step)
            obs_msg["terminated"] = terminated
            obs_msg["truncated"] = truncated
            obs_msg["reward"] = float(reward)
            send(obs_msg)

            if terminated or truncated:
                break

    except Exception as exc:
        # Send error as a terminated observation so executor can handle it
        send(
            {
                "goal": "",
                "axtree_txt": "",
                "screenshot_base64": None,
                "url": "",
                "last_action_error": f"Bridge error: {exc}",
                "terminated": True,
                "truncated": False,
                "reward": 0.0,
                "step": -1,
            }
        )
        traceback.print_exc(file=sys.stderr)
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()

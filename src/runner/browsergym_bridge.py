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


def extract_observation(obs: dict, step: int) -> dict:
    """Convert BrowserGym observation dict to our JSON protocol format."""
    # Handle open_pages_urls which may be a numpy array
    urls = obs.get("open_pages_urls", None)
    active_idx = obs.get("active_page_index", 0)
    try:
        if urls is not None and len(urls) > 0:
            current_url = str(urls[int(active_idx)])
        else:
            current_url = ""
    except (IndexError, TypeError, ValueError):
        current_url = ""

    return {
        "goal": obs.get("goal", ""),
        "axtree_txt": obs.get("axtree_txt", ""),
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
                # Manually handle the admin login flow
                try:
                    url = self.urls[site]
                    username = self.credentials[site]["username"]
                    password = self.credentials[site]["password"]
                    login_page = page.context.new_page()
                    login_page.goto(f"{url}/admin/", timeout=30000)
                    login_page.locator("#username").fill(username)
                    login_page.locator("#login").fill(password)
                    login_page.locator(".action-login").click()
                    login_page.wait_for_load_state("load", timeout=30000)
                    login_page.close()
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
        try:
            if hasattr(env, 'unwrapped') and hasattr(env.unwrapped, 'page'):
                env.unwrapped.page.set_default_timeout(60000)
        except Exception:
            pass

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

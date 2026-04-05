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
        from browsergym.utils.obs import flatten_axtree_to_str
        result = flatten_axtree_to_str(axtree_object)
        return result
    except Exception as e:
        print(f"[bridge] flatten_axtree browsergym.utils.obs failed: {e}", file=sys.stderr)
    try:
        from browsergym.core.obs import flatten_axtree_to_str
        return flatten_axtree_to_str(axtree_object)
    except Exception as e:
        print(f"[bridge] flatten_axtree browsergym.core.obs failed: {e}", file=sys.stderr)
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
        "WA_SHOPPING_ADMIN": f"{base_host}:7780/admin",
        "WA_REDDIT": f"{base_host}:9999",
        "WA_GITLAB": f"{base_host}:8023",
        "WA_WIKIPEDIA": f"{base_host}:8888",
        "WA_MAP": f"{base_host}:3000",
        "WA_HOMEPAGE": f"{base_host}:7770",
    }
    for key, default in wa_defaults.items():
        os.environ.setdefault(key, default)

    # BrowserGym evaluators for some tasks use OpenAI API for LLM-based evaluation.
    # Point them at the LiteLLM proxy so they work without a real OpenAI key.
    os.environ.setdefault("OPENAI_API_KEY", "sk-litellm")
    os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:4000")

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
                    login_page = page.context.new_page()
                    login_page.goto(f"{url}/admin/", timeout=30000)
                    login_page.locator("#username").fill(username)
                    login_page.locator("#login").fill(password)
                    login_page.locator(".action-login").click()
                    login_page.wait_for_load_state("load", timeout=30000)
                    login_page.close()
                    if len(page.context.pages) > 0:
                        page.context.pages[0].bring_to_front()
                    print(f"[bridge] ui_login for shopping_admin succeeded via /admin/", file=sys.stderr)
                except Exception as e:
                    print(f"[bridge] ui_login for shopping_admin failed (non-fatal): {e}", file=sys.stderr)
                return

            if site == "shopping":
                # SKIP shopping login during ui_login phase.
                # BrowserGym's page is at about:blank with navigation restrictions
                # here — both page.goto() and new_page().goto() return
                # about:blank#blocked. We handle shopping login AFTER env.reset()
                # when the page is fully navigable. See "Post-reset shopping login"
                # section below.
                print(f"[bridge] ui_login for shopping: DEFERRED to post-reset phase", file=sys.stderr)
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
        # Determine observation mode from config
        obs_mode = config.get("observationMode", "text-only")

        # For vision-only mode, enable Set-of-Marks (SoM) screenshot overlay.
        # SoM annotates interactive elements with numeric labels on the screenshot,
        # allowing the agent to reference elements by their label number.
        # The bid numbers in SoM match the a11y tree bids, so the same action
        # format (click("42")) works for both text-only and vision-only modes.
        use_som = obs_mode == "vision-only"
        use_axtree = obs_mode != "vision-only"  # text-only and vision both get axtree
        use_screenshot = obs_mode in ("vision", "vision-only")

        # BrowserGym observation space configuration.
        # These kwargs control what's included in the observation dict.
        # Wrap in try/except because parameter names may vary across BrowserGym versions.
        obs_kwargs = {}
        if use_screenshot or use_som:
            obs_kwargs["use_screenshot"] = use_screenshot
        if use_som:
            obs_kwargs["use_set_of_marks"] = True
        if not use_axtree:
            obs_kwargs["use_axtree"] = False

        try:
            env = gym.make(gym_task, **obs_kwargs)
        except TypeError as e:
            # If BrowserGym doesn't accept these kwargs, fall back to default
            print(f"[bridge] WARNING: gym.make kwargs failed ({e}), falling back to defaults", file=sys.stderr)
            env = gym.make(gym_task)

        print(f"[bridge] Observation mode: {obs_mode} (axtree={use_axtree}, screenshot={use_screenshot}, som={use_som})", file=sys.stderr)

        # Patch Playwright default timeout before reset (ui_login uses 10s default)
        try:
            if hasattr(env, 'unwrapped') and hasattr(env.unwrapped, 'context'):
                env.unwrapped.context.set_default_timeout(60000)
        except Exception:
            pass

        obs, info = env.reset()

        # Debug: check what page we landed on after reset
        try:
            bg_page = env.unwrapped.page
            print(f"[bridge] After reset: URL={bg_page.url}, title={bg_page.title()}", file=sys.stderr)
            # Magento pages rely on JS rendering — the a11y tree may be empty
            # right after page.goto() returns on 'load'. Wait for DOM to settle.
            try:
                bg_page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                bg_page.wait_for_timeout(5000)  # fallback: just wait 5s
            # Reload to ensure DOM is fully settled after BrowserGym's setup
            # (login + start_url navigation). This helps with Magento's JS-heavy
            # rendering and ensures the a11y tree is populated.
            bg_page.reload(timeout=60000)
            try:
                bg_page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                bg_page.wait_for_timeout(5000)
            print(f"[bridge] After reload: title={bg_page.title()}", file=sys.stderr)
        except Exception as e:
            print(f"[bridge] After reset: could not get page info: {e}", file=sys.stderr)

        # ---------------------------------------------------------------
        # Post-reset shopping login via separate tab
        # ---------------------------------------------------------------
        # BrowserGym hooks the main page's navigation — any non-agent-action
        # navigation gets blocked (about:blank#blocked). But new_page() tabs
        # are NOT guarded after env.reset(). So we:
        #   1. Open a new tab, login there (gets authenticated PHPSESSID)
        #   2. Close the tab — cookies are shared at context level
        #   3. Use env.step('goto("start_url")') to reload the main page
        #      via an agent action (which BrowserGym allows)
        # This way the main page picks up the authenticated session cookie.
        try:
            bg_page = env.unwrapped.page
            current_url = bg_page.url
            shopping_url = os.environ.get("WA_SHOPPING", "")
            needs_shopping_login = (
                shopping_url
                and shopping_url.rstrip("/") in current_url
                and "/admin" not in current_url
            )

            if needs_shopping_login:
                # Check if already logged in
                is_signed_in = bg_page.evaluate(
                    '!document.body.innerText.includes("Sign In") || '
                    'document.body.innerText.includes("Sign Out")'
                )
                if is_signed_in:
                    print(f"[bridge] Shopping: already logged in", file=sys.stderr)
                else:
                    print(f"[bridge] Shopping: logging in via HTTP request...", file=sys.stderr)
                    start_url_saved = current_url

                    try:
                        from webarena.browser_env.env_config import ACCOUNTS
                        shop_user = ACCOUNTS["shopping"]["username"]
                        shop_pass = ACCOUNTS["shopping"]["password"]
                    except Exception:
                        shop_user = "emma.lopez@gmail.com"
                        shop_pass = "Password.123"

                    # Login via raw HTTP requests — bypasses ALL browser navigation
                    # guards. BrowserGym hooks Playwright navigation, but can't
                    # intercept Python's requests library.
                    import requests as _requests
                    import urllib.parse as _urlparse

                    session = _requests.Session()

                    # Step 1: GET the login page to get form_key cookie
                    login_url = f"{shopping_url}/customer/account/login/"
                    resp1 = session.get(login_url, timeout=30)
                    print(f"[bridge] HTTP login: GET login page status={resp1.status_code}", file=sys.stderr)

                    # Extract form_key from the HTML
                    import re as _re
                    form_key_match = _re.search(r'name="form_key"\s+.*?value="([^"]+)"', resp1.text)
                    if not form_key_match:
                        form_key_match = _re.search(r'"form_key"\s*:\s*"([^"]+)"', resp1.text)
                    form_key = form_key_match.group(1) if form_key_match else ""
                    print(f"[bridge] HTTP login: form_key={form_key[:16]}...", file=sys.stderr)

                    # Step 2: POST login credentials
                    # Extract the actual form action URL from the HTML
                    action_match = _re.search(
                        r'<form[^>]*id=["\']login-form["\'][^>]*action=["\']([^"\']+)["\']',
                        resp1.text
                    )
                    if not action_match:
                        action_match = _re.search(
                            r'<form[^>]*action=["\']([^"\']*loginPost[^"\']*)["\']',
                            resp1.text
                        )
                    if action_match:
                        login_post_url = action_match.group(1)
                        # Magento's form action may have incomplete host (Docker internal URL)
                        # e.g. "http://:7770/customer/account/loginPost/"
                        # Fix by replacing with the actual shopping URL base
                        parsed_action = _urlparse.urlparse(login_post_url)
                        if not parsed_action.hostname:
                            # Missing host — use path from action, base from shopping_url
                            login_post_url = shopping_url.rstrip("/") + parsed_action.path
                    else:
                        login_post_url = f"{shopping_url}/customer/account/loginPost/"
                    print(f"[bridge] HTTP login: POST url={login_post_url}", file=sys.stderr)
                    login_data = {
                        "form_key": form_key,
                        "login[username]": shop_user,
                        "login[password]": shop_pass,
                    }
                    # Don't follow redirects — Magento's redirect URL has broken
                    # host (Docker internal). We only need the POST to succeed and
                    # the Set-Cookie header with the new PHPSESSID.
                    resp2 = session.post(login_post_url, data=login_data, timeout=30, allow_redirects=False)
                    print(f"[bridge] HTTP login: POST status={resp2.status_code}", file=sys.stderr)

                    # 302 = success (redirect to account page), 200 = login page re-rendered (wrong creds)
                    login_ok = resp2.status_code in (301, 302, 303)
                    redirect_to = resp2.headers.get("Location", "")
                    print(f"[bridge] HTTP login: redirect={redirect_to}, success={login_ok}", file=sys.stderr)

                    if login_ok:
                        # Extract the authenticated PHPSESSID from the session
                        auth_phpsessid = session.cookies.get("PHPSESSID", "")
                        print(f"[bridge] HTTP login: auth PHPSESSID={auth_phpsessid[:8]}...", file=sys.stderr)

                        # Inject the authenticated cookie into the browser context
                        ctx = env.unwrapped.context
                        shopping_host = _urlparse.urlparse(shopping_url).hostname

                        # Clear old cookies for this domain
                        ctx.clear_cookies(domain=shopping_host)

                        # Build cookie list from the HTTP session
                        browser_cookies = []
                        for cookie in session.cookies:
                            browser_cookies.append({
                                "name": cookie.name,
                                "value": cookie.value,
                                "domain": shopping_host,
                                "path": cookie.path or "/",
                            })
                        ctx.add_cookies(browser_cookies)
                        print(f"[bridge] HTTP login: injected {len(browser_cookies)} cookies into browser", file=sys.stderr)

                        # Reload main page via agent action to pick up new cookies
                        obs_reload, _, _, _, _ = env.step(f'goto("{start_url_saved}")')
                        obs = obs_reload
                        print(f"[bridge] Shopping: reloaded main page via agent goto", file=sys.stderr)

                        # Verify
                        main_page = env.unwrapped.page
                        logged_in = main_page.evaluate(
                            'document.body.innerText.includes("Sign Out") || '
                            'document.body.innerText.includes("Welcome, ")'
                        )
                        print(f"[bridge] Shopping login {'SUCCEEDED' if logged_in else 'FAILED'} on main page", file=sys.stderr)
                    else:
                        print(f"[bridge] HTTP login failed, skipping cookie injection", file=sys.stderr)
        except Exception as e:
            print(f"[bridge] Post-reset shopping login failed (non-fatal): {e}", file=sys.stderr)

        # Re-capture observation after waiting for DOM to settle.
        # Use env.step("noop()") to force a full observation cycle through
        # BrowserGym's normal pipeline (ensures a11y tree is populated).
        try:
            obs_noop, _, _, _, _ = env.step("noop()")
            obs = obs_noop
            # Debug: check what we got
            axt = obs.get("axtree_txt", "")
            axo = obs.get("axtree_object")
            print(f"[bridge] noop obs: axtree_txt len={len(axt)}, axtree_object truthy={bool(axo)}", file=sys.stderr)
            # If axtree_txt is empty but axtree_object exists, flatten it now
            if not axt and axo:
                try:
                    from browsergym.utils.obs import flatten_axtree_to_str
                    obs["axtree_txt"] = flatten_axtree_to_str(axo)
                    print(f"[bridge] Flattened axtree_object: {len(obs['axtree_txt'])} chars", file=sys.stderr)
                except Exception as fe:
                    print(f"[bridge] flatten failed: {fe}", file=sys.stderr)
        except Exception as e:
            print(f"[bridge] noop re-capture failed: {e}", file=sys.stderr)

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
        _variant_js = None  # Will be set if variant needs re-injection on navigation
        _variant_listener_pages = set()  # Track pages with registered listeners (dedup)

        def _make_variant_listener(page_ref, js):
            """Create a listener function for variant re-injection on page load."""
            def _listener():
                try:
                    page_ref.evaluate(js)
                    print(f"[bridge] Re-injected variant after navigation", file=sys.stderr)
                except Exception as e:
                    print(f"[bridge] Variant re-injection failed (non-fatal): {e}", file=sys.stderr)
            return _listener

        if variant_level != "base":
            try:
                bg_page = env.unwrapped.page
                changes = apply_variant(bg_page, variant_level)
                print(f"[bridge] Applied variant '{variant_level}': {len(changes)} DOM changes", file=sys.stderr)

                # Cache the variant JS for re-injection after navigation
                script_file = VARIANT_SCRIPTS.get(variant_level)
                if script_file:
                    js_path = INJECT_DIR / script_file
                    if js_path.exists():
                        _variant_js = js_path.read_text(encoding="utf-8")

                # Register a page load listener to re-inject variant patches
                # after every navigation. DOM patches are lost when the page
                # navigates because the DOM is rebuilt from scratch.
                # Listen on both domcontentloaded (early, before images) and load
                # (fallback) to minimize the window where agent sees unpatched DOM.
                if _variant_js:
                    _listener = _make_variant_listener(bg_page, _variant_js)
                    bg_page.on("domcontentloaded", _listener)
                    bg_page.on("load", _listener)
                    _variant_listener_pages.add(id(bg_page))
                    print(f"[bridge] Registered variant re-injection listener (domcontentloaded+load)", file=sys.stderr)

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

        # If initial observation is too short, retry before sending to agent
        if len(obs_msg.get("axtree_txt", "")) < 50:
            print(f"[bridge] Initial obs too short ({len(obs_msg.get('axtree_txt', ''))} chars), retrying...", file=sys.stderr)
            try:
                bg_page = env.unwrapped.page
                bg_page.wait_for_timeout(3000)
                obs_retry, _, _, _, _ = env.step("noop()")
                obs_msg_retry = extract_observation(obs_retry, step=0)
                if len(obs_msg_retry.get("axtree_txt", "")) > len(obs_msg.get("axtree_txt", "")):
                    obs_msg_retry["goal"] = obs_msg["goal"]
                    obs_msg = obs_msg_retry
                    print(f"[bridge] Initial obs recovered ({len(obs_msg['axtree_txt'])} chars)", file=sys.stderr)
            except Exception:
                pass
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

            # Wait for DOM to settle after action — Magento's JS-heavy pages
            # may not have the a11y tree ready immediately after env.step().
            # Without this, the agent sees "RootWebArea '', focused" (empty).
            if not terminated and not truncated:
                try:
                    current_page = env.unwrapped.page
                    current_page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass

                # If axtree_txt is empty but axtree_object exists, flatten it
                # (same fallback as initial observation capture)
                axt = obs.get("axtree_txt", "")
                if not axt and obs.get("axtree_object"):
                    obs["axtree_txt"] = flatten_axtree(obs.get("axtree_object"))

                # If axtree is too short (< 50 chars = just "RootWebArea '', focused"),
                # the DOM hasn't rendered yet. Progressive wait: try short first,
                # then longer. Most steps don't need this — only page navigations.
                axt = obs.get("axtree_txt", "")
                if len(axt) < 50:
                    for wait_ms in [1000, 2000, 3000]:
                        try:
                            current_page = env.unwrapped.page
                            try:
                                current_page.wait_for_load_state("networkidle", timeout=wait_ms)
                            except Exception:
                                current_page.wait_for_timeout(wait_ms)
                            obs_retry, _, _, _, _ = env.step("noop()")
                            axt_retry = obs_retry.get("axtree_txt", "")
                            if not axt_retry and obs_retry.get("axtree_object"):
                                axt_retry = flatten_axtree(obs_retry.get("axtree_object"))
                            if len(axt_retry) >= 50:
                                obs["axtree_txt"] = axt_retry
                                obs["axtree_object"] = obs_retry.get("axtree_object")
                                # Preserve URL from retry if it changed
                                if obs_retry.get("url"):
                                    obs["url"] = obs_retry["url"]
                                print(f"[bridge] Step {step}: recovered short obs ({len(axt)} → {len(axt_retry)} chars, wait={wait_ms}ms)", file=sys.stderr)
                                break
                        except Exception:
                            pass
                    else:
                        print(f"[bridge] Step {step}: obs still short after 3 retries ({len(obs.get('axtree_txt', ''))} chars)", file=sys.stderr)

            # Re-inject variant patches if the page changed (new tab or navigation
            # that didn't trigger the load listener). The load listener handles
            # same-page navigations, but if BrowserGym switched the active page
            # (e.g., agent opened a new tab), we need to re-register the listener
            # and re-inject on the new page.
            if _variant_js:
                try:
                    current_page = env.unwrapped.page
                    # Check if variant markers are present — if not, re-inject
                    has_variant = current_page.evaluate(
                        'document.querySelector("[data-variant-revert]") !== null'
                    )
                    if not has_variant:
                        current_page.evaluate(_variant_js)
                        # Register listener on new page if not already registered
                        # (prevents duplicate listeners on the same page)
                        if id(current_page) not in _variant_listener_pages:
                            _listener = _make_variant_listener(current_page, _variant_js)
                            current_page.on("domcontentloaded", _listener)
                            current_page.on("load", _listener)
                            _variant_listener_pages.add(id(current_page))
                        print(f"[bridge] Step {step}: re-injected variant on new/navigated page", file=sys.stderr)
                except Exception:
                    pass  # Non-fatal — variant re-injection is best-effort

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

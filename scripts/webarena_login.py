#!/usr/bin/env python3
"""
webarena_login.py — authenticate to a WebArena app and emit cookies as JSON.

Shared by any script that needs an authenticated WebArena context.
Originally the login flow lived inside scripts/replay-url-screenshots.py;
this module factors it out so TS tools (scripts/audit-operator.ts,
forthcoming A.5 batch wrapper) can call it via subprocess and inject
the returned cookies into their own Playwright context.

Strategy per app (production-validated, matches src/runner/browsergym_bridge.py):
  shopping       - HTTP POST with form_key extraction. Browser selectors
                   for Magento storefront are theme-dependent; HTTP flow
                   is the same as what the bridge uses post env.reset().
  shopping_admin - Canonical Magento admin selectors via Playwright.
  reddit         - Postmill selector fallback chain (docs vary across
                   Postmill versions shipped in WebArena).
  gitlab         - Rails standard selectors.

CLI usage (stdout = JSON, stderr = diagnostics):
  python3.11 scripts/webarena_login.py --app shopping --base-url http://10.0.1.50:7770
  python3.11 scripts/webarena_login.py --app gitlab --base-url http://10.0.1.50:8023

Output shape (on stdout):
  {
    "app": "shopping",
    "base_url": "http://10.0.1.50:7770",
    "cookies": [ {"name": "PHPSESSID", "value": "...", "domain": "10.0.1.50", "path": "/"}, ... ],
    "ok": true
  }

Exit code: 0 on success (cookies present and login appears to have succeeded),
          1 on login failure. The JSON still gets printed either way so the
          caller can decide how to handle partial cookie sets.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

# ─────────────────────────────────────────────────────────────────────
# Credentials (mirrors src/runner/browsergym_bridge.py)
# ─────────────────────────────────────────────────────────────────────

WEBARENA_ACCOUNTS: dict[str, tuple[str, str]] = {
    "shopping":       ("emma.lopez@gmail.com", "Password.123"),
    "shopping_admin": ("admin", "admin1234"),
    "reddit":         ("MarvelsGrantMan136", "test1234"),
    "gitlab":         ("byteblaze", "hello1234"),
}

# Port → app mapping. Caller can use this to resolve app from base_url
# if they prefer a URL-driven interface.
PORT_APP: dict[int, str] = {
    7770: "shopping",
    7780: "shopping_admin",
    9999: "reddit",
    8023: "gitlab",
}


# ─────────────────────────────────────────────────────────────────────
# Shopping (Magento storefront) — HTTP flow
# ─────────────────────────────────────────────────────────────────────

def _shopping_login_http(base_url: str, username: str, password: str,
                         timeout_s: int = 30) -> list[dict[str, Any]]:
    """HTTP login for Magento storefront — matches production bridge.

    Magento's form_key is CSRF-protected; browser login selectors are
    theme-dependent and untested on current WebArena. This matches
    src/runner/browsergym_bridge.py post-reset shopping login logic.

    Assumes Magento's web/unsecure/base_url is set to the private IP
    (infra/webarena.tf user-data handles this; if redirects go to a stale
    public hostname, re-run scripts/ssm-fix-magento-baseurl.json).
    """
    import requests as _requests
    import urllib.parse as _urlparse

    session = _requests.Session()
    cookies_out: list[dict[str, Any]] = []
    try:
        # Step 1: GET login page for form_key
        login_url = f"{base_url}/customer/account/login/"
        resp1 = session.get(login_url, timeout=timeout_s)
        print(f"    [login:shopping] GET login: status={resp1.status_code} "
              f"final_url={resp1.url[:80]}", file=sys.stderr)
        form_key_match = re.search(
            r'name="form_key"\s+.*?value="([^"]+)"', resp1.text
        ) or re.search(r'"form_key"\s*:\s*"([^"]+)"', resp1.text)
        form_key = form_key_match.group(1) if form_key_match else ""
        print(f"    [login:shopping] form_key={'found' if form_key else 'MISSING'} "
              f"(len={len(form_key)})", file=sys.stderr)

        # Step 2: POST credentials — form action may have broken Docker-internal host
        action_match = re.search(
            r'<form[^>]*id=["\']login-form["\'][^>]*action=["\']([^"\']+)["\']',
            resp1.text
        ) or re.search(
            r'<form[^>]*action=["\']([^"\']*loginPost[^"\']*)["\']', resp1.text
        )
        if action_match:
            login_post_url = action_match.group(1)
            parsed_action = _urlparse.urlparse(login_post_url)
            if not parsed_action.hostname:
                login_post_url = base_url.rstrip("/") + parsed_action.path
        else:
            login_post_url = f"{base_url}/customer/account/loginPost/"

        resp2 = session.post(
            login_post_url,
            data={
                "form_key": form_key,
                "login[username]": username,
                "login[password]": password,
            },
            timeout=timeout_s, allow_redirects=False,
        )
        login_ok = resp2.status_code in (301, 302, 303)
        print(f"    [login:shopping] POST status={resp2.status_code} "
              f"login_ok={login_ok}", file=sys.stderr)

        host = _urlparse.urlparse(base_url).hostname
        for c in session.cookies:
            cookies_out.append({
                "name": c.name,
                "value": c.value,
                "domain": host,
                "path": c.path or "/",
            })
    except Exception as e:
        print(f"    [login:shopping] HTTP flow failed: {e}", file=sys.stderr)
    return cookies_out


# ─────────────────────────────────────────────────────────────────────
# Browser-based login for admin / reddit / gitlab
# ─────────────────────────────────────────────────────────────────────

def _try_login_selectors(page: Any, username: str, password: str, timeout_ms: int,
                         username_selectors: list[str],
                         password_selectors: list[str]) -> bool:
    """Fill login form using a fallback chain of selectors.

    Returns True on successful form submission (doesn't verify login
    outcome — caller should check resulting cookies / URL).
    """
    u_filled = False
    for sel in username_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.fill(username, timeout=5000)
                u_filled = True
                print(f"    [login] username via '{sel}'", file=sys.stderr)
                break
        except Exception:
            continue
    p_filled = False
    for sel in password_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.fill(password, timeout=5000)
                p_filled = True
                print(f"    [login] password via '{sel}'", file=sys.stderr)
                break
        except Exception:
            continue
    if not (u_filled and p_filled):
        return False
    for sel in ['button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Sign In")', 'button:has-text("Log in")',
                'button:has-text("Login")']:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.click(timeout=5000)
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
                return True
        except Exception:
            continue
    return False


def login_and_capture_cookies(app: str, base_url: str,
                              timeout_ms: int = 30000) -> list[dict[str, Any]]:
    """Run a real login flow in a throwaway Playwright context, return cookies.

    Strategy per app (see module docstring).

    Playwright is imported lazily so callers that only need the shopping
    HTTP flow don't pay the import cost.
    """
    if app not in WEBARENA_ACCOUNTS:
        return []
    username, password = WEBARENA_ACCOUNTS[app]

    # Shopping uses HTTP flow — browser selectors for Magento storefront
    # are theme-dependent and untested. Production bridge uses HTTP too.
    if app == "shopping":
        cookies = _shopping_login_http(base_url, username, password)
        print(f"    [login] {app}: HTTP flow produced {len(cookies)} cookies",
              file=sys.stderr)
        return cookies

    from playwright.sync_api import sync_playwright
    cookies: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        try:
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            if app == "shopping_admin":
                page.goto(f"{base_url}/admin/", wait_until="networkidle")
                page.locator("#username").fill(username)
                page.locator("#login").fill(password)
                page.locator(".action-login").click()
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            elif app == "reddit":
                page.goto(f"{base_url}/login", wait_until="networkidle")
                _try_login_selectors(
                    page, username, password, timeout_ms,
                    username_selectors=[
                        "input#user_name", "input#login_username",
                        'input[name="_username"]', 'input[name="username"]',
                        'input[type="text"]',
                    ],
                    password_selectors=[
                        "input#user_password", "input#login_password",
                        'input[name="_password"]', 'input[name="password"]',
                        'input[type="password"]',
                    ])
            elif app == "gitlab":
                page.goto(f"{base_url}/users/sign_in", wait_until="networkidle")
                _try_login_selectors(
                    page, username, password, timeout_ms,
                    username_selectors=[
                        "input#user_login", 'input[name="user[login]"]',
                        'input#username', 'input[name="username"]',
                    ],
                    password_selectors=[
                        "input#user_password", 'input[name="user[password]"]',
                        'input[type="password"]',
                    ])
            cookies = context.cookies()
            print(f"    [login] {app}: captured {len(cookies)} cookies",
                  file=sys.stderr)
        except Exception as e:
            print(f"    [login] {app} FAILED: {e}", file=sys.stderr)
        finally:
            context.close()
            browser.close()
    return cookies


# ─────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Authenticate to a WebArena app and emit cookies as JSON on stdout."
    )
    ap.add_argument("--app", required=True, choices=sorted(WEBARENA_ACCOUNTS.keys()),
                    help="WebArena app to log into.")
    ap.add_argument("--base-url", required=True,
                    help="Base URL of the app, e.g. http://10.0.1.50:7770")
    ap.add_argument("--timeout-s", type=int, default=30,
                    help="Per-request timeout in seconds (default 30).")
    args = ap.parse_args()

    cookies = login_and_capture_cookies(args.app, args.base_url, args.timeout_s * 1000)
    ok = len(cookies) > 0
    print(json.dumps({
        "app": args.app,
        "base_url": args.base_url,
        "cookies": cookies,
        "ok": ok,
    }))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

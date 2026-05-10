#!/usr/bin/env python3
"""
URL Replay — base-vs-low screenshot capture for visual equivalence validation.

For each URL the agents actually visited (from
results/visual-equivalence/agent-urls-dedup.csv), this script:
  1. Launches Playwright chromium at 1280x720 (matches BrowserGym default)
  2. Injects WebArena login cookies directly into the browser context
  3. Navigates to the URL, waits for networkidle + settle
  4. For variant=base: screenshot immediately
  5. For variant=low: inject apply-low.js, wait for layout reflow, screenshot
  6. Records per-capture metadata (viewport, final URL, title, timing)

Pipeline fidelity:
  - Same chromium + same viewport as BrowserGym
  - Same apply-low.js (byte-identical file)
  - Same WebArena login credentials from webarena.browser_env.env_config.ACCOUNTS
  - Cookies set via browser context before navigation (avoids login flow
    complexity; what matters for rendering is "authenticated session cookie
    present when the page loads", which is the post-login state the agent saw)

Usage (on EC2 with WebArena at 10.0.1.50):
  python3 scripts/replay-url-screenshots.py \\
    --urls-csv results/visual-equivalence/agent-urls-dedup.csv \\
    --webarena-ip 10.0.1.50 \\
    --output ./data/visual-equivalence/replay

  # Single URL quick test
  python3 scripts/replay-url-screenshots.py --url http://10.0.1.50:7770/

Output:
  ./data/visual-equivalence/replay/<slug>/base.png
  ./data/visual-equivalence/replay/<slug>/low.png
  ./data/visual-equivalence/replay/manifest.json

Requires: playwright (pip install playwright && playwright install chromium)
"""

import argparse
import csv
import hashlib
import json
import pathlib
import re
import sys
import time
import traceback
import urllib.parse
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()
APPLY_LOW_JS = REPO_ROOT / "src" / "variants" / "patches" / "inject" / "apply-low.js"

# WebArena credentials — matches src/runner/browsergym_bridge.py defaults
WEBARENA_ACCOUNTS = {
    # app_name → (username, password, login_path_for_cookie_set)
    "shopping":       ("emma.lopez@gmail.com", "Password.123",
                       "/customer/account/loginPost/"),
    "shopping_admin": ("admin", "admin1234",
                       "/admin/admin/auth/login/"),
    "reddit":         ("MarvelsGrantMan136", "test1234", "/login"),
    "gitlab":         ("byteblaze", "hello1234", "/users/sign_in"),
}

# Port → app mapping
PORT_APP = {
    7770: "shopping",
    7780: "shopping_admin",
    9999: "reddit",
    8023: "gitlab",
}


def url_to_slug(url: str) -> str:
    """Safe filesystem slug for a URL. Uses short hash + path hint."""
    parsed = urllib.parse.urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    app = PORT_APP.get(port, f"port{port}")
    # Short path snippet (alphanumeric + hyphens only, max 40 chars)
    path = parsed.path or "/"
    path_slug = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-")[:40] or "root"
    # 8-char hash for uniqueness when paths collide
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{app}__{path_slug}__{h}"


def rewrite_ip(url: str, target_ip: str) -> str:
    """Rewrite any IP in the URL host to target_ip.

    Traces contain URLs with 10.0.1.49 (old burner) and 10.0.1.50 (recent).
    Rewrite both to the current WebArena IP so replay works on today's deploy.
    """
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname:
        return url
    # Match IPv4 pattern only — don't touch DNS hostnames
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", parsed.hostname):
        new_netloc = parsed.hostname.replace(parsed.hostname, target_ip)
        if parsed.port:
            new_netloc = f"{target_ip}:{parsed.port}"
        return urllib.parse.urlunparse(parsed._replace(netloc=new_netloc))
    return url


def _shopping_login_http(base_url: str, username: str, password: str,
                         timeout_s: int = 30) -> list[dict]:
    """HTTP login for Magento storefront — matches production bridge.

    Magento's form_key is CSRF-protected; browser login selectors are
    theme-dependent and untested on current WebArena. This matches
    src/runner/browsergym_bridge.py Post-reset shopping login logic verbatim.

    Assumes Magento's web/unsecure/base_url is set to the private IP
    (infra/webarena.tf user-data handles this; if redirects go to a stale
    public hostname, re-run scripts/ssm-fix-magento-baseurl.json).
    """
    import requests as _requests
    import urllib.parse as _urlparse

    session = _requests.Session()
    cookies_out: list[dict] = []
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
            timeout=timeout_s, allow_redirects=False
        )
        login_ok = resp2.status_code in (301, 302, 303)
        print(f"    [login:shopping] POST status={resp2.status_code} login_ok={login_ok}",
              file=sys.stderr)

        # Convert to Playwright cookie format, tagged with our base_url host
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


def _try_login_selectors(page, username: str, password: str, timeout_ms: int,
                         username_selectors: list[str],
                         password_selectors: list[str]) -> bool:
    """Fill login form using fallback chain of selectors. Returns True on submit."""
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
    # Submit — try button[type=submit] then any form button
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


def login_and_capture_cookies(pw_browser, app: str, base_url: str,
                              timeout_ms: int = 30000) -> list[dict]:
    """Run a real login flow in a throwaway context, return the resulting cookies.

    We do this once per app before the main capture loop so we have
    authenticated cookies to inject into capture contexts.

    Strategy per app:
      shopping       -> HTTP POST with form_key extraction (matches production bridge)
      shopping_admin -> canonical Magento admin selectors (battle-tested in production)
      reddit         -> selector fallback chain (Postmill selectors undocumented)
      gitlab         -> Rails standard selectors
    """
    if app not in WEBARENA_ACCOUNTS:
        return []
    username, password, _ = WEBARENA_ACCOUNTS[app]

    # Shopping uses HTTP flow — browser selectors for Magento storefront are
    # theme-dependent and untested. Production bridge uses HTTP too.
    if app == "shopping":
        cookies = _shopping_login_http(base_url, username, password)
        print(f"    [login] {app}: HTTP flow produced {len(cookies)} cookies",
              file=sys.stderr)
        return cookies

    context = pw_browser.new_context(viewport={"width": 1280, "height": 720})
    cookies: list[dict] = []
    try:
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        if app == "shopping_admin":
            # Canonical Magento admin — selectors verified in production bridge
            page.goto(f"{base_url}/admin/", wait_until="networkidle")
            page.locator("#username").fill(username)
            page.locator("#login").fill(password)
            page.locator(".action-login").click()
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        elif app == "reddit":
            # Postmill — try multiple selector candidates since docs vary
            page.goto(f"{base_url}/login", wait_until="networkidle")
            ok = _try_login_selectors(
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
            if not ok:
                print(f"    [login:reddit] selector chain exhausted — dumping form structure",
                      file=sys.stderr)
                try:
                    inputs = page.evaluate(
                        "Array.from(document.querySelectorAll('input'))"
                        ".map(i => ({id:i.id, name:i.name, type:i.type}))"
                    )
                    print(f"    [login:reddit] inputs={inputs}", file=sys.stderr)
                except Exception:
                    pass
        elif app == "gitlab":
            page.goto(f"{base_url}/users/sign_in", wait_until="networkidle")
            ok = _try_login_selectors(
                page, username, password, timeout_ms,
                username_selectors=[
                    "input#user_login", 'input[name="user[login]"]',
                    'input#username', 'input[name="username"]',
                ],
                password_selectors=[
                    "input#user_password", 'input[name="user[password]"]',
                    'input[type="password"]',
                ])
            if not ok:
                print(f"    [login:gitlab] selector chain exhausted",
                      file=sys.stderr)

        cookies = context.cookies()
        print(f"    [login] {app}: captured {len(cookies)} cookies", file=sys.stderr)
    except Exception as e:
        print(f"    [login] {app} FAILED (continuing without auth): {e}", file=sys.stderr)
    finally:
        context.close()
    return cookies


def capture_one(pw_browser, url: str, variant: str, out_path: pathlib.Path,
                cookies: list[dict], settle_ms: int = 1500,
                post_patch_ms: int = 800,
                timeout_ms: int = 45000,
                apply_js: Optional[str] = None,
                only_patch_id: Optional[int] = None,
                operator_ids: Optional[list[str]] = None,
                max_retries: int = 3) -> dict:
    """Render a URL at a variant, screenshot, return metadata.

    On transient failure (network flake, Magento DB lock, 502, timeout),
    retries up to max_retries times with exponential backoff. Records
    attempts count so the analysis can exclude cases that needed retries
    (an indicator of unstable capture).

    Variant semantics:
      - "base" / "base2" : no patch; base2 is an independent re-capture of
        the same URL (second Playwright context, same cookies) used for
        baseline-noise estimation.
      - "low"            : composite low (legacy Phase 7). Requires apply_js
        to be the bytes of apply-low.js; optional only_patch_id gates via
        window.__ONLY_PATCH_ID for per-patch ablation.
      - any other string : interpreted as an AMT operator ID (or comma-
        separated list). Requires apply_js to be the bytes of
        apply-all-individual.js; sets window.__OPERATOR_IDS accordingly.
        This is the Stage 3 mode.
    """
    rec = {
        "url": url, "variant": variant, "screenshot": None,
        "success": False, "error": None, "elapsed_s": None,
        "final_url": None, "title": None, "dom_changes": 0,
        "attempts": 0, "session_lost": False,
    }
    t_start = time.time()
    for attempt in range(1, max_retries + 1):
        rec["attempts"] = attempt
        t0 = time.time()
        context = pw_browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        rec["error"] = None  # reset per-attempt
        try:
            if cookies:
                try:
                    context.add_cookies(cookies)
                except Exception:
                    # Some cookies have odd expiry/samesite fields — retry filtered
                    clean = [{k: v for k, v in c.items()
                              if k in ("name", "value", "domain", "path",
                                       "expires", "httpOnly", "secure", "sameSite")}
                             for c in cookies]
                    context.add_cookies(clean)

            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(settle_ms)

            # Apply patch (if any) based on variant mode.
            if apply_js is not None:
                if variant == "low":
                    # Legacy composite mode.
                    if only_patch_id is not None:
                        page.evaluate(f"window.__ONLY_PATCH_ID = {int(only_patch_id)}")
                    changes = page.evaluate(apply_js)
                    rec["dom_changes"] = len(changes) if isinstance(changes, list) else 0
                    page.wait_for_timeout(post_patch_ms)
                elif operator_ids is not None and variant not in ("base", "base2"):
                    # Stage 3 individual-operator mode. Prime the runtime-
                    # protocol global, then evaluate the IIFE.
                    op_list_js = json.dumps(operator_ids)
                    page.evaluate(f"window.__OPERATOR_IDS = {op_list_js};")
                    changes = page.evaluate(apply_js)
                    rec["dom_changes"] = len(changes) if isinstance(changes, list) else 0
                    page.wait_for_timeout(post_patch_ms)
            # variant in {"base", "base2"} with no apply_js → plain capture.

            final_url = page.url
            rec["final_url"] = final_url
            try:
                rec["title"] = page.title()[:200]
            except Exception:
                pass

            # P0-3 session-lost detection — if the final URL landed on a login
            # page, the authenticated cookies expired mid-run. This capture
            # does not represent the variant rendering the agent would have
            # seen, so we mark it and exclude from analysis.
            lost_markers = ("/login", "/sign_in", "/customer/account/login",
                            "/admin/auth/login")
            if any(m in final_url for m in lost_markers) and \
               not any(m in url for m in lost_markers):
                rec["session_lost"] = True
                rec["error"] = f"session_lost redirect_to={final_url[:120]}"
                # Don't screenshot; caller should re-login
                return rec

            out_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_path), full_page=False)
            rec["screenshot"] = str(out_path)
            rec["success"] = True
            rec["elapsed_s"] = round(time.time() - t_start, 2)
            return rec
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            if attempt < max_retries:
                # Exponential backoff: 1s, 3s, 9s
                time.sleep(3 ** (attempt - 1))
        finally:
            try:
                context.close()
            except Exception:
                pass
    rec["elapsed_s"] = round(time.time() - t_start, 2)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls-csv", default="results/visual-equivalence/agent-urls-dedup.csv",
                    help="URLs to replay (from extract_agent_urls.py)")
    ap.add_argument("--url", default=None,
                    help="Single URL override (skips CSV)")
    ap.add_argument("--webarena-ip", default="10.0.1.50",
                    help="IP to rewrite historical URLs to (current WebArena)")
    ap.add_argument("--variants", nargs="+", default=["base", "base2", "low"],
                    help="Variants to capture. 'base2' = second independent "
                         "base capture for baseline-noise estimation (P0-2); "
                         "renders as base (no patches) but in its own context.")
    ap.add_argument("--output", default="./data/visual-equivalence/replay")
    ap.add_argument("--min-visits", type=int, default=1,
                    help="Only replay URLs visited >= N times in original experiments")
    ap.add_argument("--limit", type=int, default=0,
                    help="Maximum URLs to capture (0 = all)")
    ap.add_argument("--apps", nargs="+", default=None,
                    help="Filter by app (shopping shopping_admin reddit gitlab)")
    ap.add_argument("--relogin-every", type=int, default=50,
                    help="Re-login all apps every N URLs to prevent session "
                         "expiry (P0-3). Default 50.")
    args = ap.parse_args()

    # Load the variant JS bytes once
    if not APPLY_LOW_JS.exists():
        print(f"ERROR: apply-low.js not found at {APPLY_LOW_JS}", file=sys.stderr)
        sys.exit(1)
    apply_js = APPLY_LOW_JS.read_text(encoding="utf-8")

    # Build URL list
    urls: list[tuple[str, str, int]] = []  # (url, app, visits)
    if args.url:
        url = rewrite_ip(args.url, args.webarena_ip)
        parsed = urllib.parse.urlparse(url)
        app = PORT_APP.get(parsed.port or 80, "unknown")
        urls.append((url, app, 1))
    else:
        csv_path = pathlib.Path(args.urls_csv)
        if not csv_path.exists():
            print(f"ERROR: URLs CSV not found at {csv_path}. "
                  f"Run scripts/extract_agent_urls.py first.", file=sys.stderr)
            sys.exit(1)
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("replayable", "").lower() not in ("true", "yes"):
                    continue
                visits = int(row.get("visits", 0))
                if visits < args.min_visits:
                    continue
                app = row.get("app", "").strip()
                if args.apps and app not in args.apps:
                    continue
                url = rewrite_ip(row["url"], args.webarena_ip)
                urls.append((url, app, visits))
    if args.limit > 0:
        urls = urls[:args.limit]
    print(f"Replaying {len(urls)} URLs × {len(args.variants)} variants",
          file=sys.stderr)

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    all_records = []
    t_start = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Phase 1: login once per app, cache cookies
        print("\n--- Phase 1: login per app to capture cookies ---", file=sys.stderr)
        app_cookies: dict[str, list[dict]] = {}
        # Determine which apps we need cookies for
        needed_apps = sorted({app for _, app, _ in urls if app in WEBARENA_ACCOUNTS})

        def _refresh_all_logins():
            for app in needed_apps:
                port = [p for p, a in PORT_APP.items() if a == app][0]
                base_url = f"http://{args.webarena_ip}:{port}"
                print(f"  login {app} at {base_url}", file=sys.stderr)
                app_cookies[app] = login_and_capture_cookies(browser, app, base_url)

        _refresh_all_logins()

        # Phase 2: replay each URL
        print(f"\n--- Phase 2: replay {len(urls)} URLs ---", file=sys.stderr)
        total = len(urls) * len(args.variants)
        done = 0
        urls_since_relogin = 0
        session_lost_count = 0
        for url, app, visits in urls:
            # P0-3: periodic re-login to prevent session expiry over long runs
            if urls_since_relogin >= args.relogin_every:
                print(f"  [re-login] after {urls_since_relogin} URLs", file=sys.stderr)
                _refresh_all_logins()
                urls_since_relogin = 0
            urls_since_relogin += 1

            slug = url_to_slug(url)
            slug_dir = out_dir / slug
            cookies = app_cookies.get(app, [])
            for variant in args.variants:
                done += 1
                out_path = slug_dir / f"{variant}.png"
                rec = capture_one(
                    browser, url, variant, out_path,
                    cookies=cookies,
                    apply_js=apply_js,
                )
                rec.update({
                    "app": app, "visits": visits, "slug": slug,
                })
                all_records.append(rec)

                # P0-3: if session was lost, immediately re-login and retry
                # this single capture once
                if rec.get("session_lost") and app in WEBARENA_ACCOUNTS:
                    session_lost_count += 1
                    print(f"  [session lost] re-logging {app} and retrying "
                          f"{slug}/{variant}", file=sys.stderr)
                    port = [p for p, a in PORT_APP.items() if a == app][0]
                    base_url = f"http://{args.webarena_ip}:{port}"
                    app_cookies[app] = login_and_capture_cookies(
                        browser, app, base_url)
                    cookies = app_cookies[app]
                    rec2 = capture_one(
                        browser, url, variant, out_path,
                        cookies=cookies, apply_js=apply_js,
                    )
                    rec2.update({
                        "app": app, "visits": visits, "slug": slug,
                        "after_relogin": True,
                    })
                    all_records.append(rec2)
                    rec = rec2
                status = "OK" if rec["success"] else "FAIL"
                print(f"[{done}/{total}] {variant:4} {slug[:60]:<60} {status} "
                      f"({rec['elapsed_s']}s)"
                      + (f" err={rec['error'][:60]}" if rec['error'] else ""),
                      file=sys.stderr)
                # Incremental manifest
                manifest = out_dir / "manifest.json"
                with manifest.open("w", encoding="utf-8") as f:
                    json.dump({
                        "config": {
                            "urls_csv": args.urls_csv,
                            "webarena_ip": args.webarena_ip,
                            "variants": args.variants,
                            "min_visits": args.min_visits,
                            "limit": args.limit,
                        },
                        "records": all_records,
                        "elapsed_s": round(time.time() - t_start, 1),
                        "progress": {"done": done, "total": total,
                                     "success": sum(1 for r in all_records
                                                    if r["success"]),
                                     "session_lost": session_lost_count,
                                     "relogins": done // max(1, args.relogin_every * len(args.variants))},
                    }, f, indent=2)

        browser.close()

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{len(all_records)} captures succeeded in "
          f"{time.time() - t_start:.1f}s", file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()

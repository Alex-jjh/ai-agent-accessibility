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

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
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

    NOTE: Magento's base URL is baked into the AMI as a stale public hostname
    (e.g. ec2-3-131-244-37.us-east-2.compute.amazonaws.com). Every request
    gets 302-redirected to that hostname. Workaround: install a DNS-rewriting
    HTTP adapter that routes any such hostname to the private WebArena IP.
    """
    import requests as _requests
    from requests.adapters import HTTPAdapter
    import urllib.parse as _urlparse

    target_host = _urlparse.urlparse(base_url).hostname
    target_port = _urlparse.urlparse(base_url).port or 80

    class _IPRewriteAdapter(HTTPAdapter):
        """Rewrite any EC2 public hostname back to the private WebArena IP.

        Magento's canonical URL is a stale public hostname; we force all
        requests to that hostname to resolve to our private IP.
        """
        def send(self, request, **kwargs):
            parsed = _urlparse.urlparse(request.url)
            # Rewrite if host is an EC2 public hostname or resolves publicly.
            # Simpler heuristic: anything NOT matching target_host + same port -> rewrite
            if parsed.hostname and parsed.hostname != target_host:
                # Keep the original Host header so Magento returns matching canonical URL
                new_netloc = f"{target_host}:{parsed.port or target_port}"
                new_url = _urlparse.urlunparse(parsed._replace(netloc=new_netloc))
                request.url = new_url
                # Set Host header back to the original so the app sees consistent URL
                request.headers["Host"] = f"{parsed.hostname}:{parsed.port or target_port}"
            return super().send(request, **kwargs)

    session = _requests.Session()
    adapter = _IPRewriteAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    cookies_out: list[dict] = []
    try:
        # Step 1: GET login page for form_key. Allow redirects — our adapter
        # will rewrite the stale public host back to the private IP.
        login_url = f"{base_url}/customer/account/login/"
        resp1 = session.get(login_url, timeout=timeout_s, allow_redirects=True)
        print(f"    [login:shopping] GET login: status={resp1.status_code} "
              f"final_url={resp1.url[:80]}", file=sys.stderr)
        form_key_match = re.search(
            r'name="form_key"\s+.*?value="([^"]+)"', resp1.text
        ) or re.search(r'"form_key"\s*:\s*"([^"]+)"', resp1.text)
        form_key = form_key_match.group(1) if form_key_match else ""
        print(f"    [login:shopping] form_key={'found' if form_key else 'MISSING'} "
              f"(len={len(form_key)})", file=sys.stderr)

        # Step 2: POST credentials
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

        # Convert to Playwright cookie format — tag cookies with the private IP
        # host (our target_host) since that's where we'll replay URLs.
        for c in session.cookies:
            cookies_out.append({
                "name": c.name,
                "value": c.value,
                "domain": target_host,
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
                only_patch_id: Optional[int] = None) -> dict:
    """Render a URL at a variant, screenshot, return metadata."""
    t0 = time.time()
    context = pw_browser.new_context(
        viewport={"width": 1280, "height": 720},
        # Matches Playwright chromium default — don't add extra headers
    )
    rec = {
        "url": url, "variant": variant, "screenshot": None,
        "success": False, "error": None, "elapsed_s": None,
        "final_url": None, "title": None, "dom_changes": 0,
    }
    try:
        if cookies:
            try:
                context.add_cookies(cookies)
            except Exception as cerr:
                # Some cookies have odd expiry/samesite fields — retry filtered
                clean = [{k: v for k, v in c.items()
                          if k in ("name", "value", "domain", "path",
                                   "expires", "httpOnly", "secure", "sameSite")}
                         for c in cookies]
                context.add_cookies(clean)

        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Additional settle — networkidle is a better signal but some pages
        # with persistent polling never reach it
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(settle_ms)

        if variant == "low" and apply_js:
            if only_patch_id is not None:
                # Ablation mode — apply-low-individual.js, select one patch
                page.evaluate(f"window.__ONLY_PATCH_ID = {int(only_patch_id)}")
            changes = page.evaluate(apply_js)
            rec["dom_changes"] = len(changes) if isinstance(changes, list) else 0
            # Wait for layout reflow / style recalc
            page.wait_for_timeout(post_patch_ms)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out_path), full_page=False)
        rec["screenshot"] = str(out_path)
        rec["success"] = True
        rec["final_url"] = page.url
        try:
            rec["title"] = page.title()[:200]
        except Exception:
            pass
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        rec["elapsed_s"] = round(time.time() - t0, 2)
        try:
            context.close()
        except Exception:
            pass
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls-csv", default="results/visual-equivalence/agent-urls-dedup.csv",
                    help="URLs to replay (from extract_agent_urls.py)")
    ap.add_argument("--url", default=None,
                    help="Single URL override (skips CSV)")
    ap.add_argument("--webarena-ip", default="10.0.1.50",
                    help="IP to rewrite historical URLs to (current WebArena)")
    ap.add_argument("--variants", nargs="+", default=["base", "low"],
                    help="Variants to capture")
    ap.add_argument("--output", default="./data/visual-equivalence/replay")
    ap.add_argument("--min-visits", type=int, default=1,
                    help="Only replay URLs visited >= N times in original experiments")
    ap.add_argument("--limit", type=int, default=0,
                    help="Maximum URLs to capture (0 = all)")
    ap.add_argument("--apps", nargs="+", default=None,
                    help="Filter by app (shopping shopping_admin reddit gitlab)")
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
        for app in needed_apps:
            port = [p for p, a in PORT_APP.items() if a == app][0]
            base_url = f"http://{args.webarena_ip}:{port}"
            print(f"  login {app} at {base_url}", file=sys.stderr)
            app_cookies[app] = login_and_capture_cookies(browser, app, base_url)

        # Phase 2: replay each URL
        print(f"\n--- Phase 2: replay {len(urls)} URLs ---", file=sys.stderr)
        total = len(urls) * len(args.variants)
        done = 0
        for url, app, visits in urls:
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
                                                    if r["success"])},
                    }, f, indent=2)

        browser.close()

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{len(all_records)} captures succeeded in "
          f"{time.time() - t_start:.1f}s", file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()

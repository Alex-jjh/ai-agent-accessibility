#!/usr/bin/env python3
"""Quick smoke test for replay-url-screenshots.py login helpers.

Runs login_and_capture_cookies() for every app, prints cookie count + a sample.
Use this to verify selectors work on the current WebArena before running the
full experiment.

Usage (on EC2):
  cd ~/platform
  PATH=/root/.local/bin:$PATH python3 scripts/smoke-replay-login.py 10.0.1.50
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "visual-equiv"))
spec = importlib.util.spec_from_file_location(
    "replay_screens",
    pathlib.Path(__file__).parent.parent / "visual-equiv" / "replay-url-screenshots.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    webarena_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.1.50"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for app in ("shopping", "shopping_admin", "reddit", "gitlab"):
            port = [p for p, a in m.PORT_APP.items() if a == app][0]
            base = f"http://{webarena_ip}:{port}"
            print(f"\n{'=' * 60}")
            print(f"app: {app}  base: {base}")
            print('=' * 60)
            cookies = m.login_and_capture_cookies(browser, app, base, timeout_ms=45000)
            if not cookies:
                print(f"  ✗ NO COOKIES captured — login failed")
            else:
                print(f"  ✓ {len(cookies)} cookies captured")
                for c in cookies[:8]:
                    print(f"    {c.get('name', '?')}={str(c.get('value', ''))[:30]}... "
                          f"domain={c.get('domain', '?')}")

            # Now test auth by navigating to a protected URL
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            if app == "shopping":
                target = f"{base}/customer/account/"  # should show "My Account" if logged in
                signal = "My Account"
            elif app == "shopping_admin":
                target = f"{base}/admin/dashboard/"  # should show dashboard
                signal = "Dashboard"
            elif app == "reddit":
                target = f"{base}/submissions"  # user's submissions
                signal = m.WEBARENA_ACCOUNTS[app][0]  # username in nav
            elif app == "gitlab":
                target = f"{base}/dashboard"  # user dashboard
                signal = "Your work"
            try:
                page.goto(target, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                content = page.content()
                is_authed = signal.lower() in content.lower()
                print(f"  auth check: {target}")
                print(f"    signal='{signal}' found: {'YES' if is_authed else 'NO'}")
                if not is_authed:
                    # Show a hint of what's on the page
                    title = page.title()
                    print(f"    page title: {title[:80]}")
                    print(f"    final URL: {page.url}")
            except Exception as e:
                print(f"  auth check FAILED: {type(e).__name__}: {e}")
            finally:
                context.close()
        browser.close()


if __name__ == "__main__":
    main()

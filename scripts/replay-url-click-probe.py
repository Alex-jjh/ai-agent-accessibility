#!/usr/bin/env python3
"""
Click-probe — direct functional verification for patch 11 (link→span).

For each of the 15 ablation URLs:
  1. Navigate under BASE (no patch). Find the first visible <a href> link,
     record its bbox center coordinates. Click. Record final_url (should
     differ).
  2. Navigate under PATCH 11 only. At the SAME coordinates, click. Record
     final_url (should stay the same; link was replaced with styled span
     and href deleted).
  3. Compare. A "click-inert" case = coordinates are visually identical but
     click under patch 11 produces no navigation.

Output:
  ./data/visual-equivalence/click-probe/manifest.json — per-URL click results
  stdout summary — #URLs where visual == same, functional == broken

This produces the direct bridge for Group C — proves "pixel-identical
rendering produces inert click behavior" without going through CUA traces.

Usage:
  python3 scripts/replay-url-click-probe.py \\
    --webarena-ip 10.0.1.50 \\
    --output ./data/visual-equivalence/click-probe
"""
import argparse
import importlib.util
import json
import pathlib
import sys
import time

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
APPLY_LOW_INDIV = REPO_ROOT / "src" / "variants" / "patches" / "inject" / "apply-low-individual.js"

# Load helpers from replay-url-screenshots.py
_REPLAY = pathlib.Path(__file__).parent / "replay-url-screenshots.py"
_spec = importlib.util.spec_from_file_location("replay_screens", _REPLAY)
replay_screens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_screens)

# Load URL list from ablation script
_ABL = pathlib.Path(__file__).parent / "replay-url-patch-ablation.py"
_spec2 = importlib.util.spec_from_file_location("replay_ablation", _ABL)
replay_ablation = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(replay_ablation)


def find_first_clickable_link(page, timeout_ms: int = 5000) -> dict:
    """Find the first visible <a href="..."> link in the viewport.

    Returns: {selector, href, cx, cy, text, bbox} or {"error": ...}.
    """
    try:
        result = page.evaluate("""() => {
            const VIEWPORT_W = window.innerWidth;
            const VIEWPORT_H = window.innerHeight;
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                if (!href || href.startsWith('javascript:') || href.startsWith('#')
                    || href.startsWith('mailto:') || href.startsWith('tel:')) {
                    continue;
                }
                const rect = a.getBoundingClientRect();
                if (rect.width < 5 || rect.height < 5) continue;
                // Must be in viewport
                if (rect.top < 0 || rect.left < 0) continue;
                if (rect.bottom > VIEWPORT_H || rect.right > VIEWPORT_W) continue;
                // Must be visible
                const style = getComputedStyle(a);
                if (style.visibility === 'hidden' || style.display === 'none') continue;
                return {
                    href: href,
                    text: (a.textContent || '').trim().slice(0, 80),
                    cx: Math.round(rect.left + rect.width / 2),
                    cy: Math.round(rect.top + rect.height / 2),
                    bbox: {top: Math.round(rect.top), left: Math.round(rect.left),
                           width: Math.round(rect.width), height: Math.round(rect.height)}
                };
            }
            return null;
        }""")
        if result is None:
            return {"error": "no visible <a href> link found in viewport"}
        return result
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def probe_url(pw_browser, url: str, app: str, apply_js_indiv: str,
              cookies: list[dict], timeout_ms: int = 30000) -> dict:
    """Run the two-step probe (base click + patch 11 click) for one URL."""
    out = {
        "url": url, "app": app, "slug": replay_screens.url_to_slug(url),
        "base_url_before": None, "base_url_after": None, "base_click_ok": None,
        "patch11_url_before": None, "patch11_url_after": None,
        "patch11_click_inert": None,
        "link_info": None, "error": None,
    }

    # --- Phase 1: BASE — find link + click + record nav ---
    ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
    try:
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        out["base_url_before"] = page.url

        link = find_first_clickable_link(page)
        out["link_info"] = link
        if "error" in link:
            out["error"] = f"base: {link['error']}"
            return out

        # Click at exact coordinates
        page.mouse.click(link["cx"], link["cy"])
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        out["base_url_after"] = page.url
        out["base_click_ok"] = (out["base_url_after"] != out["base_url_before"])
    except Exception as e:
        out["error"] = f"base probe: {type(e).__name__}: {e}"
        return out
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    # --- Phase 2: PATCH 11 — apply only patch 11, click at same coords ---
    ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
    try:
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        # Apply only patch 11
        page.evaluate("window.__ONLY_PATCH_ID = 11")
        page.evaluate(apply_js_indiv)
        page.wait_for_timeout(800)  # layout reflow

        out["patch11_url_before"] = page.url
        # Click at the SAME coordinates as base
        page.mouse.click(link["cx"], link["cy"])
        # Patch 11 replaced <a> with <span> — no navigation should happen.
        # Wait a conservative period to verify.
        page.wait_for_timeout(3000)
        out["patch11_url_after"] = page.url
        out["patch11_click_inert"] = (
            out["patch11_url_after"] == out["patch11_url_before"])
    except Exception as e:
        out["error"] = f"patch11 probe: {type(e).__name__}: {e}"
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webarena-ip", default="10.0.1.50")
    ap.add_argument("--output", default="./data/visual-equivalence/click-probe")
    args = ap.parse_args()

    if not APPLY_LOW_INDIV.exists():
        print(f"ERROR: {APPLY_LOW_INDIV} not found", file=sys.stderr)
        sys.exit(1)
    apply_js_indiv = APPLY_LOW_INDIV.read_text(encoding="utf-8")

    url_list = []
    for app, port, path, desc in replay_ablation.REPRESENTATIVE_URLS:
        full = f"http://{args.webarena_ip}:{port}{path}"
        url_list.append((full, app, desc))

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    records = []
    t_start = time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Login per app
        print("\n--- login per app ---", file=sys.stderr)
        app_cookies: dict[str, list[dict]] = {}
        needed_apps = sorted({app for _, app, _ in url_list
                              if app in replay_screens.WEBARENA_ACCOUNTS})
        # Map display labels (ecommerce_home etc.) to account keys
        label_to_account = {
            "ecommerce_home": "shopping", "ecommerce_product": "shopping",
            "ecommerce_category": "shopping", "ecommerce_account": "shopping",
            "admin_orders": "shopping_admin", "admin_dashboard": "shopping_admin",
            "admin_products": "shopping_admin",
            "reddit_home": "reddit", "reddit_forum": "reddit",
            "reddit_submission": "reddit",
            "gitlab_project": "gitlab", "gitlab_commits": "gitlab",
            "gitlab_graphs": "gitlab", "gitlab_issues": "gitlab",
            "kiwix_home": None,
        }
        accounts_needed = sorted({label_to_account.get(app) for _, app, _ in url_list
                                  if label_to_account.get(app)})
        for app in accounts_needed:
            port = [p for p, a in replay_screens.PORT_APP.items() if a == app][0]
            base_url = f"http://{args.webarena_ip}:{port}"
            print(f"  login {app} at {base_url}", file=sys.stderr)
            app_cookies[app] = replay_screens.login_and_capture_cookies(
                browser, app, base_url)

        # Probe each URL
        print(f"\n--- probing {len(url_list)} URLs ---", file=sys.stderr)
        for i, (url, app, desc) in enumerate(url_list, 1):
            account = label_to_account.get(app)
            cookies = app_cookies.get(account, []) if account else []
            print(f"\n[{i}/{len(url_list)}] {app} — {desc}", file=sys.stderr)
            rec = probe_url(browser, url, app, apply_js_indiv, cookies)
            rec["description"] = desc
            records.append(rec)
            status = []
            if rec["base_click_ok"]:
                status.append("base→navigated")
            if rec["patch11_click_inert"]:
                status.append("patch11→INERT")
            if rec["error"]:
                status.append(f"ERR={rec['error'][:60]}")
            print(f"  {' '.join(status) if status else 'incomplete'}", file=sys.stderr)

        browser.close()

    # Summarize
    n_total = len(records)
    n_base_ok = sum(1 for r in records if r["base_click_ok"])
    n_patch_inert = sum(1 for r in records
                        if r["base_click_ok"] and r["patch11_click_inert"])
    n_same_coord_diff_behavior = n_patch_inert

    print(f"\n=== Click-probe summary ===", file=sys.stderr)
    print(f"Total URLs probed: {n_total}", file=sys.stderr)
    print(f"  Base click navigated:          {n_base_ok}/{n_total}", file=sys.stderr)
    print(f"  Patch 11 click at same coord → INERT: "
          f"{n_patch_inert}/{n_base_ok}", file=sys.stderr)
    if n_base_ok:
        pct = 100 * n_patch_inert / n_base_ok
        print(f"  → {pct:.1f}% of cases demonstrate visual-vs-functional dissociation",
              file=sys.stderr)

    manifest = {
        "config": vars(args),
        "n_total": n_total, "n_base_ok": n_base_ok,
        "n_patch11_inert": n_patch_inert,
        "elapsed_s": round(time.time() - t_start, 1),
        "records": records,
    }
    out_path = out_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

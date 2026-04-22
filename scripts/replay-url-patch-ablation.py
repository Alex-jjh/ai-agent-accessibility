#!/usr/bin/env python3
"""
URL Replay — Per-Patch Ablation

For a small set of representative URLs (one per WebArena app), apply EACH of
the 13 low-variant patches individually via apply-low-individual.js and
screenshot. Produces the Group A/B/C classification for §6 Limitations.

Reuses login + cookie helpers from replay-url-screenshots.py.

Usage:
  python3 scripts/replay-url-patch-ablation.py \\
    --webarena-ip 10.0.1.50 \\
    --output ./data/visual-equivalence/ablation-replay

Output:
  ./data/visual-equivalence/ablation-replay/<slug>/base.png
  ./data/visual-equivalence/ablation-replay/<slug>/patch_01..13.png
  ./data/visual-equivalence/ablation-replay/manifest.json
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.parse
import re

# Reuse helpers from replay-url-screenshots.py (loaded dynamically because
# the filename has hyphens — not a valid module name).
import importlib.util

_REPLAY_PATH = pathlib.Path(__file__).parent / "replay-url-screenshots.py"
if not _REPLAY_PATH.exists():
    print(f"ERROR: cannot find {_REPLAY_PATH}", file=sys.stderr)
    sys.exit(1)
_spec = importlib.util.spec_from_file_location("replay_screens", _REPLAY_PATH)
replay_screens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_screens)

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
APPLY_LOW_INDIV = REPO_ROOT / "src" / "variants" / "patches" / "inject" / "apply-low-individual.js"

# Representative URLs per app — chosen to exercise different DOM features
# that the low patches target (nav, headings, links, tables, forms, etc.).
# P0-1 reviewer fix: 4 URLs was too few to claim per-patch SSIM attribution
# generalizes. Expanded to 15 URLs across 4 apps for SSIM IQR/std reporting.
REPRESENTATIVE_URLS = [
    # (display_label, port, path, description)
    # --- shopping (Magento storefront) × 4 ---
    ("ecommerce_home",     7770, "/",
     "storefront home — nav menu, banner, product grid"),
    ("ecommerce_product",  7770, "/epson-workforce-wf-3620-wifi-direct-all-in-one-color-inkjet-printer-copier-scanner-amazon-dash-rep",
     "product page — nav, header, links, img, form, reviews tabs"),
    ("ecommerce_category", 7770, "/home-kitchen.html",
     "category listing — product grid, faceted nav, pagination"),
    ("ecommerce_account",  7770, "/customer/account/",
     "account dashboard — logged-in header, sidebar nav, forms"),
    # --- shopping_admin (Magento admin) × 3 ---
    ("admin_orders",       7780, "/admin/sales/order/",
     "admin orders — grid, thead/th, filters, actions dropdown"),
    ("admin_dashboard",    7780, "/admin/admin/dashboard/",
     "admin dashboard — summary widgets, side nav, charts"),
    ("admin_products",     7780, "/admin/catalog/product/",
     "admin products — column headers, inline actions, bulk ops"),
    # --- reddit (Postmill) × 3 ---
    ("reddit_home",        9999, "/",
     "reddit home — hot feed, sidebar, vote arrows"),
    ("reddit_forum",       9999, "/f/books",
     "forum listing — many links, headings, compact layout"),
    ("reddit_submission",  9999, "/f/books/130079/the-gene-an-intimate-history-by-siddhartha-mukherjee",
     "submission detail — comments, nested threads, user links"),
    # --- gitlab × 3 ---
    ("gitlab_project",     8023, "/primer/design",
     "project overview — tabs, readme, sidebar, file tree"),
    ("gitlab_commits",     8023, "/primer/design/-/commits/main",
     "commit log — list of commits, pagination, author links"),
    ("gitlab_graphs",      8023, "/primer/design/-/graphs/main",
     "contributors graph — svg chart, sidebar, tables"),
    # --- controls × 2 (kiwix / wiki — static content, low DOM complexity) ---
    ("kiwix_home",         8888, "/",
     "wiki home — static nav + text"),
    ("gitlab_issues",      8023, "/primer/design/-/issues",
     "gitlab issues — list, labels, filters"),
]

PATCH_DESCRIPTIONS = {
    1:  "semantic landmarks -> div",
    2:  "remove aria-* and role",
    3:  "remove <label> elements",
    4:  "remove keyboard handlers",
    5:  "shadow DOM wrap interactive",
    6:  "h1-h6 -> styled divs",
    7:  "remove img alt/aria-label/title",
    8:  "remove tabindex",
    9:  "thead/tbody/th -> div",
    10: "remove html lang",
    11: "a[href] -> span (blue underlined)",
    12: "duplicate IDs",
    13: "onfocus='this.blur()' keyboard trap",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webarena-ip", default="10.0.1.50")
    ap.add_argument("--output", default="./data/visual-equivalence/ablation-replay")
    ap.add_argument("--patches", nargs="+", type=int, default=list(range(1, 14)),
                    help="Which patches to ablate (default 1..13)")
    ap.add_argument("--urls", nargs="+", default=None,
                    help="Override representative URL set (slug-style, e.g. ecommerce)")
    args = ap.parse_args()

    if not APPLY_LOW_INDIV.exists():
        print(f"ERROR: apply-low-individual.js not found at {APPLY_LOW_INDIV}", file=sys.stderr)
        sys.exit(1)
    apply_js = APPLY_LOW_INDIV.read_text(encoding="utf-8")

    target_urls = REPRESENTATIVE_URLS
    if args.urls:
        target_urls = [u for u in REPRESENTATIVE_URLS if u[0] in args.urls]

    # Build absolute URLs with current WebArena IP
    url_list = []
    for app, port, path, desc in target_urls:
        full = f"http://{args.webarena_ip}:{port}{path}"
        url_list.append((full, app, desc))

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    all_records = []
    t_start = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Phase 1: login once per app
        print("\n--- Phase 1: login per app ---", file=sys.stderr)
        app_cookies: dict[str, list[dict]] = {}
        needed_apps = sorted({app for _, app, _ in url_list
                              if app in replay_screens.WEBARENA_ACCOUNTS})
        for app in needed_apps:
            port = [p for p, a in replay_screens.PORT_APP.items() if a == app][0]
            base_url = f"http://{args.webarena_ip}:{port}"
            print(f"  login {app} at {base_url}", file=sys.stderr)
            app_cookies[app] = replay_screens.login_and_capture_cookies(
                browser, app, base_url)

        # Phase 2: for each URL, capture base + 13 patches
        print(f"\n--- Phase 2: ablation on {len(url_list)} URLs ---", file=sys.stderr)
        total_captures = len(url_list) * (1 + len(args.patches))
        done = 0
        for url, app, desc in url_list:
            slug = replay_screens.url_to_slug(url)
            slug_dir = out_dir / slug
            cookies = app_cookies.get(app, [])

            # Base reference
            done += 1
            print(f"\n[{done}/{total_captures}] {app} BASE — {desc}", file=sys.stderr)
            rec = replay_screens.capture_one(
                browser, url, "base", slug_dir / "base.png",
                cookies=cookies, apply_js=None,
            )
            rec.update({
                "app": app, "slug": slug, "patch_id": 0,
                "patch_name": "base", "description": desc,
            })
            all_records.append(rec)
            status = "OK" if rec["success"] else "FAIL"
            print(f"  -> {status} ({rec['elapsed_s']}s)"
                  + (f" err={rec['error']}" if rec['error'] else ""),
                  file=sys.stderr)

            if not rec["success"]:
                print(f"  SKIP ablations for {app} — base capture failed", file=sys.stderr)
                done += len(args.patches)
                continue

            # Ablate each patch
            for pid in args.patches:
                done += 1
                print(f"[{done}/{total_captures}] {app} patch {pid}: "
                      f"{PATCH_DESCRIPTIONS[pid]}", file=sys.stderr)
                rec = replay_screens.capture_one(
                    browser, url, "low",
                    slug_dir / f"patch_{pid:02d}.png",
                    cookies=cookies, apply_js=apply_js,
                    only_patch_id=pid,
                )
                rec.update({
                    "app": app, "slug": slug, "patch_id": pid,
                    "patch_name": PATCH_DESCRIPTIONS[pid],
                    "description": desc,
                })
                all_records.append(rec)
                status = "OK" if rec["success"] else "FAIL"
                print(f"  -> {status} ({rec['elapsed_s']}s) "
                      f"dom_changes={rec.get('dom_changes', 0)}"
                      + (f" err={rec['error']}" if rec['error'] else ""),
                      file=sys.stderr)

                # Save manifest incrementally
                manifest = out_dir / "manifest.json"
                with manifest.open("w", encoding="utf-8") as f:
                    json.dump({
                        "config": vars(args),
                        "patch_descriptions": PATCH_DESCRIPTIONS,
                        "records": all_records,
                        "elapsed_s": round(time.time() - t_start, 1),
                    }, f, indent=2)

        browser.close()

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{len(all_records)} captures succeeded in "
          f"{time.time() - t_start:.1f}s", file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()

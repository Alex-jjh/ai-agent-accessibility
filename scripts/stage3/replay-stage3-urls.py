#!/usr/bin/env python3.11
"""Stage 3 trace-URL SSIM replay driver.

Imports helpers from scripts/visual-equiv/replay-url-screenshots.py and adds
Stage-3-specific logic:

  - Variants = {"base", "base2"} + any subset of the 26 AMT operator IDs
  - Patch artefact = apply-all-individual.js (not apply-low.js)
  - Runtime preamble = window.__OPERATOR_IDS = [variant_id]

Run on a WebArena burner EC2 (needs private-IP access to 10.0.1.50).

Example:
  python3.11 scripts/stage3/replay-stage3-urls.py \\
      --urls-csv results/stage3/visual-equiv/stage3-urls-dedup.csv \\
      --operators L1 L5 L9 L11 L12 ML1 \\
      --min-visits 2 \\
      --reps 1 \\
      --output ./data/stage3-visual-equiv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import time

# Reuse Phase 7 helpers by importing the neighbouring module.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PHASE7_DIR = REPO_ROOT / "scripts" / "visual-equiv"
sys.path.insert(0, str(PHASE7_DIR))

# Imports from the Phase 7 script (underscore-import friendly).
import importlib.util

def _load_phase7():
    spec = importlib.util.spec_from_file_location(
        "replay_phase7",
        PHASE7_DIR / "replay-url-screenshots.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

phase7 = _load_phase7()
capture_one = phase7.capture_one
login_and_capture_cookies = phase7.login_and_capture_cookies
rewrite_ip = phase7.rewrite_ip
url_to_slug = phase7.url_to_slug
PORT_APP = phase7.PORT_APP
WEBARENA_ACCOUNTS = phase7.WEBARENA_ACCOUNTS

# Apply artefact — 26-operator build from src/variants/patches/operators/*.js.
APPLY_ALL_INDIVIDUAL = REPO_ROOT / "src" / "variants" / "patches" / "inject" / "apply-all-individual.js"

VALID_OPERATORS = [
    "L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12","L13",
    "ML1","ML2","ML3",
    "H1","H2","H3","H4","H5a","H5b","H5c","H6","H7","H8",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--urls-csv", default="results/stage3/visual-equiv/stage3-urls-dedup.csv",
        help="Deduplicated URL list from extract-stage3-urls.py",
    )
    ap.add_argument(
        "--operators", nargs="+", default=None,
        help="AMT operator IDs to replay (e.g. L1 L5 L9 L11 L12 ML1). "
             "Default: ALL (all 26). Plus base + base2 are always captured.",
    )
    ap.add_argument(
        "--skip-base2", action="store_true",
        help="Skip the second independent base capture (saves ~4 percent "
             "time, sacrifices baseline-noise estimate).",
    )
    ap.add_argument(
        "--min-visits", type=int, default=1,
        help="Only replay URLs visited >= N times (see stage3-urls-summary.md).",
    )
    ap.add_argument(
        "--limit", type=int, default=0,
        help="Maximum URLs to capture (0 = all).",
    )
    ap.add_argument(
        "--apps", nargs="+", default=None,
        help="Filter by app (shopping shopping_admin reddit gitlab)",
    )
    ap.add_argument(
        "--webarena-ip", default="10.0.1.50",
        help="IP to rewrite URL hosts to (current WebArena private IP)",
    )
    ap.add_argument(
        "--output", default="./data/stage3-visual-equiv",
        help="Output directory for screenshots + manifest",
    )
    ap.add_argument(
        "--reps", type=int, default=1,
        help="Captures per (url, variant) — >1 for within-variant noise",
    )
    ap.add_argument(
        "--relogin-every", type=int, default=50,
        help="Re-login all apps every N URLs",
    )
    args = ap.parse_args()

    if args.operators is None:
        ops = VALID_OPERATORS[:]
    else:
        ops = []
        for op in args.operators:
            if op not in VALID_OPERATORS:
                print(f"ERROR: unknown operator '{op}'. Valid: {VALID_OPERATORS}",
                      file=sys.stderr)
                return 2
            ops.append(op)
    base_variants = ["base"] if args.skip_base2 else ["base", "base2"]
    variants = base_variants + ops
    print(f"[replay] variants: {variants}", file=sys.stderr)

    if not APPLY_ALL_INDIVIDUAL.exists():
        print(f"ERROR: apply-all-individual.js not found at {APPLY_ALL_INDIVIDUAL}",
              file=sys.stderr)
        return 1
    apply_js = APPLY_ALL_INDIVIDUAL.read_text(encoding="utf-8")

    # Load URL list from CSV (schema: url, app, visits, replayable, is_webarena)
    csv_path = pathlib.Path(args.urls_csv)
    if not csv_path.exists():
        print(f"ERROR: URLs CSV not found at {csv_path}", file=sys.stderr)
        return 1

    urls: list[tuple[str, str, int]] = []
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("replayable", "").lower() not in ("true", "1", "yes"):
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

    total_captures = len(urls) * len(variants) * args.reps
    print(f"[replay] {len(urls)} URLs × {len(variants)} variants × {args.reps} reps "
          f"= {total_captures} captures",
          file=sys.stderr)

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"
    manifest_fp = manifest_path.open("a", encoding="utf-8")

    from playwright.sync_api import sync_playwright
    t_start = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Phase 1: login per needed app
        needed_apps = sorted({app for _, app, _ in urls if app in WEBARENA_ACCOUNTS})
        print(f"[replay] logging in to {needed_apps}", file=sys.stderr)
        app_cookies: dict[str, list[dict]] = {}

        def refresh_logins() -> None:
            for app in needed_apps:
                port_candidates = [p for p, a in PORT_APP.items() if a == app]
                if not port_candidates:
                    continue
                base_url = f"http://{args.webarena_ip}:{port_candidates[0]}"
                app_cookies[app] = login_and_capture_cookies(browser, app, base_url)
                print(f"  login {app}: {len(app_cookies[app])} cookies",
                      file=sys.stderr)

        refresh_logins()

        # Phase 2: replay
        done = 0
        urls_since_relogin = 0
        session_lost_count = 0

        for url_idx, (url, app, visits) in enumerate(urls):
            if urls_since_relogin >= args.relogin_every:
                print(f"[replay] re-logging in after {urls_since_relogin} URLs",
                      file=sys.stderr)
                refresh_logins()
                urls_since_relogin = 0

            cookies = app_cookies.get(app, [])
            slug = url_to_slug(url)

            for variant in variants:
                operator_ids = None if variant in ("base", "base2") else [variant]
                for rep in range(args.reps):
                    suffix = "" if args.reps == 1 else f"_rep{rep}"
                    out_path = out_dir / slug / f"{variant}{suffix}.png"
                    if out_path.exists():
                        # Skip already-captured (resume support)
                        done += 1
                        continue

                    rec = capture_one(
                        browser, url, variant, out_path,
                        cookies=cookies,
                        apply_js=apply_js if variant not in ("base", "base2") else None,
                        operator_ids=operator_ids,
                    )
                    rec.update({
                        "slug": slug,
                        "app": app,
                        "visits": visits,
                        "rep": rep,
                    })
                    manifest_fp.write(json.dumps(rec) + "\n")
                    manifest_fp.flush()

                    if rec.get("session_lost"):
                        session_lost_count += 1
                        if session_lost_count >= 3:
                            print(f"[replay] 3 session_lost in a row; re-logging in",
                                  file=sys.stderr)
                            refresh_logins()
                            session_lost_count = 0

                    done += 1
                    if done % 50 == 0 or done == total_captures:
                        elapsed = time.time() - t_start
                        rate = done / max(elapsed, 1)
                        eta_s = (total_captures - done) / max(rate, 0.01)
                        print(f"[replay] {done}/{total_captures} "
                              f"({done/total_captures:.1%})  "
                              f"rate={rate:.2f} cap/s  "
                              f"eta={eta_s/60:.1f} min",
                              file=sys.stderr)

            urls_since_relogin += 1

    manifest_fp.close()
    print(f"[replay] DONE in {(time.time() - t_start)/60:.1f} min", file=sys.stderr)
    print(f"[replay] manifest: {manifest_path}", file=sys.stderr)
    print(f"[replay] screenshots: {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

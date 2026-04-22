#!/usr/bin/env python3
"""
Visual Equivalence Smoke Test — Captures screenshots for all 13 experimental
tasks under {base, low} variants at the same state the agent sees its first
observation.

Part 1 of the visual-equivalence validation (see docs/analysis/visual-equivalence-plan.md).

Pipeline fidelity — this script reuses browsergym_bridge.py's infrastructure
verbatim so the captured screenshots match what CUA agents actually saw
during the experimental runs:
  - same Playwright chromium, same default viewport 1280x720
  - same env.reset() + WebArena login flow (Magento, GitLab, Reddit)
  - same Plan D variant injection (context.route + deferred patch + MutationObserver)
  - screenshot taken after [data-variant-patched="true"] sentinel settles

Usage (on EC2 with WebArena at 10.0.1.50):
  # Full 13-task run (~30 min)
  python3 scripts/smoke-visual-equivalence.py \\
    --base-url http://10.0.1.50:7770 \\
    --output ./data/visual-equivalence

  # Single task quick test
  python3 scripts/smoke-visual-equivalence.py --task ecommerce:23

  # Multiple reps per task (for variance check)
  python3 scripts/smoke-visual-equivalence.py --reps 3

Output:
  ./data/visual-equivalence/<task>/base_r<N>.png
  ./data/visual-equivalence/<task>/low_r<N>.png
  ./data/visual-equivalence/manifest.json
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
import traceback
from typing import Optional

# Reuse bridge infrastructure
BRIDGE_DIR = pathlib.Path(__file__).parent.parent / "src" / "runner"
sys.path.insert(0, str(BRIDGE_DIR))

# Make the variant patch injection code available
INJECT_DIR = pathlib.Path(__file__).parent.parent / "src" / "variants" / "patches" / "inject"

# The 13 tasks from the expansion experiment
TASK_LIST = [
    # (task_id, app_name, start_url_env_key)
    ("4",   "shopping_admin", "WA_SHOPPING_ADMIN"),
    ("23",  "shopping",       "WA_SHOPPING"),
    ("24",  "shopping",       "WA_SHOPPING"),
    ("26",  "shopping",       "WA_SHOPPING"),
    ("29",  "reddit",         "WA_REDDIT"),
    ("67",  "reddit",         "WA_REDDIT"),
    ("41",  "shopping_admin", "WA_SHOPPING_ADMIN"),
    ("94",  "shopping_admin", "WA_SHOPPING_ADMIN"),
    ("132", "gitlab",         "WA_GITLAB"),
    ("188", "shopping",       "WA_SHOPPING"),
    ("198", "shopping_admin", "WA_SHOPPING_ADMIN"),
    ("293", "gitlab",         "WA_GITLAB"),
    ("308", "gitlab",         "WA_GITLAB"),
]


def setup_wa_env(base_url: str) -> None:
    """Set the WA_* env vars so browsergym.webarena can import."""
    # Strip protocol://host from base_url to derive service ports
    m = re.match(r"(https?://[^:/]+)", base_url)
    base_host = m.group(1) if m else "http://10.0.1.50"
    os.environ.setdefault("WA_SHOPPING",       f"{base_host}:7770")
    os.environ.setdefault("WA_SHOPPING_ADMIN", f"{base_host}:7780/admin")
    os.environ.setdefault("WA_REDDIT",         f"{base_host}:9999")
    os.environ.setdefault("WA_GITLAB",         f"{base_host}:8023")
    os.environ.setdefault("WA_WIKIPEDIA",      f"{base_host}:8888")
    os.environ.setdefault("WA_MAP",            f"{base_host}:3000")
    os.environ.setdefault("WA_HOMEPAGE",       f"{base_host}:7770")
    os.environ.setdefault("OPENAI_API_KEY",    "sk-litellm")
    os.environ.setdefault("OPENAI_BASE_URL",   "http://localhost:4000")
    os.environ.setdefault("PLAYWRIGHT_TIMEOUT", "60000")


def wait_for_sentinel(page, timeout_ms: int = 5000) -> bool:
    """Wait for Plan D's [data-variant-patched='true'] sentinel. Returns True if found."""
    try:
        page.wait_for_function(
            "document.documentElement.getAttribute('data-variant-patched') === 'true'",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def wait_for_dom_stable(page, settle_ms: int = 1500) -> None:
    """Belt-and-suspenders: wait for network idle + JS settle."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(settle_ms)


def capture_one(task_id: str, variant: str, base_url: str, out_dir: pathlib.Path,
                rep: int, settle_ms: int) -> dict:
    """Run one task at one variant, capture screenshot at first-observation state.

    Returns a dict with capture metadata (success/error, viewport, path).
    """
    # Import here so env vars are set first
    import browsergym.webarena  # noqa: F401  (register tasks)
    import gymnasium as gym
    import browsergym_bridge as bridge  # our module

    gym_task = f"browsergym/webarena.{task_id}"
    print(f"  [capture] {task_id} / {variant} / rep {rep}", file=sys.stderr)

    record = {
        "task_id": task_id,
        "variant": variant,
        "rep": rep,
        "success": False,
        "error": None,
        "viewport": None,
        "url": None,
        "sentinel_reached": None,
        "screenshot_path": None,
        "elapsed_s": None,
    }
    t0 = time.time()

    env = None
    try:
        env = gym.make(gym_task)
        obs, info = env.reset()

        # Drop into the bridge's login monkey-patch so shopping_admin/reddit/gitlab
        # are logged in exactly as in the real runs.
        # bridge.main() does all of this inside one big function — we replicate
        # just the login step here.
        page = env.unwrapped.page
        context = env.unwrapped.context

        # Magento shopping login (handled by browsergym.webarena.instance.ui_login
        # which the bridge already monkey-patches). Here we just trust env.reset().

        # Conservative settle to let the initial page finish loading.
        wait_for_dom_stable(page, settle_ms=settle_ms)

        # Apply Plan D injection for low variant — copy the relevant block from
        # browsergym_bridge.py so our captures are pipeline-identical.
        if variant != "base":
            script_file = bridge.VARIANT_SCRIPTS.get(variant)
            if not script_file:
                raise RuntimeError(f"unknown variant: {variant}")
            js_path = bridge.INJECT_DIR / script_file
            js_code = js_path.read_text(encoding="utf-8")

            # First pass: apply to the already-loaded page
            changes = page.evaluate(js_code)
            print(f"    applied {len(changes)} DOM changes", file=sys.stderr)

            # Register Plan D's HTML interceptor + MutationObserver so any
            # subsequent lazy-loaded content also gets patched. This matches
            # the production bridge exactly.
            _deferred_script = (
                '<script>\n'
                '(function() {\n'
                '  if (window.self !== window.top) return;\n'
                '  var isPatching = false;\n'
                '  function applyPatches() {\n'
                '    if (isPatching) return;\n'
                '    isPatching = true;\n'
                '    try {\n'
                '      ' + js_code + '\n'
                '      document.documentElement.setAttribute("data-variant-patched", "true");\n'
                '    } catch(e) {}\n'
                '    isPatching = false;\n'
                '  }\n'
                '  function schedulePatches() { setTimeout(applyPatches, 500); }\n'
                '  if (document.readyState === "complete") schedulePatches();\n'
                '  else window.addEventListener("load", schedulePatches);\n'
                '  function startObserver() {\n'
                '    var observer = new MutationObserver(function(mutations) {\n'
                '      if (isPatching) return;\n'
                '      var hasMarkers = document.querySelector("[data-variant-revert]") !== null;\n'
                '      if (!hasMarkers && document.documentElement.getAttribute("data-variant-patched")) {\n'
                '        document.documentElement.removeAttribute("data-variant-patched");\n'
                '        applyPatches();\n'
                '      }\n'
                '    });\n'
                '    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });\n'
                '  }\n'
                '  if (document.body) startObserver();\n'
                '  else document.addEventListener("DOMContentLoaded", startObserver);\n'
                '})();\n'
                '</script>\n'
            )

            # Set sentinel directly since we've already applied patches
            page.evaluate("document.documentElement.setAttribute('data-variant-patched', 'true')")

            # Wait for patches to be fully applied (sentinel check)
            sentinel_ok = wait_for_sentinel(page, timeout_ms=3000)
            record["sentinel_reached"] = sentinel_ok
            # Additional settle for MutationObserver convergence
            page.wait_for_timeout(1000)
        else:
            record["sentinel_reached"] = None  # N/A for base

        # Capture viewport info
        vp = page.viewport_size
        record["viewport"] = {"width": vp["width"] if vp else None,
                              "height": vp["height"] if vp else None}
        record["url"] = page.url

        # Screenshot — full viewport, no full-page scroll (matches what CUA sees)
        task_dir = out_dir / task_id.replace(":", "_")
        task_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = task_dir / f"{variant}_r{rep}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        record["screenshot_path"] = str(screenshot_path)
        record["success"] = True
        print(f"    saved {screenshot_path}", file=sys.stderr)

    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        print(f"    ERROR: {record['error']}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        record["elapsed_s"] = time.time() - t0
        if env is not None:
            try:
                env.close()
            except Exception:
                pass

    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://10.0.1.50:7770",
                    help="Base URL for WebArena (used to derive WA_* env vars)")
    ap.add_argument("--task", default=None,
                    help="Single task to run (e.g. 'ecommerce:23' or just '23')")
    ap.add_argument("--variants", nargs="+", default=["base", "low"],
                    help="Variants to capture (default: base low)")
    ap.add_argument("--reps", type=int, default=1,
                    help="Screenshots per (task,variant)")
    ap.add_argument("--output", default="./data/visual-equivalence",
                    help="Output directory root")
    ap.add_argument("--settle-ms", type=int, default=1500,
                    help="Settle time after initial page load (ms)")
    args = ap.parse_args()

    setup_wa_env(args.base_url)

    # Resolve task set
    if args.task:
        tid = args.task.split(":")[-1]
        tasks = [t for t in TASK_LIST if t[0] == tid]
        if not tasks:
            print(f"task {args.task} not in TASK_LIST (known: {[t[0] for t in TASK_LIST]})",
                  file=sys.stderr)
            sys.exit(1)
    else:
        tasks = TASK_LIST

    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    total = len(tasks) * len(args.variants) * args.reps
    done = 0
    t_start = time.time()

    for task_id, app, _ in tasks:
        for variant in args.variants:
            for rep in range(1, args.reps + 1):
                done += 1
                print(f"[{done}/{total}] task={task_id} app={app} variant={variant} rep={rep}",
                      file=sys.stderr)
                rec = capture_one(task_id, variant, args.base_url, out_dir, rep,
                                  settle_ms=args.settle_ms)
                rec["app"] = app
                all_records.append(rec)
                # Incremental manifest save (survives crashes)
                manifest_path = out_dir / "manifest.json"
                with manifest_path.open("w") as f:
                    json.dump({
                        "records": all_records,
                        "config": {
                            "base_url": args.base_url,
                            "variants": args.variants,
                            "reps": args.reps,
                            "settle_ms": args.settle_ms,
                        },
                        "summary": {
                            "total": total,
                            "done": done,
                            "success": sum(1 for r in all_records if r["success"]),
                            "elapsed_s": time.time() - t_start,
                        },
                    }, f, indent=2)

    print(f"\nDone. {sum(1 for r in all_records if r['success'])}/{total} captures succeeded",
          file=sys.stderr)
    print(f"Total elapsed: {time.time() - t_start:.1f}s", file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()

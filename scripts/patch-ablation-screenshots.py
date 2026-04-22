#!/usr/bin/env python3
"""
Per-Patch Ablation — Captures a screenshot with EACH of the 13 low-variant
patches applied individually on representative tasks. Isolates which patches
produce visual changes (Group A/B/C classification for §6 Limitations).

Uses src/variants/patches/inject/apply-low-individual.js which takes
window.__ONLY_PATCH_ID to select a single patch block.

Strategy: for each (task, patch_id):
  1. Fresh env.reset() (gives clean login + base page state)
  2. Inject apply-low-individual.js with __ONLY_PATCH_ID=patch_id
  3. Wait for DOM settle
  4. Screenshot

Using fresh resets per (task, patch) ensures no cross-contamination between
patches; this is slower but gives clean per-patch deltas.

Representative tasks (exercise different DOM features):
  - ecommerce:23 (product page): nav, header, links, img alt, form inputs, reviews
  - shopping_admin:4 (admin dashboard): nav, landmarks, tables, thead/th, datagrid
  - reddit:29 (forum listing): many links, headings, compact text layout
  - gitlab:132 (commit browser): tables, landmarks, code blocks

Usage (on EC2):
  python3 scripts/patch-ablation-screenshots.py \\
    --base-url http://10.0.1.50:7770 \\
    --tasks 23 4 29 132 \\
    --output ./data/visual-equivalence/ablation

Output structure:
  ./data/visual-equivalence/ablation/<task>/
    base.png
    patch_01.png ... patch_13.png
    manifest.json
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
import traceback

BRIDGE_DIR = pathlib.Path(__file__).parent.parent / "src" / "runner"
sys.path.insert(0, str(BRIDGE_DIR))

INJECT_DIR = pathlib.Path(__file__).parent.parent / "src" / "variants" / "patches" / "inject"

TASK_APP_MAP = {
    "4":   "shopping_admin",
    "23":  "shopping",
    "24":  "shopping",
    "26":  "shopping",
    "29":  "reddit",
    "67":  "reddit",
    "41":  "shopping_admin",
    "94":  "shopping_admin",
    "132": "gitlab",
    "188": "shopping",
    "198": "shopping_admin",
    "293": "gitlab",
    "308": "gitlab",
}

PATCH_DESCRIPTIONS = {
    1:  "semantic landmarks -> div (nav, main, header, footer, article, section, aside)",
    2:  "remove all aria-* and role attributes",
    3:  "remove all <label> elements",
    4:  "remove keyboard event handlers (onkeydown/up/press)",
    5:  "wrap interactive elements in closed Shadow DOM",
    6:  "replace h1-h6 with styled divs",
    7:  "remove img alt/aria-label/title",
    8:  "remove tabindex attributes",
    9:  "replace thead/tbody/tfoot/th with divs",
    10: "remove html lang attribute",
    11: "replace <a href> with <span onclick> (blue underlined)",
    12: "inject duplicate IDs",
    13: "add onfocus='this.blur()' (keyboard trap)",
}


def setup_wa_env(base_url: str) -> None:
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


def wait_dom_stable(page, settle_ms: int = 1500) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(settle_ms)


def capture_task_ablation(task_id: str, out_dir: pathlib.Path, settle_ms: int) -> list[dict]:
    """Capture base + 13 individual patches for one task. Returns per-patch records."""
    import browsergym.webarena  # noqa: F401
    import gymnasium as gym

    records = []
    app = TASK_APP_MAP.get(task_id, "unknown")
    gym_task = f"browsergym/webarena.{task_id}"
    task_dir = out_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    individual_js_path = INJECT_DIR / "apply-low-individual.js"
    individual_js = individual_js_path.read_text(encoding="utf-8")

    # Capture base (no patch) via a fresh env.reset
    print(f"  [{task_id}] base", file=sys.stderr)
    env = gym.make(gym_task)
    t0 = time.time()
    try:
        env.reset()
        page = env.unwrapped.page
        wait_dom_stable(page, settle_ms)
        base_path = task_dir / "base.png"
        page.screenshot(path=str(base_path), full_page=False)
        base_url = page.url
        base_viewport = page.viewport_size
        records.append({
            "task_id": task_id, "app": app, "patch_id": 0, "patch_name": "base",
            "screenshot": str(base_path), "url": base_url,
            "viewport": dict(base_viewport) if base_viewport else None,
            "elapsed_s": time.time() - t0, "success": True, "error": None,
        })
    except Exception as e:
        records.append({
            "task_id": task_id, "app": app, "patch_id": 0, "patch_name": "base",
            "screenshot": None, "error": f"{type(e).__name__}: {e}",
            "elapsed_s": time.time() - t0, "success": False,
        })
        env.close()
        return records
    env.close()

    # Apply each patch on a fresh env.reset — slow but clean
    for patch_id in range(1, 14):
        print(f"  [{task_id}] patch {patch_id}: {PATCH_DESCRIPTIONS[patch_id]}", file=sys.stderr)
        env = gym.make(gym_task)
        t0 = time.time()
        rec = {
            "task_id": task_id, "app": app, "patch_id": patch_id,
            "patch_name": PATCH_DESCRIPTIONS[patch_id],
            "screenshot": None, "elapsed_s": None, "success": False,
            "error": None, "dom_changes": 0,
        }
        try:
            env.reset()
            page = env.unwrapped.page
            wait_dom_stable(page, settle_ms)

            # Set the patch id, then evaluate the single-patch script
            page.evaluate(f"window.__ONLY_PATCH_ID = {patch_id}")
            try:
                changes = page.evaluate(individual_js)
                rec["dom_changes"] = len(changes) if isinstance(changes, list) else 0
            except Exception as eval_err:
                # Some patches may crash on some pages (e.g. patch 5 shadow DOM with
                # elements whose parents are already shadow hosts). Record and continue.
                rec["error"] = f"patch eval: {type(eval_err).__name__}: {eval_err}"

            # Settle — let any layout reflow stabilize (matters for patches 3, 9)
            page.wait_for_timeout(800)

            shot_path = task_dir / f"patch_{patch_id:02d}.png"
            page.screenshot(path=str(shot_path), full_page=False)
            rec["screenshot"] = str(shot_path)
            rec["success"] = True
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
            traceback.print_exc(file=sys.stderr)
        finally:
            rec["elapsed_s"] = time.time() - t0
            records.append(rec)
            env.close()

    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://10.0.1.50:7770")
    ap.add_argument("--tasks", nargs="+", default=["23", "4", "29", "132"],
                    help="Task IDs for ablation (default: 23 4 29 132 — one per app)")
    ap.add_argument("--output", default="./data/visual-equivalence/ablation")
    ap.add_argument("--settle-ms", type=int, default=1500)
    args = ap.parse_args()

    setup_wa_env(args.base_url)

    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    t0 = time.time()
    for i, tid in enumerate(args.tasks):
        if tid not in TASK_APP_MAP:
            print(f"WARN: task {tid} not in TASK_APP_MAP, skipping", file=sys.stderr)
            continue
        print(f"\n[{i+1}/{len(args.tasks)}] task {tid} ({TASK_APP_MAP[tid]})", file=sys.stderr)
        try:
            recs = capture_task_ablation(tid, out_dir, settle_ms=args.settle_ms)
            all_records.extend(recs)
        except Exception as e:
            print(f"  FATAL for task {tid}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        # Incremental manifest
        manifest = out_dir / "manifest.json"
        with manifest.open("w") as f:
            json.dump({
                "config": vars(args),
                "patch_descriptions": PATCH_DESCRIPTIONS,
                "records": all_records,
                "elapsed_s": time.time() - t0,
            }, f, indent=2)

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{len(all_records)} captures succeeded in {time.time()-t0:.1f}s",
          file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()

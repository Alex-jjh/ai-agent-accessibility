#!/usr/bin/env python3
"""
Visual Equivalence Smoke Test — Drives browsergym_bridge.py in "captureMode"
to grab base+low screenshots for all 13 experimental tasks at the exact
first-observation state the agent sees.

Pipeline fidelity: this script spawns browsergym_bridge.py as a subprocess
with the same task config (taskId, variantLevel, targetUrl, agentConfig) used
in the real experiments, plus an extra `captureMode.outputPath` directive.
The bridge runs env.reset + login monkey-patches + Plan D injection exactly
as it does for real runs, then writes a screenshot and exits.

Output:
  ./data/visual-equivalence/<task>/base_r<N>.png
  ./data/visual-equivalence/<task>/low_r<N>.png
  ./data/visual-equivalence/manifest.json

Usage (on EC2 with WebArena at 10.0.1.50):
  python3 scripts/smoke-visual-equivalence.py \\
    --base-url http://10.0.1.50:7770 \\
    --reps 3 \\
    --output ./data/visual-equivalence

  # Single-task test
  python3 scripts/smoke-visual-equivalence.py --task 23

Requires: browsergym, playwright, gymnasium, Pillow (same as the experiments).
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()
BRIDGE = REPO_ROOT / "src" / "runner" / "browsergym_bridge.py"

# (task_id, app_name). Matches experiment design — 13 tasks across 4 apps.
TASK_LIST = [
    ("4",   "ecommerce_admin"),
    ("23",  "ecommerce"),
    ("24",  "ecommerce"),
    ("26",  "ecommerce"),
    ("29",  "reddit"),
    ("67",  "reddit"),
    ("41",  "ecommerce_admin"),
    ("94",  "ecommerce_admin"),
    ("132", "gitlab"),
    ("188", "ecommerce"),
    ("198", "ecommerce_admin"),
    ("293", "gitlab"),
    ("308", "gitlab"),
]

APP_PORTS = {
    "ecommerce":       7770,
    "ecommerce_admin": 7780,
    "reddit":          9999,
    "gitlab":          8023,
}


def run_one(task_id: str, app: str, variant: str, base_url: str,
            screenshot_path: pathlib.Path, timeout_s: int = 180) -> dict:
    """Spawn browsergym_bridge in captureMode for a single (task, variant).

    Returns a record with success flag, timing, and any error.
    """
    # Derive target URL from base_url host + app port
    from urllib.parse import urlparse
    p = urlparse(base_url)
    host = p.hostname or "10.0.1.50"
    scheme = p.scheme or "http"
    port = APP_PORTS[app]
    target_url = f"{scheme}://{host}:{port}"

    config = {
        "taskId": task_id,
        "targetUrl": target_url,
        "taskGoal": "",
        "variantLevel": variant,
        "agentConfig": {
            "observationMode": "text-only",  # any non-cua mode works for capture
            "llmBackend": "claude-sonnet",
            "maxSteps": 1,
            "retryCount": 0,
            "retryBackoffMs": 0,
            "temperature": 0,
        },
        "captureMode": {
            "outputPath": str(screenshot_path),
        },
        # Skip vision-only SoM overlay rendering — we want clean screenshots
        "wallClockTimeoutMs": timeout_s * 1000,
    }

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task_id": task_id, "app": app, "variant": variant,
        "screenshot_path": str(screenshot_path), "success": False,
        "error": None, "elapsed_s": None, "url": None, "viewport": None,
    }
    t0 = time.time()

    try:
        # Bridge expects config JSON as argv[1]; we send nothing on stdin
        # (captureMode returns before the agent loop starts, so stdin is unused).
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), json.dumps(config)],
            input="",  # no actions needed
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        # Bridge emits one JSON line per observation; capture mode sends exactly one.
        summary_line = None
        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("captureMode"):
                summary_line = msg
                break
        if summary_line is None:
            record["error"] = f"no capture summary in bridge stdout; stderr tail: {stderr[-500:]}"
        elif summary_line.get("error"):
            record["error"] = f"bridge reported: {summary_line['error']}"
        elif not screenshot_path.exists():
            record["error"] = f"screenshot file missing after capture: {screenshot_path}"
        else:
            record["success"] = True
            record["url"] = summary_line.get("url")
            record["viewport"] = summary_line.get("viewport")
            record["axtreeLen"] = summary_line.get("axtreeLen")
    except subprocess.TimeoutExpired:
        record["error"] = f"timeout after {timeout_s}s"
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)
    finally:
        record["elapsed_s"] = round(time.time() - t0, 1)

    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://10.0.1.50:7770",
                    help="WebArena host+port (used for URL scheme/host extraction)")
    ap.add_argument("--task", default=None,
                    help="Single task to run (numeric id, e.g. '23')")
    ap.add_argument("--variants", nargs="+", default=["base", "low"],
                    help="Variants to capture (default: base low)")
    ap.add_argument("--reps", type=int, default=1,
                    help="Captures per (task, variant). Reps give within-variant variance.")
    ap.add_argument("--output", default="./data/visual-equivalence")
    ap.add_argument("--timeout-s", type=int, default=180,
                    help="Per-capture subprocess timeout")
    args = ap.parse_args()

    if not BRIDGE.exists():
        print(f"ERROR: bridge not found at {BRIDGE}", file=sys.stderr)
        sys.exit(1)

    if args.task:
        tid = args.task.split(":")[-1]
        tasks = [t for t in TASK_LIST if t[0] == tid]
        if not tasks:
            print(f"task {args.task} not in TASK_LIST. Known: {[t[0] for t in TASK_LIST]}",
                  file=sys.stderr)
            sys.exit(1)
    else:
        tasks = TASK_LIST

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    total = len(tasks) * len(args.variants) * args.reps
    done = 0
    t_start = time.time()

    for task_id, app in tasks:
        task_dir = out_dir / task_id
        for variant in args.variants:
            for rep in range(1, args.reps + 1):
                done += 1
                screenshot = task_dir / f"{variant}_r{rep}.png"
                print(f"[{done}/{total}] task={task_id} app={app} variant={variant} "
                      f"rep={rep}", file=sys.stderr)
                rec = run_one(task_id, app, variant, args.base_url, screenshot,
                              timeout_s=args.timeout_s)
                all_records.append(rec)
                print(f"  -> {'OK' if rec['success'] else 'FAIL'} "
                      f"({rec['elapsed_s']}s)"
                      + (f" err={rec['error'][:100]}" if rec['error'] else ""),
                      file=sys.stderr)

                # Incremental manifest for crash recovery
                manifest_path = out_dir / "manifest.json"
                with manifest_path.open("w") as f:
                    json.dump({
                        "records": all_records,
                        "config": {
                            "base_url": args.base_url,
                            "variants": args.variants,
                            "reps": args.reps,
                            "timeout_s": args.timeout_s,
                        },
                        "summary": {
                            "total": total,
                            "done": done,
                            "success": sum(1 for r in all_records if r["success"]),
                            "elapsed_s": round(time.time() - t_start, 1),
                        },
                    }, f, indent=2)

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{total} captures succeeded in {time.time() - t_start:.1f}s",
          file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()

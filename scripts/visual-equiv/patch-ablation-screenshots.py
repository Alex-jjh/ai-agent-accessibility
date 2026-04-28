#!/usr/bin/env python3
"""
Per-Patch Ablation — Drives browsergym_bridge.py in captureMode with
`onlyPatchId` to apply each of the 13 low-variant patches individually and
screenshot the result.

For each (task, patch_id):
  1. Fresh subprocess → bridge does env.reset + login + Plan D registration
  2. bridge loads apply-low-individual.js with window.__ONLY_PATCH_ID = N
  3. bridge waits 1000ms for layout to settle (matters for patches 3, 9)
  4. bridge screenshots and exits

Each patch gets a pristine env.reset so no cross-patch DOM contamination.

Task selection (representative per app — exercise different DOM features):
  ecommerce:23     — product page (nav, header, links, img, form, reviews)
  ecommerce_admin:4 — admin dashboard (nav, landmarks, tables, thead/th, grid)
  reddit:29         — forum listing (many links, headings)
  gitlab:132        — commit browser (tables, landmarks, code)

Usage (on EC2):
  python3 scripts/patch-ablation-screenshots.py \\
    --base-url http://10.0.1.50:7770 \\
    --tasks 23 4 29 132 \\
    --output ./data/visual-equivalence/ablation

Output:
  ./data/visual-equivalence/ablation/<task>/base.png
  ./data/visual-equivalence/ablation/<task>/patch_01.png ... patch_13.png
  ./data/visual-equivalence/ablation/manifest.json
"""

import argparse
import json
import pathlib
import subprocess
import sys
import time
import traceback
from urllib.parse import urlparse

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()
BRIDGE = REPO_ROOT / "src" / "runner" / "browsergym_bridge.py"

TASK_APP_MAP = {
    "4":   "ecommerce_admin",
    "23":  "ecommerce",
    "24":  "ecommerce",
    "26":  "ecommerce",
    "29":  "reddit",
    "67":  "reddit",
    "41":  "ecommerce_admin",
    "94":  "ecommerce_admin",
    "132": "gitlab",
    "188": "ecommerce",
    "198": "ecommerce_admin",
    "293": "gitlab",
    "308": "gitlab",
}

APP_PORTS = {
    "ecommerce":       7770,
    "ecommerce_admin": 7780,
    "reddit":          9999,
    "gitlab":          8023,
}

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


def run_one(task_id: str, app: str, base_url: str, out_path: pathlib.Path,
            patch_id: int | None, variant_level: str,
            timeout_s: int = 180) -> dict:
    """Run the bridge once to capture a single screenshot.

    - patch_id=None, variant_level="base" → screenshot of unmodified page
    - patch_id=N, variant_level="base"   → screenshot with ONLY patch N applied
      (via apply-low-individual.js, not the full low bundle)
    """
    p = urlparse(base_url)
    host = p.hostname or "10.0.1.50"
    scheme = p.scheme or "http"
    port = APP_PORTS[app]
    target_url = f"{scheme}://{host}:{port}"

    config = {
        "taskId": task_id,
        "targetUrl": target_url,
        "taskGoal": "",
        "variantLevel": variant_level,  # "base" means no full-low injection
        "agentConfig": {
            "observationMode": "text-only",
            "llmBackend": "claude-sonnet",
            "maxSteps": 1,
            "retryCount": 0,
            "retryBackoffMs": 0,
            "temperature": 0,
        },
        "captureMode": {
            "outputPath": str(out_path),
            "onlyPatchId": patch_id,  # None for base, 1..13 for ablation
        },
        "wallClockTimeoutMs": timeout_s * 1000,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "task_id": task_id, "app": app, "patch_id": patch_id or 0,
        "patch_name": "base" if patch_id is None else PATCH_DESCRIPTIONS.get(patch_id, ""),
        "screenshot": str(out_path), "success": False, "error": None,
        "elapsed_s": None, "url": None, "viewport": None,
    }
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), json.dumps(config)],
            input="",
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
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
            rec["error"] = f"no capture summary; stderr tail: {stderr[-500:]}"
        elif summary_line.get("error"):
            rec["error"] = f"bridge reported: {summary_line['error']}"
        elif not out_path.exists():
            rec["error"] = f"screenshot missing after capture: {out_path}"
        else:
            rec["success"] = True
            rec["url"] = summary_line.get("url")
            rec["viewport"] = summary_line.get("viewport")
    except subprocess.TimeoutExpired:
        rec["error"] = f"timeout after {timeout_s}s"
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)
    finally:
        rec["elapsed_s"] = round(time.time() - t0, 1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://10.0.1.50:7770")
    ap.add_argument("--tasks", nargs="+", default=["23", "4", "29", "132"],
                    help="Task IDs for ablation (default: 23 4 29 132 — one per app)")
    ap.add_argument("--patches", nargs="+", type=int, default=list(range(1, 14)),
                    help="Patch IDs to ablate (default: 1..13)")
    ap.add_argument("--output", default="./data/visual-equivalence/ablation")
    ap.add_argument("--timeout-s", type=int, default=180)
    args = ap.parse_args()

    if not BRIDGE.exists():
        print(f"ERROR: bridge not found at {BRIDGE}", file=sys.stderr)
        sys.exit(1)

    out_dir = pathlib.Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    t_start = time.time()
    total = len(args.tasks) * (1 + len(args.patches))
    done = 0

    for i, tid in enumerate(args.tasks):
        if tid not in TASK_APP_MAP:
            print(f"WARN: task {tid} not in TASK_APP_MAP, skipping", file=sys.stderr)
            continue
        app = TASK_APP_MAP[tid]
        task_dir = out_dir / tid

        # Capture base (unmodified) first — this is the reference image
        done += 1
        print(f"\n[{done}/{total}] task={tid} app={app} variant=base (reference)",
              file=sys.stderr)
        base_path = task_dir / "base.png"
        rec = run_one(tid, app, args.base_url, base_path,
                      patch_id=None, variant_level="base",
                      timeout_s=args.timeout_s)
        all_records.append(rec)
        print(f"  -> {'OK' if rec['success'] else 'FAIL'} ({rec['elapsed_s']}s)"
              + (f" err={rec['error'][:80]}" if rec['error'] else ""),
              file=sys.stderr)

        # Save incremental manifest
        _save_manifest(out_dir, all_records, args, t_start)

        # Only proceed with ablations if base capture succeeded
        if not rec["success"]:
            print(f"  WARN: skipping ablation for task {tid} (base capture failed)",
                  file=sys.stderr)
            done += len(args.patches)
            continue

        for patch_id in args.patches:
            done += 1
            print(f"[{done}/{total}] task={tid} patch={patch_id}: "
                  f"{PATCH_DESCRIPTIONS.get(patch_id, '?')}", file=sys.stderr)
            patch_path = task_dir / f"patch_{patch_id:02d}.png"
            rec = run_one(tid, app, args.base_url, patch_path,
                          patch_id=patch_id, variant_level="base",
                          timeout_s=args.timeout_s)
            all_records.append(rec)
            print(f"  -> {'OK' if rec['success'] else 'FAIL'} ({rec['elapsed_s']}s)"
                  + (f" err={rec['error'][:80]}" if rec['error'] else ""),
                  file=sys.stderr)
            _save_manifest(out_dir, all_records, args, t_start)

    ok = sum(1 for r in all_records if r["success"])
    print(f"\nDone. {ok}/{len(all_records)} captures succeeded in "
          f"{time.time() - t_start:.1f}s", file=sys.stderr)
    print(f"Manifest: {out_dir / 'manifest.json'}", file=sys.stderr)
    sys.exit(0 if ok > 0 else 1)


def _save_manifest(out_dir, records, args, t_start):
    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump({
            "config": vars(args),
            "patch_descriptions": PATCH_DESCRIPTIONS,
            "records": records,
            "elapsed_s": round(time.time() - t_start, 1),
        }, f, indent=2)


if __name__ == "__main__":
    main()

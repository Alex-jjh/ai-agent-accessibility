#!/usr/bin/env python3
"""
Visual Equivalence Analysis — Reads screenshots captured by
scripts/smoke-visual-equivalence.py and scripts/patch-ablation-screenshots.py
and computes pixel-level similarity metrics.

Metrics per pair (base vs variant or base vs single-patch):
  - SSIM (structural similarity, grayscale): 0-1, higher = more similar
  - pHash hamming distance: 0-64, lower = more similar
  - MAD: mean absolute difference in RGB, normalized 0-1
  - pct_changed: fraction of pixels with any channel diff > threshold

Classification for Group A/B/C (§6 Limitations in paper):
  A (visually identical): SSIM >= 0.98 AND pHash <= 5 AND MAD < 0.01
  B (visible change):     SSIM < 0.95  OR  pHash > 10  OR  MAD > 0.05
  C (identical but broken): A threshold met AND patch_id == 11
                            (the "blue underlined link but href deleted" patch)

Usage:
  # Analyze all-patches comparison
  python3 analysis/visual_equivalence_analysis.py \\
      --mode aggregate \\
      --input ./data/visual-equivalence \\
      --output ./results/visual-equivalence

  # Analyze per-patch ablation
  python3 analysis/visual_equivalence_analysis.py \\
      --mode ablation \\
      --input ./data/visual-equivalence/ablation \\
      --output ./results/visual-equivalence

Output:
  ./results/visual-equivalence/per_pair_metrics.csv
  ./results/visual-equivalence/per_patch_metrics.csv (ablation mode)
  ./results/visual-equivalence/diff_masks/<pair>.png (optional)
  ./results/visual-equivalence/report.md
"""

import argparse
import json
import pathlib
import sys
from typing import Optional

import numpy as np

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    from skimage.metrics import structural_similarity as ssim_fn
except ImportError:
    print("ERROR: scikit-image not installed. pip install scikit-image", file=sys.stderr)
    sys.exit(1)

try:
    import imagehash
    HAVE_IMAGEHASH = True
except ImportError:
    HAVE_IMAGEHASH = False
    print("WARN: imagehash not installed. pip install ImageHash for pHash metric. "
          "Continuing without it.", file=sys.stderr)

# -----------------------------------------------------------------------------
# Core similarity functions
# -----------------------------------------------------------------------------

def load_rgb(path: pathlib.Path) -> np.ndarray:
    """Load PNG as HxWx3 uint8 RGB array."""
    img = Image.open(path).convert("RGB")
    return np.asarray(img)


def match_dims(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """If two images differ in size, crop to common region so metrics are computable.
    Prefer to crop to the minimum size; log a warning if they differ significantly."""
    if a.shape == b.shape:
        return a, b
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    return a[:h, :w], b[:h, :w]


def compute_pair_metrics(base_path: pathlib.Path, variant_path: pathlib.Path,
                         diff_mask_out: Optional[pathlib.Path] = None,
                         diff_threshold: int = 10) -> dict:
    """Compute SSIM, pHash, MAD, pct_changed for a (base, variant) screenshot pair."""
    if not base_path.exists() or not variant_path.exists():
        return {"error": f"missing: base={base_path.exists()}, variant={variant_path.exists()}"}

    base_rgb = load_rgb(base_path)
    var_rgb = load_rgb(variant_path)
    size_mismatch = base_rgb.shape != var_rgb.shape
    base_rgb, var_rgb = match_dims(base_rgb, var_rgb)

    # SSIM on grayscale luminance
    base_gray = np.asarray(Image.fromarray(base_rgb).convert("L"))
    var_gray = np.asarray(Image.fromarray(var_rgb).convert("L"))
    ssim = ssim_fn(base_gray, var_gray, data_range=255)

    # MAD (mean absolute difference across all RGB channels, normalized 0-1)
    abs_diff = np.abs(base_rgb.astype(np.int32) - var_rgb.astype(np.int32))
    mad = float(abs_diff.mean() / 255.0)

    # Per-pixel changed mask: any channel exceeds threshold
    max_chan_diff = abs_diff.max(axis=2)
    changed_mask = max_chan_diff > diff_threshold
    pct_changed = float(changed_mask.mean())

    result = {
        "ssim": float(ssim),
        "mad": mad,
        "pct_changed": pct_changed,
        "base_shape": list(base_rgb.shape),
        "var_shape": list(var_rgb.shape),
        "size_mismatch": bool(size_mismatch),
    }

    if HAVE_IMAGEHASH:
        try:
            ph_base = imagehash.phash(Image.fromarray(base_rgb))
            ph_var = imagehash.phash(Image.fromarray(var_rgb))
            result["phash_distance"] = int(ph_base - ph_var)
        except Exception as e:
            result["phash_error"] = str(e)

    # Optional diff mask export
    if diff_mask_out is not None:
        diff_mask_out.parent.mkdir(parents=True, exist_ok=True)
        mask_rgb = np.zeros_like(base_rgb)
        mask_rgb[changed_mask] = [255, 0, 255]  # magenta where changed
        blended = (0.4 * base_rgb + 0.6 * mask_rgb).astype(np.uint8)
        Image.fromarray(blended).save(diff_mask_out)
        result["diff_mask_path"] = str(diff_mask_out)

    return result


def classify_group(metrics: dict, patch_id: int = -1) -> str:
    """Classify a pair as Group A / B / C / ambiguous based on metrics."""
    if "error" in metrics:
        return "error"
    ssim = metrics.get("ssim", 0)
    mad = metrics.get("mad", 1)
    phash = metrics.get("phash_distance", 99)  # treat missing as "large"

    visually_identical = ssim >= 0.98 and mad < 0.01 and phash <= 5
    visible_change = ssim < 0.95 or mad > 0.05 or phash > 10

    if visually_identical:
        if patch_id == 11:
            return "C"  # visually identical + known functional breakage (link→span)
        return "A"
    if visible_change:
        return "B"
    return "ambiguous"


# -----------------------------------------------------------------------------
# Aggregate mode: 13 tasks × {base, low}
# -----------------------------------------------------------------------------

def run_aggregate(input_dir: pathlib.Path, output_dir: pathlib.Path,
                  save_masks: bool) -> list[dict]:
    """For each task in input_dir, pair its base screenshot with its low screenshot
    and compute metrics. Handles multiple reps by averaging pair metrics per task."""
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run smoke-visual-equivalence.py first.",
              file=sys.stderr)
        return []
    with manifest_path.open() as f:
        manifest = json.load(f)

    # Group screenshots by task and variant
    records_by_task: dict[str, dict[str, list[str]]] = {}
    for r in manifest["records"]:
        if not r.get("success") or not r.get("screenshot_path"):
            continue
        tid = r["task_id"]
        variant = r["variant"]
        records_by_task.setdefault(tid, {}).setdefault(variant, []).append(r["screenshot_path"])

    pair_records = []
    diff_dir = output_dir / "diff_masks"

    for tid in sorted(records_by_task.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        variants = records_by_task[tid]
        if "base" not in variants or "low" not in variants:
            print(f"SKIP {tid}: missing base or low", file=sys.stderr)
            continue
        # Pair up rep 1 of each variant; extend to more reps if multiple present
        n_pairs = min(len(variants["base"]), len(variants["low"]))
        for i in range(n_pairs):
            base_p = pathlib.Path(variants["base"][i])
            low_p = pathlib.Path(variants["low"][i])
            mask_out = diff_dir / f"task_{tid}_r{i+1}.png" if save_masks else None
            print(f"  analyzing task {tid} rep {i+1}: {base_p.name} vs {low_p.name}",
                  file=sys.stderr)
            m = compute_pair_metrics(base_p, low_p, diff_mask_out=mask_out)
            m.update({
                "task_id": tid, "rep": i + 1,
                "base_path": str(base_p), "variant_path": str(low_p),
                "group": classify_group(m, patch_id=-1),
            })
            pair_records.append(m)

    return pair_records


# -----------------------------------------------------------------------------
# Ablation mode: 13 patches individually per task
# -----------------------------------------------------------------------------

def run_ablation(input_dir: pathlib.Path, output_dir: pathlib.Path,
                 save_masks: bool) -> list[dict]:
    """For each task subdirectory in input_dir with base.png + patch_01..13.png,
    compute per-patch metrics against base."""
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run patch-ablation-screenshots.py first.",
              file=sys.stderr)
        return []
    with manifest_path.open() as f:
        manifest = json.load(f)

    # Group by task
    task_records: dict[str, dict] = {}
    for r in manifest["records"]:
        if not r.get("success"):
            continue
        tid = r["task_id"]
        pid = r["patch_id"]
        task_records.setdefault(tid, {})[pid] = r

    pair_records = []
    diff_dir = output_dir / "diff_masks" / "ablation"

    for tid in sorted(task_records.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        task_data = task_records[tid]
        base_rec = task_data.get(0)
        if not base_rec:
            print(f"SKIP {tid}: no base capture", file=sys.stderr)
            continue
        base_path = pathlib.Path(base_rec["screenshot"])
        for pid in range(1, 14):
            patch_rec = task_data.get(pid)
            if not patch_rec or not patch_rec.get("screenshot"):
                print(f"  SKIP task {tid} patch {pid}: no capture", file=sys.stderr)
                continue
            patch_path = pathlib.Path(patch_rec["screenshot"])
            mask_out = diff_dir / f"task_{tid}_patch_{pid:02d}.png" if save_masks else None
            m = compute_pair_metrics(base_path, patch_path, diff_mask_out=mask_out)
            m.update({
                "task_id": tid, "patch_id": pid,
                "patch_name": patch_rec.get("patch_name", ""),
                "dom_changes": patch_rec.get("dom_changes", 0),
                "base_path": str(base_path), "variant_path": str(patch_path),
                "group": classify_group(m, patch_id=pid),
            })
            pair_records.append(m)

    return pair_records


# -----------------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------------

def write_csv(records: list[dict], path: pathlib.Path, mode: str) -> None:
    import csv
    if not records:
        return
    # Pick columns based on mode
    if mode == "ablation":
        cols = ["task_id", "patch_id", "patch_name", "dom_changes", "group",
                "ssim", "mad", "pct_changed", "phash_distance",
                "base_shape", "var_shape", "size_mismatch"]
    else:
        cols = ["task_id", "rep", "group",
                "ssim", "mad", "pct_changed", "phash_distance",
                "base_shape", "var_shape", "size_mismatch"]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            w.writerow([r.get(c, "") for c in cols])


def write_report(records: list[dict], path: pathlib.Path, mode: str) -> None:
    lines = []
    lines.append(f"# Visual Equivalence Analysis — mode={mode}\n")
    lines.append(f"Generated from {len(records)} pairs.\n")

    if mode == "ablation":
        # Per-task per-patch table
        by_task: dict[str, list[dict]] = {}
        for r in records:
            by_task.setdefault(r["task_id"], []).append(r)
        # Aggregate across tasks
        lines.append("## Group classification per patch (averaged across tasks)\n")
        lines.append("| Patch | Description | Mean SSIM | Mean MAD | Mean pHash | Group (mode) |")
        lines.append("|-------|-------------|-----------|----------|------------|--------------|")
        agg: dict[int, list[dict]] = {}
        for r in records:
            agg.setdefault(r["patch_id"], []).append(r)
        for pid in sorted(agg.keys()):
            rs = agg[pid]
            mean_ssim = np.mean([r.get("ssim", 0) for r in rs])
            mean_mad = np.mean([r.get("mad", 0) for r in rs])
            phash_vals = [r.get("phash_distance", -1) for r in rs if isinstance(r.get("phash_distance"), int)]
            mean_phash = np.mean(phash_vals) if phash_vals else -1
            # Mode group (most common classification across tasks)
            groups = [r.get("group", "?") for r in rs]
            mode_group = max(set(groups), key=groups.count) if groups else "?"
            patch_name = rs[0].get("patch_name", "")
            lines.append(f"| {pid} | {patch_name} | {mean_ssim:.4f} | {mean_mad:.4f} | "
                         f"{mean_phash:.1f} | {mode_group} |")

        # Group summary
        lines.append("\n## Group distribution\n")
        all_groups = [r["group"] for r in records]
        for g in ["A", "B", "C", "ambiguous", "error"]:
            n = all_groups.count(g)
            lines.append(f"- Group {g}: {n} / {len(all_groups)} pairs "
                         f"({100 * n / max(len(all_groups), 1):.1f}%)")

        # Per task
        lines.append("\n## Per-task details\n")
        for tid in sorted(by_task.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            lines.append(f"\n### Task {tid}\n")
            lines.append("| Patch | SSIM | MAD | pHash | pct changed | Group |")
            lines.append("|-------|------|-----|-------|-------------|-------|")
            for r in sorted(by_task[tid], key=lambda x: x["patch_id"]):
                lines.append(f"| {r['patch_id']:>2} | {r.get('ssim', 0):.4f} | "
                             f"{r.get('mad', 0):.4f} | "
                             f"{r.get('phash_distance', 'N/A')} | "
                             f"{r.get('pct_changed', 0):.2%} | {r.get('group', '?')} |")

    else:  # aggregate
        lines.append("## Per-task base-vs-low aggregate comparison\n")
        lines.append("| Task | Rep | SSIM | MAD | pHash | pct changed | Group |")
        lines.append("|------|-----|------|-----|-------|-------------|-------|")
        for r in records:
            lines.append(f"| {r['task_id']} | {r.get('rep', 1)} | "
                         f"{r.get('ssim', 0):.4f} | {r.get('mad', 0):.4f} | "
                         f"{r.get('phash_distance', 'N/A')} | "
                         f"{r.get('pct_changed', 0):.2%} | {r.get('group', '?')} |")
        lines.append("\n## Summary\n")
        if records:
            ssims = [r["ssim"] for r in records if "ssim" in r]
            lines.append(f"- Mean SSIM (base vs low, all tasks): {np.mean(ssims):.4f}")
            lines.append(f"- Min SSIM: {min(ssims):.4f}  Max SSIM: {max(ssims):.4f}")
            lines.append(f"- Tasks with SSIM >= 0.85: "
                         f"{sum(1 for s in ssims if s >= 0.85)} / {len(ssims)}")
        all_groups = [r["group"] for r in records]
        for g in ["A", "B", "C", "ambiguous", "error"]:
            n = all_groups.count(g)
            lines.append(f"- Group {g}: {n} / {len(all_groups)}")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["aggregate", "ablation"], required=True,
                    help="aggregate: 13-task base vs low; ablation: 13 patches individually")
    ap.add_argument("--input", required=True,
                    help="Directory with screenshots + manifest.json")
    ap.add_argument("--output", default="./results/visual-equivalence")
    ap.add_argument("--save-masks", action="store_true",
                    help="Save per-pair diff mask PNGs (slow, large disk)")
    args = ap.parse_args()

    input_dir = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "aggregate":
        records = run_aggregate(input_dir, output_dir, save_masks=args.save_masks)
        csv_path = output_dir / "per_pair_metrics.csv"
    else:
        records = run_ablation(input_dir, output_dir, save_masks=args.save_masks)
        csv_path = output_dir / "per_patch_metrics.csv"

    write_csv(records, csv_path, mode=args.mode)
    write_report(records, output_dir / "report.md", mode=args.mode)

    print(f"Analyzed {len(records)} pairs. Results: {output_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()

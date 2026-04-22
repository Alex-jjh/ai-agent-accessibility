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

# LPIPS (perceptual similarity, correlates with human judgment). Loaded lazily
# because torch + lpips download is heavy (~400MB model).
_LPIPS_MODEL = None
_LPIPS_DEVICE = None

def _get_lpips():
    """Load LPIPS model on first use, or return None if unavailable."""
    global _LPIPS_MODEL, _LPIPS_DEVICE
    if _LPIPS_MODEL is not None:
        return _LPIPS_MODEL, _LPIPS_DEVICE
    try:
        import torch
        import lpips as _lpips_mod
        _LPIPS_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _LPIPS_MODEL = _lpips_mod.LPIPS(net="alex", verbose=False).to(_LPIPS_DEVICE)
        _LPIPS_MODEL.eval()
        return _LPIPS_MODEL, _LPIPS_DEVICE
    except ImportError:
        print("WARN: lpips not installed. pip install lpips torch for "
              "perceptual similarity. Continuing without it.", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"WARN: LPIPS load failed ({e}); continuing without it.",
              file=sys.stderr)
        return None, None


def compute_lpips(base_rgb: np.ndarray, var_rgb: np.ndarray) -> Optional[float]:
    """Compute LPIPS distance. Returns None if model unavailable.

    Range: 0.0 (identical) to ~1.0 (very different). Human-perceptual.
    """
    model, device = _get_lpips()
    if model is None:
        return None
    import torch
    # LPIPS expects [-1, 1] normalized tensors, shape [N, 3, H, W]
    def _to_tensor(arr):
        t = torch.from_numpy(arr).float().permute(2, 0, 1).unsqueeze(0)
        t = (t / 127.5) - 1.0
        return t.to(device)
    with torch.no_grad():
        d = model(_to_tensor(base_rgb), _to_tensor(var_rgb))
    return float(d.item())


# =============================================================================
# Pre-registered thresholds (P1-2 reviewer fix).
#
# Fixed before Phase B/C runs to avoid "thresholds chosen to fit results"
# critique. Values are conservative defaults from the literature; they will
# be REPLACED with data-driven thresholds derived from Phase B0 base-vs-base
# baseline noise distribution (see derive_thresholds_from_baseline()).
# =============================================================================
PREREGISTERED_THRESHOLDS = {
    # Default thresholds used before baseline noise is known. After Phase B0
    # runs, call derive_thresholds_from_baseline(baseline_pairs) to get the
    # data-driven versions.
    "group_a_ssim_min": 0.98,       # ≥ "visually identical" (pre-baseline)
    "group_a_mad_max": 0.01,
    "group_a_phash_max": 5,
    "group_a_lpips_max": 0.05,      # LPIPS < 0.05 is human-imperceptible
    "group_b_ssim_max": 0.95,       # < "visible change"
    "group_b_mad_min": 0.05,
    "group_b_phash_min": 10,
    "group_b_lpips_min": 0.15,      # LPIPS > 0.15 is clearly different
    "source": "preregistered_default",
}


def derive_thresholds_from_baseline(baseline_metrics: list[dict]) -> dict:
    """Build data-driven thresholds from the base-vs-base2 noise distribution.

    Group A floor = μ(baseline SSIM) - 2σ, i.e. ≥98% of intrinsic noise
    would be classified as Group A. Same idea for MAD/pHash/LPIPS.
    """
    def _stats(key):
        vals = [m[key] for m in baseline_metrics
                if isinstance(m.get(key), (int, float))]
        if not vals:
            return None
        arr = np.asarray(vals, dtype=float)
        return {"mean": float(arr.mean()),
                "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
                "p05": float(np.percentile(arr, 5)),
                "p95": float(np.percentile(arr, 95)),
                "n": len(arr)}

    ssim_s = _stats("ssim")
    mad_s = _stats("mad")
    ph_s = _stats("phash_distance")
    lp_s = _stats("lpips")

    t = dict(PREREGISTERED_THRESHOLDS)
    t["source"] = "derived_from_baseline"
    t["baseline_stats"] = {
        "ssim": ssim_s, "mad": mad_s, "phash": ph_s, "lpips": lp_s
    }
    if ssim_s:
        t["group_a_ssim_min"] = max(0.90, ssim_s["mean"] - 2 * ssim_s["std"])
        t["group_b_ssim_max"] = max(0.80, ssim_s["mean"] - 4 * ssim_s["std"])
    if mad_s:
        t["group_a_mad_max"] = mad_s["mean"] + 2 * mad_s["std"]
        t["group_b_mad_min"] = mad_s["mean"] + 4 * mad_s["std"]
    if ph_s:
        t["group_a_phash_max"] = ph_s["mean"] + 2 * ph_s["std"]
        t["group_b_phash_min"] = ph_s["mean"] + 4 * ph_s["std"]
    if lp_s:
        t["group_a_lpips_max"] = lp_s["mean"] + 2 * lp_s["std"]
        t["group_b_lpips_min"] = lp_s["mean"] + 4 * lp_s["std"]
    return t

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

    # LPIPS (perceptual similarity); None if library unavailable
    lp = compute_lpips(base_rgb, var_rgb)
    if lp is not None:
        result["lpips"] = lp

    # Optional diff mask export
    if diff_mask_out is not None:
        diff_mask_out.parent.mkdir(parents=True, exist_ok=True)
        mask_rgb = np.zeros_like(base_rgb)
        mask_rgb[changed_mask] = [255, 0, 255]  # magenta where changed
        blended = (0.4 * base_rgb + 0.6 * mask_rgb).astype(np.uint8)
        Image.fromarray(blended).save(diff_mask_out)
        result["diff_mask_path"] = str(diff_mask_out)

    return result


def classify_group(metrics: dict, patch_id: int = -1,
                   thresholds: Optional[dict] = None) -> str:
    """Classify a pair as Group A / B / C / ambiguous based on metrics.

    Uses pre-registered or baseline-derived thresholds (see
    PREREGISTERED_THRESHOLDS). Group C = visually identical (Group A) AND
    patch_id indicates a functional-breakage patch (11 = link→span).
    """
    if "error" in metrics:
        return "error"
    t = thresholds or PREREGISTERED_THRESHOLDS
    ssim = metrics.get("ssim", 0)
    mad = metrics.get("mad", 1)
    phash = metrics.get("phash_distance", 99)
    lpips = metrics.get("lpips", None)

    # All-metrics AND for Group A (visually identical)
    visually_identical = (
        ssim >= t["group_a_ssim_min"]
        and mad < t["group_a_mad_max"]
        and phash <= t["group_a_phash_max"]
        and (lpips is None or lpips <= t["group_a_lpips_max"])
    )
    # Any-metric OR for Group B (visible change)
    visible_change = (
        ssim < t["group_b_ssim_max"]
        or mad > t["group_b_mad_min"]
        or phash > t["group_b_phash_min"]
        or (lpips is not None and lpips > t["group_b_lpips_min"])
    )

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
                  save_masks: bool) -> tuple[list[dict], list[dict], dict]:
    """Pair screenshots and compute metrics.

    Supports two manifest formats:
    1. Old env.reset capture (task_id + screenshot_path)   — legacy
    2. URL-replay format (url + slug + screenshot)         — current (P0-2)

    In URL-replay mode, returns THREE lists of pair metrics:
       (base_vs_low, base_vs_base2, derived_thresholds)
    so the caller can (a) compare base-vs-low to the baseline noise
    distribution statistically and (b) derive data-driven thresholds.

    In legacy mode, base_vs_base2 is [] and thresholds falls back to
    PREREGISTERED_THRESHOLDS.
    """
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run replay-url-screenshots.py first.",
              file=sys.stderr)
        return [], [], dict(PREREGISTERED_THRESHOLDS)
    with manifest_path.open() as f:
        manifest = json.load(f)

    records = manifest.get("records", [])
    if not records:
        return [], [], dict(PREREGISTERED_THRESHOLDS)

    # Detect manifest format
    is_url_replay = "slug" in records[0] or "url" in records[0]

    if is_url_replay:
        return _run_aggregate_url_replay(records, output_dir, save_masks)
    return _run_aggregate_legacy(records, output_dir, save_masks)


def _run_aggregate_url_replay(records: list[dict], output_dir: pathlib.Path,
                              save_masks: bool) -> tuple[list[dict], list[dict], dict]:
    """Pair captures for URL-replay manifest format.

    For each slug: base ↔ low (primary) and base ↔ base2 (baseline noise).
    """
    by_slug: dict[str, dict[str, dict]] = {}
    for r in records:
        if not r.get("success") or not r.get("screenshot"):
            continue
        if r.get("session_lost"):
            continue  # exclude session-lost captures (P0-3)
        # Prefer captures after re-login if both present
        key = (r["slug"], r["variant"])
        existing = by_slug.setdefault(r["slug"], {}).get(r["variant"])
        if existing is None or r.get("after_relogin"):
            by_slug[r["slug"]][r["variant"]] = r

    diff_dir = output_dir / "diff_masks"
    base_vs_low: list[dict] = []
    base_vs_base2: list[dict] = []

    for slug in sorted(by_slug.keys()):
        variants = by_slug[slug]
        base = variants.get("base")
        if base is None:
            print(f"SKIP {slug}: missing base", file=sys.stderr)
            continue

        # Primary pair: base vs low
        low = variants.get("low")
        if low is not None:
            mask_out = diff_dir / f"{slug}__base_vs_low.png" if save_masks else None
            m = compute_pair_metrics(pathlib.Path(base["screenshot"]),
                                     pathlib.Path(low["screenshot"]),
                                     diff_mask_out=mask_out)
            m.update({
                "slug": slug, "app": base.get("app", ""),
                "url": base.get("url", ""),
                "pair": "base_vs_low",
                "base_path": base["screenshot"],
                "variant_path": low["screenshot"],
            })
            base_vs_low.append(m)

        # Baseline pair: base vs base2 (P0-2)
        base2 = variants.get("base2")
        if base2 is not None:
            m = compute_pair_metrics(pathlib.Path(base["screenshot"]),
                                     pathlib.Path(base2["screenshot"]))
            m.update({
                "slug": slug, "app": base.get("app", ""),
                "url": base.get("url", ""),
                "pair": "base_vs_base2",
                "base_path": base["screenshot"],
                "variant_path": base2["screenshot"],
            })
            base_vs_base2.append(m)

    # Derive thresholds from baseline (or fall back to pre-registered)
    if base_vs_base2:
        thresholds = derive_thresholds_from_baseline(base_vs_base2)
        print(f"\n[thresholds] derived from {len(base_vs_base2)} baseline pairs:",
              file=sys.stderr)
        print(f"  Group A: ssim≥{thresholds['group_a_ssim_min']:.4f}, "
              f"mad<{thresholds['group_a_mad_max']:.4f}, "
              f"phash≤{thresholds['group_a_phash_max']:.1f}, "
              f"lpips≤{thresholds['group_a_lpips_max']:.4f}",
              file=sys.stderr)
        print(f"  Group B: ssim<{thresholds['group_b_ssim_max']:.4f}, "
              f"mad>{thresholds['group_b_mad_min']:.4f}, "
              f"phash>{thresholds['group_b_phash_min']:.1f}, "
              f"lpips>{thresholds['group_b_lpips_min']:.4f}",
              file=sys.stderr)
    else:
        thresholds = dict(PREREGISTERED_THRESHOLDS)
        print("[thresholds] no baseline pairs found; using pre-registered",
              file=sys.stderr)

    # Classify using derived thresholds
    for m in base_vs_low:
        m["group"] = classify_group(m, patch_id=-1, thresholds=thresholds)
    for m in base_vs_base2:
        m["group"] = classify_group(m, patch_id=-1, thresholds=thresholds)

    return base_vs_low, base_vs_base2, thresholds


def _run_aggregate_legacy(records: list[dict], output_dir: pathlib.Path,
                          save_masks: bool) -> tuple[list[dict], list[dict], dict]:
    """Legacy per-task manifest format (pre-URL-replay)."""
    records_by_task: dict[str, dict[str, list[str]]] = {}
    for r in records:
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
        n_pairs = min(len(variants["base"]), len(variants["low"]))
        for i in range(n_pairs):
            base_p = pathlib.Path(variants["base"][i])
            low_p = pathlib.Path(variants["low"][i])
            mask_out = diff_dir / f"task_{tid}_r{i+1}.png" if save_masks else None
            m = compute_pair_metrics(base_p, low_p, diff_mask_out=mask_out)
            m.update({
                "task_id": tid, "rep": i + 1,
                "base_path": str(base_p), "variant_path": str(low_p),
                "group": classify_group(m, patch_id=-1),
            })
            pair_records.append(m)

    return pair_records, [], dict(PREREGISTERED_THRESHOLDS)


# -----------------------------------------------------------------------------
# Ablation mode: 13 patches individually per task
# -----------------------------------------------------------------------------

def run_ablation(input_dir: pathlib.Path, output_dir: pathlib.Path,
                 save_masks: bool,
                 thresholds: Optional[dict] = None) -> list[dict]:
    """For each URL/task subdirectory in input_dir with base.png +
    patch_01..13.png, compute per-patch metrics against base.

    If `thresholds` is given (e.g. derived from Phase B0 baseline), use them
    for Group A/B/C classification. Otherwise fall back to pre-registered.
    """
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run replay-url-patch-ablation.py first.",
              file=sys.stderr)
        return []
    with manifest_path.open() as f:
        manifest = json.load(f)

    t = thresholds or PREREGISTERED_THRESHOLDS

    records = manifest.get("records", [])
    # New URL-replay format uses 'slug'; legacy uses 'task_id'
    key_field = "slug" if records and "slug" in records[0] else "task_id"

    task_records: dict[str, dict] = {}
    for r in records:
        if not r.get("success"):
            continue
        key = r[key_field]
        pid = r["patch_id"]
        task_records.setdefault(key, {})[pid] = r

    pair_records = []
    diff_dir = output_dir / "diff_masks" / "ablation"

    for key in sorted(task_records.keys()):
        task_data = task_records[key]
        base_rec = task_data.get(0)
        if not base_rec:
            print(f"SKIP {key}: no base capture", file=sys.stderr)
            continue
        base_path = pathlib.Path(base_rec["screenshot"])
        for pid in range(1, 14):
            patch_rec = task_data.get(pid)
            if not patch_rec or not patch_rec.get("screenshot"):
                print(f"  SKIP {key} patch {pid}: no capture", file=sys.stderr)
                continue
            patch_path = pathlib.Path(patch_rec["screenshot"])
            mask_out = diff_dir / f"{key}_patch_{pid:02d}.png" if save_masks else None
            m = compute_pair_metrics(base_path, patch_path, diff_mask_out=mask_out)
            m.update({
                key_field: key, "patch_id": pid,
                "patch_name": patch_rec.get("patch_name", ""),
                "dom_changes": patch_rec.get("dom_changes", 0),
                "app": patch_rec.get("app", ""),
                "base_path": str(base_path), "variant_path": str(patch_path),
                "group": classify_group(m, patch_id=pid, thresholds=t),
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
    # Pick columns based on mode. Support both old (task_id) and new (slug) keys.
    sample = records[0]
    base_key = "slug" if "slug" in sample else "task_id"
    if mode == "ablation":
        cols = [base_key, "app", "patch_id", "patch_name", "dom_changes", "group",
                "ssim", "lpips", "mad", "pct_changed", "phash_distance",
                "base_shape", "var_shape", "size_mismatch"]
    elif mode == "baseline":
        cols = [base_key, "app", "pair", "group",
                "ssim", "lpips", "mad", "pct_changed", "phash_distance",
                "base_shape", "var_shape", "size_mismatch"]
    else:  # aggregate
        cols = [base_key, "app", "url", "group",
                "ssim", "lpips", "mad", "pct_changed", "phash_distance",
                "base_shape", "var_shape", "size_mismatch"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            w.writerow([r.get(c, "") for c in cols])


def _baseline_summary_md(baseline_pairs: list[dict], thresholds: dict) -> list[str]:
    """Produce a markdown block summarizing base-vs-base2 noise distribution."""
    lines = ["\n## Baseline noise distribution (base vs base2, P0-2)\n"]
    if not baseline_pairs:
        lines.append("_No baseline pairs available._\n")
        return lines
    ssims = [r["ssim"] for r in baseline_pairs if "ssim" in r]
    mads = [r["mad"] for r in baseline_pairs if "mad" in r]
    phashes = [r["phash_distance"] for r in baseline_pairs
               if isinstance(r.get("phash_distance"), int)]
    lpips_vals = [r["lpips"] for r in baseline_pairs if "lpips" in r]

    def _s(label, vals, fmt=".4f"):
        if not vals:
            return f"- {label}: _no data_"
        a = np.asarray(vals, dtype=float)
        return (f"- **{label}**: n={len(a)}, mean={a.mean():{fmt}}, "
                f"std={a.std(ddof=1):{fmt}}, "
                f"p05={np.percentile(a,5):{fmt}}, p95={np.percentile(a,95):{fmt}}")

    lines.append(_s("SSIM", ssims))
    lines.append(_s("MAD", mads))
    lines.append(_s("pHash distance", phashes, fmt=".1f"))
    if lpips_vals:
        lines.append(_s("LPIPS", lpips_vals))

    lines.append("\n### Data-driven thresholds\n")
    lines.append(f"- Group A (visually identical, μ−2σ of baseline):")
    lines.append(f"  SSIM ≥ {thresholds['group_a_ssim_min']:.4f}, "
                 f"MAD < {thresholds['group_a_mad_max']:.4f}, "
                 f"pHash ≤ {thresholds['group_a_phash_max']:.1f}, "
                 f"LPIPS ≤ {thresholds['group_a_lpips_max']:.4f}")
    lines.append(f"- Group B (visible change, beyond μ−4σ):")
    lines.append(f"  SSIM < {thresholds['group_b_ssim_max']:.4f}, "
                 f"MAD > {thresholds['group_b_mad_min']:.4f}, "
                 f"pHash > {thresholds['group_b_phash_min']:.1f}, "
                 f"LPIPS > {thresholds['group_b_lpips_min']:.4f}")
    return lines


def _mann_whitney_block(base_vs_low: list[dict],
                        baseline: list[dict]) -> list[str]:
    """Statistical comparison: is base-vs-low SSIM significantly lower
    than base-vs-base2 baseline noise?"""
    lines = ["\n## Base-vs-low vs baseline noise (P0-2 statistical test)\n"]
    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        lines.append("_scipy not available; skipping Mann-Whitney U._\n")
        return lines
    low_ssim = [r["ssim"] for r in base_vs_low if "ssim" in r]
    base_ssim = [r["ssim"] for r in baseline if "ssim" in r]
    if not low_ssim or not base_ssim:
        lines.append("_insufficient data._\n")
        return lines
    u, p = mannwhitneyu(low_ssim, base_ssim, alternative="less")
    lines.append(f"- Mann-Whitney U (H1: base-vs-low SSIM < baseline SSIM):")
    lines.append(f"  U={u:.1f}, p={p:.4g}, n_low={len(low_ssim)}, "
                 f"n_baseline={len(base_ssim)}")
    lines.append(f"- Median SSIM: base-vs-low={np.median(low_ssim):.4f}, "
                 f"baseline={np.median(base_ssim):.4f}")
    if p < 0.05:
        lines.append("  → SIGNIFICANT: base-vs-low differs from intrinsic rendering noise.")
    else:
        lines.append("  → NOT significant: base-vs-low is within baseline noise. "
                     "**This is the expected result for most URLs** — "
                     "visual equivalence upheld on a population level.")
    return lines


def write_report(records: list[dict], path: pathlib.Path, mode: str,
                 baseline_pairs: Optional[list[dict]] = None,
                 thresholds: Optional[dict] = None) -> None:
    lines = []
    lines.append(f"# Visual Equivalence Analysis — mode={mode}\n")
    lines.append(f"Generated from {len(records)} pairs.\n")
    if thresholds:
        lines.append(f"Thresholds source: `{thresholds.get('source', 'unknown')}`\n")

    # Baseline summary first (if this is the URL-replay aggregate mode)
    if baseline_pairs:
        lines.extend(_baseline_summary_md(baseline_pairs, thresholds or PREREGISTERED_THRESHOLDS))
        lines.extend(_mann_whitney_block(records, baseline_pairs))

    sample = records[0] if records else {}
    base_key = "slug" if "slug" in sample else "task_id"

    if mode == "ablation":
        # Per-URL per-patch table
        by_url: dict[str, list[dict]] = {}
        for r in records:
            by_url.setdefault(r[base_key], []).append(r)
        # Aggregate across URLs
        lines.append("\n## Group classification per patch (stats across URLs)\n")
        lines.append("| Patch | Description | n | SSIM mean±σ | "
                     "LPIPS mean±σ | pHash mean | Group (mode) |")
        lines.append("|-------|-------------|---|-------------|"
                     "--------------|------------|--------------|")
        agg: dict[int, list[dict]] = {}
        for r in records:
            agg.setdefault(r["patch_id"], []).append(r)
        for pid in sorted(agg.keys()):
            rs = agg[pid]
            ssims = np.asarray([r.get("ssim", 0) for r in rs], dtype=float)
            lpips_vals = [r["lpips"] for r in rs if "lpips" in r]
            lpips_str = (f"{np.mean(lpips_vals):.4f}±{np.std(lpips_vals, ddof=1):.4f}"
                         if len(lpips_vals) > 1 else (f"{lpips_vals[0]:.4f}" if lpips_vals else "N/A"))
            phash_vals = [r.get("phash_distance", -1) for r in rs
                          if isinstance(r.get("phash_distance"), int)]
            mean_phash = np.mean(phash_vals) if phash_vals else -1
            groups = [r.get("group", "?") for r in rs]
            mode_group = max(set(groups), key=groups.count) if groups else "?"
            patch_name = rs[0].get("patch_name", "")
            lines.append(f"| {pid} | {patch_name} | {len(rs)} | "
                         f"{ssims.mean():.4f}±{ssims.std(ddof=1):.4f} | "
                         f"{lpips_str} | {mean_phash:.1f} | {mode_group} |")

        # Group summary
        lines.append("\n## Group distribution\n")
        all_groups = [r["group"] for r in records]
        for g in ["A", "B", "C", "ambiguous", "error"]:
            n = all_groups.count(g)
            lines.append(f"- Group {g}: {n} / {len(all_groups)} pairs "
                         f"({100 * n / max(len(all_groups), 1):.1f}%)")

        # Per URL
        lines.append("\n## Per-URL details\n")
        for key in sorted(by_url.keys()):
            lines.append(f"\n### {key}\n")
            lines.append("| Patch | SSIM | LPIPS | MAD | pHash | pct changed | Group |")
            lines.append("|-------|------|-------|-----|-------|-------------|-------|")
            for r in sorted(by_url[key], key=lambda x: x["patch_id"]):
                lp = f"{r.get('lpips'):.4f}" if isinstance(r.get('lpips'), float) else "N/A"
                lines.append(f"| {r['patch_id']:>2} | {r.get('ssim', 0):.4f} | "
                             f"{lp} | {r.get('mad', 0):.4f} | "
                             f"{r.get('phash_distance', 'N/A')} | "
                             f"{r.get('pct_changed', 0):.2%} | {r.get('group', '?')} |")

    else:  # aggregate
        lines.append("\n## Per-URL base-vs-low comparison\n")
        lines.append(f"| {base_key} | App | SSIM | LPIPS | MAD | pHash | pct changed | Group |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in records:
            lp = f"{r.get('lpips'):.4f}" if isinstance(r.get('lpips'), float) else "N/A"
            lines.append(f"| {r.get(base_key, '')} | {r.get('app', '')} | "
                         f"{r.get('ssim', 0):.4f} | {lp} | "
                         f"{r.get('mad', 0):.4f} | "
                         f"{r.get('phash_distance', 'N/A')} | "
                         f"{r.get('pct_changed', 0):.2%} | {r.get('group', '?')} |")
        lines.append("\n## Summary\n")
        if records:
            ssims = [r["ssim"] for r in records if "ssim" in r]
            lines.append(f"- Mean SSIM (base vs low, n={len(ssims)}): "
                         f"{np.mean(ssims):.4f} ± {np.std(ssims, ddof=1):.4f}")
            lines.append(f"- Median SSIM: {np.median(ssims):.4f} "
                         f"(p05={np.percentile(ssims,5):.4f}, "
                         f"p95={np.percentile(ssims,95):.4f})")
            lpips_vals = [r["lpips"] for r in records if "lpips" in r]
            if lpips_vals:
                lines.append(f"- Mean LPIPS (n={len(lpips_vals)}): "
                             f"{np.mean(lpips_vals):.4f} "
                             f"± {np.std(lpips_vals, ddof=1):.4f}")
        all_groups = [r["group"] for r in records]
        for g in ["A", "B", "C", "ambiguous", "error"]:
            n = all_groups.count(g)
            lines.append(f"- Group {g}: {n} / {len(all_groups)}")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["aggregate", "ablation"], required=True,
                    help="aggregate: URL-replay base/low (+ base2 baseline if present); "
                         "ablation: 13 patches individually")
    ap.add_argument("--input", required=True,
                    help="Directory with screenshots + manifest.json")
    ap.add_argument("--output", default="./results/visual-equivalence")
    ap.add_argument("--save-masks", action="store_true",
                    help="Save per-pair diff mask PNGs (slow, large disk)")
    ap.add_argument("--thresholds-json", default=None,
                    help="Optional JSON file with precomputed thresholds "
                         "(usually written by aggregate mode; reuse in ablation mode)")
    args = ap.parse_args()

    input_dir = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "aggregate":
        base_vs_low, baseline, thresholds = run_aggregate(
            input_dir, output_dir, save_masks=args.save_masks)
        # Write aggregate + baseline CSVs
        write_csv(base_vs_low, output_dir / "per_pair_metrics.csv", mode="aggregate")
        if baseline:
            write_csv(baseline, output_dir / "baseline_noise.csv", mode="baseline")
        write_report(base_vs_low, output_dir / "report.md", mode="aggregate",
                     baseline_pairs=baseline, thresholds=thresholds)
        # Persist thresholds for reuse by ablation mode
        (output_dir / "thresholds.json").write_text(
            json.dumps(thresholds, indent=2, default=str), encoding="utf-8")
        print(f"Wrote thresholds.json (source={thresholds.get('source')})",
              file=sys.stderr)
    else:
        # Load thresholds if available — otherwise fall back to pre-registered
        thresholds = PREREGISTERED_THRESHOLDS
        if args.thresholds_json:
            with open(args.thresholds_json) as f:
                thresholds = json.load(f)
            print(f"Loaded thresholds from {args.thresholds_json}", file=sys.stderr)
        records = run_ablation(input_dir, output_dir, save_masks=args.save_masks,
                               thresholds=thresholds)
        write_csv(records, output_dir / "per_patch_metrics.csv", mode="ablation")
        write_report(records, output_dir / "report.md", mode="ablation",
                     thresholds=thresholds)

    print(f"Analyzed {len(records)} pairs. Results: {output_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()

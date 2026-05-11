#!/usr/bin/env python3
"""
Stage 4b SSIM Analysis — Per-Operator Visual Equivalence
=========================================================

Computes SSIM and pHash distance for each operator vs base across all
336 URLs captured in Stage 4b. Produces:

  results/stage3/visual-equiv/ssim-per-operator.csv   — aggregate stats
  results/stage3/visual-equiv/ssim-per-url.csv         — per-URL detail
  results/stage3/visual-equiv/ssim-audit-candidates.md — top 20 for human review

Usage:
  python3 scripts/stage3/ssim-analysis.py

Dependencies: scikit-image, Pillow, imagehash, numpy, scipy, pandas
"""

import os
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import imagehash
from scipy import stats

try:
    from tqdm import tqdm
except ImportError:
    # Fallback: simple counter if tqdm not installed
    class tqdm:
        def __init__(self, iterable, **kwargs):
            self._it = iterable
            self._desc = kwargs.get("desc", "")
            self._total = kwargs.get("total", None)
            self._n = 0
        def __iter__(self):
            for item in self._it:
                self._n += 1
                if self._n % 20 == 0:
                    print(f"  {self._desc}: {self._n}/{self._total or '?'}", flush=True)
                yield item
        def __enter__(self): return self
        def __exit__(self, *a): pass

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "stage4b-ssim-replay"
OUT_DIR = ROOT / "results" / "stage3" / "visual-equiv"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# All 26 AMT operators + base2 (noise baseline)
OPERATORS = [
    "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10",
    "L11", "L12", "L13",
    "ML1", "ML2", "ML3",
    "H1", "H2", "H3", "H4", "H5a", "H5b", "H5c", "H6", "H7", "H8",
    "base2",  # noise floor: independent re-capture of base
]

OP_FAMILY = {
    **{f"L{i}": "Low" for i in range(1, 14)},
    **{f"ML{i}": "Midlow" for i in range(1, 4)},
    **{f"H{i}": "High" for i in range(1, 9)},
    "H5a": "High", "H5b": "High", "H5c": "High",
    "base2": "Baseline",
}


def load_image_gray(path: Path) -> np.ndarray:
    """Load image as float32 grayscale [0,1]."""
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr


def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """SSIM on RGB images (channel_axis=2)."""
    # Resize to same shape if needed
    if img1.shape != img2.shape:
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = img1[:h, :w]
        img2 = img2[:h, :w]
    try:
        val = ssim(img1, img2, channel_axis=2, data_range=1.0)
        return float(val)
    except Exception:
        return float("nan")


def compute_phash_dist(path1: Path, path2: Path) -> int:
    """pHash Hamming distance (0=identical, 64=max)."""
    try:
        h1 = imagehash.phash(Image.open(path1))
        h2 = imagehash.phash(Image.open(path2))
        return int(h1 - h2)
    except Exception:
        return -1


def main():
    print("=" * 70)
    print("STAGE 4b SSIM ANALYSIS")
    print("=" * 70)

    # Discover all URL slugs
    slugs = sorted([
        d.name for d in DATA_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    print(f"\nFound {len(slugs)} URL directories")

    # Per-URL, per-operator records
    records = []
    missing_base = 0
    missing_op = defaultdict(int)

    for slug in tqdm(slugs, desc="URLs", total=len(slugs)):
        slug_dir = DATA_DIR / slug
        base_path = slug_dir / "base.png"
        base2_path = slug_dir / "base2.png"

        if not base_path.exists():
            missing_base += 1
            continue

        base_img = load_image_gray(base_path)

        for op in OPERATORS:
            op_path = slug_dir / f"{op}.png"
            if not op_path.exists():
                missing_op[op] += 1
                continue

            op_img = load_image_gray(op_path)
            ssim_val = compute_ssim(base_img, op_img)
            phash_dist = compute_phash_dist(base_path, op_path)

            records.append({
                "slug": slug,
                "operator": op,
                "family": OP_FAMILY.get(op, "Unknown"),
                "ssim": ssim_val,
                "phash_dist": phash_dist,
            })

    print(f"Missing base.png: {missing_base}")
    if missing_op:
        print(f"Missing operator screenshots: {dict(missing_op)}")

    df = pd.DataFrame(records)
    print(f"\nTotal records: {len(df)}")

    # ── Per-URL detail ──────────────────────────────────────────────────
    url_detail_path = OUT_DIR / "ssim-per-url.csv"
    df.to_csv(url_detail_path, index=False)
    print(f"Written: {url_detail_path}")

    # ── Baseline noise floor (base2 vs base) ───────────────────────────
    baseline = df[df["operator"] == "base2"]["ssim"].dropna()
    noise_mean = baseline.mean()
    noise_std = baseline.std()
    noise_p05 = baseline.quantile(0.05)
    print(f"\nBaseline noise (base2 vs base):")
    print(f"  n={len(baseline)}, mean={noise_mean:.4f}, std={noise_std:.4f}, p05={noise_p05:.4f}")

    # ── Per-operator aggregate ──────────────────────────────────────────
    op_df = df[df["operator"] != "base2"].copy()
    agg = []
    for op in OPERATORS:
        if op == "base2":
            continue
        sub = op_df[op_df["operator"] == op]["ssim"].dropna()
        if len(sub) == 0:
            continue

        # Wilcoxon signed-rank test vs baseline (paired by URL)
        # Get paired (base2, op) SSIM values for same slugs
        base2_sub = df[df["operator"] == "base2"].set_index("slug")["ssim"]
        op_sub = df[df["operator"] == op].set_index("slug")["ssim"]
        common = base2_sub.index.intersection(op_sub.index)
        if len(common) >= 10:
            try:
                stat, p_wilcox = stats.wilcoxon(
                    base2_sub[common].values,
                    op_sub[common].values,
                    alternative="greater"  # H1: base2 SSIM > op SSIM (op degrades)
                )
            except Exception:
                p_wilcox = float("nan")
        else:
            p_wilcox = float("nan")

        # Cohen's d vs baseline
        if noise_std > 0:
            cohens_d = (noise_mean - sub.mean()) / noise_std
        else:
            cohens_d = float("nan")

        agg.append({
            "operator": op,
            "family": OP_FAMILY.get(op, "Unknown"),
            "n_urls": len(sub),
            "ssim_mean": round(sub.mean(), 4),
            "ssim_median": round(sub.median(), 4),
            "ssim_p10": round(sub.quantile(0.10), 4),
            "ssim_p25": round(sub.quantile(0.25), 4),
            "ssim_p75": round(sub.quantile(0.75), 4),
            "ssim_p90": round(sub.quantile(0.90), 4),
            "ssim_std": round(sub.std(), 4),
            "ssim_min": round(sub.min(), 4),
            "phash_mean": round(op_df[op_df["operator"] == op]["phash_dist"].mean(), 2),
            "delta_from_noise": round(sub.mean() - noise_mean, 4),
            "cohens_d": round(cohens_d, 3),
            "wilcoxon_p": round(p_wilcox, 6) if not math.isnan(p_wilcox) else "nan",
            "visual_change": "YES" if sub.median() < 0.99 else "no",
        })

    agg_df = pd.DataFrame(agg).sort_values("ssim_median")
    agg_path = OUT_DIR / "ssim-per-operator.csv"
    agg_df.to_csv(agg_path, index=False)
    print(f"Written: {agg_path}")

    # ── Print summary table ─────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("PER-OPERATOR SSIM SUMMARY (sorted by median SSIM)")
    print(f"{'─'*70}")
    print(f"{'Op':<8} {'Family':<8} {'Median':>7} {'Mean':>7} {'p10':>7} {'p90':>7} {'ΔNoise':>8} {'Visual?':>8}")
    print("  " + "-" * 65)
    for _, row in agg_df.iterrows():
        flag = "⚠️ CHANGE" if row["visual_change"] == "YES" else "  stable"
        print(f"  {row['operator']:<6} {row['family']:<8} "
              f"{row['ssim_median']:>7.4f} {row['ssim_mean']:>7.4f} "
              f"{row['ssim_p10']:>7.4f} {row['ssim_p90']:>7.4f} "
              f"{row['delta_from_noise']:>+8.4f}  {flag}")

    # ── Tier classification ─────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("VISUAL CHANGE CLASSIFICATION")
    print(f"{'─'*70}")
    visual_change = agg_df[agg_df["visual_change"] == "YES"]
    visual_stable = agg_df[agg_df["visual_change"] == "no"]
    print(f"  Operators with visual change (median SSIM < 0.99): {len(visual_change)}")
    for _, row in visual_change.iterrows():
        print(f"    {row['operator']}: median={row['ssim_median']:.4f}, "
              f"p10={row['ssim_p10']:.4f}")
    print(f"  Operators visually stable (median SSIM ≥ 0.99): {len(visual_stable)}")

    # ── Audit candidates (most interesting for human review) ────────────
    # Select: (a) operators with largest visual change, (b) operators with
    # surprising SSIM given their behavioral drop
    print(f"\n{'─'*70}")
    print("AUDIT CANDIDATES (top 20 URLs for human review)")
    print(f"{'─'*70}")

    # For each visually-changing operator, find URLs with most change
    audit_rows = []
    for op in ["L5", "L6", "L9", "L11", "L1"]:
        sub = df[df["operator"] == op].sort_values("ssim")
        for _, row in sub.head(4).iterrows():
            audit_rows.append({
                "operator": op,
                "slug": row["slug"],
                "ssim": row["ssim"],
                "phash_dist": row["phash_dist"],
                "reason": f"{op} most-changed URL",
            })

    # Also add L1 (landmark paradox: SSIM=1.0 but -40pp drop)
    l1_sub = df[df["operator"] == "L1"].sort_values("ssim")
    for _, row in l1_sub.head(4).iterrows():
        audit_rows.append({
            "operator": "L1",
            "slug": row["slug"],
            "ssim": row["ssim"],
            "phash_dist": row["phash_dist"],
            "reason": "L1 landmark paradox (expect SSIM≈1.0)",
        })

    audit_df = pd.DataFrame(audit_rows).drop_duplicates(subset=["slug", "operator"])

    # Write audit guide
    audit_path = OUT_DIR / "ssim-audit-candidates.md"
    with open(audit_path, "w") as f:
        f.write("# SSIM Audit Candidates — Human Review Guide\n\n")
        f.write(f"**Generated**: by `scripts/stage3/ssim-analysis.py`\n")
        f.write(f"**Purpose**: Spot-check {len(audit_df)} (operator, URL) pairs "
                f"to visually confirm SSIM findings.\n\n")
        f.write("For each entry: open `data/stage4b-ssim-replay/<slug>/base.png` "
                "and `<operator>.png` side by side.\n\n")
        f.write("| # | Operator | SSIM | pHash | Slug | Reason |\n")
        f.write("|---|----------|------|-------|------|--------|\n")
        for i, (_, row) in enumerate(audit_df.iterrows(), 1):
            f.write(f"| {i} | {row['operator']} | {row['ssim']:.4f} | "
                    f"{row['phash_dist']} | `{row['slug']}` | {row['reason']} |\n")
        f.write("\n## What to look for\n\n")
        f.write("- **L5 (Shadow DOM)**: buttons/controls should lose styling\n")
        f.write("- **L6 (heading→div)**: heading text should shrink to body size\n")
        f.write("- **L9 (table→div)**: table borders/structure should disappear\n")
        f.write("- **L11 (link→span)**: links should still appear blue+underlined\n")
        f.write("- **L1 (landmark→div)**: page should look IDENTICAL (SSIM≈1.0)\n")
        f.write("- **H-operators**: page should look IDENTICAL (enhancements invisible)\n")

    print(f"Written: {audit_path}")
    print(f"\nTop audit candidates:")
    for _, row in audit_df.head(10).iterrows():
        print(f"  {row['operator']}: SSIM={row['ssim']:.4f} — {row['slug'][:50]}")

    # ── Key paper claims verification ───────────────────────────────────
    print(f"\n{'─'*70}")
    print("PAPER CLAIM VERIFICATION")
    print(f"{'─'*70}")

    claims = {
        "L1 (landmark paradox) SSIM ≈ 1.0": ("L1", 0.99),
        "L5 (Shadow DOM) SSIM < 0.97": ("L5", None),
        "L6 (heading→div) SSIM < 0.97": ("L6", None),
        "L11 (link→span) SSIM > 0.97": ("L11", 0.97),
        "All H-operators SSIM ≥ 0.99": (None, 0.99),
    }

    for claim, (op, threshold) in claims.items():
        if op:
            row = agg_df[agg_df["operator"] == op]
            if len(row) == 0:
                print(f"  ❓ {claim}: operator not found")
                continue
            median = row.iloc[0]["ssim_median"]
            if threshold:
                ok = median >= threshold if "≈ 1.0" in claim or "> 0.97" in claim else median < threshold
                status = "✅" if ok else "❌"
            else:
                status = "📊"
            print(f"  {status} {claim}: median={median:.4f}")
        else:
            # All H-operators
            h_ops = agg_df[agg_df["family"] == "High"]
            all_ok = (h_ops["ssim_median"] >= 0.99).all()
            min_h = h_ops["ssim_median"].min()
            status = "✅" if all_ok else "❌"
            print(f"  {status} {claim}: min_median={min_h:.4f}")

    print(f"\n{'═'*70}")
    print(f"Analysis complete. Outputs in {OUT_DIR}")
    print(f"{'═'*70}")


if __name__ == "__main__":
    main()

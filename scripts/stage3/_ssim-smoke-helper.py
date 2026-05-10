#!/usr/bin/env python3.11
"""One-off helper: compute SSIM between base.png and each sibling png under
the given output directory. Used by ssm-stage4b-single-url-smoke.

Usage: python3.11 _ssim-smoke-helper.py <output-dir>
"""
import sys
from pathlib import Path
from skimage.metrics import structural_similarity as ssim
from skimage.io import imread

d = Path(sys.argv[1])
subs = [x for x in d.iterdir() if x.is_dir()]
print(f"subdirs: {[s.name for s in subs]}")
for sub in subs:
    base = sub / "base.png"
    if not base.exists():
        print(f"  {sub.name}: no base.png")
        continue
    bimg = imread(str(base))
    print(f"\nurl: {sub.name}")
    for p in sorted(sub.glob("*.png")):
        if p.name == "base.png":
            continue
        try:
            i = imread(str(p))
            s = ssim(bimg, i, channel_axis=2)
            print(f"  {p.stem:<10}: SSIM = {s:.4f}")
        except Exception as e:
            print(f"  {p.stem:<10}: ERROR {e}")

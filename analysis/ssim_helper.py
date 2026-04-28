#!/usr/bin/env python3
"""
ssim_helper.py — compute SSIM between two PNG files.

Usage:
    python3 ssim_helper.py path/to/before.png path/to/after.png

Writes a single float in [0, 1] to stdout (1 = identical).
Exits non-zero on failure.

Used by scripts/audit-operator.ts to avoid bringing in a node-native
SSIM dependency. scikit-image is already in analysis/requirements.txt.
"""
import sys

try:
    from skimage.io import imread
    from skimage.metrics import structural_similarity as ssim
    from skimage.transform import resize
    import numpy as np
except ImportError as e:
    print(f"missing dep: {e}", file=sys.stderr)
    sys.exit(3)


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: ssim_helper.py before.png after.png", file=sys.stderr)
        sys.exit(2)

    a = imread(sys.argv[1])
    b = imread(sys.argv[2])

    # Match dimensions — if operator injected elements change page
    # height, screenshots differ. We resize `after` to `before` shape
    # rather than pad, because we care about visual impact of the
    # manipulation on comparable viewport content.
    if a.shape != b.shape:
        b = resize(b, a.shape, anti_aliasing=True, preserve_range=True).astype(a.dtype)

    # SSIM needs grayscale for the simple API or multichannel=True.
    # For colour PNGs we average the per-channel SSIM.
    if a.ndim == 3:
        score = ssim(a, b, channel_axis=-1, data_range=255)
    else:
        score = ssim(a, b, data_range=255)

    # Clamp to [0,1] — scikit-image can occasionally return values
    # slightly outside that range on near-identical images.
    score = max(0.0, min(1.0, float(score)))
    print(f"{score:.6f}")


if __name__ == "__main__":
    main()

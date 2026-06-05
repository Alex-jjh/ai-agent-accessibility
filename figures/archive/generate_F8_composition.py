#!/usr/bin/env python3.11
"""
Figure F8: Compositional Scatter (Expected vs Observed Drop)
=============================================================

PURPOSE (paper §5.4):
  Show whether pairwise operator combinations are additive, super-additive,
  or sub-additive. The key finding: 50% of pairs are super-additive —
  operators AMPLIFY each other's damage.

DESIGN RATIONALE:
  - Scatter plot: X = expected drop (sum of individual drops), Y = observed pair drop
  - Diagonal line = perfect additivity (observed == expected)
  - Points ABOVE diagonal = super-additive (worse than sum of parts)
  - Points BELOW diagonal = sub-additive (less than sum of parts)
  - Points colored by interaction type (3 categories)
  - Key pairs labeled: L6+L11 (biggest amplifier), L1+L5 (biggest saturation)

WHY THIS DESIGN:
  - The diagonal reference makes additivity/deviation immediately visible
  - Super-additive points above the line are the "surprise" — operators
    that individually do nothing (L6, L11) combine to be devastating
  - The L6+L11 point (expected ≈ -5pp, observed ≈ +19pp) is the most
    dramatic outlier — it's 24pp above the diagonal
  - Sub-additive points below the line show "failure saturation" (L5 ceiling)

DATA SOURCE:
  Hardcoded from docs/analysis/mode-a-C2-composition-analysis.md
  (28 pairs, text-only agent, GT-corrected)

OUTPUT:
  figures/F8_composition.png (300 DPI)
  figures/F8_composition.pdf (vector)

USAGE:
  python3.11 figures/generate_F8_composition.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 8,
    'figure.dpi': 300,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

OUT = Path(__file__).resolve().parent

# ── Data: 28 pairwise combinations (text-only, GT-corrected) ──
# Format: (pair_label, expected_drop_pp, observed_drop_pp)
# Expected = sum of individual drops from Mode A
# Observed = actual pair drop from C.2
# Source: docs/analysis/mode-a-C2-composition-analysis.md

PAIRS = [
    # (label, expected, observed, interaction_type)
    # Super-additive (observed > expected + 5pp)
    ("L6+L11", -4.7, 19.4, "super"),
    ("L9+L11", 5.6, 24.6, "super"),
    ("L1+L6", 33.8, 50.2, "super"),
    ("L4+L6", -2.1, 11.7, "super"),
    ("L6+L9", -2.1, 11.7, "super"),
    ("L4+L11", 3.0, 14.3, "super"),
    ("L5+L11", 23.6, 34.8, "super"),
    ("L1+L11", 41.5, 50.2, "super"),
    ("L11+L12", 15.9, 22.0, "super"),
    ("L6+L12", 8.2, 16.9, "super"),
    ("L1+L9", 44.1, 52.8, "super"),
    ("L4+L9", 5.6, 14.3, "super"),
    ("L1+L4", 41.5, 50.2, "super"),
    ("L4+L12", 15.9, 22.0, "super"),
    # Additive (|observed - expected| <= 5pp)
    ("L1+L2", 44.1, 44.6, "additive"),
    ("L2+L6", -2.1, 3.1, "additive"),
    ("L2+L11", 5.6, 8.7, "additive"),
    ("L2+L4", 5.6, 8.7, "additive"),
    ("L2+L9", 8.2, 11.7, "additive"),
    ("L5+L6", 15.9, 11.7, "additive"),
    ("L5+L9", 26.2, 27.1, "additive"),
    ("L2+L12", 18.5, 16.9, "additive"),
    ("L9+L12", 18.5, 16.9, "additive"),
    # Sub-additive (observed < expected - 5pp)
    ("L1+L5", 62.1, 45.1, "sub"),
    ("L4+L5", 23.6, 6.6, "sub"),
    ("L5+L12", 36.5, 22.0, "sub"),
    ("L2+L5", 26.2, 16.9, "sub"),
    ("L1+L12", 54.4, 47.7, "sub"),
]

# ── Colors ──
COLORS = {
    "super": "#C0392B",    # red — super-additive (amplification)
    "additive": "#7F8C8D", # gray — additive (expected)
    "sub": "#2471A3",      # blue — sub-additive (saturation)
}

# ── Plot ──
fig, ax = plt.subplots(figsize=(7, 7))

# Diagonal reference line (perfect additivity)
ax.plot([-10, 70], [-10, 70], 'k--', linewidth=0.8, alpha=0.4, zorder=1)
ax.fill_between([-10, 70], [-10, 70], [70, 70], alpha=0.03, color='#C0392B', zorder=0)
ax.fill_between([-10, 70], [-15, 65], [-10, 70], alpha=0.03, color='#2471A3', zorder=0)

# Plot points by type
for itype, color in COLORS.items():
    subset = [(l, e, o) for l, e, o, t in PAIRS if t == itype]
    if not subset:
        continue
    labels, exps, obss = zip(*subset)
    label_map = {"super": f"Super-additive (n={len(subset)})",
                 "additive": f"Additive (n={len(subset)})",
                 "sub": f"Sub-additive (n={len(subset)})"}
    ax.scatter(exps, obss, c=color, s=60, alpha=0.8, edgecolors='white',
               linewidth=0.5, label=label_map[itype], zorder=5)

# Annotate key pairs
annotations = {
    "L6+L11": (+8, +6),   # biggest amplifier
    "L1+L5": (-12, -8),   # biggest saturation
    "L1+L6": (+5, +5),    # structural skeleton loss
    "L5+L11": (+5, -8),   # dual channel closure
}
for label, exp, obs, itype in PAIRS:
    if label in annotations:
        dx, dy = annotations[label]
        ax.annotate(
            label, xy=(exp, obs), xytext=(exp + dx, obs + dy),
            fontsize=7, fontweight='bold', color=COLORS[itype],
            arrowprops=dict(arrowstyle='->', color=COLORS[itype], lw=0.8),
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      edgecolor=COLORS[itype], alpha=0.9),
        )

# Axes
ax.set_xlabel('Expected Drop (sum of individual operator drops, pp)', fontsize=9)
ax.set_ylabel('Observed Pair Drop (pp)', fontsize=9)
ax.set_xlim(-10, 70)
ax.set_ylim(-5, 60)
ax.set_aspect('equal')

# Title
ax.set_title('Compositional Interaction: Expected vs Observed Pairwise Drop\n'
             '(28 pairs, Claude text-only, GT-corrected)',
             fontsize=10, fontweight='bold', pad=12)

# Region labels
ax.text(55, 15, 'Sub-additive\n(failure saturation)', fontsize=8,
        color='#2471A3', ha='center', style='italic', alpha=0.7)
ax.text(15, 50, 'Super-additive\n(amplification)', fontsize=8,
        color='#C0392B', ha='center', style='italic', alpha=0.7)

# Legend
ax.legend(loc='upper left', fontsize=8, framealpha=0.9)

plt.tight_layout()

# Save
fig.savefig(OUT / "F8_composition.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "F8_composition.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

print(f"✅ F8 saved: {OUT / 'F8_composition.png'}")
print(f"✅ F8 saved: {OUT / 'F8_composition.pdf'}")

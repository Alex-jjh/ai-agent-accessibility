#!/usr/bin/env python3.11
"""
Figure F5: DOM Signature Heatmap
=================================

PURPOSE (paper §4.X "Variant Authenticity Verification"):
  Show each operator's objective DOM fingerprint — what it actually changes
  in the page, measured independently of any agent behavior.

DESIGN RATIONALE:
  - Heatmap: rows = operators (sorted by behavioral drop), columns = DOM dimensions
  - Color: diverging RdBu (red = large positive change, blue = large negative)
  - Values normalized per column (z-score) for visual comparability
    (raw values span 0 to 365 — without normalization, L11 dominates everything)
  - Row order matches F4 (behavioral drop chart) for easy cross-reference
  - Column grouping: Structure (D) | Semantics (A) | Visual (V) | Functional (F)

WHY THIS DESIGN:
  - Heatmap is standard for "items × dimensions" matrices in HCI papers
  - Z-score normalization lets readers compare across dimensions
  - Matching row order with F4 creates a visual "aha" moment:
    L1 has modest heatmap values but tops the behavioral chart (misalignment!)
    L11 has extreme heatmap values but is near the bottom behaviorally
  - Column grouping reinforces the 4-layer model (D/A/V/F)

DATA SOURCE:
  results/amt/dom_signature_matrix.csv
  results/amt/behavioral_signature_matrix.csv (for sort order)

OUTPUT:
  figures/F5_dom_heatmap.png (300 DPI)
  figures/F5_dom_heatmap.pdf (vector)

USAGE:
  python3.11 figures/generate_F5_dom_heatmap.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 8,
    'figure.dpi': 300,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent

# ── Load data ──
dom_df = pd.read_csv(ROOT / "results" / "amt" / "dom_signature_matrix.csv")
beh_df = pd.read_csv(ROOT / "results" / "amt" / "behavioral_signature_matrix.csv")

# Sort by Claude text-only drop (most destructive at top)
beh_df['sort_key'] = -beh_df['claude_text_drop']  # negative so largest drop = smallest sort key
sort_order = beh_df.sort_values('sort_key')['operator'].tolist()

# Reorder dom_df to match
dom_df = dom_df.set_index('operator').loc[sort_order].reset_index()

# Select key dimensions for display (8 most informative)
display_dims = [
    'D1_totalTagChanges',
    'A1_rolesChanged',
    'A2_namesChanged',
    'A3_totalAriaStateChanges',
    'V1_ssim',
    'F1_interactiveCountDelta',
    'F2_inlineHandlerDelta',
    'F3_focusableCountDelta',
]

# Pretty column names
col_labels = {
    'D1_totalTagChanges': 'D1\nTag Δ',
    'A1_rolesChanged': 'A1\nRoles',
    'A2_namesChanged': 'A2\nNames',
    'A3_totalAriaStateChanges': 'A3\nStates',
    'V1_ssim': 'V1\nSSIM',
    'F1_interactiveCountDelta': 'F1\nInteractive',
    'F2_inlineHandlerDelta': 'F2\nHandlers',
    'F3_focusableCountDelta': 'F3\nFocusable',
}

# Extract matrix
matrix = dom_df[display_dims].copy()

# Z-score normalize per column (except V1 which is inverted: 1.0 = no change)
# For V1, invert so that lower SSIM = higher "change"
matrix['V1_ssim'] = 1.0 - matrix['V1_ssim']  # now 0 = no change, 0.2 = big change

# Z-score normalize
matrix_z = (matrix - matrix.mean()) / matrix.std()
# Replace NaN (zero-variance columns) with 0
matrix_z = matrix_z.fillna(0)

# Row labels
row_labels = [f"{row['operator']}  {row['description']}" for _, row in dom_df.iterrows()]

# ── Plot ──
fig, ax = plt.subplots(figsize=(7, 9))

# Use seaborn heatmap
sns.heatmap(
    matrix_z,
    ax=ax,
    cmap='RdBu_r',  # red = high change, blue = low/negative
    center=0,
    vmin=-2, vmax=3,
    linewidths=0.3,
    linecolor='white',
    cbar_kws={'label': 'Z-score (normalized change magnitude)', 'shrink': 0.6},
    xticklabels=[col_labels[d] for d in display_dims],
    yticklabels=row_labels,
)

# Column group separators
for x_pos in [1, 4, 5]:  # after D1, after A3, after V1
    ax.axvline(x=x_pos, color='black', linewidth=1.5, zorder=10)

# Column group labels at top
ax.text(0.5, -0.8, 'Structure', ha='center', fontsize=7, fontweight='bold', color='#2C3E50')
ax.text(2.5, -0.8, 'Semantics', ha='center', fontsize=7, fontweight='bold', color='#2C3E50')
ax.text(4.5, -0.8, 'Visual', ha='center', fontsize=7, fontweight='bold', color='#2C3E50')
ax.text(6.5, -0.8, 'Functional', ha='center', fontsize=7, fontweight='bold', color='#2C3E50')

# Title
ax.set_title('DOM Signature Matrix — Per-Operator Change Profile\n'
             '(Z-score normalized, sorted by behavioral impact)',
             fontsize=10, fontweight='bold', pad=20)

ax.set_xlabel('')
ax.set_ylabel('')
ax.tick_params(axis='y', labelsize=7)
ax.tick_params(axis='x', labelsize=8, rotation=0)

plt.tight_layout()

# Save
fig.savefig(OUT / "F5_dom_heatmap.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "F5_dom_heatmap.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

print(f"✅ F5 saved: {OUT / 'F5_dom_heatmap.png'}")
print(f"✅ F5 saved: {OUT / 'F5_dom_heatmap.pdf'}")

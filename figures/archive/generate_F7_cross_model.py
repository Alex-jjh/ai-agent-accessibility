#!/usr/bin/env python3.11
"""
Figure F7: Cross-Model Comparison (Cleveland Dot Plot)
=======================================================

PURPOSE (paper §5.3):
  Show that the accessibility effect generalizes across model families
  (Claude vs Llama 4), while revealing the "adaptive recovery gap" —
  Claude adapts to some operators that Llama 4 cannot.

DESIGN RATIONALE:
  - Cleveland dot plot (connected dots): clean, minimal, high data density
  - Each row = one operator, two dots connected by a line
  - Left dot (blue) = Claude text-only drop, Right dot (purple) = Llama 4 drop
  - Only show top-12 operators (those with >5pp drop in either model)
  - Highlight L11 gap: Claude +1.5pp vs Llama +14.6pp (adaptive recovery)
  - Highlight L1/L5 agreement: both models show large drops (robust effect)

WHY THIS DESIGN:
  - Cleveland dot plots are superior to grouped bar charts for paired comparisons
    (Cleveland & McGill 1984 — position along common scale > length)
  - The connecting line makes the GAP between models immediately visible
  - L11's long horizontal line is the visual "aha" — same DOM damage, 10× behavioral difference
  - Sorted by Claude drop to maintain consistency with F4

DATA SOURCE:
  results/amt/behavioral_signature_matrix.csv

OUTPUT:
  figures/F7_cross_model.png (300 DPI)
  figures/F7_cross_model.pdf (vector)

USAGE:
  python3.11 figures/generate_F7_cross_model.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 8,
    'figure.dpi': 300,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent

# ── Colors ──
CLAUDE_COLOR = '#2471A3'
LLAMA_COLOR = '#8E44AD'
HIGHLIGHT_COLOR = '#C0392B'

# ── Load data ──
df = pd.read_csv(ROOT / "results" / "amt" / "behavioral_signature_matrix.csv")
df['claude_drop_pp'] = df['claude_text_drop'] * 100
df['llama4_drop_pp'] = df['llama4_text_drop'] * 100

# Filter: show operators where either model drops > 4pp
df_show = df[(df['claude_drop_pp'] > 4) | (df['llama4_drop_pp'] > 4)].copy()
df_show = df_show.sort_values('claude_drop_pp', ascending=True)

# ── Plot ──
fig, ax = plt.subplots(figsize=(7, 5))

y_pos = np.arange(len(df_show))

# Connecting lines
for i, (_, row) in enumerate(df_show.iterrows()):
    c_drop = row['claude_drop_pp']
    l_drop = row['llama4_drop_pp']
    # Highlight L11 (largest gap)
    if row['operator'] == 'L11':
        ax.plot([c_drop, l_drop], [i, i], color=HIGHLIGHT_COLOR, linewidth=2.5,
                zorder=3, alpha=0.8)
        ax.annotate('Adaptive Recovery Gap\n(Claude uses goto() workaround,\nLlama 4 cannot)',
                    xy=((c_drop + l_drop) / 2, i), xytext=(25, i + 1.5),
                    fontsize=7, color=HIGHLIGHT_COLOR, style='italic',
                    arrowprops=dict(arrowstyle='->', color=HIGHLIGHT_COLOR, lw=0.8))
    else:
        ax.plot([c_drop, l_drop], [i, i], color='#CCCCCC', linewidth=1.2, zorder=2)

# Claude dots
ax.scatter(df_show['claude_drop_pp'], y_pos, s=50, color=CLAUDE_COLOR,
           zorder=5, label='Claude Sonnet 4')

# Llama 4 dots
ax.scatter(df_show['llama4_drop_pp'], y_pos, s=50, color=LLAMA_COLOR,
           marker='D', zorder=5, label='Llama 4 Maverick')

# Y-axis labels
labels = [f"{row['operator']}  {row['description']}" for _, row in df_show.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=7)

# X-axis
ax.set_xlabel('Drop from H-baseline (percentage points)', fontsize=9)
ax.axvline(x=0, color='#AAAAAA', linestyle='--', linewidth=0.6)

# Title
ax.set_title('Cross-Model Replication: Claude vs Llama 4 Per-Operator Drop\n'
             '(text-only agent, operators with >4pp effect in either model)',
             fontsize=9, fontweight='bold', pad=12)

# Legend
ax.legend(loc='lower right', fontsize=8, framealpha=0.9)

plt.tight_layout()

# Save
fig.savefig(OUT / "F7_cross_model.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "F7_cross_model.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

print(f"✅ F7 saved: {OUT / 'F7_cross_model.png'}")
print(f"✅ F7 saved: {OUT / 'F7_cross_model.pdf'}")

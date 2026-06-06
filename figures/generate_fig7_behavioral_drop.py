#!/usr/bin/env python3
"""
Figure 7: Per-Operator Behavioral Drop (paper §5.1, fig:behavioral-drop)
========================================================================

Per-operator behavioral impact — the "damage ranking" of all 26 AMT operators
on the Stage 3 breadth set (48 tasks x 3 reps = 144 obs/operator, Claude
text-only), with Llama 4 Maverick drops overlaid for the operators that have a
cross-model contrast.

DATA SOURCE (Stage 3 breadth, the paper's primary dataset):
  results/stage3/per-operator-stage3.csv   (Claude drop_pp + significance)
  results/stage3/cross-model-stage3.csv     (Llama 4 drop_pp; from stage3_statistics)
  results/amt/behavioral_signature_matrix.csv (operator family + description labels)

Family is derived from the operator id (L*/ML*/H*); the description map mirrors
the behavioral_signature_matrix labels.

OUTPUT: figures/fig7_behavioral_drop.{png,pdf}

USAGE: python3 figures/generate_fig7_behavioral_drop.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300,
    'axes.spines.top': False, 'axes.spines.right': False,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
STAGE3 = ROOT / "results" / "stage3" / "per-operator-stage3.csv"
CROSS = ROOT / "results" / "stage3" / "cross-model-stage3.csv"
BEH = ROOT / "results" / "amt" / "behavioral_signature_matrix.csv"

COLORS = {'Low': '#C0392B', 'Midlow': '#E67E22', 'High': '#27AE60'}
LLAMA_COLOR = '#8E44AD'
BASELINE_COLOR = '#2C3E50'


def family_of(op: str) -> str:
    if op.startswith('ML'):
        return 'Midlow'
    if op.startswith('H'):
        return 'High'
    return 'Low'


# ── Load ──
df = pd.read_csv(STAGE3)
desc = {r['operator']: r['description'] for _, r in pd.read_csv(BEH).iterrows()}
cross = pd.read_csv(CROSS).set_index('operator')['llama_drop_pp'].to_dict()

df['family'] = df['operator'].map(family_of)
df['description'] = df['operator'].map(lambda o: desc.get(o, o))
df['llama_drop_pp'] = df['operator'].map(lambda o: cross.get(o, np.nan))
df = df.sort_values('drop_pp', ascending=True).reset_index(drop=True)

# H-baseline success rate for the annotation (pooled H operators)
h_rate = df[df['operator'].str.startswith('H')].apply(
    lambda r: r['rate'], axis=1).mean() * 100

# ── Plot ──
fig, ax = plt.subplots(figsize=(7, 8))
y_pos = np.arange(len(df))
bar_colors = [COLORS[f] for f in df['family']]

ax.barh(y_pos, df['drop_pp'], height=0.7, color=bar_colors,
        edgecolor='white', linewidth=0.3, alpha=0.85)

# Llama 4 markers only where a cross-model contrast exists
mask = df['llama_drop_pp'].notna()
ax.scatter(df.loc[mask, 'llama_drop_pp'], y_pos[mask.values], marker='D', s=25,
           color=LLAMA_COLOR, zorder=5, label='Llama 4 Maverick (text-only)')

ax.axvline(x=0, color=BASELINE_COLOR, linestyle='--', linewidth=0.8, alpha=0.6)
ax.text(0.5, len(df) - 0.5, f'H-baseline\n({h_rate:.1f}%)', fontsize=7,
        color=BASELINE_COLOR, ha='left', va='top', style='italic')

labels = [f"{r['operator']}  {r['description']}" for _, r in df.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=7)
# Mark Holm-significant operators with a bold star on the label
for i, r in df.iterrows():
    if str(r.get('significant')) == 'True':
        ax.text(-9.3, i, '*', fontsize=11, fontweight='bold', va='center',
                color=COLORS[r['family']])

ax.set_xlabel('Drop from H-baseline (percentage points, Stage 3 breadth)', fontsize=9)
ax.set_xlim(-10, 35)
ax.set_xticks([-10, 0, 10, 20, 30])
ax.set_title('Per-Operator Behavioral Impact\n(Claude text-only, Stage 3: 48 tasks x 3 reps, GT-corrected)',
             fontsize=10, fontweight='bold', pad=12)

# Annotate the two destructive anchors with correct Stage 3 values
for _, r in df.iterrows():
    y = df.index[df['operator'] == r['operator']][0]
    if r['operator'] == 'L1':
        ax.annotate(f"Landmark Paradox:\n~6 elements, SSIM=1.000, {r['drop_pp']:.0f}pp",
                    xy=(r['drop_pp'], y), xytext=(r['drop_pp'] - 4, y + 1.6),
                    fontsize=6.5, color='#C0392B', style='italic', ha='right',
                    arrowprops=dict(arrowstyle='->', color='#C0392B', lw=0.8))
    elif r['operator'] == 'L11':
        ax.annotate("L11: 365 DOM changes,\nyet Claude adapts (+2.3pp)",
                    xy=(r['drop_pp'], y), xytext=(r['drop_pp'] + 4, y - 1.8),
                    fontsize=6.5, color=LLAMA_COLOR, style='italic', ha='left',
                    arrowprops=dict(arrowstyle='->', color=LLAMA_COLOR, lw=0.8))

from matplotlib.patches import Patch
from matplotlib.lines import Line2D
legend_elements = [
    Patch(facecolor=COLORS['Low'], label='Low family (L1-L13)'),
    Patch(facecolor=COLORS['Midlow'], label='Midlow family (ML1-ML3)'),
    Patch(facecolor=COLORS['High'], label='High family (H1-H8, incl. H5a/b/c)'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=LLAMA_COLOR,
           markersize=6, label='Llama 4 Maverick'),
    Line2D([0], [0], marker='$*$', color=COLORS['Low'], linestyle='None',
           markersize=8, label='Holm-significant (p<0.05)'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=7, framealpha=0.9)

plt.tight_layout()
fig.savefig(OUT / "fig7_behavioral_drop.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "fig7_behavioral_drop.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none', metadata={'CreationDate': None})
plt.close()
print(f"OK fig7 saved: {OUT / 'fig7_behavioral_drop.png'}")
print(f"   L1={df[df.operator=='L1'].drop_pp.values[0]:.1f}pp, "
      f"L11={df[df.operator=='L11'].drop_pp.values[0]:.1f}pp, "
      f"H-baseline={h_rate:.1f}%")

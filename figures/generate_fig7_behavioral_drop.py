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

from figstyle import apply_rc, COLWIDTH_IN, FAMILY_COLORS, FAMILY_HATCH
apply_rc()

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
STAGE3 = ROOT / "results" / "stage3" / "per-operator-stage3.csv"
CROSS = ROOT / "results" / "stage3" / "cross-model-stage3.csv"
BEH = ROOT / "results" / "amt" / "behavioral_signature_matrix.csv"

COLORS = FAMILY_COLORS
LLAMA_COLOR = '#8E44AD'
BASELINE_COLOR = '#2C3E50'
STAR_COLOR = '#2C3E50'   # neutral so the single legend swatch is honest


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

# H-baseline success rate for the annotation — computed over the pooled High
# operators BEFORE we drop them from the plot (must use the full frame).
n_high = int(df['operator'].str.startswith('H').sum())
h_rate = df[df['operator'].str.startswith('H')]['rate'].mean() * 100

# The 10 High operators are the pooled baseline itself, so their "drop from
# H-baseline" is 0 by construction (zero-length bars + a green legend swatch
# that never appears). We therefore do NOT plot them as bars; they are
# represented by the zero-line reference and a note. Only the L/ML operators
# (the ones actually measured against the High baseline) get bars.
df = df[~df['operator'].str.startswith('H')].copy()
df = df.sort_values('drop_pp', ascending=True).reset_index(drop=True)

# ── Plot ──
fig, ax = plt.subplots(figsize=(COLWIDTH_IN, 6.0))
y_pos = np.arange(len(df))
bar_colors = [COLORS[f] for f in df['family']]
bar_hatch = [FAMILY_HATCH[f] for f in df['family']]

bars = ax.barh(y_pos, df['drop_pp'], height=0.7, color=bar_colors,
               edgecolor='white', linewidth=0.3, alpha=0.85)
# Redundant hatch per family so Low/Midlow/High survive grayscale + CVD.
for bar, h in zip(bars, bar_hatch):
    if h:
        bar.set_hatch(h)

# Llama 4 markers only where a cross-model contrast exists
mask = df['llama_drop_pp'].notna()
ax.scatter(df.loc[mask, 'llama_drop_pp'], y_pos[mask.values], marker='D', s=28,
           color=LLAMA_COLOR, edgecolors='white', linewidth=0.5, zorder=5,
           label='Llama 4 Maverick (text-only)')

ax.axvline(x=0, color='#27AE60', linestyle='--', linewidth=1.0, alpha=0.9)
# Place the baseline note in the open whitespace on the mid-right (the bars
# there are short), below the L11 callout and above the legend.
ax.text(19, len(df) * 0.40,
        f'Green line = H-baseline ({h_rate:.1f}%)\n= pooled High family\n({n_high} enhancement ops;\ndrop = 0 by construction)',
        fontsize=6.5, color='#1E8449', ha='left', va='center', style='italic',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                  edgecolor='#27AE60', linewidth=0.6, alpha=0.9))

labels = [f"{r['operator']}  {r['description']}" for _, r in df.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=7)
# Mark Holm-significant operators with a bold star on the label
for i, r in df.iterrows():
    if str(r.get('significant')) == 'True':
        ax.text(-9.3, i, '*', fontsize=11, fontweight='bold', va='center',
                color=STAR_COLOR)

ax.set_xlabel('Drop from H-baseline (percentage points, Stage 3 breadth)', fontsize=9)
ax.set_xlim(-10, 35)
ax.set_xticks([-10, 0, 10, 20, 30])
# (Title + run description live in the LaTeX \caption.)

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
    Patch(facecolor=COLORS['Low'], edgecolor='white', hatch=FAMILY_HATCH['Low'], label='Low family (L1-L13)'),
    Patch(facecolor=COLORS['Midlow'], edgecolor='white', hatch=FAMILY_HATCH['Midlow'], label='Midlow family (ML1-ML3)'),
    Line2D([0], [0], color='#27AE60', linestyle='--', linewidth=1.0,
           label='High family = baseline (drop $\\equiv$ 0)'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=LLAMA_COLOR,
           markersize=6, label='Llama 4 Maverick'),
    Line2D([0], [0], marker='$*$', color=STAR_COLOR, linestyle='None',
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

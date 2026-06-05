#!/usr/bin/env python3
"""
Figure 8: Signature Alignment Scatter (paper §5.2, fig:alignment-scatter)
=========================================================================

THE core-contribution figure: DOM change magnitude (x) vs behavioral drop (y),
one point per operator, colored by alignment quadrant. The L1-vs-L11 contrast
is the visual anchor of the Landmark Paradox.

CRITICAL — this figure MUST use the paper's operational definition so its
quadrant counts match §5.2 / Appendix (tab:alignment-sensitivity) exactly:
  - DOM-active  <=>  (|D1| + |A1| + |A2|) >= 5.0  OR  SSIM (V1) < 0.99
  - behav-active <=> Claude text-only drop >= 5.0 pp   (Mode A depth set,
                     consistent with the quadrant memberships reported in §5.2)
This reproduces 2 / 13 / 9 / 2 (aligned-active / aligned-null /
agent-adaptation / structural-criticality) = 11/26 misaligned = 42.3%.

DATA SOURCE:
  results/amt/dom_signature_matrix.csv          (D1,A1,A2,V1 = SSIM)
  results/amt/behavioral_signature_matrix.csv   (claude_text_drop, depth set)

OUTPUT: figures/fig8_alignment_scatter.{png,pdf}
USAGE:  python3 figures/generate_fig8_alignment_scatter.py
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
DOM = ROOT / "results" / "amt" / "dom_signature_matrix.csv"
BEH = ROOT / "results" / "amt" / "behavioral_signature_matrix.csv"

# Paper-default thresholds (main.tex Appendix tab:alignment-sensitivity, bold row)
DOM_THRESHOLD = 5.0
SSIM_THRESHOLD = 0.99
BEH_THRESHOLD = 5.0  # pp

QUAD_COLORS = {
    'Aligned (both active)': '#27AE60',
    'Aligned (both null)': '#2471A3',
    'Agent adaptation': '#E67E22',
    'Structural criticality': '#C0392B',
}

dom = pd.read_csv(DOM)
beh = pd.read_csv(BEH)[['operator', 'claude_text_drop']]

# Paper's DOM-active magnitude = |D1| + |A1| + |A2|
dom['dom_mag'] = (dom['D1_totalTagChanges'].abs()
                  + dom['A1_rolesChanged'].abs()
                  + dom['A2_namesChanged'].abs())
dom['ssim'] = dom['V1_ssim']

m = dom[['operator', 'dom_mag', 'ssim']].merge(beh, on='operator')
m['drop_pp'] = m['claude_text_drop'] * 100


def quadrant(r):
    dom_active = (r['dom_mag'] >= DOM_THRESHOLD) or (r['ssim'] < SSIM_THRESHOLD)
    beh_active = r['drop_pp'] >= BEH_THRESHOLD
    if dom_active and beh_active:
        return 'Aligned (both active)'
    if (not dom_active) and (not beh_active):
        return 'Aligned (both null)'
    if dom_active and (not beh_active):
        return 'Agent adaptation'
    return 'Structural criticality'


m['quadrant'] = m.apply(quadrant, axis=1)
m['dom_mag_plot'] = m['dom_mag'] + 1  # avoid log(0)

counts = m['quadrant'].value_counts().to_dict()
mis = counts.get('Agent adaptation', 0) + counts.get('Structural criticality', 0)
print(f"Quadrant counts: {counts}")
print(f"Misaligned: {mis}/26 = {100*mis/26:.1f}%")

fig, ax = plt.subplots(figsize=(7, 6))
for quad, color in QUAD_COLORS.items():
    sub = m[m['quadrant'] == quad]
    ax.scatter(sub['dom_mag_plot'], sub['drop_pp'], c=color, s=70, alpha=0.85,
               edgecolors='white', linewidth=0.6, zorder=5,
               label=f"{quad} (n={len(sub)})")

ax.axhline(y=BEH_THRESHOLD, color='#AAAAAA', linestyle='--', linewidth=0.8, zorder=1)
ax.axvline(x=DOM_THRESHOLD + 1, color='#AAAAAA', linestyle='--', linewidth=0.8, zorder=1)

# Annotate the L1-vs-L11 contrast (the signature finding) + a couple anchors
ANNOT = {
    'L1':  (10, 6),   'L11': (-10, -7),
    'L5':  (-15, 4),  'L12': (8, 4), 'L10': (8, -5),
}
for _, r in m.iterrows():
    if r['operator'] in ANNOT:
        dx, dy = ANNOT[r['operator']]
        ax.annotate(r['operator'],
                    xy=(r['dom_mag_plot'], r['drop_pp']),
                    xytext=(r['dom_mag_plot'] * (1.6 if dx > 0 else 0.55),
                            r['drop_pp'] + dy),
                    fontsize=9, fontweight='bold', color=QUAD_COLORS[r['quadrant']],
                    arrowprops=dict(arrowstyle='->', color=QUAD_COLORS[r['quadrant']],
                                    lw=0.9, connectionstyle='arc3,rad=0.2'),
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              edgecolor='none', alpha=0.85))

ax.set_xscale('log')
ax.set_xlabel('DOM change magnitude  |D1|+|A1|+|A2|  (log scale; SSIM<0.99 also counts as DOM-active)',
              fontsize=8)
ax.set_ylabel('Claude text-only drop from H-baseline (pp, depth set)', fontsize=9)
ax.set_ylim(-8, 45)
ax.set_xlim(0.8, 700)

# Corner quadrant labels
ax.text(1.1, 43, 'Structural\ncriticality', fontsize=8, color='#C0392B',
        ha='left', va='top', style='italic', alpha=0.7)
ax.text(650, 43, 'Aligned\n(both active)', fontsize=8, color='#27AE60',
        ha='right', va='top', style='italic', alpha=0.7)
ax.text(1.1, -6, 'Aligned\n(both null)', fontsize=8, color='#2471A3',
        ha='left', va='bottom', style='italic', alpha=0.7)
ax.text(650, -6, 'Agent\nadaptation', fontsize=8, color='#E67E22',
        ha='right', va='bottom', style='italic', alpha=0.7)

ax.set_title(f'Signature Alignment: DOM Magnitude vs Behavioral Impact\n'
             f'(26 operators; {mis}/26 = {100*mis/26:.0f}% misaligned at paper-default thresholds)',
             fontsize=10, fontweight='bold', pad=12)
ax.legend(loc='upper center', fontsize=7, ncol=2, framealpha=0.9,
          bbox_to_anchor=(0.5, -0.10))

plt.tight_layout()
fig.savefig(OUT / "fig8_alignment_scatter.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "fig8_alignment_scatter.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"OK fig8 saved: {OUT / 'fig8_alignment_scatter.png'}")

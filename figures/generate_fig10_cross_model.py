#!/usr/bin/env python3
"""
Figure 10: Cross-Model Replication (paper §5.3, fig:cross-model)
================================================================

Cleveland dot plot of per-operator drop, Claude Sonnet 4 vs Llama 4 Maverick,
on the Stage 3 breadth set. The connecting line length is the cross-model gap;
the L11 line is the visual "aha" (the adaptive recovery gap): Claude drops only
+2.3pp where Llama 4 drops +14.1pp despite identical DOM damage.

This visualizes a HEADLINE finding (§5.3, Breslow-Day p<0.001) that previously
had no figure in the paper.

DATA SOURCE (Stage 3 breadth, both models):
  results/stage3/cross-model-stage3.csv   (emitted by analysis/stage3_statistics.py)
  results/amt/behavioral_signature_matrix.csv  (operator descriptions)

OUTPUT: figures/fig10_cross_model.{png,pdf}
USAGE:  python3 figures/generate_fig10_cross_model.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

from figstyle import apply_rc, COLWIDTH_IN, MODEL_COLORS, MODEL_MARKER
apply_rc()

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
CROSS = ROOT / "results" / "stage3" / "cross-model-stage3.csv"
BEH = ROOT / "results" / "amt" / "behavioral_signature_matrix.csv"

CLAUDE_COLOR = MODEL_COLORS['claude']
LLAMA_COLOR = MODEL_COLORS['llama']
HIGHLIGHT_COLOR = '#C0392B'

df = pd.read_csv(CROSS)
desc = {r['operator']: r['description'] for _, r in pd.read_csv(BEH).iterrows()}
df['description'] = df['operator'].map(lambda o: desc.get(o, o))
df = df.sort_values('claude_drop_pp', ascending=True).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(COLWIDTH_IN, 4.5))
y_pos = np.arange(len(df))

for i, row in df.iterrows():
    c, l = row['claude_drop_pp'], row['llama_drop_pp']
    if row['operator'] == 'L11':
        ax.plot([c, l], [i, i], color=HIGHLIGHT_COLOR, linewidth=2.5, zorder=3, alpha=0.85)
        ax.annotate('Adaptive recovery gap:\nClaude uses goto() fallback,\nLlama 4 persists with clicks',
                    xy=((c + l) / 2, i), xytext=(l + 1, i - 1.5),
                    fontsize=7, color=HIGHLIGHT_COLOR, style='italic', ha='left',
                    arrowprops=dict(arrowstyle='->', color=HIGHLIGHT_COLOR, lw=0.8))
    else:
        ax.plot([c, l], [i, i], color='#999999', linewidth=1.2, zorder=2)

ax.scatter(df['claude_drop_pp'], y_pos, s=55, color=CLAUDE_COLOR,
           marker=MODEL_MARKER['claude'], edgecolors='white', linewidth=0.4,
           zorder=5, label='Claude Sonnet 4')
ax.scatter(df['llama_drop_pp'], y_pos, s=55, color=LLAMA_COLOR,
           marker=MODEL_MARKER['llama'], edgecolors='white', linewidth=0.4,
           zorder=5, label='Llama 4 Maverick')

labels = [f"{r['operator']}  {r['description']}" for _, r in df.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel('Drop from H-baseline (percentage points, Stage 3 breadth)', fontsize=9)
ax.axvline(x=0, color='#AAAAAA', linestyle='--', linewidth=0.6)
# Headroom on the right so the L11 adaptive-recovery-gap callout never clips.
_xmax = max(df['claude_drop_pp'].max(), df['llama_drop_pp'].max())
ax.set_xlim(min(df['claude_drop_pp'].min(), df['llama_drop_pp'].min()) - 2, _xmax + 12)
# (Title + Breslow-Day p live in the LaTeX \caption.)
ax.legend(loc='lower right', fontsize=8, framealpha=0.9)

plt.tight_layout()
fig.savefig(OUT / "fig10_cross_model.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "fig10_cross_model.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none', metadata={'CreationDate': None})
plt.close()
print(f"OK fig10 saved: {OUT / 'fig10_cross_model.png'}")
l11 = df[df.operator == 'L11'].iloc[0]
print(f"   L11: Claude {l11['claude_drop_pp']:+.1f}pp vs Llama {l11['llama_drop_pp']:+.1f}pp")

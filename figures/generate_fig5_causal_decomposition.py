#!/usr/bin/env python3
"""
Figure 5: Contribution Decomposition of Composite Low Effects (paper §5.1,
fig:causal-decomp)
==========================================================================

Two-agent contribution decomposition of the composite-Low drop (Claude-only).
The text-only agent drops 55.4pp under composite Low; the DOM-bypassing CUA
agent drops 35.4pp. The CUA drop bounds the FUNCTIONAL pathway (DOM breakage
visible to every agent, ~35pp, 95% bootstrap CI [15.4, 55.4]); the residual
SEMANTIC contribution (~20pp, CI [-13.8, 52.3]) crosses zero. Because composite
Low is not visually equivalent to base (median SSIM=0.897), the CUA drop also
carries visual degradation, so 35.4pp is an upper bound on the pure functional
pathway and 20.0pp a lower bound on the semantic residual; the decomposition
is reported as a bounded heuristic, not a precisely estimated effect size.

This regenerates the previously script-less figure5_causal_decomposition.png.
It is READ-ONLY w.r.t. the frozen data: it consumes the locked
results/bootstrap_decomposition.csv (the same triples carried in
key-numbers.json) and writes a PNG/PDF only.

DATA SOURCE (frozen, locked in key-numbers.json):
  results/bootstrap_decomposition.csv
    pathway,point_estimate,ci_lo,ci_hi,n_bootstrap
    text_only_drop,55.4,29.2,80.0,2000
    cua_drop,35.4,15.4,55.4,2000
    semantic_contribution,20.0,-13.8,52.3,2000

OUTPUT: figures/fig5_causal_decomposition.{png,pdf}
USAGE:  python3 figures/generate_fig5_causal_decomposition.py
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300,
    'axes.spines.top': False, 'axes.spines.right': False,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
DECOMP = ROOT / "results" / "bootstrap_decomposition.csv"
SOM_LOW_RATE = 4.6   # composite SoM low (Table 1)
SOM_BASE_RATE = 27.7  # composite SoM base (Table 1) -> SoM drop ~23.1pp from a lower baseline

# ── Load the frozen, locked decomposition triples ──
df = pd.read_csv(DECOMP).set_index('pathway')
text_drop = df.loc['text_only_drop']
cua_drop = df.loc['cua_drop']
semantic = df.loc['semantic_contribution']

# ── Plot: a stacked functional/semantic decomposition bar for the text-only
#    drop, beside the directly-measured CUA (functional) drop, each with its
#    bootstrap 95% CI; the zero-crossing semantic CI is drawn explicitly. ──
fig, ax = plt.subplots(figsize=(5.2, 4.2))

FUNC_COLOR = '#2471A3'    # functional pathway (DOM breakage, all agents)
SEM_COLOR = '#C0392B'     # residual semantic contribution
SOM_COLOR = '#7F8C8D'     # SoM supplementary corroboration

x_text, x_cua = 0.0, 1.1
width = 0.55

# Text-only total drop, split into functional (CUA-measured) + semantic residual
ax.bar(x_text, cua_drop['point_estimate'], width, color=FUNC_COLOR,
       edgecolor='white', label=f"Functional pathway ({cua_drop['point_estimate']:.0f}pp)")
ax.bar(x_text, semantic['point_estimate'], width,
       bottom=cua_drop['point_estimate'], color=SEM_COLOR, alpha=0.85,
       edgecolor='white',
       label=f"Semantic residual ({semantic['point_estimate']:.0f}pp, CI crosses 0)")

# Directly-measured CUA drop (functional pathway, with its bootstrap CI)
ax.bar(x_cua, cua_drop['point_estimate'], width, color=FUNC_COLOR, alpha=0.55,
       edgecolor='white', hatch='//')
ax.errorbar(x_cua, cua_drop['point_estimate'],
            yerr=[[cua_drop['point_estimate'] - cua_drop['ci_lo']],
                  [cua_drop['ci_hi'] - cua_drop['point_estimate']]],
            fmt='none', ecolor='#1B2631', elinewidth=1.2, capsize=4, zorder=6)

# Semantic-residual CI annotation (crosses zero) on the text-only bar
sem_mid = cua_drop['point_estimate'] + semantic['point_estimate']
ax.errorbar(x_text + 0.0, sem_mid,
            yerr=[[semantic['point_estimate'] - semantic['ci_lo']],
                  [semantic['ci_hi'] - semantic['point_estimate']]],
            fmt='none', ecolor='#641E16', elinewidth=1.2, capsize=4, zorder=6)

# Text-only total drop reference line
ax.axhline(text_drop['point_estimate'], color='#566573', linestyle=':',
           linewidth=0.9, alpha=0.7)
ax.text(1.72, text_drop['point_estimate'],
        f"text-only total\n{text_drop['point_estimate']:.1f}pp",
        fontsize=7, color='#566573', va='center', ha='left', style='italic')

# SoM supplementary corroboration marker (from a lower 27.7% baseline)
som_drop = SOM_BASE_RATE - SOM_LOW_RATE
ax.scatter([x_cua + 0.0], [som_drop], marker='v', s=45, color=SOM_COLOR,
           zorder=7)
ax.annotate(f"SoM drop {som_drop:.1f}pp\n(from 27.7% baseline)",
            xy=(x_cua, som_drop), xytext=(x_cua + 0.18, som_drop - 9),
            fontsize=6.5, color=SOM_COLOR, style='italic', ha='left',
            arrowprops=dict(arrowstyle='->', color=SOM_COLOR, lw=0.7))

ax.axhline(0, color='black', linewidth=0.6)
ax.set_xticks([x_text, x_cua])
ax.set_xticklabels(['Text-only\n(functional + semantic)', 'CUA\n(functional, DOM-bypass)'],
                   fontsize=8)
ax.set_ylabel('Drop from base under composite Low (pp)', fontsize=9)
ax.set_ylim(-20, 85)
ax.set_title('Contribution Decomposition of Composite-Low Effects (Claude)\n'
             'Functional pathway well-bounded; semantic residual CI crosses zero',
             fontsize=8.5, fontweight='bold', pad=10)
ax.legend(loc='upper right', fontsize=7, framealpha=0.9)

# Bounded-heuristic caption note: SSIM context
ax.text(-0.42, -16,
        'Composite Low is not visually equivalent to base (median SSIM=0.897):\n'
        'CUA 35.4pp = upper bound on functional pathway; 20.0pp = lower bound on semantic residual.',
        fontsize=6, color='#34495E', style='italic')

plt.tight_layout()
fig.savefig(OUT / "fig5_causal_decomposition.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "fig5_causal_decomposition.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none', metadata={'CreationDate': None})
plt.close()
print(f"OK fig5 saved: {OUT / 'fig5_causal_decomposition.png'}")
print(f"   functional(CUA)={cua_drop['point_estimate']}pp CI[{cua_drop['ci_lo']},{cua_drop['ci_hi']}]; "
      f"semantic={semantic['point_estimate']}pp CI[{semantic['ci_lo']},{semantic['ci_hi']}]; "
      f"text-only total={text_drop['point_estimate']}pp")

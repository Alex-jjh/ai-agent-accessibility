#!/usr/bin/env python3
"""
Figure 9: Compositional Interaction (paper §5.4, fig:composition)
=================================================================

Expected vs observed pairwise drop for the 28 operator pairs. Points above the
additivity diagonal are super-additive (amplification); below are sub-additive
(saturation). The L6+L11 amplifier (~+24pp interaction) is the visual anchor.

Unlike the previous version, the 28 pairs are NOT hardcoded — they are computed
live via the canonical analysis path (amt_statistics.test_compositional_interaction
on Mode A singletons + C.2 pairs with GT corrections), the SAME path the verifier
uses, guaranteeing the 15 super / 9 additive / 4 sub split and binomial p=0.019.

DATA SOURCE (canonical, GT-corrected):
  data/mode-a-shard-a, data/mode-a-shard-b   (singletons + H-baseline)
  data/c2-composition-shard-a, -b             (pairs)

OUTPUT: figures/fig9_composition.{png,pdf}
USAGE:  python3 figures/generate_fig9_composition.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.amt_statistics import load_cases, test_compositional_interaction

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300,
    'axes.spines.top': False, 'axes.spines.right': False,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data"

CAT_COLOR = {
    'super-additive': '#C0392B',
    'additive': '#7F8C8D',
    'sub-additive': '#2471A3',
}

# ── Compute the 28 pairs via the canonical path ──
singletons = load_cases([DATA / "mode-a-shard-a", DATA / "mode-a-shard-b"])
pairs = load_cases([DATA / "c2-composition-shard-a", DATA / "c2-composition-shard-b"])
results, summary = test_compositional_interaction(singletons, pairs, agent="text-only")
print(f"super={summary['super']} additive={summary['additive']} "
      f"sub={summary['sub']} binom_p={summary['binomial_p']:.4f}")

fig, ax = plt.subplots(figsize=(7, 7))
ax.plot([-10, 70], [-10, 70], 'k--', linewidth=0.8, alpha=0.4, zorder=1)
ax.fill_between([-10, 70], [-10, 70], [70, 70], alpha=0.03, color='#C0392B', zorder=0)
ax.fill_between([-10, 70], [-15, 65], [-10, 70], alpha=0.03, color='#2471A3', zorder=0)

for cat, color in CAT_COLOR.items():
    sub = [r for r in results if r['category'] == cat]
    if not sub:
        continue
    xs = [r['expected_drop_pp'] for r in sub]
    ys = [r['observed_drop_pp'] for r in sub]
    nice = {'super-additive': 'Super-additive', 'additive': 'Additive',
            'sub-additive': 'Sub-additive'}[cat]
    ax.scatter(xs, ys, c=color, s=60, alpha=0.8, edgecolors='white',
               linewidth=0.5, label=f"{nice} (n={len(sub)})", zorder=5)

# Annotate the amplifier anchors
by_pair = {r['pair']: r for r in results}
ANNOT = {'L6+L11': (8, 6), 'L9+L11': (8, 4), 'L1+L5': (-12, -8), 'L4+L5': (8, -4)}
for pair, (dx, dy) in ANNOT.items():
    r = by_pair.get(pair)
    if not r:
        continue
    ax.annotate(pair, xy=(r['expected_drop_pp'], r['observed_drop_pp']),
                xytext=(r['expected_drop_pp'] + dx, r['observed_drop_pp'] + dy),
                fontsize=7, fontweight='bold', color=CAT_COLOR[r['category']],
                arrowprops=dict(arrowstyle='->', color=CAT_COLOR[r['category']], lw=0.8),
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          edgecolor=CAT_COLOR[r['category']], alpha=0.9))

ax.set_xlabel('Expected drop (sum of individual operator drops, pp)', fontsize=9)
ax.set_ylabel('Observed pair drop (pp)', fontsize=9)
ax.set_xlim(-10, 70)
ax.set_ylim(-5, 60)
ax.set_aspect('equal')
ax.text(55, 15, 'Sub-additive\n(failure saturation)', fontsize=8,
        color='#2471A3', ha='center', style='italic', alpha=0.7)
ax.text(15, 50, 'Super-additive\n(amplification)', fontsize=8,
        color='#C0392B', ha='center', style='italic', alpha=0.7)
ax.set_title(f'Compositional Interaction: Expected vs Observed Pairwise Drop\n'
             f'(28 pairs, Claude text-only, GT-corrected; '
             f'{summary["super"]} super / {summary["additive"]} additive / '
             f'{summary["sub"]} sub, binomial p={summary["binomial_p"]:.3f})',
             fontsize=9.5, fontweight='bold', pad=12)
ax.legend(loc='upper left', fontsize=8, framealpha=0.9)

plt.tight_layout()
fig.savefig(OUT / "fig9_composition.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "fig9_composition.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"OK fig9 saved: {OUT / 'fig9_composition.png'}")

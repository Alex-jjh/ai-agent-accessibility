#!/usr/bin/env python3
"""
Figure 6: Token Consumption by Variant (paper §5.1, fig:token-violin)
=====================================================================

Per-case token consumption for the text-only Claude agent across the four
composite variants. Low accessibility inflates median token usage ~2.4x
(low median ~102.6K vs base ~42.3K) and produces long upper tails; the most
extreme base/low/high cases reach ~6.1e5 tokens.

This regenerates the previously script-less figure6_token_violin.png. It is
READ-ONLY w.r.t. the frozen data: it consumes the locked
results/trace-summaries.jsonl `total_tokens` field and writes a PNG/PDF only.

NOTE ON THE THROTTLE / CONTEXT-WINDOW ANNOTATION (LIT-OBS-5 coordination):
The earlier version of this figure drew a dashed line at "~200K context
window limit". The 608K-token tail and the provider-side volume/throttle
reality (see LIT-OBS-5) make a single 200K "failure threshold" line
misleading. This version draws the dashed reference at the empirically
observed Claude Sonnet input context window (200K tokens) and labels it as a
GENERIC context-window reference, not a per-case failure threshold; the
observed maxima exceed it, which the caption notes. If LIT-OBS-5 finalizes a
different throttle framing, the label here should be aligned to it.

DATA SOURCE (frozen):
  results/trace-summaries.jsonl   (text-only Claude rows, total_tokens)

OUTPUT: figures/fig6_token_violin.{png,pdf}
USAGE:  python3 figures/generate_fig6_token_violin.py
"""
import json
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300,
    'axes.spines.top': False, 'axes.spines.right': False,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
TRACES = ROOT / "results" / "trace-summaries.jsonl"

# Generic context-window reference (Claude Sonnet input window), NOT a
# per-case failure threshold (see module docstring / LIT-OBS-5).
CONTEXT_WINDOW_REF = 200_000

ORDER = ['low', 'medium-low', 'base', 'high']
LABELS = {'low': 'Low', 'medium-low': 'Med-low', 'base': 'Base', 'high': 'High'}
VARIANT_COLOR = {
    'low': '#C0392B', 'medium-low': '#E67E22', 'base': '#2C3E50', 'high': '#27AE60',
}


def main():
    by_variant = {v: [] for v in ORDER}
    with open(TRACES) as f:
        for line in f:
            d = json.loads(line)
            if d.get('agent_type') != 'text-only' or d.get('model') != 'claude-sonnet':
                continue
            v = d.get('variant')
            if v in by_variant:
                by_variant[v].append(d.get('total_tokens', 0))

    data = [np.array(by_variant[v], dtype=float) for v in ORDER]
    positions = np.arange(1, len(ORDER) + 1)

    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    parts = ax.violinplot(data, positions=positions, widths=0.8,
                          showmedians=True, showextrema=True)
    for i, body in enumerate(parts['bodies']):
        body.set_facecolor(VARIANT_COLOR[ORDER[i]])
        body.set_edgecolor('white')
        body.set_alpha(0.65)
    for key in ('cmedians', 'cmaxes', 'cmins', 'cbars'):
        if key in parts:
            parts[key].set_color('#34495E')
            parts[key].set_linewidth(1.0)

    # Overlay per-case points (jittered) so the long upper tails are visible
    rng = np.random.default_rng(20260607)
    for i, arr in enumerate(data):
        xj = positions[i] + rng.uniform(-0.12, 0.12, size=len(arr))
        ax.scatter(xj, arr, s=6, color=VARIANT_COLOR[ORDER[i]], alpha=0.35,
                   edgecolors='none', zorder=3)

    # Generic context-window reference line (NOT a failure threshold)
    ax.axhline(CONTEXT_WINDOW_REF, color='#7F8C8D', linestyle='--',
               linewidth=0.9, alpha=0.8)
    ax.text(len(ORDER) + 0.35, CONTEXT_WINDOW_REF,
            'context-window\nreference (200K)', fontsize=6.5,
            color='#7F8C8D', va='center', ha='left', style='italic')

    med_low = median(by_variant['low'])
    med_base = median(by_variant['base'])
    ratio = med_low / med_base
    ax.annotate(f"median {med_low/1e3:.0f}K\n({ratio:.1f}x base)",
                xy=(1, med_low), xytext=(1.05, med_low + 90_000),
                fontsize=6.5, color='#C0392B', style='italic',
                arrowprops=dict(arrowstyle='->', color='#C0392B', lw=0.7))

    ax.set_xticks(positions)
    ax.set_xticklabels([LABELS[v] for v in ORDER], fontsize=8)
    ax.set_ylabel('Total tokens per case (text-only Claude)', fontsize=9)
    ax.set_ylim(0, 660_000)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x/1e3:.0f}K'))
    ax.set_title('Token Consumption by Variant (text-only Claude)\n'
                 f'Low inflates median ~{ratio:.1f}x; tails reach ~6.1e5 tokens',
                 fontsize=8.5, fontweight='bold', pad=10)

    plt.tight_layout()
    fig.savefig(OUT / "fig6_token_violin.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    fig.savefig(OUT / "fig6_token_violin.pdf", bbox_inches='tight',
                facecolor='white', edgecolor='none', metadata={'CreationDate': None})
    plt.close()
    print(f"OK fig6 saved: {OUT / 'fig6_token_violin.png'}")
    for v in ORDER:
        arr = by_variant[v]
        print(f"   {v}: n={len(arr)} median={median(arr):.0f} max={max(arr)}")
    print(f"   low/base median ratio = {ratio:.2f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate remaining paper figures:
  - Figure 3: L1/L2/L3 Severity Framework infographic
  - Figure 5: Causal Decomposition schematic (redone with new data + human analog)
  - Table 2: Per-task success heatmap (Claude text-only)

Also handles renaming per the final naming convention.
"""
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300})

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures"

# Shared palette
C_LOW = '#C0392B'; C_ML = '#E67E22'; C_BASE = '#2471A3'; C_HIGH = '#27AE60'
BORDER = '#2C3E50'

def _box(ax, x, y, w, h, text, fc, fs=7, bold=False, ec=BORDER, lw=0.7, tc='black', al=1.0, va='center'):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=al)
    ax.add_patch(r)
    if text:
        ax.text(x + w/2, y + h/2, text, fontsize=fs, fontweight='bold' if bold else 'normal',
                ha='center', va=va, color=tc, linespacing=1.3)

def _lbl(ax, x, y, text, fs=7, c='black', ha='center', va='center', wt='normal', sty='normal'):
    ax.text(x, y, text, fontsize=fs, color=c, ha=ha, va=va, fontweight=wt, fontstyle=sty, linespacing=1.2)

def _arr(ax, x1, y1, x2, y2, c=BORDER, lw=1.2, ls='-'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw, linestyle=ls))


# ============================================================
# Figure 3: L1/L2/L3 Severity Framework
# ============================================================
def figure3_severity():
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis('off'); ax.set_aspect('equal')

    cols = [
        {
            'label': 'L1 Decorative', 'color': '#95A5A6', 'fill': '#F2F3F4',
            'icon': '[img]', 'x': 0.3,
            'definition': 'Missing alt text on\ndecorative images,\nempty headings',
            'code': '<img src="logo.png">\n(no alt attribute)',
            'prevalence': '~70% of sites',
            'human': 'Minor — screen\nreaders skip',
            'agent': 'None\n(0pp impact)',
        },
        {
            'label': 'L2 Annotational', 'color': '#F39C12', 'fill': '#FEF9E7',
            'icon': '[tag]', 'x': 4.1,
            'definition': 'Missing/wrong ARIA\nlabels, broken form\nlabel associations',
            'code': '<button>✕</button>\n(no aria-label)',
            'prevalence': '~20% of sites',
            'human': 'Moderate —\nconfusing labels',
            'agent': 'None\n(0pp impact)',
        },
        {
            'label': 'L3 Structural', 'color': C_LOW, 'fill': '#FDEDEC',
            'icon': '[DOM]', 'x': 7.9,
            'definition': 'Semantic HTML replaced\nwith generic containers\n(<nav>→<div>, <a>→<span>)',
            'code': '<div onclick="...">\n  instead of <button>',
            'prevalence': '83.3% of 34 sites',
            'human': 'Severe —\nnavigation breaks',
            'agent': 'Catastrophic\n(−55pp)',
        },
    ]

    col_w = 3.5
    for col in cols:
        x = col['x']
        ec = col['color']
        fc = col['fill']
        lw = 1.2 if col['label'] != 'L3 Structural' else 2.5

        # Column background
        _box(ax, x, 0.3, col_w, 5.2, '', fc, ec=ec, lw=lw)

        # Header
        _lbl(ax, x + col_w/2, 5.2, col['icon'], fs=16)
        _lbl(ax, x + col_w/2, 4.85, col['label'], fs=10, wt='bold', c=ec)

        # Definition
        _lbl(ax, x + col_w/2, 4.2, col['definition'], fs=7.5, c='#333')

        # Code example box
        _box(ax, x + 0.2, 3.2, col_w - 0.4, 0.7, col['code'],
             '#2C3E50', fs=7, tc='#ECF0F1', ec='#1A252F', lw=0.5)

        # Prevalence
        _lbl(ax, x + col_w/2, 2.75, 'Prevalence:', fs=7, wt='bold', c='#555')
        _lbl(ax, x + col_w/2, 2.45, col['prevalence'], fs=8, wt='bold', c=ec)

        # Human impact
        _lbl(ax, x + col_w/2, 2.0, 'Human impact:', fs=7, wt='bold', c='#555')
        _lbl(ax, x + col_w/2, 1.65, col['human'], fs=7.5, c='#333')

        # Agent impact
        _lbl(ax, x + col_w/2, 1.15, 'Agent impact:', fs=7, wt='bold', c='#555')
        agent_c = ec if col['label'] == 'L3 Structural' else '#27AE60'
        _lbl(ax, x + col_w/2, 0.8, col['agent'], fs=8, wt='bold', c=agent_c)

    # Bottom summary
    _lbl(ax, 6, 0.05,
         'Web accessibility is traditionally treated as a uniform compliance problem. '
         'Our data shows only L3 violations cascade into AI agent failure.',
         fs=8, wt='bold', c='#333')

    fig.savefig(OUT / "figure3_severity_framework.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("✅ Figure 3 (L1/L2/L3 Severity Framework) saved")
    print("   30s takeaway: Only L3 structural violations are fatal to agents")


# ============================================================
# Figure 5: Causal Decomposition (redone with new data)
# ============================================================
def figure5_causal():
    # Compute from CSV
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
    cua = df[(df["agent_type"] == "cua") & (df["model"] == "claude-sonnet")]
    som = df[(df["agent_type"] == "vision-only") & (df["model"] == "claude-sonnet")]

    text_base = 100 * tc[tc["variant"] == "base"]["success"].mean()
    text_low = 100 * tc[tc["variant"] == "low"]["success"].mean()
    cua_base = 100 * cua[cua["variant"] == "base"]["success"].mean()
    cua_low = 100 * cua[cua["variant"] == "low"]["success"].mean()
    som_base = 100 * som[som["variant"] == "base"]["success"].mean()
    som_low = 100 * som[som["variant"] == "low"]["success"].mean()

    text_drop = text_base - text_low
    cua_drop = cua_base - cua_low
    som_drop = som_base - som_low
    semantic = text_drop - cua_drop

    print(f"  Text-only drop: {text_drop:.1f}pp | CUA drop: {cua_drop:.1f}pp | "
          f"Semantic: {semantic:.1f}pp | SoM drop: {som_drop:.1f}pp")

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.set_xlim(0, 12); ax.set_ylim(-0.5, 6.5); ax.axis('off'); ax.set_aspect('equal')

    # Source: L3 Violation
    _box(ax, 0.2, 2.5, 2.5, 1.8, '', '#FADBD8', ec=C_LOW, lw=2.5)
    _lbl(ax, 1.45, 3.7, 'L3 Structural\nViolation', fs=11, wt='bold', c='#922B21')
    _lbl(ax, 1.45, 2.9, '<nav>→<div>\n<a>→<span>', fs=7, c='#922B21')

    # ── Semantic Pathway (top, blue) ──
    _arr(ax, 2.7, 4.0, 4.5, 5.0, c='#2E86C1', lw=2.5)
    _box(ax, 4.5, 4.5, 2.8, 1.2, 'A11y Tree\nDegraded\n(labels, roles lost)', '#D6EAF8', fs=8, ec='#2E86C1', lw=1.5)
    _arr(ax, 7.3, 5.1, 8.5, 5.1, c='#2E86C1', lw=2.5)
    _box(ax, 8.5, 4.5, 2.0, 1.2, '', '#AED6F1', ec='#2E86C1', lw=1.5)
    _lbl(ax, 9.5, 5.3, 'Text-only\nAgent Fails', fs=9, wt='bold', c='#1A5276')
    _lbl(ax, 9.5, 4.75, f'~{semantic:.0f}pp', fs=11, wt='bold', c='#2E86C1')
    _lbl(ax, 3.6, 5.8, 'Semantic Pathway', fs=9, wt='bold', c='#2E86C1', sty='italic')

    # Human analog: screen reader
    _lbl(ax, 10.8, 5.5, 'SR', fs=12, wt='bold', c='#2E86C1')
    _lbl(ax, 10.8, 5.0, 'Screen reader\nusers face same\nsemantic loss', fs=6.5, c='#2E86C1', sty='italic')

    # ── Functional Pathway (bottom, orange) ──
    _arr(ax, 2.7, 2.8, 4.5, 1.8, c='#E67E22', lw=2.5)
    _box(ax, 4.5, 1.2, 2.8, 1.2, 'DOM Structure\nBroken\n(hrefs, handlers lost)', '#FDEBD0', fs=8, ec='#E67E22', lw=1.5)
    _arr(ax, 7.3, 1.8, 8.5, 1.8, c='#E67E22', lw=2.5)
    _box(ax, 8.5, 1.2, 2.0, 1.2, '', '#F5CBA7', ec='#E67E22', lw=1.5)
    _lbl(ax, 9.5, 2.0, 'CUA Agent\nFails', fs=9, wt='bold', c='#784212')
    _lbl(ax, 9.5, 1.45, f'~{cua_drop:.0f}pp', fs=11, wt='bold', c='#E67E22')
    _lbl(ax, 3.6, 0.7, 'Functional Pathway', fs=9, wt='bold', c='#E67E22', sty='italic')

    # Human analog: keyboard nav
    _lbl(ax, 10.8, 2.2, 'KB', fs=12, wt='bold', c='#E67E22')
    _lbl(ax, 10.8, 1.7, 'Keyboard-nav\nusers face same\nstructural loss', fs=6.5, c='#E67E22', sty='italic')

    # ── SoM branch (dashed, purple) ──
    _arr(ax, 7.3, 1.5, 8.5, 0.3, c='#8E44AD', lw=1.5, ls='--')
    _lbl(ax, 9.5, 0.3, f'SoM: phantom bids\n({som_low:.1f}% at low)', fs=7.5, c='#8E44AD', sty='italic')
    _lbl(ax, 9.5, -0.15, f'Δ ≈ {som_drop:.0f}pp', fs=8, wt='bold', c='#8E44AD')

    # Decomposition logic box
    _lbl(ax, 6, -0.4,
         f'Decomposition: text-only drop ({text_drop:.0f}pp) − CUA drop ({cua_drop:.0f}pp) '
         f'= {semantic:.0f}pp semantic pathway (upper-bound estimate)',
         fs=7.5, c='#555',)

    fig.savefig(OUT / "figure5_causal_decomposition.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("✅ Figure 5 (Causal Decomposition) saved")
    print(f"   30s takeaway: Two pathways — ~{semantic:.0f}pp semantic + ~{cua_drop:.0f}pp functional")


# ============================================================
# Table 2: Per-task Success Heatmap (Claude text-only)
# ============================================================
def table2_heatmap():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
    meta = pd.read_csv(ROOT / "results" / "task-metadata.csv")

    tasks = sorted(tc["task_id"].unique())
    variant_order = ['low', 'medium-low', 'base', 'high']
    variant_labels = ['Low', 'M-L', 'Base', 'High']

    matrix = []
    labels = []
    for tid in tasks:
        m = meta[meta["task_id"] == tid].iloc[0] if tid in meta["task_id"].values else None
        app = m["app_short"] if m is not None else "?"
        depth = m["nav_depth"] if m is not None else "?"
        labels.append(f"{tid} ({app}, {depth})")
        row = []
        for v in variant_order:
            cell = tc[(tc["task_id"] == tid) & (tc["variant"] == v)]
            rate = 100 * cell["success"].mean() if len(cell) > 0 else 0
            row.append(rate)
        matrix.append(row)

    matrix = np.array(matrix)
    deltas = matrix[:, 2] - matrix[:, 0]  # base - low

    # Print stats
    print(f"  Tasks: {len(tasks)} | Mean Low: {matrix[:,0].mean():.1f}% | "
          f"Mean Base: {matrix[:,2].mean():.1f}% | Mean Δ: {deltas.mean():.1f}pp | "
          f"SD Δ: {deltas.std():.1f}pp")
    print(f"  All tasks show Δ ≥ 0pp: {(deltas >= 0).all()}")

    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

    ax.set_xticks(range(4))
    ax.set_xticklabels(variant_labels, fontsize=9)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel('Accessibility Variant', fontsize=10)
    ax.set_ylabel('Task ID (app, nav depth)', fontsize=10)

    # Cell text
    for i in range(len(tasks)):
        for j in range(4):
            val = matrix[i, j]
            color = 'white' if val < 30 or val > 85 else 'black'
            ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=color)

    # Delta column annotation
    for i in range(len(tasks)):
        d = deltas[i]
        c = C_LOW if d > 30 else (C_ML if d > 0 else C_HIGH)
        ax.text(4.3, i, f'−{d:.0f}pp' if d > 0 else f'{d:.0f}pp',
                ha='center', va='center', fontsize=7.5, color=c, fontweight='bold')
    ax.text(4.3, -0.8, 'Δ(B−L)', ha='center', va='center', fontsize=8, fontweight='bold')

    # Summary row
    means = matrix.mean(axis=0)
    ax.text(-0.5, len(tasks) + 0.3, 'Mean:', ha='right', va='center', fontsize=8, fontweight='bold')
    for j in range(4):
        ax.text(j, len(tasks) + 0.3, f'{means[j]:.1f}', ha='center', va='center',
                fontsize=8, fontweight='bold', color='#333')
    ax.text(4.3, len(tasks) + 0.3, f'−{deltas.mean():.1f}', ha='center', va='center',
            fontsize=8, fontweight='bold', color=C_LOW)

    cbar = plt.colorbar(im, ax=ax, shrink=0.75, pad=0.15)
    cbar.set_label('Success Rate (%)', fontsize=9)

    plt.tight_layout()
    fig.savefig(OUT / "table2_per_task_heatmap.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("✅ Table 2 (Per-task Heatmap) saved")
    print(f"   30s takeaway: Effect consistent across all 13 tasks (SD={deltas.std():.1f}pp)")


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("Generating remaining figures...")
    print("=" * 60)

    print("\n--- Figure 3: L1/L2/L3 Severity Framework ---")
    figure3_severity()

    print("\n--- Figure 5: Causal Decomposition ---")
    figure5_causal()

    print("\n--- Table 2: Per-task Heatmap ---")
    table2_heatmap()

    print("\n" + "=" * 60)
    print("All figures generated.")
    print("=" * 60)

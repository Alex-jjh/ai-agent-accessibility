#!/usr/bin/env python3
"""
Generate all paper figures from combined-experiment.csv.
Outputs to experiment/figures/ as 300dpi PNG files.

Figures:
  - figure2_main_results.png  (2×2 grouped bar chart)
  - figure3_token_violin.png  (violin + boxplot)
  - figure5_per_task_heatmap.png (13-task heatmap table)
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")

# Color scheme
COLORS = {
    'low': '#C0392B',
    'medium-low': '#E67E22',
    'base': '#2E86C1',
    'high': '#27AE60',
}
VARIANT_ORDER = ['low', 'medium-low', 'base', 'high']
VARIANT_LABELS = ['Low', 'Med-Low', 'Base', 'High']

# ============================================================
# Figure 2: Main Results — 2×2 panel bar chart
# ============================================================
def figure2():
    combos = [
        ("text-only", "claude-sonnet", "Text-only Claude"),
        ("vision-only", "claude-sonnet", "SoM Claude"),
        ("cua", "claude-sonnet", "CUA Claude"),
        ("text-only", "llama4-maverick", "Text-only Llama 4"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    fig.suptitle("", fontsize=1)  # no suptitle, caption in LaTeX

    for idx, (agent, model, label) in enumerate(combos):
        ax = axes[idx // 2][idx % 2]
        sub = df[(df["agent_type"] == agent) & (df["model"] == model)]

        rates = []
        for v in VARIANT_ORDER:
            vdf = sub[sub["variant"] == v]
            rate = 100 * vdf["success"].mean() if len(vdf) > 0 else 0
            rates.append(rate)

        bars = ax.bar(range(4), rates,
                      color=[COLORS[v] for v in VARIANT_ORDER],
                      edgecolor='white', linewidth=0.5, width=0.7)

        # Value labels on top
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                    f'{rate:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_xticks(range(4))
        ax.set_xticklabels(VARIANT_LABELS, fontsize=9)
        ax.set_ylim(0, 115)
        ax.set_ylabel('Success Rate (%)' if idx % 2 == 0 else '', fontsize=10)
        ax.set_title(label, fontsize=11, fontweight='bold', pad=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.axhline(y=50, color='#CCCCCC', linestyle=':', linewidth=0.5)

        # Step-function annotation for Claude text-only
        if agent == "text-only" and model == "claude-sonnet":
            ax.annotate('', xy=(1, rates[1]-2), xytext=(0, rates[0]+2),
                        arrowprops=dict(arrowstyle='->', color='#333333', lw=1.5))
            ax.text(0.5, (rates[0]+rates[1])/2, f'+{rates[1]-rates[0]:.1f}pp',
                    ha='center', va='center', fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF3CD', edgecolor='#E67E22', alpha=0.9))

        # SoM baseline annotation
        if agent == "vision-only":
            ax.axhline(y=27.7, color='#999999', linestyle='--', linewidth=1)
            ax.text(3.4, 29, 'SoM baseline\n(see §5.6)', fontsize=7,
                    ha='right', va='bottom', color='#666666', style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / "figure2_main_results.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"✅ Figure 2 saved: {OUT / 'figure2_main_results.png'}")


# ============================================================
# Figure 3: Token Consumption Violin Plot
# ============================================================
def figure3():
    # Text-only Claude only (primary agent)
    tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")].copy()
    tc = tc[tc["total_tokens"].notna() & (tc["total_tokens"] > 0)]
    tc["tokens_k"] = tc["total_tokens"] / 1000

    fig, ax = plt.subplots(figsize=(8, 5))

    positions = range(4)
    data_by_variant = []
    for v in VARIANT_ORDER:
        vdata = tc[tc["variant"] == v]["tokens_k"].values
        data_by_variant.append(vdata)

    parts = ax.violinplot(data_by_variant, positions=positions,
                          showmeans=False, showmedians=False, showextrema=False)

    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(COLORS[VARIANT_ORDER[i]])
        pc.set_alpha(0.6)
        pc.set_edgecolor(COLORS[VARIANT_ORDER[i]])

    # Overlay boxplots
    bp = ax.boxplot(data_by_variant, positions=positions, widths=0.15,
                    patch_artist=True, showfliers=True,
                    flierprops=dict(marker='o', markersize=3, alpha=0.4),
                    medianprops=dict(color='white', linewidth=2),
                    boxprops=dict(linewidth=0.5),
                    whiskerprops=dict(linewidth=0.5),
                    capprops=dict(linewidth=0.5))
    for i, patch in enumerate(bp['boxes']):
        patch.set_facecolor(COLORS[VARIANT_ORDER[i]])
        patch.set_alpha(0.8)

    # Context window limit line
    ax.axhline(y=200, color='#E74C3C', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.5, 205, 'Context limit (~200K)', fontsize=8, color='#E74C3C',
            ha='right', va='bottom', style='italic')

    # Median annotation for Low vs Base
    low_med = np.median(data_by_variant[0])
    base_med = np.median(data_by_variant[2])
    ax.annotate(f'Low median: {low_med:.0f}K\nBase median: {base_med:.0f}K\n({low_med/base_med:.1f}×)',
                xy=(0, low_med), xytext=(0.8, low_med + 80),
                fontsize=8, ha='center',
                arrowprops=dict(arrowstyle='->', color='#666666', lw=1),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF3CD', edgecolor='#E67E22', alpha=0.9))

    ax.set_xticks(positions)
    ax.set_xticklabels(VARIANT_LABELS, fontsize=10)
    ax.set_ylabel('Token Consumption (K)', fontsize=11)
    ax.set_xlabel('Accessibility Variant', fontsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(OUT / "figure3_token_violin.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"✅ Figure 3 saved: {OUT / 'figure3_token_violin.png'}")


# ============================================================
# Figure 5: Per-Task Heatmap (Table 5 as visual)
# ============================================================
def figure5_heatmap():
    # Claude text-only only
    tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]

    tasks = sorted(tc["task_id"].unique())
    task_meta = pd.read_csv(ROOT / "results" / "task-metadata.csv")

    matrix = []
    labels = []
    for tid in tasks:
        row = []
        meta = task_meta[task_meta["task_id"] == tid].iloc[0] if tid in task_meta["task_id"].values else None
        app = meta["app_short"] if meta is not None else "?"
        depth = meta["nav_depth"] if meta is not None else "?"
        labels.append(f"{tid} ({app}, {depth})")
        for v in VARIANT_ORDER:
            cell = tc[(tc["task_id"] == tid) & (tc["variant"] == v)]
            rate = 100 * cell["success"].mean() if len(cell) > 0 else 0
            row.append(rate)
        matrix.append(row)

    matrix = np.array(matrix)

    fig, ax = plt.subplots(figsize=(7, 6))

    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

    ax.set_xticks(range(4))
    ax.set_xticklabels(VARIANT_LABELS, fontsize=10)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Accessibility Variant', fontsize=11)
    ax.set_ylabel('Task ID (app, nav depth)', fontsize=11)

    # Text annotations in cells
    for i in range(len(tasks)):
        for j in range(4):
            val = matrix[i, j]
            color = 'white' if val < 40 or val > 80 else 'black'
            ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=color)

    # Add delta column
    # Draw it as text to the right
    for i in range(len(tasks)):
        delta = matrix[i, 2] - matrix[i, 0]  # base - low
        ax.text(4.3, i, f'−{delta:.0f}pp' if delta > 0 else f'+{abs(delta):.0f}pp',
                ha='center', va='center', fontsize=8,
                color='#C0392B' if delta > 30 else '#E67E22')
    ax.text(4.3, -0.8, 'Δ(B−L)', ha='center', va='center', fontsize=9, fontweight='bold')

    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.15)
    cbar.set_label('Success Rate (%)', fontsize=10)

    plt.tight_layout()
    fig.savefig(OUT / "figure5_per_task_heatmap.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"✅ Figure 5 saved: {OUT / 'figure5_per_task_heatmap.png'}")


# ============================================================
# Figure 4: Causal Decomposition Schematic
# ============================================================
def figure4_schematic():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Source box
    ax.add_patch(plt.Rectangle((0.3, 2.2), 2.2, 1.6, facecolor='#FADBD8',
                                edgecolor='#C0392B', linewidth=2, zorder=2))
    ax.text(1.4, 3.0, 'L3 Structural\nViolation', ha='center', va='center',
            fontsize=11, fontweight='bold', color='#922B21')
    ax.text(1.4, 2.5, '<nav>→<div>\n<a>→<span>', ha='center', va='center',
            fontsize=7, color='#922B21', family='monospace')

    # Semantic pathway (top)
    ax.annotate('', xy=(4.5, 4.2), xytext=(2.5, 3.5),
                arrowprops=dict(arrowstyle='->', color='#2E86C1', lw=2.5))
    ax.add_patch(plt.Rectangle((4.5, 3.6), 2.5, 1.2, facecolor='#D6EAF8',
                                edgecolor='#2E86C1', linewidth=1.5, zorder=2))
    ax.text(5.75, 4.2, 'A11y Tree\nDegraded', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#1A5276')

    ax.annotate('', xy=(8.2, 4.2), xytext=(7.0, 4.2),
                arrowprops=dict(arrowstyle='->', color='#2E86C1', lw=2.5))
    ax.add_patch(plt.Rectangle((8.2, 3.6), 1.5, 1.2, facecolor='#AED6F1',
                                edgecolor='#2E86C1', linewidth=1.5, zorder=2))
    ax.text(8.95, 4.4, 'Text-only\nAgent Fails', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#1A5276')
    ax.text(8.95, 3.8, '~20pp', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#2E86C1')

    # Label
    ax.text(3.5, 4.8, 'Semantic Pathway', fontsize=10, fontweight='bold',
            color='#2E86C1', style='italic')

    # Functional pathway (bottom)
    ax.annotate('', xy=(4.5, 1.8), xytext=(2.5, 2.5),
                arrowprops=dict(arrowstyle='->', color='#E67E22', lw=2.5))
    ax.add_patch(plt.Rectangle((4.5, 1.2), 2.5, 1.2, facecolor='#FDEBD0',
                                edgecolor='#E67E22', linewidth=1.5, zorder=2))
    ax.text(5.75, 1.8, 'DOM Structure\nBroken', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#784212')

    ax.annotate('', xy=(8.2, 1.8), xytext=(7.0, 1.8),
                arrowprops=dict(arrowstyle='->', color='#E67E22', lw=2.5))
    ax.add_patch(plt.Rectangle((8.2, 1.2), 1.5, 1.2, facecolor='#F5CBA7',
                                edgecolor='#E67E22', linewidth=1.5, zorder=2))
    ax.text(8.95, 2.0, 'CUA Agent\nFails', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#784212')
    ax.text(8.95, 1.4, '~35pp', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#E67E22')

    # Label
    ax.text(3.5, 0.8, 'Functional Pathway', fontsize=10, fontweight='bold',
            color='#E67E22', style='italic')

    # SoM branch from functional
    ax.annotate('', xy=(8.2, 0.4), xytext=(7.0, 1.4),
                arrowprops=dict(arrowstyle='->', color='#8E44AD', lw=1.5, linestyle='dashed'))
    ax.text(8.95, 0.4, 'SoM: phantom\nbids (4.6%)', ha='center', va='center',
            fontsize=8, color='#8E44AD', style='italic')

    # Decomposition logic box at bottom
    ax.text(5.0, -0.2, 'Decomposition: text-only drop (55pp) − CUA drop (35pp) = 20pp semantic pathway',
            ha='center', va='center', fontsize=8, color='#555555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F8F9FA', edgecolor='#CCCCCC'))

    plt.tight_layout()
    fig.savefig(OUT / "figure4_causal_decomposition.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"✅ Figure 4 saved: {OUT / 'figure4_causal_decomposition.png'}")


# ============================================================
# Run all
# ============================================================
if __name__ == "__main__":
    print("Generating paper figures...")
    figure2()
    figure3()
    figure4_schematic()
    figure5_heatmap()
    print("\nAll figures generated.")

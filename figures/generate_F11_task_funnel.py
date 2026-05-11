#!/usr/bin/env python3
"""
F11: Task Selection Funnel — 684 → 48 tasks
============================================
Visualizes the 7-gate pre-registered exclusion pipeline.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np

# ── Data from exclusion-report.md ──────────────────────────────────────
stages = [
    ("WebArena\n(4 apps)", 684, "#2471A3"),
    ("After infra\nfailures\n(Gates 1–2)", 684 - 15 - 6, "#2471A3"),  # 663
    ("After stochastic\nbase\n(Gate 3)", 684 - 15 - 6 - 258, "#2471A3"),  # 405
    ("After trivial\ntasks\n(Gate 4)", 684 - 15 - 6 - 258 - 155, "#2471A3"),  # 250
    ("After step\nbudget\n(Gate 5)", 684 - 15 - 6 - 258 - 155 - 1, "#2471A3"),  # 249
    ("After state\nmutation\n(Gate 6)", 684 - 15 - 6 - 258 - 155 - 1 - 165, "#2471A3"),  # 84
    ("After trivial\nref answer\n(Gate 7)", 48, "#27AE60"),  # 48
]

# Verify arithmetic
assert stages[1][1] == 663, f"Expected 663, got {stages[1][1]}"
assert stages[2][1] == 405, f"Expected 405, got {stages[2][1]}"
assert stages[3][1] == 250, f"Expected 250, got {stages[3][1]}"
assert stages[4][1] == 249, f"Expected 249, got {stages[4][1]}"
assert stages[5][1] == 84, f"Expected 84, got {stages[5][1]}"
assert stages[6][1] == 48, f"Expected 48, got {stages[6][1]}"

# Exclusion counts per gate
exclusions = [
    ("Infra failures\n(goto timeout, crash)", 21, "#E74C3C"),
    ("Stochastic base\n(<3/3 success)", 258, "#E74C3C"),
    ("Trivial tasks\n(<3 steps)", 155, "#E74C3C"),
    ("Step budget\n(>25 steps)", 1, "#E74C3C"),
    ("State mutation\n(url_match/program_html)", 165, "#E74C3C"),
    ("Trivial ref answer\n(≤2 char tokens)", 36, "#E74C3C"),
]

fig, ax = plt.subplots(figsize=(10, 7))
ax.set_xlim(0, 10)
ax.set_ylim(0, len(stages) + 0.5)
ax.axis('off')

# Draw funnel boxes
box_width_max = 8.0
box_height = 0.65
y_positions = np.linspace(len(stages) - 0.5, 0.5, len(stages))

for i, (label, n, color) in enumerate(stages):
    y = y_positions[i]
    # Width proportional to n
    w = box_width_max * (n / 684)
    x_left = (10 - w) / 2
    
    # Box
    rect = mpatches.FancyBboxPatch(
        (x_left, y - box_height/2), w, box_height,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.85
    )
    ax.add_patch(rect)
    
    # Count label inside box
    ax.text(5, y, f"n = {n}", ha='center', va='center',
            fontsize=11, fontweight='bold', color='white')
    
    # Stage label on left
    ax.text(x_left - 0.2, y, label, ha='right', va='center',
            fontsize=8.5, color='#2C3E50', linespacing=1.3)
    
    # Arrow down (except last)
    if i < len(stages) - 1:
        y_next = y_positions[i + 1]
        ax.annotate('', xy=(5, y_next + box_height/2 + 0.05),
                    xytext=(5, y - box_height/2 - 0.05),
                    arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.5))
        
        # Exclusion annotation on right
        excl_label, excl_n, excl_color = exclusions[i]
        y_mid = (y + y_next) / 2
        ax.text(8.8, y_mid, f"−{excl_n}", ha='right', va='center',
                fontsize=9, color=excl_color, fontweight='bold')
        ax.text(9.0, y_mid, excl_label, ha='left', va='center',
                fontsize=7.5, color='#7F8C8D', linespacing=1.2)
        # Horizontal line to exclusion
        ax.plot([5 + box_width_max * (stages[i][1] / 684) / 2 + 0.1, 8.7],
                [y_mid, y_mid], color='#BDC3C7', lw=0.8, linestyle='--')

# Title
ax.text(5, len(stages) + 0.1, 'Task Selection Funnel: 684 → 48 Tasks',
        ha='center', va='bottom', fontsize=13, fontweight='bold', color='#2C3E50')

# App breakdown at bottom
ax.text(5, -0.1,
        'Final 48 tasks: ecommerce (22) · ecommerce_admin (12) · gitlab (13) · reddit (1)',
        ha='center', va='top', fontsize=9, color='#27AE60', style='italic')

plt.tight_layout()
plt.savefig('figures/F11_task_funnel.png', dpi=300, bbox_inches='tight',
            facecolor='white')
plt.savefig('figures/F11_task_funnel.pdf', bbox_inches='tight',
            facecolor='white')
print("Saved: figures/F11_task_funnel.{png,pdf}")

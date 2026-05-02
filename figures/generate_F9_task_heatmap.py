#!/usr/bin/env python3.11
"""
Figure F9: Per-Task × Operator Heatmap (Supplementary)
=======================================================

PURPOSE (supplementary material):
  Show the full 13 tasks × 26 operators success rate matrix. Reveals
  which tasks are operator-sensitive (task 67, task 4) vs operator-immune
  (task 132, task 188), and which operators are task-specific vs universal.

DESIGN RATIONALE:
  - Large heatmap: rows = 13 tasks, columns = 26 operators
  - Cell color: 0% (dark red) → 100% (dark green), white at 50%
  - Cell text: success percentage (3 reps per cell, so 0/33/67/100%)
  - Rows sorted by app then task ID (grouped by application)
  - Columns sorted by behavioral drop (matches F4 order)
  - Row annotations: app name + task description

WHY THIS DESIGN:
  - The full matrix is too large for the main paper but essential for
    supplementary (reviewers will want to see per-task breakdowns)
  - Color makes patterns pop: task 67's column of reds vs task 132's all-greens
  - Matching column order with F4 maintains visual consistency
  - App grouping shows that admin tasks are most operator-sensitive

DATA SOURCE:
  data/mode-a-shard-a/ + data/mode-a-shard-b/ (raw case JSON files)
  scripts/amt/ground-truth-corrections.json

OUTPUT:
  figures/F9_task_heatmap.png (300 DPI)
  figures/F9_task_heatmap.pdf (vector)

USAGE:
  python3.11 figures/generate_F9_task_heatmap.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import json, glob
from pathlib import Path
from collections import defaultdict

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 7,
    'figure.dpi': 300,
})

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent

# ── Operator order (sorted by behavioral drop, from F4) ──
OP_ORDER = [
    "L1", "L5", "L12", "L10", "L2", "L9", "L13", "ML1", "H4",
    "L4", "L7", "L8", "L11", "ML2", "H2", "H3", "H5b", "H7",
    "ML3", "L3", "H1", "H5c", "H8", "L6", "H5a", "H6",
]

# ── Task metadata ──
TASK_META = {
    "4": "admin: Top-3 bestsellers",
    "41": "admin: Top search term",
    "94": "admin: Invoice grand total",
    "198": "admin: Cancelled order customer",
    "23": "ecom: Reviewers (fingerprint)",
    "24": "ecom: Reviewers (unfair price)",
    "26": "ecom: Reviewers (customer svc)",
    "188": "ecom: Cancelled order cost",
    "29": "reddit: Count downvoted comments",
    "67": "reddit: Book names top 10",
    "132": "gitlab: Commits by kilian",
    "293": "gitlab: SSH clone command",
    "308": "gitlab: Top contributor",
}

TASK_ORDER = ["4", "41", "94", "198", "23", "24", "26", "188", "29", "67", "132", "293", "308"]

# ── Load GT corrections ──
with open(ROOT / "scripts" / "amt" / "ground-truth-corrections.json") as f:
    corrections = json.load(f)["corrections"]
ADDITIONAL_GT = {}
for tid, info in corrections.items():
    ADDITIONAL_GT[tid] = [a.lower() for a in info["additional_valid"]]

# ── Load Mode A cases (text-only only) ──
data_dirs = [ROOT / "data" / "mode-a-shard-a", ROOT / "data" / "mode-a-shard-b"]
# Build: op_task_stats[(opId, taskId)] = {"ok": N, "total": N}
op_task_stats = defaultdict(lambda: {"ok": 0, "total": 0})

for data_dir in data_dirs:
    for fpath in glob.glob(str(data_dir / "*/cases/*.json")):
        if "/scan-result" in fpath or "/trace-attempt" in fpath or "/classification" in fpath:
            continue
        with open(fpath) as fh:
            d = json.load(fh)
        cid = d.get("caseId", "")
        parts = cid.split(":")
        if len(parts) != 6:
            continue
        t = d.get("trace", {})
        agent = t.get("agentConfig", {}).get("observationMode", "?")
        if agent != "text-only":
            continue
        tid = parts[2]
        opId = parts[5]
        original_success = t.get("success", False)

        # Extract answer for GT correction
        answer = ""
        for s in t.get("steps", []):
            a = s.get("action", "")
            if "send_msg_to_user" in a:
                answer = a
                break

        corrected_success = original_success
        if tid in ADDITIONAL_GT and not original_success and answer:
            answer_lower = answer.lower()
            for valid in ADDITIONAL_GT[tid]:
                if valid in answer_lower:
                    corrected_success = True
                    break

        op_task_stats[(opId, tid)]["total"] += 1
        if corrected_success:
            op_task_stats[(opId, tid)]["ok"] += 1

# ── Build matrix ──
matrix = np.zeros((len(TASK_ORDER), len(OP_ORDER)))
for i, tid in enumerate(TASK_ORDER):
    for j, op in enumerate(OP_ORDER):
        stats = op_task_stats[(op, tid)]
        if stats["total"] > 0:
            matrix[i, j] = stats["ok"] / stats["total"] * 100
        else:
            matrix[i, j] = np.nan

# ── Plot ──
fig, ax = plt.subplots(figsize=(14, 6))

# Custom colormap: red (0%) → white (50%) → green (100%)
from matplotlib.colors import LinearSegmentedColormap
colors_list = ['#C0392B', '#FADBD8', '#FFFFFF', '#D5F5E3', '#27AE60']
cmap = LinearSegmentedColormap.from_list('rg', colors_list, N=256)

sns.heatmap(
    matrix, ax=ax, cmap=cmap, vmin=0, vmax=100,
    linewidths=0.5, linecolor='white',
    annot=True, fmt='.0f', annot_kws={'size': 6},
    cbar_kws={'label': 'Success Rate (%)', 'shrink': 0.8},
    xticklabels=OP_ORDER,
    yticklabels=[TASK_META[t] for t in TASK_ORDER],
)

# Title
ax.set_title('Per-Task × Per-Operator Success Rate (Claude Text-Only, GT-Corrected)\n'
             'N=3 reps per cell. Operators sorted by overall behavioral drop (left=most destructive).',
             fontsize=9, fontweight='bold', pad=12)

ax.set_xlabel('Operator (sorted by drop)', fontsize=8)
ax.set_ylabel('')
ax.tick_params(axis='x', rotation=45, labelsize=7)
ax.tick_params(axis='y', labelsize=7)

plt.tight_layout()

# Save
fig.savefig(OUT / "F9_task_heatmap.png", dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(OUT / "F9_task_heatmap.pdf", bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()

print(f"✅ F9 saved: {OUT / 'F9_task_heatmap.png'}")
print(f"✅ F9 saved: {OUT / 'F9_task_heatmap.pdf'}")

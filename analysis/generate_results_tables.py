#!/usr/bin/env python3
"""
Generate and verify Results section numbers against key-numbers.md.
Must be run from experiment/ directory.
"""
import math
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")

print(f"Total cases: {len(df)}")
print()

# ============================================================
# Table 1: Success rates matrix
# ============================================================
print("=" * 60)
print("TABLE 1: Success Rates by Variant × Agent × Model")
print("=" * 60)

combos = [
    ("text-only", "claude-sonnet", "Text-only Claude"),
    ("text-only", "llama4-maverick", "Text-only Llama 4"),
    ("cua", "claude-sonnet", "CUA Claude"),
    ("vision-only", "claude-sonnet", "SoM Claude"),
]

for agent, model, label in combos:
    print(f"\n--- {label} ---")
    sub = df[(df["agent_type"] == agent) & (df["model"] == model)]
    for v in ["low", "medium-low", "base", "high"]:
        vdf = sub[sub["variant"] == v]
        n = len(vdf)
        s = int(vdf["success"].sum())
        pct = 100 * s / n if n > 0 else 0
        print(f"  {v:12s}: {s}/{n} ({pct:.1f}%)")

# ============================================================
# Cochran-Armitage trend test
# ============================================================
print("\n" + "=" * 60)
print("COCHRAN-ARMITAGE TREND TESTS")
print("=" * 60)

def cochran_armitage(succs, tots):
    scores = np.array([0, 1, 2, 3], dtype=float)
    s = np.array(succs, dtype=float)
    n = np.array(tots, dtype=float)
    N = n.sum()
    R = s.sum()
    p_hat = R / N
    T = np.sum(scores * s) - (R / N) * np.sum(scores * n)
    var = p_hat * (1 - p_hat) * (np.sum(scores**2 * n) - np.sum(scores * n)**2 / N)
    Z = T / math.sqrt(var) if var > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(Z)))
    return Z, p

for agent, model, label in combos:
    sub = df[(df["agent_type"] == agent) & (df["model"] == model)]
    succs, tots = [], []
    for v in ["low", "medium-low", "base", "high"]:
        vdf = sub[sub["variant"] == v]
        succs.append(int(vdf["success"].sum()))
        tots.append(len(vdf))
    Z, p = cochran_armitage(succs, tots)
    print(f"  {label:25s}: Z={Z:.3f}, p={p:.8f}")

# ============================================================
# Chi-square + Cramér's V: low vs base
# ============================================================
print("\n" + "=" * 60)
print("CHI-SQUARE: LOW vs BASE")
print("=" * 60)

for agent, model, label in [("text-only", "claude-sonnet", "Text-only Claude"),
                              ("text-only", "llama4-maverick", "Text-only Llama 4")]:
    sub = df[(df["agent_type"] == agent) & (df["model"] == model)]
    low = sub[sub["variant"] == "low"]
    base = sub[sub["variant"] == "base"]
    table = np.array([
        [int(low["success"].sum()), len(low) - int(low["success"].sum())],
        [int(base["success"].sum()), len(base) - int(base["success"].sum())]
    ])
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    N_test = table.sum()
    V = math.sqrt(chi2 / N_test)
    # Odds ratio
    a, b, c, d = table[0, 0], table[0, 1], table[1, 0], table[1, 1]
    OR = (a * d) / (b * c) if b * c > 0 else float('inf')
    print(f"  {label}: chi2={chi2:.2f}, p={p:.8f}, V={V:.3f}, OR={OR:.2f}")

# ============================================================
# Causal decomposition
# ============================================================
print("\n" + "=" * 60)
print("CAUSAL DECOMPOSITION (Claude only)")
print("=" * 60)

text_c = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
cua_c = df[(df["agent_type"] == "cua") & (df["model"] == "claude-sonnet")]

text_low = 100 * text_c[text_c["variant"] == "low"]["success"].mean()
text_base = 100 * text_c[text_c["variant"] == "base"]["success"].mean()
cua_low = 100 * cua_c[cua_c["variant"] == "low"]["success"].mean()
cua_base = 100 * cua_c[cua_c["variant"] == "base"]["success"].mean()

text_drop = text_base - text_low
cua_drop = cua_base - cua_low
semantic = text_drop - cua_drop

print(f"  Text-only: base {text_base:.1f}% - low {text_low:.1f}% = {text_drop:.1f}pp")
print(f"  CUA:       base {cua_base:.1f}% - low {cua_low:.1f}% = {cua_drop:.1f}pp")
print(f"  Semantic:  {text_drop:.1f} - {cua_drop:.1f} = {semantic:.1f}pp")

# ============================================================
# Token stats (text-only Claude)
# ============================================================
print("\n" + "=" * 60)
print("TOKEN INFLATION (text-only Claude)")
print("=" * 60)

tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
if "total_tokens" in tc.columns:
    low_tokens = tc[tc["variant"] == "low"]["total_tokens"].dropna()
    base_tokens = tc[tc["variant"] == "base"]["total_tokens"].dropna()
    print(f"  Low  median: {low_tokens.median():.0f} ({low_tokens.median()/1000:.0f}K)")
    print(f"  Base median: {base_tokens.median():.0f} ({base_tokens.median()/1000:.0f}K)")
    print(f"  Max tokens:  {tc['total_tokens'].max():.0f} ({tc['total_tokens'].max()/1000:.0f}K)")
    if len(low_tokens) > 0 and len(base_tokens) > 0:
        stat, p = stats.mannwhitneyu(low_tokens, base_tokens, alternative='two-sided')
        print(f"  Wilcoxon p={p:.8f}")
else:
    print("  total_tokens column not found")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

#!/usr/bin/env python3
"""
Majority-Vote Sensitivity Analysis
====================================
Aggregates 5 repetitions per cell into a single majority-vote outcome.
Tests whether all primary findings preserve significance under this
conservative aggregation (N=208 cells instead of N=1,040 observations).
"""
import math
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def wilson_ci(s, n, alpha=0.05):
    if n == 0: return 0.0, 0.0
    p = s / n
    z = stats.norm.ppf(1 - alpha / 2)
    d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    m = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return max(0, c - m), min(1, c + m)

def cochran_armitage(succs, tots):
    scores = np.array([0, 1, 2, 3], dtype=float)
    s = np.array(succs, dtype=float)
    n = np.array(tots, dtype=float)
    N = n.sum()
    if N == 0: return 0.0, 1.0
    R = s.sum()
    p_hat = R / N
    T = np.sum(scores * s) - (R / N) * np.sum(scores * n)
    var = p_hat * (1 - p_hat) * (np.sum(scores**2 * n) - np.sum(scores * n)**2 / N)
    Z = T / math.sqrt(var) if var > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(Z)))
    return Z, p

def low_vs_rest(succs, tots):
    low_s, low_n = succs[0], tots[0]
    rest_s, rest_n = sum(succs[1:]), sum(tots[1:])
    if low_n == 0 or rest_n == 0: return 0.0, 1.0
    table = np.array([[low_s, low_n - low_s], [rest_s, rest_n - rest_s]])
    if table.min() < 5:
        _, p = stats.fisher_exact(table)
        z = stats.norm.ppf(1 - p/2) if p < 1 else 0
        return z, p
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    return math.sqrt(chi2), p

def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    print(f"Original N = {len(df)}")

    # Majority vote: group by cell, collapse 5 reps → 1 outcome
    cells = df.groupby(['task_id', 'variant', 'agent_type', 'model', 'model_family']).agg(
        n_reps=('success', 'size'),
        n_success=('success', 'sum')
    ).reset_index()
    cells['majority_success'] = (cells['n_success'] >= 3).astype(int)

    # Count variance cells
    variance_cells = cells[(cells['n_success'] > 0) & (cells['n_success'] < cells['n_reps'])]
    print(f"Majority-vote N = {len(cells)} cells")
    print(f"Cells with between-rep variance: {len(variance_cells)} / {len(cells)} ({100*len(variance_cells)/len(cells):.1f}%)")

    variant_order = ['low', 'medium-low', 'base', 'high']
    combos = [
        ('anthropic', 'text-only', 'Claude text-only'),
        ('anthropic', 'vision-only', 'Claude SoM'),
        ('anthropic', 'cua', 'Claude CUA'),
        ('meta', 'text-only', 'Llama 4 text-only'),
    ]

    mv_rows = []
    comp_rows = []
    all_preserve = True

    for mf, at, label in combos:
        sub = cells[(cells['model_family'] == mf) & (cells['agent_type'] == at)]
        if len(sub) == 0:
            print(f"\n  {label}: NO DATA")
            continue

        succs, tots = [], []
        for v in variant_order:
            vsub = sub[sub['variant'] == v]
            n = len(vsub)
            s = int(vsub['majority_success'].sum())
            succs.append(s)
            tots.append(n)
            rate = 100 * s / n if n > 0 else 0
            lo, hi = wilson_ci(s, n)
            mv_rows.append({
                'model_family': mf, 'agent_type': at, 'variant': v,
                'n_cells': n, 'majority_success_rate': round(rate, 1),
                'ci_lo': round(lo * 100, 1), 'ci_hi': round(hi * 100, 1),
            })

        ca_z, ca_p = cochran_armitage(succs, tots)
        bin_z, bin_p = low_vs_rest(succs, tots)

        # Update rows with test stats
        for row in mv_rows[-4:]:
            row['trend_z'] = round(ca_z, 3)
            row['trend_p'] = ca_p
            row['binary_z'] = round(bin_z, 3)
            row['binary_p'] = bin_p

        rates = [100 * s / n if n > 0 else 0 for s, n in zip(succs, tots)]
        sig = bin_p < 0.001

        print(f"\n  {label}:")
        print(f"    Rates: {' / '.join(f'{r:.1f}%' for r in rates)}")
        print(f"    C-A Z={ca_z:.3f}, p={ca_p:.6f}")
        print(f"    Low-vs-rest Z={bin_z:.3f}, p={bin_p:.6f}")
        print(f"    Preserves significance (p<0.001): {'YES' if sig else 'NO'}")

        if not sig and mf == 'anthropic' and at == 'text-only':
            all_preserve = False
            print("    ⚠️ PRIMARY FINDING DOES NOT PRESERVE — ALERT ALEX")

        # Comparison row
        comp_rows.append({
            'panel': label,
            'original_trend_z': None,  # filled below
            'majority_trend_z': round(ca_z, 3),
            'original_binary_p': None,
            'majority_binary_p': bin_p,
            'preserves': sig,
        })

    # Also compute original stats for comparison
    orig_combos = [
        ('anthropic', 'text-only', 'Claude text-only'),
        ('anthropic', 'vision-only', 'Claude SoM'),
        ('anthropic', 'cua', 'Claude CUA'),
        ('meta', 'text-only', 'Llama 4 text-only'),
    ]
    for i, (mf, at, label) in enumerate(orig_combos):
        sub = df[(df['model_family'] == mf) & (df['agent_type'] == at)]
        if len(sub) == 0: continue
        succs, tots = [], []
        for v in variant_order:
            vsub = sub[sub['variant'] == v]
            succs.append(int(vsub['success'].sum()))
            tots.append(len(vsub))
        ca_z, ca_p = cochran_armitage(succs, tots)
        bin_z, bin_p = low_vs_rest(succs, tots)
        if i < len(comp_rows):
            comp_rows[i]['original_trend_z'] = round(ca_z, 3)
            comp_rows[i]['original_binary_p'] = bin_p

    # Save
    mv_df = pd.DataFrame(mv_rows)
    mv_df.to_csv(ROOT / "results" / "majority_vote_sensitivity.csv", index=False)
    print(f"\n✅ Saved: results/majority_vote_sensitivity.csv")

    comp_df = pd.DataFrame(comp_rows)
    comp_df.to_csv(ROOT / "results" / "majority_vote_comparison.csv", index=False)
    print(f"✅ Saved: results/majority_vote_comparison.csv")

    print(f"\n{'='*60}")
    if all_preserve:
        print("✅ ALL PRIMARY FINDINGS PRESERVE SIGNIFICANCE UNDER MAJORITY VOTE")
    else:
        print("⚠️ SOME FINDINGS DO NOT PRESERVE — CHECK OUTPUT ABOVE")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

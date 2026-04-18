#!/usr/bin/env python3
"""
Compute primary, secondary, and tertiary test statistics per panel.
- Primary: Binary Low-vs-Rest (Fisher exact / chi-square)
- Secondary: Cochran-Armitage trend test
- Tertiary: Jonckheere-Terpstra (Mann-Whitney based)
"""
import math, sys
import pandas as pd, numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def wilson_ci(s, n, alpha=0.05):
    if n == 0: return 0., 0.
    p = s / n; z = stats.norm.ppf(1 - alpha/2)
    d = 1 + z**2/n; c = (p + z**2/(2*n))/d
    m = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))/d
    return max(0, c-m), min(1, c+m)

def cochran_armitage(succs, tots):
    sc = np.arange(4, dtype=float); s = np.array(succs, dtype=float); n = np.array(tots, dtype=float)
    N = n.sum(); R = s.sum()
    if N == 0: return 0., 1.
    p = R/N; T = (sc*s).sum() - R/N*(sc*n).sum()
    v = p*(1-p)*((sc**2*n).sum() - (sc*n).sum()**2/N)
    Z = T/math.sqrt(v) if v > 0 else 0
    return Z, 2*(1-stats.norm.cdf(abs(Z)))

def low_vs_rest(succs, tots):
    a, b = succs[0], tots[0]-succs[0]
    c, d = sum(succs[1:]), sum(tots[1:])-sum(succs[1:])
    if tots[0]==0 or sum(tots[1:])==0: return 0.,1.,1.,(0.,1.)
    table = np.array([[a,b],[c,d]])
    OR = (a*d)/(b*c) if b*c > 0 else float('inf')
    # Fisher for p-value (always valid)
    _, p = stats.fisher_exact(table, alternative='two-sided')
    # Chi-square Z for reporting
    if table.min() >= 5:
        chi2, _, _, _ = stats.chi2_contingency(table, correction=False)
        z = math.sqrt(chi2)
    else:
        z = abs(stats.norm.ppf(p/2)) if p < 1 else 0
    # OR CI (Woolf logit method)
    if 0 in [a,b,c,d]:
        or_ci = (0., float('inf'))
    else:
        se = math.sqrt(1/a + 1/b + 1/c + 1/d)
        lo = math.exp(math.log(OR) - 1.96*se)
        hi = math.exp(math.log(OR) + 1.96*se)
        or_ci = (lo, hi)
    return z, p, OR, or_ci

def jonckheere_terpstra(groups):
    """JT test: sum of Mann-Whitney U for all i<j pairs."""
    k = len(groups)
    S = 0; n_pairs = 0
    for i in range(k):
        for j in range(i+1, k):
            if len(groups[i]) > 0 and len(groups[j]) > 0:
                u, _ = stats.mannwhitneyu(groups[i], groups[j], alternative='less')
                S += u
                n_pairs += 1
    # Normal approximation
    ns = [len(g) for g in groups]; N = sum(ns)
    E = (N**2 - sum(n**2 for n in ns)) / 4
    V_num = N**2 * (2*N + 3) - sum(n**2 * (2*n + 3) for n in ns)
    V = V_num / 72
    Z = (S - E) / math.sqrt(V) if V > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(Z)))
    return Z, p

def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    variant_order = ['low', 'medium-low', 'base', 'high']
    combos = [
        ('anthropic', 'text-only', 'Claude text-only'),
        ('anthropic', 'vision-only', 'Claude SoM'),
        ('anthropic', 'cua', 'Claude CUA'),
        ('meta', 'text-only', 'Llama 4 text-only'),
    ]
    rows = []
    for mf, at, label in combos:
        sub = df[(df['model_family']==mf) & (df['agent_type']==at)]
        if len(sub) == 0:
            print(f"  {label}: NO DATA"); continue
        succs, tots, groups = [], [], []
        for v in variant_order:
            vs = sub[sub['variant']==v]
            succs.append(int(vs['success'].sum())); tots.append(len(vs))
            groups.append(vs['success'].astype(float).values)
        # Binary
        bz, bp, bor, bor_ci = low_vs_rest(succs, tots)
        # C-A
        caz, cap = cochran_armitage(succs, tots)
        # J-T
        jtz, jtp = jonckheere_terpstra(groups)
        print(f"  {label}:")
        print(f"    Binary: Z={bz:.3f} p={bp:.2e} OR={bor:.2f} CI=[{bor_ci[0]:.2f}, {bor_ci[1]:.2f}]")
        print(f"    C-A:    Z={caz:.3f} p={cap:.2e}")
        print(f"    J-T:    Z={jtz:.3f} p={jtp:.2e}")
        rows.append({
            'model_family': mf, 'agent_type': at,
            'binary_z': round(bz,3), 'binary_p': bp,
            'binary_or': round(bor,2), 'binary_or_ci_lo': round(bor_ci[0],2), 'binary_or_ci_hi': round(bor_ci[1],2),
            'ca_z': round(caz,3), 'ca_p': cap,
            'jt_z': round(jtz,3), 'jt_p': jtp,
        })
    pd.DataFrame(rows).to_csv(ROOT / "results" / "primary_stats_per_panel.csv", index=False)
    print(f"\n✅ Saved: results/primary_stats_per_panel.csv")

if __name__ == '__main__':
    main()

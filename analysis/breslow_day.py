#!/usr/bin/env python3
"""Breslow-Day test for homogeneity of odds ratios across Claude vs Llama 4."""
import math, numpy as np, pandas as pd
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    tables = []
    ors = []
    for model in ['claude-sonnet', 'llama4-maverick']:
        sub = df[(df['agent_type']=='text-only') & (df['model']==model)]
        low = sub[sub['variant']=='low']
        base = sub[sub['variant']=='base']
        a = int(low['success'].sum()); b = len(low) - a
        c = int(base['success'].sum()); d = len(base) - c
        OR = (a*d)/(b*c) if b*c > 0 else float('inf')
        print(f"  {model}: low={a}/{a+b} ({100*a/(a+b):.1f}%), base={c}/{c+d} ({100*c/(c+d):.1f}%), OR={OR:.4f}")
        tables.append(np.array([[a, b], [c, d]]))
        ors.append(OR)

    # Mantel-Haenszel common OR
    num = sum(t[0,0]*t[1,1]/(t.sum()) for t in tables)
    den = sum(t[0,1]*t[1,0]/(t.sum()) for t in tables)
    OR_mh = num / den if den > 0 else float('inf')

    # Breslow-Day: compare each stratum's OR to common OR
    # For each table, compute expected 'a' under common OR, then chi-square
    BD = 0
    for t in tables:
        a, b, c, d = t[0,0], t[0,1], t[1,0], t[1,1]
        n1 = a + b; n2 = c + d; m1 = a + c; N = n1 + n2
        # Solve quadratic for expected a: OR_mh = a_e*(n2-m1+a_e) / ((n1-a_e)*(m1-a_e))
        # Rearranging: (1-OR_mh)*a_e^2 + (OR_mh*(n1+m1) + n2 - m1)*a_e - OR_mh*n1*m1 = 0
        A_coef = 1 - OR_mh
        B_coef = OR_mh*(n1 + m1) + n2 - m1
        C_coef = -OR_mh * n1 * m1
        if abs(A_coef) < 1e-10:
            a_e = -C_coef / B_coef if B_coef != 0 else a
        else:
            disc = B_coef**2 - 4*A_coef*C_coef
            if disc < 0: continue
            r1 = (-B_coef + math.sqrt(disc)) / (2*A_coef)
            r2 = (-B_coef - math.sqrt(disc)) / (2*A_coef)
            # Pick root in valid range
            a_e = r1 if 0 < r1 < min(n1, m1) else r2
        b_e = n1 - a_e; c_e = m1 - a_e; d_e = n2 - c_e
        if any(x <= 0 for x in [a_e, b_e, c_e, d_e]): continue
        var_a = 1 / (1/a_e + 1/b_e + 1/c_e + 1/d_e)
        BD += (a - a_e)**2 * var_a

    K = len(tables)
    p_bd = 1 - stats.chi2.cdf(BD, K - 1)

    print(f"\n  Breslow-Day: χ²({K-1}) = {BD:.3f}, p = {p_bd:.4f}")
    print(f"  Mantel-Haenszel common OR = {OR_mh:.4f}")
    print(f"  Individual ORs: Claude={ors[0]:.4f}, Llama4={ors[1]:.4f}")

    # MH OR CI (Robins-Breslow-Greenland)
    R = sum(t[0,0]*t[1,1]/t.sum() for t in tables)
    S = sum(t[0,1]*t[1,0]/t.sum() for t in tables)
    P = sum((t[0,0]+t[1,1])/t.sum() * t[0,0]*t[1,1]/t.sum() for t in tables)
    Q = sum((t[0,1]+t[1,0])/t.sum() * t[0,0]*t[1,1]/t.sum() for t in tables)
    Rp = sum((t[0,0]+t[1,1])/t.sum() * t[0,1]*t[1,0]/t.sum() for t in tables)
    Sp = sum((t[0,1]+t[1,0])/t.sum() * t[0,1]*t[1,0]/t.sum() for t in tables)

    var_ln = P/(2*R**2) + (Q+Rp)/(2*R*S) + Sp/(2*S**2)
    se_ln = math.sqrt(var_ln) if var_ln > 0 else 0
    ci_lo = OR_mh * math.exp(-1.96 * se_ln)
    ci_hi = OR_mh * math.exp(1.96 * se_ln)
    print(f"  MH OR 95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")

    interpretation = "homogeneous" if p_bd > 0.10 else "heterogeneous"
    print(f"\n  Interpretation: ORs are {interpretation} (p {'>' if p_bd > 0.10 else '<'} 0.10)")
    if p_bd < 0.10:
        print("  → Supports qualitative observation: Claude step-function vs Llama gradient")
    else:
        print("  → Supports cross-model replication of Low-vs-Base effect")

    with open(ROOT / "results" / "breslow_day_cross_model.txt", 'w') as f:
        f.write(f"Breslow-Day Test for Cross-Model Homogeneity\n")
        f.write(f"Agent: text-only, Variants: Low vs Base\n\n")
        f.write(f"Claude: OR = {ors[0]:.4f}\n")
        f.write(f"Llama4: OR = {ors[1]:.4f}\n\n")
        f.write(f"Breslow-Day χ²({K-1}) = {BD:.3f}, p = {p_bd:.4f}\n")
        f.write(f"MH common OR = {OR_mh:.4f} [{ci_lo:.4f}, {ci_hi:.4f}]\n\n")
        f.write(f"Interpretation: {interpretation}\n")
    print(f"\n✅ Saved: results/breslow_day_cross_model.txt")

if __name__ == '__main__':
    main()

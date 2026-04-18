#!/usr/bin/env python3
"""
Figure 2: Main Results — 2×3 panel bar chart (v2)

Rows: Claude Sonnet 3.5 / Llama 4 Maverick
Cols: Text-Only / SoM Vision / CUA
Each panel: 4 bars (Low / M-L / Base / High) with Wilson 95% CI

Annotations:
  - Step-function bracket in Claude × Text-Only (+61.5pp)
  - Step-like annotation in Claude × CUA
  - Gradient arrow in Llama × Text-Only (monotone)
  - SoM baseline dashed line with exact number + evidentiary caveat
  - SoM L2-insensitive bracket (M-L = Base = 27.7%)
  - Per-panel Δ footer with Cochran-Armitage Z or Low-vs-rest Z

Color palette matches Figure 1 variant severity colors.
"""
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300})

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures"

# Variant colors (match Figure 1)
C_LOW = '#C0392B'; C_ML = '#E67E22'; C_BASE = '#2471A3'; C_HIGH = '#27AE60'
BORDER = '#2C3E50'
VARIANT_ORDER = ['low', 'medium-low', 'base', 'high']
VARIANT_LABELS = ['Low', 'M-L', 'Base', 'High']
VARIANT_COLORS = [C_LOW, C_ML, C_BASE, C_HIGH]

AGENT_ORDER = ['text-only', 'vision-only', 'cua']
AGENT_LABELS = ['Text-Only', 'SoM Vision', 'CUA']
MODEL_ORDER = ['anthropic', 'meta']
MODEL_LABELS = ['Claude Sonnet 3.5', 'Llama 4 Maverick']


def wilson_ci(successes, n, alpha=0.05):
    """Wilson score interval for binomial proportion. Returns (lo, hi)."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    z = stats.norm.ppf(1 - alpha / 2)
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return max(0, center - margin), min(1, center + margin)


def cochran_armitage(succs, tots):
    """Cochran-Armitage trend test for ordered proportions."""
    scores = np.array([0, 1, 2, 3], dtype=float)
    s = np.array(succs, dtype=float)
    n = np.array(tots, dtype=float)
    N = n.sum()
    if N == 0:
        return 0.0, 1.0
    R = s.sum()
    p_hat = R / N
    T = np.sum(scores * s) - (R / N) * np.sum(scores * n)
    var = p_hat * (1 - p_hat) * (np.sum(scores**2 * n) - np.sum(scores * n)**2 / N)
    Z = T / math.sqrt(var) if var > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(Z)))
    return Z, p


def low_vs_rest_test(succs, tots):
    """Binary 2×2 chi-square: Low vs (M-L + Base + High) combined."""
    low_s, low_n = succs[0], tots[0]
    rest_s = sum(succs[1:])
    rest_n = sum(tots[1:])
    if low_n == 0 or rest_n == 0:
        return 0.0, 1.0
    table = np.array([
        [low_s, low_n - low_s],
        [rest_s, rest_n - rest_s]
    ])
    if table.min() < 5:
        _, p = stats.fisher_exact(table)
        # Approximate Z from p
        z = stats.norm.ppf(1 - p/2) if p < 1 else 0
        return z, p
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    z = math.sqrt(chi2) if chi2 > 0 else 0
    return z, p


def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    print(f"Total rows: {len(df)}")

    stats_rows = []
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    fig.subplots_adjust(hspace=0.50, wspace=0.08, left=0.08, right=0.97, top=0.90, bottom=0.13)

    x = np.arange(4)

    for row_idx, (model_fam, model_label) in enumerate(zip(MODEL_ORDER, MODEL_LABELS)):
        for col_idx, (agent, agent_label) in enumerate(zip(AGENT_ORDER, AGENT_LABELS)):
            ax = axes[row_idx][col_idx]
            sub = df[(df["model_family"] == model_fam) & (df["agent_type"] == agent)]

            rates, ci_los, ci_his, succs_list, tots_list = [], [], [], [], []
            for v in VARIANT_ORDER:
                vdf = sub[sub["variant"] == v]
                n = len(vdf)
                s = int(vdf["success"].sum())
                rate = s / n if n > 0 else 0
                lo, hi = wilson_ci(s, n)
                rates.append(rate * 100)
                ci_los.append(rate * 100 - lo * 100)
                ci_his.append(hi * 100 - rate * 100)
                succs_list.append(s)
                tots_list.append(n)

            # ── Empty panels (Llama × SoM/CUA) ──
            if sum(tots_list) == 0:
                ax.text(1.5, 50, 'Not tested\n(Claude only)',
                        ha='center', va='center', fontsize=9, color='#AAAAAA', style='italic')
                ax.set_xticks(x)
                ax.set_xticklabels(VARIANT_LABELS, fontsize=8)
                ax.set_ylim(0, 115)
                ax.set_yticks([0, 20, 40, 60, 80, 100])
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                if row_idx == 0:
                    ax.set_title(agent_label, fontsize=10, fontweight='bold', pad=10)
                if col_idx == 0:
                    ax.set_ylabel('Task Success Rate (%)', fontsize=9)
                # Still add empty stats rows
                for v in VARIANT_ORDER:
                    stats_rows.append({
                        'model_family': model_fam, 'agent_type': agent, 'variant': v,
                        'n': 0, 'successes': 0, 'success_rate': 0,
                        'ci_lo': 0, 'ci_hi': 0,
                        'trend_z': 0, 'trend_p': 1, 'binary_z': 0, 'binary_p': 1,
                    })
                continue

            print(f"  {model_label} × {agent_label}: "
                  + " | ".join(f"{v}={s}/{n} ({r:.1f}%)"
                               for v, s, n, r in zip(VARIANT_LABELS, succs_list, tots_list, rates)))

            # ── Statistics ──
            ca_z, ca_p = cochran_armitage(succs_list, tots_list)
            bin_z, bin_p = low_vs_rest_test(succs_list, tots_list)
            delta_pp = rates[2] - rates[0]  # base - low
            is_nonmonotonic = rates[1] > rates[2] + 2  # M-L > Base

            print(f"    C-A Z={ca_z:.3f} p={ca_p:.6f} | Low-vs-rest Z={bin_z:.3f} p={bin_p:.6f}")

            # Add stats rows
            for vi, v in enumerate(VARIANT_ORDER):
                stats_rows.append({
                    'model_family': model_fam, 'agent_type': agent, 'variant': v,
                    'n': tots_list[vi], 'successes': succs_list[vi],
                    'success_rate': round(rates[vi], 1),
                    'ci_lo': round(rates[vi] - ci_los[vi], 1),
                    'ci_hi': round(rates[vi] + ci_his[vi], 1),
                    'trend_z': round(ca_z, 3), 'trend_p': round(ca_p, 8),
                    'binary_z': round(bin_z, 3), 'binary_p': round(bin_p, 8),
                })

            # ── Draw bars ──
            yerr = np.array([ci_los, ci_his])
            ax.bar(x, rates, color=VARIANT_COLORS, edgecolor=BORDER,
                   linewidth=0.8, width=0.65, alpha=0.85, zorder=3)
            ax.errorbar(x, rates, yerr=yerr, fmt='none', ecolor='black',
                        elinewidth=1.0, capsize=3, zorder=4)

            # Numeric labels
            for xi, r in zip(x, rates):
                ax.text(xi, r + max(ci_his) + 1.5, f'{r:.1f}',
                        ha='center', va='bottom', fontsize=8, fontweight='bold', zorder=5)

            # Chance line
            ax.axhline(y=50, color='#999999', linestyle=':', linewidth=0.8, zorder=1)

            # Axis config (Fix 4: ylim 115)
            ax.set_ylim(0, 115)
            ax.set_xticks(x)
            ax.set_xticklabels(VARIANT_LABELS, fontsize=8)
            ax.set_yticks([0, 20, 40, 60, 80, 100])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(axis='y', labelsize=8)

            if row_idx == 0:
                ax.set_title(agent_label, fontsize=10, fontweight='bold', pad=10)
            if col_idx == 0:
                ax.set_ylabel('Task Success Rate (%)', fontsize=9)

            # ════════════════════════════════════════════
            # ANNOTATIONS
            # ════════════════════════════════════════════

            # A. Step-function (Claude × Text-Only)
            if model_fam == 'anthropic' and agent == 'text-only':
                step_delta = rates[1] - rates[0]
                mid_y = (rates[0] + rates[1]) / 2
                ax.annotate('', xy=(1, rates[1] - 3), xytext=(0, rates[0] + 3),
                            arrowprops=dict(arrowstyle='->', color=C_LOW, lw=2,
                                            connectionstyle='arc3,rad=-0.3'))
                ax.text(0.5, mid_y + 5, f'Δ = +{step_delta:.1f}pp\nstep-function',
                        ha='center', va='center', fontsize=8, fontweight='bold', color=C_LOW,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF3CD',
                                  edgecolor=C_ML, alpha=0.95))

            # B. Step-like (Claude × CUA) — Fix 1
            if model_fam == 'anthropic' and agent == 'cua':
                step_delta = rates[1] - rates[0]
                ax.annotate('', xy=(1, rates[1] - 3), xytext=(0, rates[0] + 3),
                            arrowprops=dict(arrowstyle='->', color='#555555', lw=1.5,
                                            connectionstyle='arc3,rad=-0.3'))
                ax.text(0.5, (rates[0] + rates[1]) / 2 + 3,
                        f'+{step_delta:.0f}pp\nstep-like',
                        ha='center', va='center', fontsize=7, color='#555555', style='italic')

            # C. Gradient (Llama × Text-Only) — Fix 1
            if model_fam == 'meta' and agent == 'text-only':
                ax.annotate('', xy=(3, rates[3] - 3), xytext=(0, rates[0] + 3),
                            arrowprops=dict(arrowstyle='->', color='#555555', lw=1.2))
                ax.text(1.5, max(rates) + 6, 'gradient (monotone)',
                        ha='center', va='bottom', fontsize=7, color='#555555', style='italic')

            # D. SoM annotations — Fix 2 + Fix 3
            if agent == 'vision-only':
                base_rate = rates[2]
                # Dashed baseline (Fix 3: exact number + evidentiary caveat)
                ax.axhline(y=base_rate, color='#888888', linestyle='--', linewidth=0.7, zorder=2)
                ax.text(3.4, base_rate + 2,
                        f'SoM baseline = {base_rate:.1f}%\nlimits evidentiary power (§5.6)',
                        fontsize=6.5, ha='right', va='bottom', color='#888888', style='italic')

                # Fix 2: L2-insensitive bracket (M-L = Base)
                if model_fam == 'anthropic' and abs(rates[1] - rates[2]) < 1:
                    bracket_y = max(rates[1], rates[2]) + max(ci_his) + 8
                    ax.plot([1, 1, 2, 2], [bracket_y - 2, bracket_y, bracket_y, bracket_y - 2],
                            color='#7D3C98', lw=1.2, zorder=5)
                    ax.text(1.5, bracket_y + 1,
                            f'L2-insensitive:\nM-L = Base = {rates[1]:.1f}%',
                            ha='center', va='bottom', fontsize=7, fontweight='bold',
                            style='italic', color='#7D3C98')

            # E. Per-panel footer — Fix 5
            p_stars = '***' if ca_p < 0.001 else ('**' if ca_p < 0.01 else ('*' if ca_p < 0.05 else 'n.s.'))

            if is_nonmonotonic:
                footer = f'Low vs. rest: Δ = −{delta_pp:.1f}pp{p_stars} | Z = {bin_z:.2f} (threshold)'
            else:
                footer = f'Trend Z = {ca_z:.2f}{p_stars} | Low→Base: Δ = −{delta_pp:.1f}pp'

            ax.text(1.5, -15, footer, ha='center', va='top', fontsize=6.5,
                    color='#555555', transform=ax.transData)

    # Row labels
    for row_idx, label in enumerate(MODEL_LABELS):
        fig.text(0.02, 0.73 - row_idx * 0.42, label, fontsize=10, fontweight='bold',
                 rotation=90, ha='center', va='center')

    fig.text(0.52, 0.04, 'Accessibility Variant', fontsize=9, ha='center')

    # Save
    fig.savefig(OUT / "figure2_main_results.png", dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"\n✅ Figure 2 saved: {OUT / 'figure2_main_results.png'}")

    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(OUT / "figure2_stats.csv", index=False)
    print(f"✅ Stats saved: {OUT / 'figure2_stats.csv'}")
    print(f"\nTotal evaluable cases: {len(df)}")


if __name__ == '__main__':
    main()

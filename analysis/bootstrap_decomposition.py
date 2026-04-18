#!/usr/bin/env python3
"""Bootstrap CIs for pathway decomposition + Holm-Bonferroni correction."""
import numpy as np, pandas as pd, math
from scipy import stats
from statsmodels.stats.multitest import multipletests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
np.random.seed(42)
B = 2000

def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    tasks = sorted(df['task_id'].unique())

    # Pre-compute per-task success rates
    def task_rates(data, agent, model):
        sub = data[(data['agent_type']==agent) & (data['model']==model)]
        rates = {}
        for v in ['low', 'base']:
            vs = sub[sub['variant']==v]
            rates[v] = vs['success'].mean() if len(vs) > 0 else np.nan
        return rates

    # Point estimates
    text_rates = {t: task_rates(df[df['task_id']==t], 'text-only', 'claude-sonnet') for t in tasks}
    cua_rates = {t: task_rates(df[df['task_id']==t], 'cua', 'claude-sonnet') for t in tasks}

    text_drop = np.mean([text_rates[t]['base'] - text_rates[t]['low'] for t in tasks]) * 100
    cua_drop = np.mean([cua_rates[t]['base'] - cua_rates[t]['low'] for t in tasks]) * 100
    semantic = text_drop - cua_drop

    print(f"Point estimates: text_drop={text_drop:.1f}pp, cua_drop={cua_drop:.1f}pp, semantic={semantic:.1f}pp")

    # Bootstrap
    boot_text, boot_cua, boot_sem = [], [], []
    for _ in range(B):
        sampled = np.random.choice(tasks, size=len(tasks), replace=True)
        td = np.mean([text_rates[t]['base'] - text_rates[t]['low'] for t in sampled]) * 100
        cd = np.mean([cua_rates[t]['base'] - cua_rates[t]['low'] for t in sampled]) * 100
        boot_text.append(td)
        boot_cua.append(cd)
        boot_sem.append(td - cd)

    boot_text = np.array(boot_text)
    boot_cua = np.array(boot_cua)
    boot_sem = np.array(boot_sem)

    def ci(arr):
        return np.percentile(arr, 2.5), np.percentile(arr, 97.5)

    text_ci = ci(boot_text)
    cua_ci = ci(boot_cua)
    sem_ci = ci(boot_sem)
    combined_ci = ci(boot_text)  # same as text_drop since it's the total

    print(f"\nBootstrap 95% CIs (B={B}):")
    print(f"  Text-only drop: {text_drop:.1f}pp [{text_ci[0]:.1f}, {text_ci[1]:.1f}]")
    print(f"  CUA drop:       {cua_drop:.1f}pp [{cua_ci[0]:.1f}, {cua_ci[1]:.1f}]")
    print(f"  Semantic:       {semantic:.1f}pp [{sem_ci[0]:.1f}, {sem_ci[1]:.1f}]")

    # Additivity check: does text_drop ≈ semantic + cua_drop?
    sum_ci = ci(boot_sem + boot_cua)
    print(f"  Sum (sem+func): [{sum_ci[0]:.1f}, {sum_ci[1]:.1f}] vs text_drop={text_drop:.1f}")
    overlap = sum_ci[0] <= text_drop <= sum_ci[1]
    print(f"  Additivity plausible: {overlap}")

    # Save
    rows = [
        {'pathway': 'text_only_drop', 'point_estimate': round(text_drop,1), 'ci_lo': round(text_ci[0],1), 'ci_hi': round(text_ci[1],1), 'n_bootstrap': B},
        {'pathway': 'cua_drop', 'point_estimate': round(cua_drop,1), 'ci_lo': round(cua_ci[0],1), 'ci_hi': round(cua_ci[1],1), 'n_bootstrap': B},
        {'pathway': 'semantic_contribution', 'point_estimate': round(semantic,1), 'ci_lo': round(sem_ci[0],1), 'ci_hi': round(sem_ci[1],1), 'n_bootstrap': B},
    ]
    pd.DataFrame(rows).to_csv(ROOT / "results" / "bootstrap_decomposition.csv", index=False)
    np.savez(ROOT / "results" / "bootstrap_decomposition_full.npz",
             text=boot_text, cua=boot_cua, semantic=boot_sem)
    print(f"\n✅ Saved: results/bootstrap_decomposition.csv + .npz")

    # ── Holm-Bonferroni correction ──
    print(f"\n{'='*60}")
    print("Holm-Bonferroni Correction for Secondary Tests")
    print(f"{'='*60}")

    # Collect all secondary p-values
    stats_df = pd.read_csv(ROOT / "results" / "primary_stats_per_panel.csv")
    secondary_tests = []
    for _, row in stats_df.iterrows():
        if row['model_family'] == 'anthropic' and row['agent_type'] == 'text-only':
            continue  # primary, no correction needed
        secondary_tests.append({
            'test': f"{row['model_family']}_{row['agent_type']}_binary",
            'raw_p': row['binary_p'],
        })
        secondary_tests.append({
            'test': f"{row['model_family']}_{row['agent_type']}_trend",
            'raw_p': row['ca_p'],
        })

    # Add cross-model chi-square
    secondary_tests.append({'test': 'claude_low_vs_base_chi2', 'raw_p': 2.83e-11})  # from key-numbers
    secondary_tests.append({'test': 'llama4_low_vs_base_chi2', 'raw_p': 1.09e-04})

    raw_ps = [t['raw_p'] for t in secondary_tests]
    reject, adjusted, _, _ = multipletests(raw_ps, method='holm')

    for t, adj, rej in zip(secondary_tests, adjusted, reject):
        t['holm_p'] = adj
        t['significant'] = rej
        print(f"  {t['test']:40s}: raw={t['raw_p']:.2e} → holm={adj:.2e} {'✓' if rej else '✗'}")

    pd.DataFrame(secondary_tests).to_csv(ROOT / "results" / "multiple_comparisons_corrected.csv", index=False)
    print(f"\n✅ Saved: results/multiple_comparisons_corrected.csv")

if __name__ == '__main__':
    main()

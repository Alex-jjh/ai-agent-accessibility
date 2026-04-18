#!/usr/bin/env python3
"""
GLMM Analysis: Compare nested models for the accessibility effect.
Uses statsmodels GEE as primary (robust to misspecification) and
BinomialBayesMixedGLM for random-intercept model.
"""
import pandas as pd, numpy as np
from pathlib import Path
from scipy import stats
import statsmodels.api as sm
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod.families import Binomial
from statsmodels.genmod.cov_struct import Exchangeable

ROOT = Path(__file__).resolve().parent.parent

def main():
    df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")
    # Use all data (all agents, all models) for the full model
    df['success_int'] = df['success'].astype(int)
    df['variant_ord'] = df['variant'].map({'low':0,'medium-low':1,'base':2,'high':3})
    df['is_low'] = (df['variant'] == 'low').astype(int)

    print("=" * 60)
    print("GLMM / GEE Analysis")
    print("=" * 60)

    # ── Model 0: GEE with exchangeable correlation, variant linear ──
    print("\n--- M0: GEE variant_ordinal + (exchangeable|task_id) ---")
    m0 = GEE.from_formula(
        'success_int ~ variant_ord',
        groups='task_id',
        data=df,
        family=Binomial(),
        cov_struct=Exchangeable()
    ).fit()
    print(f"  β_variant = {m0.params['variant_ord']:.4f}, z = {m0.tvalues['variant_ord']:.3f}, p = {m0.pvalues['variant_ord']:.2e}")
    print(f"  Scale = {m0.scale:.4f}")

    # ── Model 1: GEE with model_family as fixed effect ──
    print("\n--- M1: GEE variant_ord + model_family + (exchangeable|task_id) ---")
    df['is_meta'] = (df['model_family'] == 'meta').astype(int)
    m1 = GEE.from_formula(
        'success_int ~ variant_ord + is_meta',
        groups='task_id',
        data=df,
        family=Binomial(),
        cov_struct=Exchangeable()
    ).fit()
    print(f"  β_variant = {m1.params['variant_ord']:.4f}, z = {m1.tvalues['variant_ord']:.3f}, p = {m1.pvalues['variant_ord']:.2e}")
    print(f"  β_meta = {m1.params['is_meta']:.4f}, z = {m1.tvalues['is_meta']:.3f}, p = {m1.pvalues['is_meta']:.2e}")

    # ── Model 2: GEE with variant as factor (categorical) ──
    print("\n--- M2: GEE C(variant) + (exchangeable|task_id) ---")
    m2 = GEE.from_formula(
        'success_int ~ C(variant, Treatment(reference="base"))',
        groups='task_id',
        data=df,
        family=Binomial(),
        cov_struct=Exchangeable()
    ).fit()
    print(m2.summary().tables[1])

    # ── Model 3: GEE with binary Low indicator ──
    print("\n--- M3: GEE is_low + (exchangeable|task_id) ---")
    m3 = GEE.from_formula(
        'success_int ~ is_low',
        groups='task_id',
        data=df,
        family=Binomial(),
        cov_struct=Exchangeable()
    ).fit()
    print(f"  β_low = {m3.params['is_low']:.4f}, z = {m3.tvalues['is_low']:.3f}, p = {m3.pvalues['is_low']:.2e}")
    or_low = np.exp(m3.params['is_low'])
    print(f"  OR(low) = {or_low:.3f}")

    # ── Per-agent-type GEE (Claude text-only only) ──
    print("\n--- M4: GEE variant_ord, Claude text-only only ---")
    tc = df[(df['agent_type']=='text-only') & (df['model']=='claude-sonnet')]
    m4 = GEE.from_formula(
        'success_int ~ variant_ord',
        groups='task_id',
        data=tc,
        family=Binomial(),
        cov_struct=Exchangeable()
    ).fit()
    print(f"  β_variant = {m4.params['variant_ord']:.4f}, z = {m4.tvalues['variant_ord']:.3f}, p = {m4.pvalues['variant_ord']:.2e}")

    # ── Save comparison ──
    rows = [
        {'model': 'M0_GEE_linear', 'formula': 'success~variant_ord+(exch|task)', 'beta_variant': round(m0.params['variant_ord'],4), 'z': round(m0.tvalues['variant_ord'],3), 'p': m0.pvalues['variant_ord'], 'qic': round(m0.qic()[0],1) if hasattr(m0,'qic') else None},
        {'model': 'M1_GEE_model', 'formula': 'success~variant_ord+model+(exch|task)', 'beta_variant': round(m1.params['variant_ord'],4), 'z': round(m1.tvalues['variant_ord'],3), 'p': m1.pvalues['variant_ord'], 'qic': round(m1.qic()[0],1) if hasattr(m1,'qic') else None},
        {'model': 'M3_GEE_binary', 'formula': 'success~is_low+(exch|task)', 'beta_variant': round(m3.params['is_low'],4), 'z': round(m3.tvalues['is_low'],3), 'p': m3.pvalues['is_low'], 'qic': round(m3.qic()[0],1) if hasattr(m3,'qic') else None},
        {'model': 'M4_GEE_claude_text', 'formula': 'success~variant_ord+(exch|task) [Claude TO]', 'beta_variant': round(m4.params['variant_ord'],4), 'z': round(m4.tvalues['variant_ord'],3), 'p': m4.pvalues['variant_ord'], 'qic': round(m4.qic()[0],1) if hasattr(m4,'qic') else None},
    ]
    pd.DataFrame(rows).to_csv(ROOT / "results" / "glmm_model_comparison.csv", index=False)
    print(f"\n✅ Saved: results/glmm_model_comparison.csv")

    # Summary
    print(f"\n{'='*60}")
    print("KEY RESULTS FOR PAPER:")
    print(f"  GEE (all data, linear): β={m0.params['variant_ord']:.4f}, z={m0.tvalues['variant_ord']:.3f}, p={m0.pvalues['variant_ord']:.2e}")
    print(f"  GEE (binary low): β={m3.params['is_low']:.4f}, z={m3.tvalues['is_low']:.3f}, p={m3.pvalues['is_low']:.2e}, OR={or_low:.3f}")
    print(f"  GEE (Claude TO): β={m4.params['variant_ord']:.4f}, z={m4.tvalues['variant_ord']:.3f}, p={m4.pvalues['variant_ord']:.2e}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

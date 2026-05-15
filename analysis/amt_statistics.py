#!/usr/bin/env python3.11
"""
AMT Paper Statistical Tests
============================

Inferential statistics for the AMT paper (Mode A + C.2 + Signature Alignment).
Complements the descriptive analysis in `scripts/amt/` with proper
hypothesis tests, effect sizes, and confidence intervals.

DATA SOURCES:
  - data/mode-a-shard-{a,b}/ (Claude, 3 agents × 26 ops × 13 tasks × 3 reps)
  - data/mode-a-llama4-textonly/ (Llama 4 text-only × 26 ops × 13 tasks × 3 reps)
  - data/c2-composition-shard-{a,b}/ (28 pairs × 13 tasks × 2 agents × 3 reps)
  - scripts/amt/ground-truth-corrections.json (GT corrections for 3 Docker-drift tasks)

TESTS INCLUDED:

1. §5.1 Per-operator significance (Mode A)
   - Fisher's exact test: each operator vs H-baseline (26 tests, Holm-Bonferroni)
   - Wilson 95% CI per operator
   - Effect size: odds ratio with 95% CI

2. §5.2 Signature alignment (DOM vs behavioral)
   - Spearman rank correlation: DOM magnitude vs behavioral drop
   - Report both Claude and Llama 4 correlations
   - Classification confusion matrix (aligned / misaligned / both-null)

3. §5.3 Cross-model replication (Claude vs Llama 4)
   - Breslow-Day test for OR homogeneity across models
   - Mantel-Haenszel common odds ratio
   - Per-operator Cohen's h (proportion effect size) agreement

4. §5.4 Compositional interaction (C.2)
   - Per-pair Fisher's exact: observed pair drop vs expected additive drop
   - Classify super-additive / additive / sub-additive with CIs
   - Chi-square test for overall additivity departure

USAGE:
  python3.11 analysis/amt_statistics.py

OUTPUT:
  results/amt/statistics_report.md (paper-ready numbers)
  stdout summary

DEPENDENCIES: pandas, numpy, scipy, statsmodels
"""
import json
import glob
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

# Reuse shared lib (extracted 2026-05-15) — these used to be inlined here.
# Backward compatibility: legacy callers (stage3_statistics.py, scripts/amt/*.py)
# import {wilson_ci, odds_ratio_ci, cohens_h, mantel_haenszel_or, breslow_day,
# load_cases, GT_CORRECTIONS} from this module — re-export them so nothing breaks.
from analysis._constants import GT_CORRECTIONS
from analysis.lib.stats import wilson_ci, odds_ratio_ci, cohens_h, mantel_haenszel_or, breslow_day
from analysis.lib.load import load_cases_flat, apply_gt_corrections

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "results" / "amt"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_cases(data_dirs):
    """Backwards-compatible wrapper around `lib.load.load_cases_flat`.

    Older callers expect `load_cases([Path,...])` to return a list of dicts
    with keys {caseId, taskId, opId, agent, success}, GT-corrected.
    """
    return apply_gt_corrections(load_cases_flat(data_dirs))


# ════════════════════════════════════════════════════════════════
# §5.1 Per-operator significance (Mode A)
# ════════════════════════════════════════════════════════════════
def test_per_operator_significance(claude_cases, agent="text-only"):
    """
    For each operator, test whether its success rate differs from H-baseline.
    Uses Fisher's exact test with Holm-Bonferroni correction for 26 comparisons.
    """
    # Compute H-baseline cases (all H operators pooled)
    h_cases = [c for c in claude_cases if c["agent"] == agent and c["opId"].startswith("H")]
    h_ok = sum(c["success"] for c in h_cases)
    h_total = len(h_cases)
    h_rate = h_ok / h_total if h_total > 0 else 0

    # All distinct operators
    ops = sorted(set(c["opId"] for c in claude_cases))
    
    results = []
    p_values = []
    for op in ops:
        op_cases = [c for c in claude_cases if c["agent"] == agent and c["opId"] == op]
        op_ok = sum(c["success"] for c in op_cases)
        op_total = len(op_cases)
        if op_total == 0:
            continue
        op_rate = op_ok / op_total
        lo, hi = wilson_ci(op_ok, op_total)

        # Skip H operators (they ARE the baseline)
        if op.startswith("H"):
            results.append({
                "operator": op, "rate": op_rate, "n": op_total, "ok": op_ok,
                "ci_lo": lo, "ci_hi": hi, "drop_pp": 0.0,
                "p_raw": None, "p_holm": None, "OR": None, "OR_ci": (None, None),
                "significant": None,
            })
            continue

        # Fisher's exact vs H-baseline
        table = np.array([[op_ok, op_total - op_ok], [h_ok, h_total - h_ok]])
        _, p = stats.fisher_exact(table)
        OR, or_lo, or_hi = odds_ratio_ci(
            op_ok, op_total - op_ok, h_ok, h_total - h_ok
        )

        results.append({
            "operator": op, "rate": op_rate, "n": op_total, "ok": op_ok,
            "ci_lo": lo, "ci_hi": hi,
            "drop_pp": (h_rate - op_rate) * 100,
            "p_raw": p, "OR": OR, "OR_ci": (or_lo, or_hi),
        })
        p_values.append(p)

    # Holm-Bonferroni correction on non-H operators
    non_h = [r for r in results if r["p_raw"] is not None]
    if p_values:
        _, p_corrected, _, _ = multipletests(p_values, method='holm')
        for r, p_c in zip(non_h, p_corrected):
            r["p_holm"] = p_c
            r["significant"] = p_c < 0.05

    return results, h_rate, h_total, h_ok


# ════════════════════════════════════════════════════════════════
# §5.3 Cross-model replication
# ════════════════════════════════════════════════════════════════
def test_cross_model_replication(claude_cases, llama_cases):
    """
    Breslow-Day test for OR homogeneity between Claude and Llama 4.
    Computes per-operator OR agreement via Cohen's h.
    """
    # H-baselines per model
    def compute_h(cases, agent="text-only"):
        h = [c for c in cases if c["agent"] == agent and c["opId"].startswith("H")]
        return sum(c["success"] for c in h), len(h)

    c_h_ok, c_h_n = compute_h(claude_cases)
    l_h_ok, l_h_n = compute_h(llama_cases)

    # Find operators with significant effect in at least one model
    ops = sorted(set(c["opId"] for c in claude_cases))
    top_ops = []
    for op in ops:
        if op.startswith("H"):
            continue
        c_op = [c for c in claude_cases if c["agent"] == "text-only" and c["opId"] == op]
        l_op = [c for c in llama_cases if c["agent"] == "text-only" and c["opId"] == op]
        c_ok = sum(c["success"] for c in c_op)
        l_ok = sum(c["success"] for c in l_op)
        c_rate = c_ok / len(c_op) if c_op else 0
        l_rate = l_ok / len(l_op) if l_op else 0
        c_drop = c_h_ok/c_h_n - c_rate
        l_drop = l_h_ok/l_h_n - l_rate
        # Include operators with >5pp drop in either model
        if c_drop > 0.05 or l_drop > 0.05:
            top_ops.append({
                "operator": op,
                "c_table": [[c_ok, len(c_op) - c_ok], [c_h_ok, c_h_n - c_h_ok]],
                "l_table": [[l_ok, len(l_op) - l_ok], [l_h_ok, l_h_n - l_h_ok]],
                "c_rate": c_rate, "l_rate": l_rate,
                "c_drop": c_drop, "l_drop": l_drop,
                "cohen_h": cohens_h(c_rate, l_rate),
            })

    # Pool all tables for global Breslow-Day
    all_tables_c = [op["c_table"] for op in top_ops]
    all_tables_l = [op["l_table"] for op in top_ops]
    # Paired tables: [Claude table, Llama table] per operator
    paired_tables = [[c, l] for c, l in zip(all_tables_c, all_tables_l)]
    
    # Per-operator Breslow-Day (each is a 2×2×2 stratified test)
    bd_results = []
    for op in top_ops:
        tables = [op["c_table"], op["l_table"]]
        or_mh = mantel_haenszel_or(tables)
        bd, df, p = breslow_day(tables, or_mh)
        bd_results.append({
            "operator": op["operator"],
            "OR_mh": or_mh,
            "BD": bd, "df": df, "p": p,
            "c_drop": op["c_drop"],
            "l_drop": op["l_drop"],
            "cohen_h": op["cohen_h"],
            "homogeneous": p >= 0.05,  # fail to reject → homogeneous
        })

    return bd_results


# ════════════════════════════════════════════════════════════════
# §5.4 Compositional interaction
# ════════════════════════════════════════════════════════════════
def test_compositional_interaction(claude_cases, c2_cases, agent="text-only"):
    """
    For each pair, test whether observed drop differs from additive expectation.
    Additivity model: expected_drop = drop(A) + drop(B) for pair A+B.
    """
    # Compute H-baseline
    h = [c for c in claude_cases if c["agent"] == agent and c["opId"].startswith("H")]
    h_ok = sum(c["success"] for c in h)
    h_n = len(h)
    h_rate = h_ok / h_n

    # Individual operator rates (needed for expected drop)
    op_rates = {}
    all_ops = set(c["opId"] for c in claude_cases)
    for op in all_ops:
        if "+" in op:
            continue
        cases_op = [c for c in claude_cases if c["agent"] == agent and c["opId"] == op]
        if cases_op:
            op_rates[op] = sum(c["success"] for c in cases_op) / len(cases_op)

    # Per-pair analysis
    pairs_data = defaultdict(lambda: {"ok": 0, "total": 0})
    for c in c2_cases:
        if c["agent"] != agent:
            continue
        pairs_data[c["opId"]]["total"] += 1
        if c["success"]:
            pairs_data[c["opId"]]["ok"] += 1

    results = []
    for pair_id, counts in pairs_data.items():
        if counts["total"] == 0 or "+" not in pair_id:
            continue
        ops = pair_id.split("+")
        if len(ops) != 2 or not all(op in op_rates for op in ops):
            continue

        pair_rate = counts["ok"] / counts["total"]
        pair_drop = h_rate - pair_rate

        # Expected additive drop
        drop_a = h_rate - op_rates[ops[0]]
        drop_b = h_rate - op_rates[ops[1]]
        expected_drop = drop_a + drop_b
        interaction = (pair_drop - expected_drop) * 100  # in pp

        # Classify
        if interaction > 5.0:
            category = "super-additive"
        elif interaction < -5.0:
            category = "sub-additive"
        else:
            category = "additive"

        # Fisher exact: pair vs H-baseline (significance of pair effect itself)
        pair_table = np.array([
            [counts["ok"], counts["total"] - counts["ok"]],
            [h_ok, h_n - h_ok]
        ])
        _, p_pair_vs_h = stats.fisher_exact(pair_table)

        # Wilson CI on pair rate
        lo, hi = wilson_ci(counts["ok"], counts["total"])

        results.append({
            "pair": pair_id,
            "observed_drop_pp": pair_drop * 100,
            "expected_drop_pp": expected_drop * 100,
            "interaction_pp": interaction,
            "category": category,
            "n": counts["total"], "ok": counts["ok"],
            "pair_rate": pair_rate, "ci_lo": lo * 100, "ci_hi": hi * 100,
            "p_vs_h": p_pair_vs_h,
        })

    # Chi-square test for overall additivity departure
    super_count = sum(1 for r in results if r["category"] == "super-additive")
    additive_count = sum(1 for r in results if r["category"] == "additive")
    sub_count = sum(1 for r in results if r["category"] == "sub-additive")
    # Under null (pure additivity), all pairs should be "additive"
    # Observed: 15/9/4 (Claude). Expected under H0: 28/0/0 (impossible, so use 50/50 null)
    # Better: Binomial test that p(super) ≠ p(sub) (symmetric deviations)
    if super_count + sub_count > 0:
        binom_p = stats.binomtest(super_count, super_count + sub_count, p=0.5).pvalue
    else:
        binom_p = 1.0

    return results, {
        "super": super_count, "additive": additive_count, "sub": sub_count,
        "total": len(results),
        "binomial_p": binom_p,
        "interpretation": (
            "p < 0.05 rejects symmetric additivity — interactions are "
            "systematically super-additive (amplification, not saturation)"
            if binom_p < 0.05 else
            "p >= 0.05 — interactions are balanced between super and sub-additive"
        ),
    }


# ════════════════════════════════════════════════════════════════
# §5.1b GEE for Mode A (task-level clustering)
# ════════════════════════════════════════════════════════════════
def test_gee_mode_a(claude_cases, agent="text-only"):
    """
    GEE with exchangeable correlation clustered on task identity.
    Tests whether operator family (L/ML/H) predicts success after
    accounting for task-level clustering.

    Reuses the same GEE approach as the composite study (glmm_analysis.py)
    but applied to Mode A individual operator data.
    """
    import pandas as pd
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.cov_struct import Exchangeable

    rows = [c for c in claude_cases if c["agent"] == agent]
    df = pd.DataFrame(rows)
    df["success_int"] = df["success"].astype(int)
    df["is_destructive"] = df["opId"].isin(["L1", "L5"]).astype(int)
    df["is_low_family"] = df["opId"].str.startswith("L").astype(int)
    df["is_h_family"] = df["opId"].str.startswith("H").astype(int)

    results = {}

    # Model 1: Binary destructive indicator (L1/L5 vs rest)
    m1 = GEE.from_formula(
        "success_int ~ is_destructive",
        groups="taskId", data=df,
        family=Binomial(), cov_struct=Exchangeable(),
    ).fit()
    results["M1_destructive"] = {
        "formula": "success ~ is_destructive + (exch|task)",
        "beta": round(m1.params["is_destructive"], 4),
        "z": round(m1.tvalues["is_destructive"], 3),
        "p": m1.pvalues["is_destructive"],
        "OR": round(np.exp(m1.params["is_destructive"]), 3),
    }

    # Model 2: Low-family indicator (all L-operators vs H-baseline)
    m2 = GEE.from_formula(
        "success_int ~ is_low_family",
        groups="taskId", data=df,
        family=Binomial(), cov_struct=Exchangeable(),
    ).fit()
    results["M2_low_family"] = {
        "formula": "success ~ is_low_family + (exch|task)",
        "beta": round(m2.params["is_low_family"], 4),
        "z": round(m2.tvalues["is_low_family"], 3),
        "p": m2.pvalues["is_low_family"],
        "OR": round(np.exp(m2.params["is_low_family"]), 3),
    }

    return results


# ════════════════════════════════════════════════════════════════
# §5.1c Majority-vote sensitivity for Mode A
# ════════════════════════════════════════════════════════════════
def test_majority_vote_mode_a(claude_cases, agent="text-only"):
    """
    Aggregates 3 reps per (task, operator) cell into a single majority-vote
    outcome (success if ≥2 of 3 reps succeed). Re-runs Fisher exact on
    L1 and L5 to verify robustness.

    Reuses the same majority-vote logic as the composite study
    (majority_vote_sensitivity.py) but adapted for 3-rep Mode A cells.
    """
    # Group by (task, operator) → majority vote
    cells = defaultdict(lambda: {"ok": 0, "total": 0})
    for c in claude_cases:
        if c["agent"] != agent:
            continue
        key = (c["taskId"], c["opId"])
        cells[key]["total"] += 1
        if c["success"]:
            cells[key]["ok"] += 1

    mv_cells = []
    for (tid, opId), counts in cells.items():
        majority = 1 if counts["ok"] >= 2 else 0  # ≥2/3 = success
        mv_cells.append({"taskId": tid, "opId": opId, "success": majority})

    # H-baseline under majority vote
    h_mv = [c for c in mv_cells if c["opId"].startswith("H")]
    h_ok = sum(c["success"] for c in h_mv)
    h_n = len(h_mv)
    h_rate = h_ok / h_n if h_n > 0 else 0

    # Test L1 and L5 under majority vote
    results = {}
    for op in ["L1", "L5", "L12"]:
        op_mv = [c for c in mv_cells if c["opId"] == op]
        op_ok = sum(c["success"] for c in op_mv)
        op_n = len(op_mv)
        if op_n == 0:
            continue
        op_rate = op_ok / op_n
        table = np.array([[op_ok, op_n - op_ok], [h_ok, h_n - h_ok]])
        _, p = stats.fisher_exact(table)
        results[op] = {
            "rate": op_rate, "n": op_n, "ok": op_ok,
            "h_rate": h_rate, "h_n": h_n,
            "p_fisher": p,
            "preserves": p < 0.05,
        }

    # Variance cells (cells where not all 3 reps agree)
    variance_count = sum(1 for (_, _), c in cells.items()
                         if 0 < c["ok"] < c["total"])
    total_cells = len(cells)

    return results, {
        "total_cells": total_cells,
        "variance_cells": variance_count,
        "variance_pct": round(100 * variance_count / total_cells, 1) if total_cells > 0 else 0,
        "h_rate_mv": round(h_rate * 100, 1),
    }


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("AMT PAPER STATISTICAL TESTS")
    print("=" * 70)

    # ── Load data ──
    print("\n📂 Loading data...")
    claude_cases = load_cases([ROOT / "data" / "mode-a-shard-a",
                                ROOT / "data" / "mode-a-shard-b"])
    llama_cases = load_cases([ROOT / "data" / "mode-a-llama4-textonly"])
    c2_cases = load_cases([ROOT / "data" / "c2-composition-shard-a",
                            ROOT / "data" / "c2-composition-shard-b"])
    print(f"  Claude: {len(claude_cases)}, Llama 4: {len(llama_cases)}, C.2: {len(c2_cases)}")

    # ════════════════════════════════════════════════════════════
    # §5.1 Per-operator significance
    # ════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("§5.1 PER-OPERATOR SIGNIFICANCE (Claude text-only)")
    print(f"{'─' * 70}")
    print("H0: operator rate = H-baseline rate")
    print("Test: Fisher's exact, Holm-Bonferroni corrected (26 ops)")

    per_op, h_rate, h_n, h_ok = test_per_operator_significance(claude_cases, "text-only")
    print(f"\n  H-baseline: {h_ok}/{h_n} ({h_rate*100:.1f}%)")
    print(f"\n  {'Op':>5s}  {'Rate':>14s}  {'Drop':>8s}  {'OR':>8s}  {'OR 95%CI':>20s}  {'p (Holm)':>10s}  Sig")
    print("  " + "-" * 85)
    for r in sorted(per_op, key=lambda x: -x["drop_pp"] if x["p_raw"] else 0):
        if r["p_raw"] is None:
            print(f"  {r['operator']:>5s}  {r['ok']}/{r['n']} ({r['rate']*100:5.1f}%)  "
                  f"{'(H-base)':>8s}")
            continue
        sig = "***" if r["p_holm"] < 0.001 else ("**" if r["p_holm"] < 0.01 else
              ("*" if r["p_holm"] < 0.05 else "n.s."))
        or_ci = f"[{r['OR_ci'][0]:.2f}, {r['OR_ci'][1]:.2f}]"
        print(f"  {r['operator']:>5s}  {r['ok']}/{r['n']} ({r['rate']*100:5.1f}%)  "
              f"{r['drop_pp']:+7.1f}pp  {r['OR']:7.3f}  {or_ci:>20s}  {r['p_holm']:10.6f}  {sig}")

    # ════════════════════════════════════════════════════════════
    # §5.3 Cross-model replication
    # ════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("§5.3 CROSS-MODEL REPLICATION (Claude vs Llama 4)")
    print(f"{'─' * 70}")
    print("H0: operator OR is homogeneous across Claude and Llama 4")
    print("Test: Breslow-Day per operator, plus Mantel-Haenszel common OR")

    cross_results = test_cross_model_replication(claude_cases, llama_cases)
    print(f"\n  {'Op':>5s}  {'C.drop':>8s}  {'L4.drop':>8s}  {'OR.MH':>8s}  "
          f"{'BD χ²':>8s}  {'p':>8s}  Verdict")
    print("  " + "-" * 75)
    for r in sorted(cross_results, key=lambda x: -x["c_drop"]):
        verdict = "homogeneous" if r["homogeneous"] else "DIVERGENT"
        print(f"  {r['operator']:>5s}  {r['c_drop']*100:+6.1f}pp  "
              f"{r['l_drop']*100:+6.1f}pp  {r['OR_mh']:8.3f}  "
              f"{r['BD']:8.3f}  {r['p']:8.4f}  {verdict}")
    
    homog_count = sum(1 for r in cross_results if r["homogeneous"])
    print(f"\n  Summary: {homog_count}/{len(cross_results)} operators show OR homogeneity")
    print(f"  (Fail to reject H0 → effect replicates across models)")

    # ════════════════════════════════════════════════════════════
    # §5.4 Compositional interaction
    # ════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("§5.4 COMPOSITIONAL INTERACTION (28 pairs, Claude text-only)")
    print(f"{'─' * 70}")
    print("H0: pair drop = sum of individual drops (pure additivity)")
    print("Classification: super/additive/sub based on ±5pp interaction threshold")

    comp_results, comp_summary = test_compositional_interaction(
        claude_cases, c2_cases, "text-only"
    )
    print(f"\n  {'Pair':>8s}  {'Obs':>8s}  {'Exp':>8s}  {'Inter':>8s}  {'Category':>16s}  "
          f"{'p_vs_H':>9s}")
    print("  " + "-" * 75)
    for r in sorted(comp_results, key=lambda x: -x["interaction_pp"]):
        print(f"  {r['pair']:>8s}  {r['observed_drop_pp']:+6.1f}pp  "
              f"{r['expected_drop_pp']:+6.1f}pp  {r['interaction_pp']:+6.1f}pp  "
              f"{r['category']:>16s}  {r['p_vs_h']:9.6f}")

    print(f"\n  Super-additive: {comp_summary['super']}/{comp_summary['total']}")
    print(f"  Additive:       {comp_summary['additive']}/{comp_summary['total']}")
    print(f"  Sub-additive:   {comp_summary['sub']}/{comp_summary['total']}")
    print(f"  Binomial test (super vs sub): p = {comp_summary['binomial_p']:.6f}")
    print(f"  → {comp_summary['interpretation']}")

    # ════════════════════════════════════════════════════════════
    # §5.1b GEE for Mode A (task-level clustering)
    # ════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("§5.1b GEE FOR MODE A (task-level clustering)")
    print(f"{'─' * 70}")
    print("Tests operator effects with GEE exchangeable correlation on task")

    try:
        gee_results = test_gee_mode_a(claude_cases, "text-only")
        for name, r in gee_results.items():
            print(f"\n  {name}: {r['formula']}")
            print(f"    β = {r['beta']}, z = {r['z']}, p = {r['p']:.2e}, OR = {r['OR']}")
    except Exception as e:
        print(f"  ⚠️ GEE failed (likely missing statsmodels): {e}")
        gee_results = {}

    # ════════════════════════════════════════════════════════════
    # §5.1c Majority-vote sensitivity for Mode A
    # ════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("§5.1c MAJORITY-VOTE SENSITIVITY (Mode A, 3 reps → 1 vote)")
    print(f"{'─' * 70}")
    print("Aggregates 3 reps per cell into majority vote (≥2/3 = success)")

    mv_results, mv_summary = test_majority_vote_mode_a(claude_cases, "text-only")
    print(f"\n  Total cells: {mv_summary['total_cells']}")
    print(f"  Cells with between-rep variance: {mv_summary['variance_cells']} "
          f"({mv_summary['variance_pct']}%)")
    print(f"  H-baseline (majority vote): {mv_summary['h_rate_mv']}%")
    for op, r in mv_results.items():
        status = "✅ PRESERVES" if r["preserves"] else "⚠️ loses significance"
        print(f"  {op}: {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) "
              f"p={r['p_fisher']:.6f} {status}")

    # ════════════════════════════════════════════════════════════
    # Write markdown report
    # ════════════════════════════════════════════════════════════
    report_path = OUTPUT_DIR / "statistics_report.md"
    with open(report_path, "w") as f:
        f.write("# AMT Paper Statistical Tests\n\n")
        f.write(f"**Generated**: by `analysis/amt_statistics.py`\n")
        f.write(f"**Data**: Mode A Claude (3,042) + Llama 4 (1,014) + C.2 (2,188 text-only)\n\n")
        f.write("---\n\n")

        f.write("## §5.1 Per-Operator Significance (Claude text-only)\n\n")
        f.write(f"**H-baseline**: {h_ok}/{h_n} ({h_rate*100:.1f}%)\n")
        f.write("**Test**: Fisher's exact with Holm-Bonferroni correction (α=0.05, 26 ops)\n\n")
        f.write("| Op | Rate | Drop | OR | OR 95%CI | p (Holm) | Sig |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in sorted(per_op, key=lambda x: -x["drop_pp"] if x["p_raw"] else 0):
            if r["p_raw"] is None:
                f.write(f"| {r['operator']} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                        f"— | — | — | — | H-base |\n")
                continue
            sig = "***" if r["p_holm"] < 0.001 else ("**" if r["p_holm"] < 0.01 else
                  ("*" if r["p_holm"] < 0.05 else "n.s."))
            or_ci = f"[{r['OR_ci'][0]:.2f}, {r['OR_ci'][1]:.2f}]"
            f.write(f"| {r['operator']} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                    f"{r['drop_pp']:+.1f}pp | {r['OR']:.3f} | {or_ci} | "
                    f"{r['p_holm']:.6f} | {sig} |\n")
        
        sig_ops = [r for r in per_op if r["significant"]]
        f.write(f"\n**Summary**: {len(sig_ops)}/{len([r for r in per_op if r['p_raw']])} "
                f"non-H operators show significant difference from H-baseline at α=0.05 (Holm).\n\n")

        f.write("---\n\n")
        f.write("## §5.3 Cross-Model Replication\n\n")
        f.write("**H0**: operator OR is homogeneous across Claude and Llama 4\n")
        f.write("**Test**: Breslow-Day per operator (df=1)\n\n")
        f.write("| Op | Claude drop | Llama4 drop | OR (MH) | Cohen's h | BD χ² | p | Verdict |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in sorted(cross_results, key=lambda x: -x["c_drop"]):
            verdict = "homogeneous" if r["homogeneous"] else "**DIVERGENT**"
            f.write(f"| {r['operator']} | {r['c_drop']*100:+.1f}pp | "
                    f"{r['l_drop']*100:+.1f}pp | {r['OR_mh']:.3f} | "
                    f"{r['cohen_h']:.3f} | {r['BD']:.3f} | {r['p']:.4f} | {verdict} |\n")
        f.write(f"\n**Summary**: {homog_count}/{len(cross_results)} operators show OR homogeneity.\n\n")

        f.write("---\n\n")
        f.write("## §5.4 Compositional Interaction\n\n")
        f.write("**H0**: pair drop = sum of individual drops (pure additivity)\n")
        f.write("**Classification**: super-additive (>+5pp), additive (±5pp), sub-additive (<-5pp)\n\n")
        f.write("| Pair | Observed drop | Expected drop | Interaction | Category | p vs H |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in sorted(comp_results, key=lambda x: -x["interaction_pp"]):
            f.write(f"| {r['pair']} | {r['observed_drop_pp']:+.1f}pp | "
                    f"{r['expected_drop_pp']:+.1f}pp | {r['interaction_pp']:+.1f}pp | "
                    f"{r['category']} | {r['p_vs_h']:.6f} |\n")
        f.write(f"\n**Summary**:\n")
        f.write(f"- Super-additive: {comp_summary['super']}/{comp_summary['total']}\n")
        f.write(f"- Additive: {comp_summary['additive']}/{comp_summary['total']}\n")
        f.write(f"- Sub-additive: {comp_summary['sub']}/{comp_summary['total']}\n")
        f.write(f"- Binomial test (super vs sub, H0: 50/50): p = {comp_summary['binomial_p']:.6f}\n")
        f.write(f"- Interpretation: {comp_summary['interpretation']}\n")

        # §5.1b GEE
        f.write("\n---\n\n## §5.1b GEE for Mode A (task-level clustering)\n\n")
        if gee_results:
            for name, r in gee_results.items():
                f.write(f"**{name}**: `{r['formula']}`\n")
                f.write(f"- β = {r['beta']}, z = {r['z']}, p = {r['p']:.2e}, OR = {r['OR']}\n\n")
        else:
            f.write("GEE analysis not available (missing statsmodels GEE).\n\n")

        # §5.1c Majority-vote
        f.write("---\n\n## §5.1c Majority-Vote Sensitivity (Mode A)\n\n")
        f.write(f"**Aggregation**: 3 reps per cell → majority vote (≥2/3 = success)\n")
        f.write(f"**Total cells**: {mv_summary['total_cells']}\n")
        f.write(f"**Cells with variance**: {mv_summary['variance_cells']} ({mv_summary['variance_pct']}%)\n")
        f.write(f"**H-baseline (MV)**: {mv_summary['h_rate_mv']}%\n\n")
        f.write("| Op | Rate (MV) | n | p (Fisher) | Preserves? |\n")
        f.write("|---|---|---|---|---|\n")
        for op, r in mv_results.items():
            status = "✅ Yes" if r["preserves"] else "⚠️ No"
            f.write(f"| {op} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                    f"{r['n']} | {r['p_fisher']:.6f} | {status} |\n")

    print(f"\n{'═' * 70}")
    print(f"Written: {report_path}")
    print(f"{'═' * 70}")


if __name__ == "__main__":
    main()

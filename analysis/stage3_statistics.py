#!/usr/bin/env python3
"""
Stage 3 Statistical Analysis — Breadth Expansion (48 tasks × 26 ops × 3 reps)
===============================================================================

Runs the same statistical tests as amt_statistics.py but on Stage 3 data.
Reuses all statistical helpers from amt_statistics.py.

DATA SOURCES:
  - data/stage3-claude/   (Claude Sonnet 4, text-only, 3,744 cases)
  - data/stage3-llama/    (Llama 4 Maverick, text-only, 3,744 cases)

TESTS:
  1. Per-operator significance (Fisher exact + Holm-Bonferroni, 26 tests)
  2. GEE for task-level clustering (destructive indicator + Low-family)
  3. Majority-vote sensitivity (3 reps → 1 vote)
  4. Cross-model replication (Breslow-Day per operator)
  5. Spearman correlation: DOM magnitude vs behavioral drop

OUTPUT:
  results/stage3/statistics_report.md
  results/stage3/per-operator-stage3.csv

USAGE:
  python3 analysis/stage3_statistics.py
"""

import glob
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

# ── Reuse statistical helpers from amt_statistics ──────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from amt_statistics import (
    wilson_ci, odds_ratio_ci, cohens_h,
    mantel_haenszel_or, breslow_day,
    test_per_operator_significance,
    test_cross_model_replication,
    test_gee_mode_a,
    test_majority_vote_mode_a,
)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "stage3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Stage 3 has no GT corrections needed (Gate 6 excluded state-mutation tasks)
# But keep the same corrections for consistency with Mode A
GT_CORRECTIONS = {
    "41": ["abomin", "abdomin"],
    "198": ["veronica costello"],
    "293": ["git clone ssh://git@10.0.1.50:2222/convexegg/super_awesome_robot.git"],
}


def load_stage3_cases(data_dir: Path) -> list:
    """
    Load Stage 3 cases. Different structure from Mode A:
    - Cases are directories: <app>_individual_<taskId>_<ci>_<attempt>_<opId>/
    - Trace is in trace-attempt-1.json (or trace-attempt-2.json for retries)
    - No top-level caseId field; parse from directory name
    """
    cases = []
    run_dirs = list(data_dir.glob("*/runs/*/cases/*/"))
    if not run_dirs:
        # Try flat structure
        run_dirs = list(data_dir.glob("*/cases/*/"))

    for case_dir in run_dirs:
        dir_name = case_dir.name
        # Format: <app>_individual_<taskId>_<ci>_<attempt>_<opId>
        # e.g. ecommerce_admin_individual_187_0_1_H1
        # Find "individual" marker — split on it
        if "_individual_" not in dir_name:
            continue
        app, rest = dir_name.split("_individual_", 1)
        after = rest.split("_")
        if len(after) < 4:
            continue
        tid = after[0]
        opId = after[3]

        # Load trace — use highest-numbered attempt (final result)
        trace_files = sorted(case_dir.glob("trace-attempt-*.json"))
        if not trace_files:
            continue
        trace_path = trace_files[-1]  # highest attempt = final result

        with open(trace_path) as f:
            t = json.load(f)

        agent = t.get("agentConfig", {}).get("observationMode", "text-only")
        success = t.get("success", False)
        outcome = t.get("outcome", "")

        # Apply GT corrections (same as Mode A)
        if not success and tid in GT_CORRECTIONS:
            answer = ""
            for s in t.get("steps", []):
                a = s.get("action", "")
                if "send_msg_to_user" in a:
                    answer = a
                    break
            if answer:
                for valid in GT_CORRECTIONS[tid]:
                    if valid in answer.lower():
                        success = True
                        break

        cases.append({
            "caseId": dir_name,
            "taskId": tid,
            "opId": opId,
            "app": app,
            "agent": agent,
            "success": success,
            "outcome": outcome,
            "totalTokens": t.get("totalTokens", 0),
            "totalSteps": t.get("totalSteps", 0),
        })

    return cases


def main():
    print("=" * 70)
    print("STAGE 3 STATISTICAL ANALYSIS (48 tasks × 26 ops × 3 reps)")
    print("=" * 70)

    # ── Load data ──────────────────────────────────────────────────────
    print("\n📂 Loading Stage 3 data...")
    claude_cases = load_stage3_cases(ROOT / "data" / "stage3-claude")
    llama_cases = load_stage3_cases(ROOT / "data" / "stage3-llama")
    print(f"  Claude: {len(claude_cases)} cases")
    print(f"  Llama 4: {len(llama_cases)} cases")

    if len(claude_cases) == 0:
        print("  ❌ No Claude cases found. Check data directory structure.")
        return
    if len(llama_cases) == 0:
        print("  ❌ No Llama cases found. Check data directory structure.")
        return

    # ── §5.1 Per-operator significance ────────────────────────────────
    print(f"\n{'─'*70}")
    print("§5.1 PER-OPERATOR SIGNIFICANCE (Stage 3 Claude text-only)")
    print(f"{'─'*70}")

    per_op, h_rate, h_n, h_ok = test_per_operator_significance(
        claude_cases, "text-only"
    )
    print(f"\n  H-baseline: {h_ok}/{h_n} ({h_rate*100:.1f}%)")
    print(f"\n  {'Op':<6} {'Rate':>14}  {'Drop':>8}  {'OR':>8}  {'OR 95%CI':>20}  {'p(Holm)':>10}  Sig")
    print("  " + "-" * 80)

    rows = []
    for r in sorted(per_op, key=lambda x: -x["drop_pp"] if x["p_raw"] else 0):
        if r["p_raw"] is None:
            print(f"  {r['operator']:<6}  {r['ok']}/{r['n']} ({r['rate']*100:5.1f}%)  {'(H-base)':>8}")
            rows.append({**r, "dataset": "stage3"})
            continue
        sig = ("***" if r["p_holm"] < 0.001 else
               "**" if r["p_holm"] < 0.01 else
               "*" if r["p_holm"] < 0.05 else "n.s.")
        or_ci = f"[{r['OR_ci'][0]:.2f}, {r['OR_ci'][1]:.2f}]"
        print(f"  {r['operator']:<6}  {r['ok']}/{r['n']} ({r['rate']*100:5.1f}%)  "
              f"{r['drop_pp']:+7.1f}pp  {r['OR']:7.3f}  {or_ci:>20}  "
              f"{r['p_holm']:10.6f}  {sig}")
        rows.append({**r, "dataset": "stage3"})

    sig_ops = [r for r in per_op if r.get("significant")]
    print(f"\n  Significant operators: {len(sig_ops)}/16 non-H operators")

    # Save per-operator CSV
    df_ops = pd.DataFrame(rows)
    df_ops.to_csv(OUT_DIR / "per-operator-stage3.csv", index=False)

    # ── §5.1b GEE for task-level clustering ───────────────────────────
    print(f"\n{'─'*70}")
    print("§5.1b GEE (task-level clustering, Stage 3)")
    print(f"{'─'*70}")
    try:
        gee_results = test_gee_mode_a(claude_cases, "text-only")
        for name, r in gee_results.items():
            print(f"  {name}: β={r['beta']}, z={r['z']}, p={r['p']:.2e}, OR={r['OR']}")
    except Exception as e:
        print(f"  ⚠️ GEE failed: {e}")
        gee_results = {}

    # ── §5.1c Majority-vote sensitivity ───────────────────────────────
    print(f"\n{'─'*70}")
    print("§5.1c MAJORITY-VOTE SENSITIVITY (Stage 3, 3 reps → 1 vote)")
    print(f"{'─'*70}")
    mv_results, mv_summary = test_majority_vote_mode_a(claude_cases, "text-only")
    print(f"  Total cells: {mv_summary['total_cells']}")
    print(f"  Cells with variance: {mv_summary['variance_cells']} ({mv_summary['variance_pct']}%)")
    print(f"  H-baseline (MV): {mv_summary['h_rate_mv']}%")
    for op, r in mv_results.items():
        status = "✅ PRESERVES" if r["preserves"] else "⚠️ loses significance"
        print(f"  {op}: {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) p={r['p_fisher']:.6f} {status}")

    # ── §5.3 Cross-model replication ──────────────────────────────────
    print(f"\n{'─'*70}")
    print("§5.3 CROSS-MODEL REPLICATION (Stage 3 Claude vs Llama 4)")
    print(f"{'─'*70}")
    cross_results = test_cross_model_replication(claude_cases, llama_cases)
    print(f"\n  {'Op':<6}  {'C.drop':>8}  {'L4.drop':>8}  {'OR.MH':>8}  {'BD χ²':>8}  {'p':>8}  Verdict")
    print("  " + "-" * 70)
    for r in sorted(cross_results, key=lambda x: -x["c_drop"]):
        verdict = "homogeneous" if r["homogeneous"] else "DIVERGENT"
        print(f"  {r['operator']:<6}  {r['c_drop']*100:+6.1f}pp  "
              f"{r['l_drop']*100:+6.1f}pp  {r['OR_mh']:8.3f}  "
              f"{r['BD']:8.3f}  {r['p']:8.4f}  {verdict}")
    homog = sum(1 for r in cross_results if r["homogeneous"])
    print(f"\n  {homog}/{len(cross_results)} operators show OR homogeneity")

    # ── §5.2 Spearman: DOM magnitude vs behavioral drop ───────────────
    print(f"\n{'─'*70}")
    print("§5.2 SPEARMAN: DOM MAGNITUDE vs BEHAVIORAL DROP")
    print(f"{'─'*70}")
    dom_path = ROOT / "results" / "amt" / "dom_signature_matrix.csv"
    if dom_path.exists():
        dom_df = pd.read_csv(dom_path)
        # Compute total DOM magnitude per operator
        dom_cols = [c for c in dom_df.columns if c.startswith(("D1", "A1", "A2", "F1"))]
        if dom_cols:
            dom_df["dom_magnitude"] = dom_df[dom_cols].abs().sum(axis=1)
        else:
            dom_df["dom_magnitude"] = dom_df.select_dtypes(include=[float]).abs().sum(axis=1)

        # Merge with behavioral drops
        op_drops = {r["operator"]: r["drop_pp"]
                    for r in per_op if r.get("p_raw") is not None}
        dom_df["behavioral_drop"] = dom_df["operator"].map(op_drops)
        merged = dom_df.dropna(subset=["behavioral_drop"])

        if len(merged) >= 5:
            rho, p_spearman = stats.spearmanr(
                merged["dom_magnitude"], merged["behavioral_drop"]
            )
            print(f"  Spearman ρ = {rho:.3f}, p = {p_spearman:.4f}")
            print(f"  Interpretation: {'significant' if p_spearman < 0.05 else 'not significant'}")
            print(f"  (negative ρ = larger DOM change → smaller behavioral drop = misalignment)")
        else:
            print(f"  ⚠️ Not enough operators with both DOM and behavioral data")
    else:
        print(f"  ⚠️ DOM signature matrix not found at {dom_path}")

    # ── Token inflation analysis ───────────────────────────────────────
    print(f"\n{'─'*70}")
    print("TOKEN INFLATION (Stage 3 Claude, text-only)")
    print(f"{'─'*70}")
    text_cases = [c for c in claude_cases if c["agent"] == "text-only"]
    h_tokens = [c["totalTokens"] for c in text_cases
                if c["opId"].startswith("H") and c["totalTokens"] > 0]
    l1_tokens = [c["totalTokens"] for c in text_cases
                 if c["opId"] == "L1" and c["totalTokens"] > 0]
    l5_tokens = [c["totalTokens"] for c in text_cases
                 if c["opId"] == "L5" and c["totalTokens"] > 0]

    if h_tokens and l1_tokens:
        stat, p_wilcox = stats.mannwhitneyu(l1_tokens, h_tokens, alternative="greater")
        print(f"  H-baseline tokens: median={np.median(h_tokens):.0f}, "
              f"p90={np.percentile(h_tokens, 90):.0f}")
        print(f"  L1 tokens: median={np.median(l1_tokens):.0f}, "
              f"p90={np.percentile(l1_tokens, 90):.0f}")
        print(f"  L5 tokens: median={np.median(l5_tokens):.0f}, "
              f"p90={np.percentile(l5_tokens, 90):.0f}")
        ratio = np.median(l1_tokens) / np.median(h_tokens) if np.median(h_tokens) > 0 else 0
        print(f"  L1/H-baseline token ratio: {ratio:.2f}×")
        print(f"  Wilcoxon L1 > H-baseline: p = {p_wilcox:.2e}")

    # ── Write markdown report ──────────────────────────────────────────
    report_path = OUT_DIR / "statistics_report.md"
    with open(report_path, "w") as f:
        f.write("# Stage 3 Statistical Analysis\n\n")
        f.write(f"**Data**: Stage 3 Claude ({len(claude_cases)}) + Llama 4 ({len(llama_cases)})\n")
        f.write(f"**Tasks**: 48 (pre-registered 7-gate selection)\n")
        f.write(f"**Operators**: 26 AMT operators × 3 reps\n\n")
        f.write("---\n\n")

        f.write("## §5.1 Per-Operator Significance (Claude text-only)\n\n")
        f.write(f"**H-baseline**: {h_ok}/{h_n} ({h_rate*100:.1f}%)\n")
        f.write("**Test**: Fisher's exact + Holm-Bonferroni (26 operators)\n\n")
        f.write("| Op | Rate | Drop | OR | OR 95%CI | p (Holm) | Sig |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in sorted(per_op, key=lambda x: -x["drop_pp"] if x["p_raw"] else 0):
            if r["p_raw"] is None:
                f.write(f"| {r['operator']} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                        f"— | — | — | — | H-base |\n")
                continue
            sig = ("***" if r["p_holm"] < 0.001 else
                   "**" if r["p_holm"] < 0.01 else
                   "*" if r["p_holm"] < 0.05 else "n.s.")
            or_ci = f"[{r['OR_ci'][0]:.2f}, {r['OR_ci'][1]:.2f}]"
            f.write(f"| {r['operator']} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                    f"{r['drop_pp']:+.1f}pp | {r['OR']:.3f} | {or_ci} | "
                    f"{r['p_holm']:.6f} | {sig} |\n")
        f.write(f"\n**Significant**: {len(sig_ops)}/16 non-H operators\n\n")

        f.write("---\n\n## §5.1b GEE (task-level clustering)\n\n")
        if gee_results:
            for name, r in gee_results.items():
                f.write(f"**{name}**: β={r['beta']}, z={r['z']}, p={r['p']:.2e}, OR={r['OR']}\n\n")

        f.write("---\n\n## §5.1c Majority-Vote Sensitivity\n\n")
        f.write(f"Total cells: {mv_summary['total_cells']}, "
                f"variance: {mv_summary['variance_cells']} ({mv_summary['variance_pct']}%)\n\n")
        f.write("| Op | Rate (MV) | p | Preserves? |\n|---|---|---|---|\n")
        for op, r in mv_results.items():
            f.write(f"| {op} | {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) | "
                    f"{r['p_fisher']:.6f} | {'✅' if r['preserves'] else '⚠️'} |\n")

        f.write("\n---\n\n## §5.3 Cross-Model Replication\n\n")
        f.write("| Op | Claude drop | Llama4 drop | OR (MH) | BD χ² | p | Verdict |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in sorted(cross_results, key=lambda x: -x["c_drop"]):
            verdict = "homogeneous" if r["homogeneous"] else "**DIVERGENT**"
            f.write(f"| {r['operator']} | {r['c_drop']*100:+.1f}pp | "
                    f"{r['l_drop']*100:+.1f}pp | {r['OR_mh']:.3f} | "
                    f"{r['BD']:.3f} | {r['p']:.4f} | {verdict} |\n")
        f.write(f"\n**{homog}/{len(cross_results)} operators show OR homogeneity**\n")

    print(f"\n{'═'*70}")
    print(f"Written: {report_path}")
    print(f"Written: {OUT_DIR / 'per-operator-stage3.csv'}")
    print(f"{'═'*70}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Supplementary statistical companions for audit remediation (cluster STAT/GEE/POW/EFF).

NON-DESTRUCTIVE: reads frozen artifacts read-only; writes ONLY to
results/supplementary/*.csv. Does NOT mutate any frozen results CSV/JSON.

Outputs:
  - design_effect_adjusted_z.csv : cluster-robust (design-effect-adjusted) Z/p
        for the composite text-only Low-vs-rest headline (STAT-1 / DET-1).
  - gee_categorical_m2.csv        : pooled C(variant) categorical GEE coefficients
        (the source of the "Medium-low/High do not differ" claim) (STAT-1 / GEE-1).
  - per_operator_cohens_h.csv     : Cohen's h per significant Stage 3 operator vs
        the 91.9% Claude H-baseline (EFF-2).
  - power_analysis.csv            : reproducible design-stage power figures (POW-1/2).

All inputs are frozen: results/combined-experiment.csv,
results/stage3/per-operator-stage3.csv, results/stats/full_report.md (ICC),
results/glmm_model_comparison.csv.
"""
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/alexjia/amt-workspace/ai-agent-accessibility"
RESULTS = os.path.join(REPO, "results")
SUPP = os.path.join(RESULTS, "supplementary")
os.makedirs(SUPP, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Design-effect-adjusted (cluster-robust) Z for composite text-only L-vs-rest
# ---------------------------------------------------------------------------
def design_effect_adjusted_z():
    # Frozen naive repetition-level statistic (primary_stats_per_panel.csv /
    # key-numbers.json actual = 9.8287). We re-state it here and derive the
    # design-effect-deflated companion. We do NOT overwrite the frozen value.
    z_naive = 9.829  # text-only Claude binary Low-vs-rest (Fisher-inverted/chi-sq)

    # ICCs (exchangeable working correlation = task-level dep_params) from the
    # frozen full_report.md Level-3 GEE block:
    #   pooled all text-only (both models): 0.247
    #   Llama 4 text-only:                  0.548
    icc_pooled = 0.247
    icc_llama = 0.548
    m = 5  # repetitions per task-cell in the composite study (natural cluster size)

    rows = []
    for label, icc in [("pooled_text_only", icc_pooled), ("llama4_text_only", icc_llama)]:
        deff = 1.0 + (m - 1) * icc
        z_adj = z_naive / math.sqrt(deff)
        # two-sided normal-tail p
        from scipy.stats import norm

        p_adj = 2.0 * norm.sf(abs(z_adj))
        rows.append(
            dict(
                basis=label,
                icc=icc,
                cluster_size_m=m,
                design_effect=round(deff, 4),
                z_naive=z_naive,
                z_cluster_robust=round(z_adj, 4),
                p_cluster_robust=p_adj,
            )
        )

    # Also persist the two already-computed cluster-conservative anchors so the
    # paper footnote/table can cite a single provenance file.
    rows.append(
        dict(
            basis="majority_vote_anchor",
            icc=np.nan,
            cluster_size_m=m,
            design_effect=np.nan,
            z_naive=z_naive,
            z_cluster_robust=4.005,  # results/majority_vote_sensitivity.csv
            p_cluster_robust=6.20629896861182e-05,
        )
    )
    rows.append(
        dict(
            basis="pooled_is_low_GEE_M3",
            icc=icc_pooled,
            cluster_size_m=m,
            design_effect=np.nan,
            z_naive=z_naive,
            z_cluster_robust=-5.632,  # results/glmm_model_comparison.csv M3
            p_cluster_robust=1.7834808988701228e-08,
        )
    )

    df = pd.DataFrame(rows)
    out = os.path.join(SUPP, "design_effect_adjusted_z.csv")
    df.to_csv(out, index=False)
    print(f"[1] wrote {out}")
    print(df.to_string(index=False))


# ---------------------------------------------------------------------------
# 2. Pooled categorical C(variant) GEE (M2) -- persist the coefficients that
#    back the "Medium-low and High do not differ from Base" claim.
# ---------------------------------------------------------------------------
def gee_categorical_m2():
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.genmod.cov_struct import Exchangeable
    from statsmodels.genmod.families import Binomial

    df = pd.read_csv(os.path.join(RESULTS, "combined-experiment.csv"))
    # Pooled across all agents + both model families (matches the M3 pooled spec).
    # Identify the success column and variant/task columns robustly.
    cols = {c.lower(): c for c in df.columns}
    succ = cols.get("success") or cols.get("task_success") or cols.get("ok")
    var = cols.get("variant")
    task = cols.get("task_id") or cols.get("task") or cols.get("taskid")
    if succ is None or var is None or task is None:
        print(f"[2] SKIP gee_categorical_m2: columns not found. have={list(df.columns)}")
        return

    d = df[[succ, var, task]].copy()
    d.columns = ["success", "variant", "task_id"]
    # success may be bool/str
    if d["success"].dtype == object:
        d["success"] = (
            d["success"].astype(str).str.lower().isin(["true", "1", "success", "1.0"]).astype(int)
        )
    else:
        d["success"] = d["success"].astype(float).round().astype(int)
    # Reference category = base
    d["variant"] = pd.Categorical(
        d["variant"], categories=["base", "low", "medium-low", "high"], ordered=False
    )
    d = d.dropna(subset=["variant"])

    try:
        model = smf.gee(
            "success ~ C(variant, Treatment(reference='base'))",
            groups="task_id",
            data=d,
            family=Binomial(),
            cov_struct=Exchangeable(),
        )
        res = model.fit()
        out_rows = []
        for name in res.params.index:
            out_rows.append(
                dict(
                    term=name,
                    beta=res.params[name],
                    se=res.bse[name],
                    z=res.tvalues[name],
                    p=res.pvalues[name],
                )
            )
        rdf = pd.DataFrame(out_rows)
        out = os.path.join(SUPP, "gee_categorical_m2.csv")
        rdf.to_csv(out, index=False)
        print(f"[2] wrote {out}")
        print(rdf.to_string(index=False))
    except Exception as e:  # perfect separation can blow up; disclose
        out = os.path.join(SUPP, "gee_categorical_m2.csv")
        pd.DataFrame([dict(term="ERROR", beta=np.nan, se=np.nan, z=np.nan, p=str(e))]).to_csv(
            out, index=False
        )
        print(f"[2] wrote {out} (with error note: {e})")


# ---------------------------------------------------------------------------
# 3. Per-operator Cohen's h vs 91.9% Claude H-baseline (EFF-2)
# ---------------------------------------------------------------------------
def per_operator_cohens_h():
    def cohens_h(p1, p2):
        return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))

    df = pd.read_csv(os.path.join(RESULTS, "stage3", "per-operator-stage3.csv"))
    h_baseline = 0.919  # Claude Stage 3 pooled H-baseline (key-numbers.json)
    sig = df[df["operator"].isin(["L1", "L9", "L5", "L12"])].copy()
    rows = []
    for _, r in sig.iterrows():
        h = cohens_h(float(r["rate"]), h_baseline)
        rows.append(
            dict(
                operator=r["operator"],
                rate=round(float(r["rate"]), 4),
                h_baseline=h_baseline,
                cohens_h=round(h, 3),  # negative => below baseline
                cohens_h_abs=round(abs(h), 3),
                magnitude=(
                    "large"
                    if abs(h) >= 0.5
                    else "medium"
                    if abs(h) >= 0.2
                    else "small"
                ),
                OR=round(float(r["OR"]), 3),
            )
        )
    rdf = pd.DataFrame(rows)
    out = os.path.join(SUPP, "per_operator_cohens_h.csv")
    rdf.to_csv(out, index=False)
    print(f"[3] wrote {out}")
    print(rdf.to_string(index=False))


# ---------------------------------------------------------------------------
# 4. Reproducible power analysis (POW-1 / POW-2)
# ---------------------------------------------------------------------------
def power_analysis():
    from statsmodels.stats.power import NormalIndPower

    def cohens_h(p1, p2):
        return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))

    analysis = NormalIndPower()
    rows = []

    def add(label, base, drop_pp, n1, ratio, alpha, alt):
        p1 = base
        p2 = base - drop_pp / 100.0
        h = abs(cohens_h(p1, p2))
        pw = analysis.power(
            effect_size=h, nobs1=n1, alpha=alpha, ratio=ratio, alternative=alt
        )
        rows.append(
            dict(
                scenario=label,
                baseline=base,
                drop_pp=drop_pp,
                cohens_h=round(h, 3),
                n1=n1,
                ratio=ratio,
                alpha=alpha,
                alternative=alt,
                power=round(pw, 4),
            )
        )

    # --- Stage 3 (POW-2): n1=144 per operator vs nb=1440 pooled H-baseline ---
    # Pooled H-baseline 91.9%. Holm across 26 tests -> alpha=0.05/26.
    holm = 0.05 / 26.0
    add("stage3_20pp_a05_2s", 0.919, 20, 144, 10, 0.05, "two-sided")
    add("stage3_20pp_holm_2s", 0.919, 20, 144, 10, holm, "two-sided")
    add("stage3_15pp_holm_2s", 0.919, 15, 144, 10, holm, "two-sided")
    # Baseline-conditionality demo: same nominal 20pp drop from a 50% baseline.
    add("stage3_20pp_from50_holm_2s", 0.50, 20, 144, 10, holm, "two-sided")

    # --- Mode A (POW-1): n1=39 per operator vs nb=390 H-baseline (93.9%) ------
    add("modeA_20pp_a05_2s", 0.9385, 20, 39, 10, 0.05, "two-sided")
    add("modeA_20pp_holm_2s", 0.9385, 20, 39, 10, holm, "two-sided")
    add("modeA_20pp_a05_1s", 0.9385, 20, 39, 10, 0.05, "larger")
    add("modeA_20pp_holm_1s", 0.9385, 20, 39, 10, holm, "larger")

    rdf = pd.DataFrame(rows)
    out = os.path.join(SUPP, "power_analysis.csv")
    rdf.to_csv(out, index=False)
    print(f"[4] wrote {out}")
    print(rdf.to_string(index=False))


if __name__ == "__main__":
    design_effect_adjusted_z()
    print()
    gee_categorical_m2()
    print()
    per_operator_cohens_h()
    print()
    power_analysis()

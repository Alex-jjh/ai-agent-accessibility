#!/usr/bin/env python3
"""TRIANG-4 remediation: corroborate the 66.1% site-variance figure.

The paper's §5.6 reports "site identity explains 66.1% of success variance" from
a descriptive sum-of-squares partition on binary success (griffith_triangulation.py).
A reviewer can object that an additive SS partition on 0/1 outcomes with crossed
(not nested) site and participant factors is non-standard. This script corroborates
the descriptive number with a proper crossed random-effects logistic model and
reports the variance-partition coefficient (VPC) on the latent scale.

Frozen-data-safe: reads only the deposited Griffith Excel via the existing loader;
writes a NEW supplementary CSV. No experiment re-run, no frozen artifact mutated.

Usage: analysis/.venv/bin/python results/supplementary/triang_variance_partition.py
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

# Reuse the audited loader from the main triangulation script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "analysis"))
from griffith_triangulation import load_from_excel, TASK_ORDER  # noqa: E402

SITE_OF = {t: t[:2] for t in TASK_ORDER}  # MM1->MM, GG2->GG, ...


def build_long(data):
    """Long-format (success, site, participant) rows; drop the ambiguous P23-GG1."""
    rows = []
    for pid, tasks in data.items():
        for task, (success, _t) in tasks.items():
            if pid == 23 and task == "GG1":
                continue  # ambiguous N/A entry, excluded (319 usable of 320)
            rows.append((1 if success else 0, SITE_OF[task], f"P{pid}"))
    return rows


def ss_partition(rows):
    """Descriptive additive SS partition (reproduces the paper's 66.1%)."""
    y = np.array([r[0] for r in rows], float)
    grand = y.mean()
    ss_total = ((y - grand) ** 2).sum()

    def factor_ss(idx):
        groups: dict[str, list[float]] = {}
        for r in rows:
            groups.setdefault(r[idx], []).append(r[0])
        return sum(len(v) * (np.mean(v) - grand) ** 2 for v in groups.values())

    ss_site = factor_ss(1)
    ss_part = factor_ss(2)
    return ss_site / ss_total, ss_part / ss_total, ss_total


def crossed_vpc(rows):
    """Crossed random-effects logistic VPC (latent-scale, Snijders-Bosker).

    Fit success ~ 1 + (1|site) + (1|participant) via a binomial GLMM. statsmodels
    has no crossed-RE binomial GLMM, so we fit the two variance components with a
    method-of-moments / Laplace fallback: use BinomialBayesMixedGLM if available,
    else fall back to a logit-scale ANOVA-of-empirical-logits approximation.
    VPC_site = var_site / (var_site + var_part + pi^2/3).
    """
    import pandas as pd

    df = pd.DataFrame(rows, columns=["y", "site", "pid"])
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

        # crossed: two independent random intercepts
        vc = {"site": "0 + C(site)", "pid": "0 + C(pid)"}
        m = BinomialBayesMixedGLM.from_formula("y ~ 1", vc, df)
        res = m.fit_vb()
        # vcp_mean are log-sd of the VC; recover variances
        names = list(res.model.vcp_names)
        sds = np.exp(np.asarray(res.vcp_mean))
        var = {n: float(s ** 2) for n, s in zip(names, sds)}
        v_site = var.get("site", 0.0)
        v_pid = var.get("pid", 0.0)
        method = "BinomialBayesMixedGLM (variational Bayes, latent logit scale)"
    except Exception as exc:  # noqa: BLE001
        # Fallback: variance of group empirical logits (Haldane-corrected).
        def group_logit_var(col):
            g = df.groupby(col)["y"].agg(["sum", "count"])
            p = (g["sum"] + 0.5) / (g["count"] + 1.0)
            lg = np.log(p / (1 - p))
            return float(np.var(lg, ddof=1))

        v_site = group_logit_var("site")
        v_pid = group_logit_var("pid")
        method = f"empirical-logit variance fallback ({type(exc).__name__})"

    resid = np.pi ** 2 / 3.0
    denom = v_site + v_pid + resid
    return v_site / denom, v_pid / denom, v_site, v_pid, method


def main() -> int:
    data = load_from_excel()
    rows = build_long(data)
    n = len(rows)
    site_ss, part_ss, _ = ss_partition(rows)
    vpc_site, vpc_pid, v_site, v_pid, method = crossed_vpc(rows)

    out = os.path.join(os.path.dirname(__file__), "triang_variance_partition.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "value", "note"])
        w.writerow(["n_usable_trials", n, "320 total minus ambiguous P23-GG1"])
        w.writerow(["ss_site_frac", round(site_ss, 4), "descriptive SS partition (paper's 66.1%)"])
        w.writerow(["ss_participant_frac", round(part_ss, 4), "descriptive SS partition"])
        w.writerow(["vpc_site_latent", round(vpc_site, 4), "crossed RE logistic VPC, site"])
        w.writerow(["vpc_participant_latent", round(vpc_pid, 4), "crossed RE logistic VPC, participant"])
        w.writerow(["var_site_logit", round(v_site, 4), method])
        w.writerow(["var_participant_logit", round(v_pid, 4), method])
    print(f"n={n} usable trials")
    print(f"  SS partition:  site={site_ss:.3f}  participant={part_ss:.3f}")
    print(f"  crossed VPC:   site={vpc_site:.3f}  participant={vpc_pid:.3f}  [{method}]")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

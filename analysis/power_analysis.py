#!/usr/bin/env python3
"""Design-stage power analysis for the AMT per-operator tests (POW-1 / POW-2).

This is the committed, reproducible source for the power figures cited in the
paper's Sample-size justification paragraph (sections/04-methodology.tex). It
recomputes power via the normal approximation to the two-proportion test (the
design-stage analogue of the Fisher exact analysis used for inference),
two-sided at alpha=0.05, conditional on the observed high-baseline rates, and
writes to results/supplementary/power_analysis.csv (NEW file; no frozen
artifact is mutated).

Run:  analysis/.venv/bin/python analysis/power_analysis.py
"""
import math
import os

import pandas as pd
from statsmodels.stats.power import NormalIndPower

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPP = os.path.join(REPO, "results", "supplementary")
os.makedirs(SUPP, exist_ok=True)

HOLM_ALPHA = 0.05 / 26.0  # Holm-Bonferroni across 26 operators (most conservative step)


def cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def compute() -> pd.DataFrame:
    analysis = NormalIndPower()
    rows = []

    def add(label, base, drop_pp, n1, ratio, alpha, alt):
        h = abs(cohens_h(base, base - drop_pp / 100.0))
        pw = analysis.power(effect_size=h, nobs1=n1, alpha=alpha, ratio=ratio, alternative=alt)
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

    # Stage 3 (POW-2): n1=144/operator vs nb=1440 pooled H-baseline 91.9%.
    add("stage3_20pp_a05_2s", 0.919, 20, 144, 10, 0.05, "two-sided")
    add("stage3_20pp_holm_2s", 0.919, 20, 144, 10, HOLM_ALPHA, "two-sided")
    add("stage3_15pp_holm_2s", 0.919, 15, 144, 10, HOLM_ALPHA, "two-sided")
    add("stage3_20pp_from50_holm_2s", 0.50, 20, 144, 10, HOLM_ALPHA, "two-sided")

    # Mode A (POW-1): n1=39/operator vs nb=390 H-baseline 93.9%.
    add("modeA_20pp_a05_2s", 0.9385, 20, 39, 10, 0.05, "two-sided")
    add("modeA_20pp_holm_2s", 0.9385, 20, 39, 10, HOLM_ALPHA, "two-sided")
    add("modeA_20pp_a05_1s", 0.9385, 20, 39, 10, 0.05, "larger")
    add("modeA_20pp_holm_1s", 0.9385, 20, 39, 10, HOLM_ALPHA, "larger")

    return pd.DataFrame(rows)


def main():
    df = compute()
    out = os.path.join(SUPP, "power_analysis.csv")
    df.to_csv(out, index=False)
    print(f"wrote {out}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()

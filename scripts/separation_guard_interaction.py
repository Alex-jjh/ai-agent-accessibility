#!/usr/bin/env python3
"""GEE-3 supplement-hygiene companion: detect quasi/perfect separation in the
Level-4 interaction GEE and emit an HONEST annotation, WITHOUT mutating any
frozen derived artifact.

Per HARD CONSTRAINT #1, this script does NOT overwrite the frozen
results/stats/full_report.md, results/stats/interaction_tests.csv, or
results/glmm_model_comparison.csv. It reads them read-only and writes a NEW
annotated companion to results/supplementary/interaction_separation_annotated.csv
plus a short markdown note. The build-supplementary.sh repoint and the
regeneration of the shipped statistics-composite.md require a user decision
(see remediation response_entry for GEE-3).

Separation rule (the guard that should be added to run_statistics.py Level-4):
  a coefficient is flagged as separation-driven if |beta| > 50 OR se == 0 OR
  beta/se is NaN. When any coefficient is flagged, the interaction is reported
  as "unestimable (separation)" rather than "Significant", and no p-value with
  se == 0 is emitted.
"""
import math
import os

import numpy as np
import pandas as pd

REPO = "/home/alexjia/amt-workspace/ai-agent-accessibility"
RESULTS = os.path.join(REPO, "results")
SUPP = os.path.join(RESULTS, "supplementary")
os.makedirs(SUPP, exist_ok=True)

SEP_BETA_THRESH = 50.0


def is_separation(beta, se):
    if pd.isna(beta) or pd.isna(se):
        return True
    if se == 0.0:
        return True
    if abs(beta) > SEP_BETA_THRESH:
        return True
    return False


def main():
    src = os.path.join(RESULTS, "stats", "interaction_tests.csv")
    df = pd.read_csv(src)  # read-only
    rows = []
    flagged_tests = {}
    for _, r in df.iterrows():
        flag = is_separation(r["beta"], r["se"])
        flagged_tests.setdefault(r["test"], False)
        flagged_tests[r["test"]] = flagged_tests[r["test"]] or flag
        rows.append(
            dict(
                test=r["test"],
                predictor=r["predictor"],
                beta=r["beta"],
                se=r["se"],
                p_raw=r["p"],
                separation_flag=flag,
            )
        )

    out_rows = []
    for r in rows:
        verdict = (
            "unestimable (separation)"
            if flagged_tests[r["test"]]
            else "estimable"
        )
        # Suppress p-values produced with se==0 (degenerate).
        p_reported = "" if (r["se"] == 0.0 or pd.isna(r["se"])) else r["p_raw"]
        out_rows.append({**r, "model_verdict": verdict, "p_reported": p_reported})

    odf = pd.DataFrame(out_rows)
    out_csv = os.path.join(SUPP, "interaction_separation_annotated.csv")
    odf.to_csv(out_csv, index=False)
    print(f"wrote {out_csv}")
    print(odf.to_string(index=False))

    note = os.path.join(SUPP, "interaction_separation_note.md")
    with open(note, "w") as f:
        f.write("# Level-4 Interaction GEE: separation diagnosis (GEE-3)\n\n")
        f.write(
            "The frozen `results/stats/full_report.md` Level-4a (Agent x Variant) "
            "block reports a coefficient of beta=-7.99e22 with SE=0.000 and labels "
            "the interaction 'Significant'. This is textbook perfect/quasi-"
            "separation, driven by CUA being near-ceiling-invariant except at Low "
            "(base 93.8%, med-low 98.5%). A stable logistic interaction is "
            "therefore UNESTIMABLE, not significant. Level-4b (Model x Variant) is "
            "all-NaN for the same reason on the Claude text-only side.\n\n"
        )
        f.write(
            "Honest restatement: 'Agent x variant interaction: CUA is near-ceiling-"
            "invariant except at Low, so a stable logistic interaction is "
            "unestimable (perfect separation).'\n\n"
        )
        f.write(
            "The paper body does NOT rely on this degenerate model: the "
            "architecture/CUA-vs-text decomposition rests on the B=2,000 bootstrap "
            "CIs (explicitly downgraded to a heuristic, sec 5.1), and cross-model "
            "heterogeneity rests on Breslow-Day chi2(1)=221.8. This is supplement "
            "hygiene only.\n\n"
        )
        f.write(
            "ACTION REQUIRED (user decision): adding the separation guard to "
            "analysis/run_statistics.py and regenerating the shipped "
            "paper-supplementary/statistics-composite.md (a copy of the frozen "
            "full_report.md) would remove the misleading 'Significant' line, but "
            "regenerating a frozen derived artifact is out of scope under the "
            "frozen-data constraint without explicit approval. This companion file "
            "documents the corrected interpretation in the meantime.\n"
        )
    print(f"wrote {note}")


if __name__ == "__main__":
    main()

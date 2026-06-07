# Level-4 Interaction GEE: separation diagnosis (GEE-3)

The frozen `results/stats/full_report.md` Level-4a (Agent x Variant) block reports a coefficient of beta=-7.99e22 with SE=0.000 and labels the interaction 'Significant'. This is textbook perfect/quasi-separation, driven by CUA being near-ceiling-invariant except at Low (base 93.8%, med-low 98.5%). A stable logistic interaction is therefore UNESTIMABLE, not significant. Level-4b (Model x Variant) is all-NaN for the same reason on the Claude text-only side.

Honest restatement: 'Agent x variant interaction: CUA is near-ceiling-invariant except at Low, so a stable logistic interaction is unestimable (perfect separation).'

The paper body does NOT rely on this degenerate model: the architecture/CUA-vs-text decomposition rests on the B=2,000 bootstrap CIs (explicitly downgraded to a heuristic, sec 5.1), and cross-model heterogeneity rests on Breslow-Day chi2(1)=221.8. This is supplement hygiene only.

ACTION REQUIRED (user decision): adding the separation guard to analysis/run_statistics.py and regenerating the shipped paper-supplementary/statistics-composite.md (a copy of the frozen full_report.md) would remove the misleading 'Significant' line, but regenerating a frozen derived artifact is out of scope under the frozen-data constraint without explicit approval. This companion file documents the corrected interpretation in the meantime.

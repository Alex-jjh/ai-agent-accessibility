# Clarification: the `preserves` column in `results/majority_vote_comparison.csv`

Created 2026-06-07 as a NEW companion note for the CHI/ASSETS 2027 revision
(audit finding DET-2). It does **not** modify the frozen artifact
`results/majority_vote_comparison.csv`; it only documents how to read it.

## What `preserves` means in the frozen CSV

The boolean `preserves` column flags whether a panel's majority-vote binary
Low-vs-rest result clears a **strict `p < 0.001` bar**, not the `alpha = 0.05`
threshold used for the paper's primary inference. With four 208-cell panels the
values are:

| panel              | majority_binary_p | preserves (p<0.001) | significant at alpha=0.05 |
|--------------------|-------------------|---------------------|----------------------------|
| Claude text-only   | 6.21e-05          | True                | yes (p < 1e-3)             |
| Claude CUA         | 5.13e-04          | True                | yes (p < 1e-3)             |
| Claude SoM         | 0.0243            | **False**           | **yes** (marginal)         |
| Llama 4 text-only  | 0.0483            | **False**           | **yes** (marginal)         |

So `preserves=False` for SoM and Llama 4 does **not** mean the Low-vs-rest
effect disappears under majority vote: both remain significant at `alpha=0.05`
(max p = Llama 4, 0.048). They only fall below the conservative `p<0.001` bar
because the 5-reps-to-1-vote aggregation reduces the effective sample to 208
cells and thus statistical power.

## How the paper now states this (no number changed)

- `paper/main.tex` Appendix "Majority-Vote Sensitivity Analysis" already reads
  these two panels as "transition from p < 1e-5 to marginal significance."
- `paper/sections/04-methodology.tex` agent-configuration footnote now states:
  majority vote "preserves significance at alpha=0.05 for all four
  agent x model panels, with the two strongest (Claude text-only, CUA) at
  p < 1e-3 and SoM (p=0.024) and Llama 4 (p=0.048) weakening to marginal
  significance under the reduced power of the 208-cell analysis."

This removes the earlier surface contradiction between the methodology footnote
("preserves all primary findings") and both the appendix wording and the
`preserves=False` CSV flags. No frozen value was altered; the headline
majority-vote anchor (Claude text-only Z=4.005, p=6.2e-5) is unchanged.

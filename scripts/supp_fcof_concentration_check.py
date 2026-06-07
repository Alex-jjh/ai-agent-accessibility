#!/usr/bin/env python3
"""Supplementary re-analysis for finding LIT-OBS-5 (literature/citation cluster).

Question: Is the F_COF (context-overflow / token-volume) failure mode
*concentrated* under low accessibility for text-only agents, as the draft
prose at 02-related-work.tex:37 and 05-results.tex:166 implied, OR is it
roughly flat across variants?

This script ONLY READS the frozen artifact
results/stats/failure_distribution.csv and writes a NEW summary CSV to
results/supplementary/. It mutates no frozen input.

Conclusion (printed + written): for text-only agents, F_COF counts are
nearly flat across base/high/low (12 / 11 / 13), whereas timeout
(1 -> 24 from high -> low) and F_ENF (0 -> 7) genuinely concentrate under
low accessibility. The reframe in 02:37 ("concentrates the OTHER failure
modes -- structural infeasibility and timeout -- under low; raises
token-volume-failure risk at the tail") is therefore supported by the
frozen data. The headline 2.4x token shift (sensitivity.csv) is unchanged.
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "stats" / "failure_distribution.csv"
OUT_DIR = ROOT / "results" / "supplementary"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "lit_obs5_fcof_concentration.csv"

VARIANT_ORDER = ["base", "high", "medium-low", "low"]
MODES = ["F_COF", "F_ENF", "timeout"]


def main() -> None:
    counts = {m: {v: 0 for v in VARIANT_ORDER} for m in MODES}
    with SRC.open() as fh:
        for row in csv.DictReader(fh):
            if row["agent_type"] != "text-only":
                continue
            ft = row["failure_type"]
            var = row["variant"]
            if ft in counts and var in counts[ft]:
                counts[ft][var] = int(row["count"])

    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["agent_type", "failure_type"] + VARIANT_ORDER
                   + ["low_minus_base", "concentrated_under_low"])
        for m in MODES:
            base = counts[m]["base"]
            low = counts[m]["low"]
            delta = low - base
            # "concentrated" = low exceeds base by more than 2x AND by >=5 count
            concentrated = (low >= 2 * max(base, 1)) and (delta >= 5)
            w.writerow(["text-only", m]
                       + [counts[m][v] for v in VARIANT_ORDER]
                       + [delta, concentrated])
            print(f"{m:8s} base={base:3d} high={counts[m]['high']:3d} "
                  f"low={low:3d}  low-base={delta:+d}  "
                  f"concentrated_under_low={concentrated}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Supplementary re-analysis (DET-4): per-agent non-determinism breakdown.

The methodology footnote (04-methodology.tex L82) reports only the POOLED
non-determinism figure (23.1% of cells, 48/208). DET-4 asks for the per-agent
breakdown (which is heterogeneous) AND the per-variant SoM breakdown (which
shows the phantom-bid collapse cell is actually one of the MOST deterministic
SoM cells, contradicting the "mechanism built on noise" framing).

A cell = (task, variant, agent_type, model_family), 5 reps. Non-deterministic
iff the 5 reps disagree on binary success.

HARD CONSTRAINT COMPLIANCE: reads results/combined-experiment.csv read-only;
writes only results/supplementary/nondeterminism_by_agent.csv (NEW file).

Run: analysis/.venv/bin/python analysis/supplementary/nondeterminism_by_agent.py
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results" / "combined-experiment.csv"
OUT = ROOT / "results" / "supplementary" / "nondeterminism_by_agent.csv"

TRUTHY = ("True", "true", "1")


def main():
    with open(SRC) as f:
        rows = list(csv.DictReader(f))

    cells = defaultdict(list)
    for r in rows:
        key = (r["task_id"], r["variant"], r["agent_type"], r["model_family"])
        cells[key].append(r["success"] in TRUTHY)

    by_agent = defaultdict(lambda: [0, 0])       # (agent,model) -> [nondet, total]
    som_by_variant = defaultdict(lambda: [0, 0])  # variant -> [nondet, total]
    som_low_unanimous0 = 0
    som_low_total = 0

    for (tid, var, agent, model), vals in cells.items():
        nondet = 0 < sum(vals) < len(vals)
        by_agent[(agent, model)][1] += 1
        if nondet:
            by_agent[(agent, model)][0] += 1
        if agent == "vision-only":
            som_by_variant[var][1] += 1
            if nondet:
                som_by_variant[var][0] += 1
            if var == "low":
                som_low_total += 1
                if sum(vals) == 0:
                    som_low_unanimous0 += 1

    out_rows = []
    tot_nd = tot_n = 0
    for (agent, model), (nd, n) in sorted(by_agent.items()):
        out_rows.append({"scope": "per_agent", "key": f"{agent}/{model}",
                         "nondet_cells": nd, "total_cells": n,
                         "nondet_pct": round(100 * nd / n, 1)})
        tot_nd += nd
        tot_n += n
    out_rows.append({"scope": "pooled", "key": "all_agents",
                     "nondet_cells": tot_nd, "total_cells": tot_n,
                     "nondet_pct": round(100 * tot_nd / tot_n, 1)})
    for var, (nd, n) in sorted(som_by_variant.items()):
        out_rows.append({"scope": "som_per_variant", "key": var,
                         "nondet_cells": nd, "total_cells": n,
                         "nondet_pct": round(100 * nd / n, 1)})
    out_rows.append({"scope": "som_low_unanimous_fail", "key": "tasks_0of5",
                     "nondet_cells": som_low_unanimous0, "total_cells": som_low_total,
                     "nondet_pct": round(100 * som_low_unanimous0 / som_low_total, 1)})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scope", "key", "nondet_cells", "total_cells", "nondet_pct"])
        w.writeheader()
        w.writerows(out_rows)

    for r in out_rows:
        print(f"{r['scope']:<24} {r['key']:<18} {r['nondet_cells']}/{r['total_cells']} = {r['nondet_pct']}%")
    print(f"\nWrote {OUT} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()

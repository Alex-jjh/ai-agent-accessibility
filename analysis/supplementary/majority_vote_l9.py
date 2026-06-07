#!/usr/bin/env python3
"""
Supplementary re-analysis (DET-3 / DET-5): majority-vote sensitivity including L9.

Context
-------
The published majority-vote sensitivity check (analysis/amt_statistics.py
test_majority_vote_mode_a, op list hard-coded to ["L1","L5","L12"]) tested
L1, L5, L12 but NOT L9 -- even though L9 is the second-most-significant
Stage-3 operator (Holm p=0.000105). The audit (DET-3) flagged that the
05-results.tex footnote reports only the two operators that pass (L1, L5),
silently dropping L12 (tested, p=0.078, does not preserve) and never testing
L9. DET-5 flagged that the promised Mode-A (depth-set) majority-vote numbers
are never reported.

This script re-derives the majority-vote Fisher tests for ALL FOUR headline
operators (L1, L5, L9, L12) on the FROZEN Stage-3 breadth set and the FROZEN
Mode-A depth set, reading the same case JSONs the published pipeline reads.

HARD CONSTRAINT COMPLIANCE
--------------------------
- Reads frozen data read-only (data/stage3-claude, data/mode-a-shard-{a,b}).
- Does NOT mutate amt_statistics.py, stage3_statistics.py, or any results CSV.
- Writes a single NEW file: results/supplementary/majority_vote_l9.csv
- Uses the IDENTICAL majority-vote and Fisher logic as the published code
  (success if >=2/3 reps succeed; Fisher exact vs pooled H-baseline) so the
  L1/L5/L12 numbers reproduce the published statistics_report.md exactly,
  validating that the only change is the addition of L9.

Run:
    analysis/.venv/bin/python analysis/supplementary/majority_vote_l9.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))

# Reuse the published loaders so the frozen data is parsed identically.
from amt_statistics import load_cases  # noqa: E402
from stage3_statistics import load_stage3_cases  # noqa: E402

OPS = ["L1", "L5", "L9", "L12"]
OUT = ROOT / "results" / "supplementary" / "majority_vote_l9.csv"


def majority_vote_fisher(cases, agent="text-only", reps_for_majority=2):
    """Identical logic to test_majority_vote_mode_a, but over OPS (incl. L9).

    reps_for_majority: success if ok >= this many (2 for 3-rep cells).
    """
    cells = defaultdict(lambda: {"ok": 0, "total": 0})
    for c in cases:
        if c["agent"] != agent:
            continue
        key = (c["taskId"], c["opId"])
        cells[key]["total"] += 1
        if c["success"]:
            cells[key]["ok"] += 1

    mv_cells = []
    for (tid, opId), counts in cells.items():
        majority = 1 if counts["ok"] >= reps_for_majority else 0
        mv_cells.append({"taskId": tid, "opId": opId, "success": majority})

    h_mv = [c for c in mv_cells if c["opId"].startswith("H")]
    h_ok = sum(c["success"] for c in h_mv)
    h_n = len(h_mv)
    h_rate = h_ok / h_n if h_n else 0.0

    results = {}
    for op in OPS:
        op_mv = [c for c in mv_cells if c["opId"] == op]
        op_ok = sum(c["success"] for c in op_mv)
        op_n = len(op_mv)
        if op_n == 0:
            continue
        table = np.array([[op_ok, op_n - op_ok], [h_ok, h_n - h_ok]])
        _, p = stats.fisher_exact(table)
        results[op] = {
            "ok": op_ok, "n": op_n, "rate": op_ok / op_n,
            "h_ok": h_ok, "h_n": h_n, "h_rate": h_rate,
            "p_fisher": p, "preserves": p < 0.05,
        }

    total_cells = len(cells)
    variance = sum(1 for _, c in cells.items() if 0 < c["ok"] < c["total"])
    summary = {
        "total_cells": total_cells,
        "variance_cells": variance,
        "variance_pct": round(100 * variance / total_cells, 1) if total_cells else 0,
    }
    return results, summary


def main():
    rows = []

    # ---- Stage 3 breadth set (1,248 cells: 48 tasks x 26 ops) ----
    s3 = load_stage3_cases(ROOT / "data" / "stage3-claude")
    s3_res, s3_sum = majority_vote_fisher(s3, "text-only")
    print(f"[Stage 3] cells={s3_sum['total_cells']} variance={s3_sum['variance_cells']} ({s3_sum['variance_pct']}%)")
    for op in OPS:
        r = s3_res.get(op)
        if not r:
            print(f"  {op}: ABSENT")
            continue
        print(f"  {op}: {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) p={r['p_fisher']:.6f} preserves={r['preserves']}")
        rows.append({
            "dataset": "stage3_breadth", "operator": op,
            "mv_ok": r["ok"], "mv_n": r["n"], "mv_rate_pct": round(r["rate"]*100, 1),
            "h_ok": r["h_ok"], "h_n": r["h_n"], "h_rate_pct": round(r["h_rate"]*100, 1),
            "p_fisher": r["p_fisher"], "preserves_alpha05": r["preserves"],
            "total_cells": s3_sum["total_cells"], "variance_pct": s3_sum["variance_pct"],
        })

    # ---- Mode A depth set (338 cells: 13 tasks x 26 ops) ----
    ma = load_cases([ROOT / "data" / "mode-a-shard-a", ROOT / "data" / "mode-a-shard-b"])
    ma_res, ma_sum = majority_vote_fisher(ma, "text-only")
    print(f"[Mode A] cells={ma_sum['total_cells']} variance={ma_sum['variance_cells']} ({ma_sum['variance_pct']}%)")
    for op in OPS:
        r = ma_res.get(op)
        if not r:
            print(f"  {op}: ABSENT")
            continue
        print(f"  {op}: {r['ok']}/{r['n']} ({r['rate']*100:.1f}%) p={r['p_fisher']:.6f} preserves={r['preserves']}")
        rows.append({
            "dataset": "modea_depth", "operator": op,
            "mv_ok": r["ok"], "mv_n": r["n"], "mv_rate_pct": round(r["rate"]*100, 1),
            "h_ok": r["h_ok"], "h_n": r["h_n"], "h_rate_pct": round(r["h_rate"]*100, 1),
            "p_fisher": r["p_fisher"], "preserves_alpha05": r["preserves"],
            "total_cells": ma_sum["total_cells"], "variance_pct": ma_sum["variance_pct"],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3.11
"""Identify tasks that look like infra failures rather than real a11y effects.

Heuristic: if H-operators (enhancements) also collapse, something's wrong with
the environment for that task - not the operator semantics.

Baseline reference: in Mode A, Llama 4 H-operators averaged ~70-75% success.
Claude H-operators averaged 90-97%.

We flag any task where the H-operator mean success is <30%.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path

H_OPS = {"H1","H2","H3","H4","H5a","H5b","H5c","H6","H7","H8"}
L_OPS = {f"L{i}" for i in range(1,14)}
ML_OPS = {"ML1","ML2","ML3"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--label", default="Stage 3")
    ap.add_argument("--h-op-threshold", type=float, default=0.30,
                    help="Flag tasks where H-op mean success is below this (default 0.30)")
    args = ap.parse_args()

    files = sorted(glob.glob(f"{args.data_dir}/*/cases/*.json"))
    by_task_op = collections.defaultdict(lambda: {"succ":0, "total":0})

    for fp in files:
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        cid = d.get("caseId", "")
        parts = cid.split(":")
        if len(parts) < 6:
            continue
        app, _, task, _ci, _a, op = parts[:6]
        task_key = f"{app}:{task}"
        rec = by_task_op[(task_key, op)]
        rec["total"] += 1
        if (d.get("trace") or {}).get("success"):
            rec["succ"] += 1

    # Aggregate per task × family
    per_task = collections.defaultdict(lambda: {"H":{"s":0,"n":0}, "L":{"s":0,"n":0}, "ML":{"s":0,"n":0}, "all":{"s":0,"n":0}})
    for (tk, op), rec in by_task_op.items():
        fam = "H" if op in H_OPS else ("ML" if op in ML_OPS else "L")
        per_task[tk][fam]["s"] += rec["succ"]
        per_task[tk][fam]["n"] += rec["total"]
        per_task[tk]["all"]["s"] += rec["succ"]
        per_task[tk]["all"]["n"] += rec["total"]

    print(f"[{args.label}] Per-task family success rates:")
    print(f"{'task':<25} {'L-mean':>8} {'ML-mean':>8} {'H-mean':>8} {'overall':>8}  flag")
    rows = []
    for tk, fams in per_task.items():
        h_rate = fams["H"]["s"] / max(fams["H"]["n"], 1)
        l_rate = fams["L"]["s"] / max(fams["L"]["n"], 1)
        ml_rate = fams["ML"]["s"] / max(fams["ML"]["n"], 1)
        ov = fams["all"]["s"] / max(fams["all"]["n"], 1)
        rows.append((ov, tk, l_rate, ml_rate, h_rate))

    rows.sort()
    flagged = []
    for ov, tk, l, ml, h in rows:
        flag = ""
        if h < args.h_op_threshold:
            flag = " ← H-COLLAPSE (infra suspect)"
            flagged.append(tk)
        elif ov < 0.15:
            flag = " ← low everywhere"
        print(f"{tk:<25} {l:>7.1%} {ml:>7.1%} {h:>7.1%} {ov:>7.1%}  {flag}")

    print()
    print(f"Flagged {len(flagged)} tasks with H-op mean < {args.h_op_threshold:.0%}:")
    for tk in flagged:
        print(f"  - {tk}")
    print()
    print("Interpretation:")
    print("  H-operators are ENHANCEMENTS (add ARIA, skip links, table scopes, etc.).")
    print("  They should preserve or slightly improve baseline behaviour.")
    print("  If H-op success collapses, the task was not robustly solvable in this")
    print("  environment regardless of a11y manipulation — likely Docker state drift")
    print("  or task-specific fragility (e.g. timing, session, order effects).")
    print()
    print("  These tasks should be investigated before inclusion in the primary")
    print("  analysis. Options: (a) post-hoc correction if trace shows GT drift,")
    print("  (b) exclude as infra confound and document in paper.")

    return 0 if not flagged else 2


if __name__ == "__main__":
    raise SystemExit(main())

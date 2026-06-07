#!/usr/bin/env python3
"""
Read-only re-analysis for audit finding TASK-2 (CHI/ASSETS 2027 paper).

Purpose: back the paper's "distributed across applications" anti-concentration
argument (main.tex sec:task-selection-bias, Checks 2-3) with a verifiable
recomputation that (a) reproduces the per-app drop table tab:per-app-effects
and (b) reports the per-operator success rates with the single reddit task
(reddit:69) dropped entirely, showing the L1<L9<L5<L12 ranking is preserved
and that L9's rate RISES without reddit (i.e. L9 is admin-driven, not
"admin/reddit-driven").

Reads ONLY the frozen Stage 3 Claude export
  data/stage3-claude/exports/experiment-data.csv  (3,744 cases = 26 ops x 48 tasks x 3 reps)
Writes ONLY to results/supplementary/stage3_no_reddit_reground.csv.
Does NOT mutate any frozen artifact.

Reproduces frozen results/stage3/per-operator-stage3.csv pooled rates exactly
(L1 92/144, L9 114/144, L5 116/144, L12 121/144), confirming the export is the
same data the locked aggregate was built from.
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)                      # results/
REPO = os.path.dirname(RES)                       # ai-agent-accessibility/
SRC = os.path.join(REPO, "data", "stage3-claude", "exports", "experiment-data.csv")
OUT = os.path.join(HERE, "stage3_no_reddit_reground.csv")

H_OPS = ["H1", "H2", "H3", "H4", "H5a", "H5b", "H5c", "H6", "H7", "H8"]
SIG_OPS = ["L1", "L9", "L5", "L12"]
APPS = ["ecommerce", "ecommerce_admin", "gitlab", "reddit"]


def op_of(case_id):
    # caseId format: "<app>:individual:<task>:0:<rep>:<OP>"
    return case_id.split(":")[-1]


def main():
    rows = []
    with open(SRC) as f:
        for r in csv.DictReader(f):
            rows.append(r)

    def succ(r):
        return r["success"] == "true"

    # ---- (1) per-app, per-operator counts + per-app H-baseline ----
    pa = {}  # (app, op) -> [ok, n]
    for r in rows:
        key = (r["app"], op_of(r["caseId"]))
        ok, n = pa.get(key, (0, 0))
        pa[key] = (ok + succ(r), n + 1)

    out_rows = []

    # per-app H-baseline = pooled H operators within that app
    hbase = {}
    for app in APPS:
        ok = sum(pa.get((app, h), (0, 0))[0] for h in H_OPS)
        n = sum(pa.get((app, h), (0, 0))[1] for h in H_OPS)
        hbase[app] = ok / n if n else float("nan")
        out_rows.append({
            "analysis": "per_app_Hbaseline", "app": app, "operator": "H_pooled",
            "ok": ok, "n": n, "rate_pct": round(100 * hbase[app], 1),
            "drop_pp_from_Hbase": "", "obs_per_single_op": pa.get((app, "L1"), (0, 0))[1],
        })

    # per-app drop for each significant operator (reproduces tab:per-app-effects)
    for app in APPS:
        for op in SIG_OPS:
            ok, n = pa.get((app, op), (0, 0))
            rate = ok / n if n else float("nan")
            out_rows.append({
                "analysis": "per_app_drop", "app": app, "operator": op,
                "ok": ok, "n": n, "rate_pct": round(100 * rate, 1),
                "drop_pp_from_Hbase": round(100 * (rate - hbase[app]), 1),
                "obs_per_single_op": n,
            })

    # ---- (2) full vs no-reddit pooled per-operator rates ----
    full = {}
    nored = {}
    for r in rows:
        op = op_of(r["caseId"])
        fok, fn = full.get(op, (0, 0))
        full[op] = (fok + succ(r), fn + 1)
        if r["app"] != "reddit":
            nok, nn = nored.get(op, (0, 0))
            nored[op] = (nok + succ(r), nn + 1)

    for op in SIG_OPS:
        fok, fn = full[op]
        nok, nn = nored[op]
        fr = 100 * fok / fn
        nr = 100 * nok / nn
        out_rows.append({
            "analysis": "pooled_full_vs_noreddit", "app": "ALL", "operator": op,
            "ok": f"{fok}->{nok}", "n": f"{fn}->{nn}",
            "rate_pct": f"{fr:.1f}->{nr:.1f}",
            "drop_pp_from_Hbase": round(nr - fr, 2),  # = delta from dropping reddit
            "obs_per_single_op": nn,
        })

    # ranking sanity (most destructive first), full and no-reddit
    full_rank = sorted(SIG_OPS, key=lambda o: full[o][0] / full[o][1])
    nored_rank = sorted(SIG_OPS, key=lambda o: nored[o][0] / nored[o][1])
    out_rows.append({
        "analysis": "ranking", "app": "ALL", "operator": "full",
        "ok": "", "n": "", "rate_pct": " < ".join(full_rank),
        "drop_pp_from_Hbase": "", "obs_per_single_op": "",
    })
    out_rows.append({
        "analysis": "ranking", "app": "ALL", "operator": "no_reddit",
        "ok": "", "n": "", "rate_pct": " < ".join(nored_rank),
        "drop_pp_from_Hbase": "", "obs_per_single_op": "",
    })

    cols = ["analysis", "app", "operator", "ok", "n", "rate_pct",
            "drop_pp_from_Hbase", "obs_per_single_op"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    print(f"wrote {OUT} ({len(out_rows)} rows)")
    print("full ranking   :", full_rank)
    print("no-reddit rank :", nored_rank)
    for op in SIG_OPS:
        fok, fn = full[op]
        nok, nn = nored[op]
        print(f"  {op}: full {100*fok/fn:.1f}% (n={fn}) -> no-reddit {100*nok/nn:.1f}% (n={nn})")


if __name__ == "__main__":
    main()

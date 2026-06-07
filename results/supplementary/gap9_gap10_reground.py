#!/usr/bin/env python3
"""
Read-only re-analysis for audit findings GAP-9 (enhancement arm) and
GAP-10 (quote provenance / behavioral spine) for the CHI/ASSETS 2027 paper.

GAP-9 (enhancement / High-family arm):
  The paper's only quoted enhancement effect ("Llama 4 H2 skip-nav +8.5pp
  above Llama H-baseline 76.2%", 05 L84 / 06 L24) is measured against a
  *self-inclusive pooled-H baseline* (circular) and does NOT reproduce from
  any frozen Llama operator export:
      - data/stage3-llama  : H2 = 69.4% vs pooled-H 70.3%  => -0.9pp
      - data/mode-a-llama4 : H2 = 61.5% vs pooled-H 54.6%  => +6.9pp
  The 76.2%/84.6% figures trace only to docs/analysis/mode-a-analysis.md
  (an older expansion-llama4 run) and are not in key-numbers.json.
  The ONLY base-referenced enhancement contrast the frozen data supports is
  the composite study's base->high (a base variant exists only in Phase 1 /
  composite). We recompute it with a Fisher exact test per model so the
  asymmetric-dose-response claim can carry an explicit test (mirroring the
  Low arm) or be demoted to descriptive.

GAP-10 (quote provenance / adaptive-recovery behavioral spine):
  Neither load-bearing agent quote ("The sidebar links don't seem to be
  working as expected", 06 L22; "I can see the Continue button ... but I
  don't see its bid number", 05 L161) appears in ANY released artifact;
  trace-summaries.jsonl carries no chain-of-thought field. We promote the
  reproducible goto()-usage asymmetry under composite Low as the quantitative
  backbone of the adaptive-recovery claim, plus an L5 ghost-button proxy
  (click_failures) by model and variant.

Reads ONLY frozen artifacts:
  results/trace-summaries.jsonl                 (composite Phase 1, 520 text-only rows)
  data/stage3-llama/exports/experiment-data.csv (Llama Stage 3 per-operator)
  data/mode-a-llama4-textonly/exports/experiment-data.csv (Llama Mode A per-operator)
Writes ONLY:
  results/supplementary/gap9_enhancement_base_referenced.csv
  results/supplementary/gap10_goto_asymmetry.csv
Does NOT mutate any frozen artifact.
"""
import csv, json, os
from collections import defaultdict
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
REPO = os.path.dirname(RES)
TRACES = os.path.join(RES, "trace-summaries.jsonl")
STAGE3_LLAMA = os.path.join(REPO, "data", "stage3-llama", "exports", "experiment-data.csv")
MODEA_LLAMA = os.path.join(REPO, "data", "mode-a-llama4-textonly", "exports", "experiment-data.csv")
OUT_ENH = os.path.join(HERE, "gap9_enhancement_base_referenced.csv")
OUT_GOTO = os.path.join(HERE, "gap10_goto_asymmetry.csv")

H_OPS = ["H1", "H2", "H3", "H4", "H5a", "H5b", "H5c", "H6", "H7", "H8"]


def _truthy(s):
    return str(s).strip().lower() in ("true", "1", "yes")


def per_op_export(path):
    agg = defaultdict(lambda: {"n": 0, "ok": 0})
    with open(path) as f:
        for row in csv.DictReader(f):
            op = row["caseId"].split(":")[-1]
            agg[op]["n"] += 1
            agg[op]["ok"] += 1 if _truthy(row["success"]) else 0
    return agg


def main():
    # ---- GAP-9: base-referenced enhancement (composite Phase 1, frozen traces)
    comp = defaultdict(lambda: {"n": 0, "ok": 0})
    with open(TRACES) as f:
        for line in f:
            d = json.loads(line)
            if d["agent_type"] != "text-only":
                continue
            if d["variant"] not in ("base", "high"):
                continue
            k = (d["model"], d["variant"])
            comp[k]["n"] += 1
            comp[k]["ok"] += 1 if d["success"] else 0

    enh_rows = []
    for model in ("claude-sonnet", "llama4-maverick"):
        b, h = comp[(model, "base")], comp[(model, "high")]
        rb, rh = b["ok"] / b["n"], h["ok"] / h["n"]
        table = [[h["ok"], h["n"] - h["ok"]], [b["ok"], b["n"] - b["ok"]]]
        OR, p = st.fisher_exact(table)
        enh_rows.append({
            "source": "composite_phase1_base_referenced",
            "model": model,
            "base_rate": round(rb, 4), "base_n": b["n"],
            "high_rate": round(rh, 4), "high_n": h["n"],
            "delta_pp": round((rh - rb) * 100, 1),
            "fisher_OR": round(OR, 3), "fisher_p": round(p, 4),
            "significant_a05": p < 0.05,
        })

    # ---- GAP-9: show the dual-baseline incoherence quantitatively (Llama)
    for label, path in (("stage3-llama", STAGE3_LLAMA), ("mode-a-llama4", MODEA_LLAMA)):
        agg = per_op_export(path)
        hn = sum(agg[o]["n"] for o in H_OPS)
        hok = sum(agg[o]["ok"] for o in H_OPS)
        hbase = hok / hn
        h2 = agg["H2"]
        enh_rows.append({
            "source": f"{label}_H2_vs_selfinclusive_pooledH",
            "model": "llama4-maverick",
            "base_rate": round(hbase, 4), "base_n": hn,   # base_rate column reused as pooled-H baseline
            "high_rate": round(h2["ok"] / h2["n"], 4), "high_n": h2["n"],
            "delta_pp": round((h2["ok"] / h2["n"] - hbase) * 100, 1),
            "fisher_OR": "", "fisher_p": "",   # circular baseline; no valid base-referenced test
            "significant_a05": "circular_pooledH_baseline",
        })

    with open(OUT_ENH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(enh_rows[0].keys()))
        w.writeheader()
        w.writerows(enh_rows)

    # ---- GAP-10: goto() asymmetry + click-failure proxy (composite, frozen traces)
    goto = defaultdict(lambda: {"n": 0, "goto_any": 0, "goto_sum": 0,
                                "cf_sum": 0, "maxcons_any": 0})
    with open(TRACES) as f:
        for line in f:
            d = json.loads(line)
            if d["agent_type"] != "text-only":
                continue
            k = (d["model"], d["variant"])
            a = goto[k]
            a["n"] += 1
            gc = d.get("goto_count", 0)
            a["goto_sum"] += gc
            a["goto_any"] += 1 if gc > 0 else 0
            a["cf_sum"] += d.get("click_failures", 0)
            a["maxcons_any"] += 1 if d.get("max_consecutive_click_failures", 0) > 0 else 0

    goto_rows = []
    for k in sorted(goto):
        a = goto[k]
        n = a["n"]
        goto_rows.append({
            "model": k[0], "variant": k[1], "n": n,
            "goto_use_pct": round(100 * a["goto_any"] / n, 1),
            "goto_mean_per_case": round(a["goto_sum"] / n, 2),
            "click_fail_mean": round(a["cf_sum"] / n, 2),
            "any_consecutive_clickfail_pct": round(100 * a["maxcons_any"] / n, 1),
        })

    with open(OUT_GOTO, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(goto_rows[0].keys()))
        w.writeheader()
        w.writerows(goto_rows)

    print("WROTE", OUT_ENH)
    for r in enh_rows:
        print("  ", r)
    print("WROTE", OUT_GOTO)
    for r in goto_rows:
        print("  ", r)


if __name__ == "__main__":
    main()

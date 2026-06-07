#!/usr/bin/env python3
"""Supplementary composition robustness re-analysis (COMP-1..5).

Re-analysis ONLY of frozen data; reads results/CSV + data/*-shard-* read-only and
writes NEW files under results/supplementary/. Does NOT mutate any frozen artifact.

Reproduces, from the frozen 2,184-case C.2 data + Mode A singletons:
  COMP-4: CUA-arm super-additivity (text-only vs CUA, shipped classifier path)
  COMP-1: band-width sweep (+-3..7pp) of the super/additive/sub classification
  COMP-2: pre- vs post-GT-correction counts + conditional-binomial disclosure
  COMP-3: logit/odds-ratio-scale interaction for the 5 named pairs + neg-baseline
  COMP-5: per-pair bootstrap CI on the interaction term (no per-pair test ships)
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats

from analysis.lib.load import apply_gt_corrections, load_cases_flat

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
OUT = REPO / "results" / "supplementary"
OUT.mkdir(parents=True, exist_ok=True)

C2_DIRS = [DATA / "c2-composition-shard-a", DATA / "c2-composition-shard-b"]
MODE_A_DIRS = [DATA / "mode-a-shard-a", DATA / "mode-a-shard-b"]

NAMED5 = ["L6+L11", "L9+L11", "L1+L6", "L4+L6", "L6+L9"]


def per_pair(claude_cases, c2_cases, agent, band=5.0):
    """Replicate amt_statistics.test_compositional_interaction classification."""
    h = [c for c in claude_cases if c["agent"] == agent and c["opId"].startswith("H")]
    h_ok = sum(c["success"] for c in h)
    h_n = len(h)
    h_rate = h_ok / h_n

    op_rates = {}
    for op in set(c["opId"] for c in claude_cases):
        if "+" in op:
            continue
        cs = [c for c in claude_cases if c["agent"] == agent and c["opId"] == op]
        if cs:
            op_rates[op] = sum(c["success"] for c in cs) / len(cs)

    pairs = {}
    for c in c2_cases:
        if c["agent"] != agent or "+" not in c["opId"]:
            continue
        d = pairs.setdefault(c["opId"], {"ok": 0, "total": 0})
        d["total"] += 1
        d["ok"] += int(bool(c["success"]))

    rows = []
    for pid, ct in pairs.items():
        ops = pid.split("+")
        if len(ops) != 2 or not all(o in op_rates for o in ops):
            continue
        pr = ct["ok"] / ct["total"]
        pair_drop = h_rate - pr
        da = h_rate - op_rates[ops[0]]
        db = h_rate - op_rates[ops[1]]
        exp = da + db
        inter = (pair_drop - exp) * 100
        cat = "super-additive" if inter > band else ("sub-additive" if inter < -band else "additive")
        rows.append(dict(pair=pid, n=ct["total"], ok=ct["ok"], pair_rate=pr,
                         observed_drop_pp=pair_drop * 100, expected_drop_pp=exp * 100,
                         interaction_pp=inter, category=cat,
                         drop_a_pp=da * 100, drop_b_pp=db * 100,
                         rate_a=op_rates[ops[0]], rate_b=op_rates[ops[1]]))
    return rows, h_rate, op_rates


def counts(rows):
    s = sum(r["category"] == "super-additive" for r in rows)
    a = sum(r["category"] == "additive" for r in rows)
    b = sum(r["category"] == "sub-additive" for r in rows)
    p = stats.binomtest(s, s + b, 0.5).pvalue if (s + b) else 1.0
    return s, a, b, p


def write_csv(name, fieldnames, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote results/supplementary/{name} ({len(rows)} rows)")


def main():
    claude = apply_gt_corrections(load_cases_flat(MODE_A_DIRS))
    c2 = apply_gt_corrections(load_cases_flat(C2_DIRS))
    c2_raw = load_cases_flat(C2_DIRS)            # PRE GT-correction
    claude_raw = load_cases_flat(MODE_A_DIRS)    # PRE GT-correction

    print("=== COMP-4: CUA vs text-only super-additivity (post-GT) ===")
    rows_t, h_t, _ = per_pair(claude, c2, "text-only")
    rows_c, h_c, _ = per_pair(claude, c2, "cua")
    st = counts(rows_t)
    sc = counts(rows_c)
    print(f"  text-only H-baseline={h_t:.4f}  super/add/sub/p = {st[0]}/{st[1]}/{st[2]}/{st[3]:.4f}")
    print(f"  CUA       H-baseline={h_c:.4f}  super/add/sub/p = {sc[0]}/{sc[1]}/{sc[2]}/{sc[3]:.4f}")
    write_csv("comp4_arm_contrast.csv",
              ["arm", "n_pairs", "super", "additive", "sub", "binomial_p", "h_baseline_rate"],
              [dict(arm="text-only", n_pairs=len(rows_t), super=st[0], additive=st[1], sub=st[2],
                    binomial_p=round(st[3], 4), h_baseline_rate=round(h_t, 4)),
               dict(arm="cua", n_pairs=len(rows_c), super=sc[0], additive=sc[1], sub=sc[2],
                    binomial_p=round(sc[3], 4), h_baseline_rate=round(h_c, 4))])

    print("=== COMP-1: band-width sweep (text-only) ===")
    sweep = []
    for band in (3, 4, 5, 6, 7):
        rows_b, _, _ = per_pair(claude, c2, "text-only", band=float(band))
        s, a, b, p = counts(rows_b)
        sweep.append(dict(band_pp=band, super=s, additive=a, sub=b, binomial_p=round(p, 4),
                          significant=("yes" if p < 0.05 else "no")))
        print(f"  +-{band}pp -> {s}/{a}/{b}  p={p:.4f}")
    write_csv("comp1_band_sweep.csv", ["band_pp", "super", "additive", "sub", "binomial_p", "significant"], sweep)

    print("=== COMP-2: pre/post-GT counts + conditioning disclosure ===")
    rows_pre, _, _ = per_pair(claude_raw, c2_raw, "text-only")
    s0, a0, b0, p0 = counts(rows_pre)
    s1, a1, b1, p1 = counts(rows_t)
    # all-28 sharp-null sign test (for disclosure)
    all28 = stats.binomtest(s1, 28, 0.5).pvalue
    print(f"  pre-GT : {s0}/{a0}/{b0}  conditional-binom p={p0:.4f}")
    print(f"  post-GT: {s1}/{a1}/{b1}  conditional-binom p={p1:.4f}")
    print(f"  all-28 sign test binomtest({s1},28,0.5) p={all28:.4f}")
    # one-sample tests on the 28 continuous interaction terms (post-GT)
    inter = np.array([r["interaction_pp"] for r in rows_t])
    w_stat, w_p = stats.wilcoxon(inter)
    t_stat, t_p = stats.ttest_1samp(inter, 0.0)
    sgn = stats.binomtest(int((inter > 0).sum()), int((inter != 0).sum()), 0.5).pvalue
    print(f"  mean interaction = {inter.mean():.2f}pp ; Wilcoxon p={w_p:.4f} ; t p={t_p:.4f} ; sign p={sgn:.4f}")
    write_csv("comp2_gt_sensitivity.csv",
              ["scenario", "super", "additive", "sub", "conditional_binom_p", "note"],
              [dict(scenario="pre_gt_correction", super=s0, additive=a0, sub=b0,
                    conditional_binom_p=round(p0, 4), note="binomial conditions on super+sub only"),
               dict(scenario="post_gt_correction", super=s1, additive=a1, sub=b1,
                    conditional_binom_p=round(p1, 4), note="paper headline; GT corrections applied"),
               dict(scenario="all28_sharp_null", super=s1, additive="", sub="",
                    conditional_binom_p=round(all28, 4), note="binomtest(super,28,0.5); naive omnibus"),
               dict(scenario="mean_interaction_wilcoxon", super="", additive="", sub="",
                    conditional_binom_p=round(w_p, 4),
                    note=f"H0 mean=0; mean={inter.mean():.2f}pp; t_p={t_p:.4f}; sign_p={sgn:.4f}")])

    print("=== COMP-3: logit-scale interaction + negative-baseline (named 5) ===")
    h = [c for c in claude if c["agent"] == "text-only" and c["opId"].startswith("H")]
    h_ok, h_n = sum(c["success"] for c in h), len(h)

    def rate_n(opid):
        cs = [c for c in claude if c["agent"] == "text-only" and c["opId"] == opid]
        return sum(c["success"] for c in cs), len(cs)

    def pair_rate_n(pid):
        cs = [c for c in c2 if c["agent"] == "text-only" and c["opId"] == pid]
        return sum(c["success"] for c in cs), len(cs)

    def logit(ok, n):  # Haldane-Anscombe 0.5 correction for 0/1 cells
        p = (ok + 0.5) / (n + 1.0)
        return math.log(p / (1 - p))

    c3 = []
    by_pid = {r["pair"]: r for r in rows_t}
    for pid in NAMED5:
        a, b = pid.split("+")
        oka, na = rate_n(a)
        okb, nb = rate_n(b)
        okp, npr = pair_rate_n(pid)
        # logit-scale interaction: logit(pair) - [logit(A)+logit(B)-logit(H)]
        L_h = logit(h_ok, h_n)
        L_a, L_b, L_p = logit(oka, na), logit(okb, nb), logit(okp, npr)
        expected_logit = L_a + L_b - L_h
        inter_logit = L_p - expected_logit
        # interaction as deviation of OR: positive logit interaction => worse than mult-independent
        # (note: success modeled; harm = lower success, so sign interpreted in text)
        r_pp = by_pid[pid]
        # clamp-at-0 pp interaction: credit individual drops only if > 0
        da = max(0.0, r_pp["drop_a_pp"])
        db = max(0.0, r_pp["drop_b_pp"])
        inter_clamped = r_pp["observed_drop_pp"] - (da + db)
        c3.append(dict(pair=pid,
                       interaction_pp=round(r_pp["interaction_pp"], 1),
                       expected_drop_pp=round(r_pp["expected_drop_pp"], 1),
                       drop_a_pp=round(r_pp["drop_a_pp"], 1),
                       drop_b_pp=round(r_pp["drop_b_pp"], 1),
                       neg_baseline=("yes" if r_pp["expected_drop_pp"] < 0 else "no"),
                       interaction_pp_clamped0=round(inter_clamped, 1),
                       interaction_logit=round(inter_logit, 3),
                       super_additive_pp=("yes" if r_pp["interaction_pp"] > 5 else "no"),
                       super_additive_clamped=("yes" if inter_clamped > 5 else "no"),
                       super_additive_logit=("yes" if inter_logit < 0 else "no")))
        print(f"  {pid}: pp_inter={r_pp['interaction_pp']:.1f} exp_drop={r_pp['expected_drop_pp']:.1f} "
              f"clamped={inter_clamped:.1f} logit_inter={inter_logit:.3f} negbase={r_pp['expected_drop_pp']<0}")
    write_csv("comp3_logit_negbaseline.csv",
              ["pair", "interaction_pp", "expected_drop_pp", "drop_a_pp", "drop_b_pp", "neg_baseline",
               "interaction_pp_clamped0", "interaction_logit", "super_additive_pp",
               "super_additive_clamped", "super_additive_logit"], c3)

    print("=== COMP-5: per-pair bootstrap CI on interaction term (all 28) ===")
    rng = np.random.default_rng(20260607)
    B = 2000
    # Pre-build per-arm cell success vectors for resampling
    h_succ = np.array([int(bool(c["success"])) for c in claude
                       if c["agent"] == "text-only" and c["opId"].startswith("H")])

    def succ_vec_op(opid):
        return np.array([int(bool(c["success"])) for c in claude
                         if c["agent"] == "text-only" and c["opId"] == opid])

    def succ_vec_pair(pid):
        return np.array([int(bool(c["success"])) for c in c2
                         if c["agent"] == "text-only" and c["opId"] == pid])

    op_vecs = {}
    c5 = []
    for r in sorted(rows_t, key=lambda x: -x["interaction_pp"]):
        pid = r["pair"]
        a, b = pid.split("+")
        for o in (a, b):
            if o not in op_vecs:
                op_vecs[o] = succ_vec_op(o)
        pv = succ_vec_pair(pid)
        boots = np.empty(B)
        for i in range(B):
            hr = h_succ[rng.integers(0, len(h_succ), len(h_succ))].mean()
            ar = op_vecs[a][rng.integers(0, len(op_vecs[a]), len(op_vecs[a]))].mean()
            br = op_vecs[b][rng.integers(0, len(op_vecs[b]), len(op_vecs[b]))].mean()
            pr = pv[rng.integers(0, len(pv), len(pv))].mean()
            boots[i] = ((hr - pr) - ((hr - ar) + (hr - br))) * 100
        lo, hi = np.percentile(boots, [2.5, 97.5])
        c5.append(dict(pair=pid, n=r["n"], interaction_pp=round(r["interaction_pp"], 1),
                       boot_ci_lo=round(lo, 1), boot_ci_hi=round(hi, 1),
                       ci_excludes_zero=("yes" if (lo > 0 or hi < 0) else "no")))
    n_excl = sum(x["ci_excludes_zero"] == "yes" for x in c5)
    print(f"  {n_excl}/28 pairs have a 95% bootstrap CI on the interaction excluding 0")
    write_csv("comp5_interaction_bootstrap_ci.csv",
              ["pair", "n", "interaction_pp", "boot_ci_lo", "boot_ci_hi", "ci_excludes_zero"], c5)

    print("DONE. All outputs under results/supplementary/")


if __name__ == "__main__":
    main()

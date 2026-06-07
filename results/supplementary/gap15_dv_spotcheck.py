#!/usr/bin/env python3
"""
GAP-15 (dependent-variable construct validity) spot-check for the
CHI/ASSETS 2027 paper.

Two construct-validity threats were flagged by the audit:
  (a) string-match / very-low-step "successes": a binary task-success DV
      that accepts a 1-step send_msg_to_user may credit a case that never
      engaged the manipulated DOM region.
  (b) throttle-censoring: the headline binary-success DV counts provider
      429/throttle rejections as task failures.

This script computes ONLY the part that is a clean, frozen-data spot-check
without external field semantics: the rate of very-low-step Low-variant
"successes" (total_steps <= 1 and <= 2) per model, plus the token floor of
those cases, so the §Limitations DV paragraph can cite a measured rate.

The throttle-censored sensitivity number (threat b) is NOT computed here:
the throttle-vs-genuine failure_type/error_messages classification overlaps
LIT-OBS-5's throttle-relabeling scope and must be computed once, jointly,
to avoid double-counting (see audit fix plan, GAP-15 blockers). Inspection
of the frozen composite traces shows the text-only failure_type field
carries no 429/RateLimit/throttle code (codes are timeout / F_UNK / F_COF /
F_ENF / F_REA / F_AMB) and error_messages strings are Playwright
TimeoutError, not provider 429s, so a throttle-censored recomputation cannot
be derived from the composite trace summaries alone and is deferred.

Reads ONLY frozen artifacts:
  results/trace-summaries.jsonl   (composite Phase 1 text-only rows)
Writes ONLY:
  results/supplementary/gap15_dv_spotcheck.csv
Does NOT mutate any frozen artifact and does NOT re-run any experiment.
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
TRACES = os.path.join(RES, "trace-summaries.jsonl")
OUT = os.path.join(HERE, "gap15_dv_spotcheck.csv")


def main():
    # (model, variant) -> aggregates over text-only successes
    agg = defaultdict(lambda: {
        "n_success": 0,
        "le1_step_success": 0,
        "le2_step_success": 0,
        "min_tokens_among_le1": None,
    })
    # also tally failure_type codes among Low text-only to document the
    # absence of an explicit throttle/429 code (threat b non-computability)
    low_fail_codes = defaultdict(int)

    with open(TRACES) as f:
        for line in f:
            d = json.loads(line)
            if d.get("agent_type") != "text-only":
                continue
            model = d["model"]
            variant = d["variant"]
            steps = d.get("total_steps", 0)
            if d.get("success"):
                a = agg[(model, variant)]
                a["n_success"] += 1
                if steps <= 1:
                    a["le1_step_success"] += 1
                    tk = d.get("total_tokens", 0)
                    if a["min_tokens_among_le1"] is None or tk < a["min_tokens_among_le1"]:
                        a["min_tokens_among_le1"] = tk
                if steps <= 2:
                    a["le2_step_success"] += 1
            else:
                if variant == "low":
                    low_fail_codes[d.get("failure_type")] += 1

    rows = []
    for (model, variant) in sorted(agg):
        a = agg[(model, variant)]
        ns = a["n_success"]
        rows.append({
            "model": model,
            "variant": variant,
            "n_success": ns,
            "le1_step_success": a["le1_step_success"],
            "le1_step_success_pct": round(100 * a["le1_step_success"] / ns, 1) if ns else "",
            "le2_step_success": a["le2_step_success"],
            "le2_step_success_pct": round(100 * a["le2_step_success"] / ns, 1) if ns else "",
            "min_tokens_among_le1": a["min_tokens_among_le1"] if a["min_tokens_among_le1"] is not None else "",
        })

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("WROTE", OUT)
    for r in rows:
        print("  ", r)
    print("Low text-only failure_type codes (no explicit throttle/429 code present):")
    print("  ", dict(low_fail_codes))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Expansion Smoke Test Comparison: SoM (vision-only) vs CUA
Analyzes data from:
  - data/archive/expansion-som-smoke/ (28 cases, 7 tasks × 4 variants × 1 rep)
  - data/archive/expansion-cua-smoke/ (28 cases, 7 tasks × 4 variants × 1 rep)
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────
SOM_DIR = Path("data/archive/expansion-som-smoke")
CUA_DIR = Path("data/archive/expansion-cua-smoke")

VARIANT_ORDER = ["low", "medium-low", "base", "high"]
VARIANT_SHORT = {"low": "low", "medium-low": "ml", "base": "base", "high": "high"}

# ── Data Loading ───────────────────────────────────────────────────────────

def find_case_jsons(root_dir: Path) -> list[Path]:
    """Recursively find all JSON trace files (with caseId field), skip metadata files."""
    results = []
    skip_names = {"run-state.json", "manifest.json", "scan-result.json",
                  "experiment-data.csv", "failure-classifications.csv",
                  "scan-metrics.csv", "trace-summaries.csv"}
    for path in root_dir.rglob("*.json"):
        if path.name in skip_names:
            continue
        # Skip files in exports/ or track-a/ subdirectories (those have different formats)
        rel = path.relative_to(root_dir)
        parts = rel.parts
        if "exports" in parts:
            continue
        if "track-a" in parts:
            continue  # trace-attempt-1.json has different schema
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "caseId" in data:
                results.append(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return sorted(results)


def load_cases(root_dir: Path, agent_label: str) -> list[dict]:
    """Load all case JSONs from a directory, extract key fields."""
    paths = find_case_jsons(root_dir)
    cases = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        trace = raw.get("trace", {})
        cases.append({
            "agent": agent_label,
            "caseId": raw.get("caseId", ""),
            "app": raw.get("app", ""),
            "variant": raw.get("variant", ""),
            "taskId": raw.get("taskId", ""),
            "observationMode": raw.get("agentConfig", {}).get("observationMode", ""),
            "success": trace.get("success", False),
            "outcome": trace.get("outcome", "unknown"),
            "totalTokens": trace.get("totalTokens", 0),
            "totalSteps": trace.get("totalSteps", 0),
            "durationMs": trace.get("durationMs", 0),
        })
    return cases


# ── Display Helpers ────────────────────────────────────────────────────────

def task_label(app: str, task_id: str) -> str:
    """Short label like 'gitlab:132' or 'admin:41'."""
    app_short = {
        "ecommerce_admin": "admin",
        "ecommerce": "ecom",
        "gitlab": "gitlab",
        "reddit": "reddit",
    }
    return f"{app_short.get(app, app)}:{task_id}"


def print_separator(char="═", width=90):
    print(char * width)


def print_header(title: str, width=90):
    print()
    print_separator("═", width)
    print(f"  {title}")
    print_separator("═", width)


# ── Per-Agent Analysis ─────────────────────────────────────────────────────

def analyze_agent(cases: list[dict], agent_name: str):
    """Print full analysis for one agent type."""
    print_header(f"{agent_name} SMOKE TEST RESULTS  ({len(cases)} cases)")

    # Collect unique tasks and variants
    tasks = sorted(set((c["app"], c["taskId"]) for c in cases),
                   key=lambda t: (t[0], int(t[1])))
    variants_present = sorted(set(c["variant"] for c in cases),
                              key=lambda v: VARIANT_ORDER.index(v) if v in VARIANT_ORDER else 99)

    # ── (a) Task × Variant success matrix ──
    print(f"\n  Task × Variant Success Matrix")
    print(f"  {'Task':<16}", end="")
    for v in variants_present:
        print(f"  {VARIANT_SHORT.get(v, v):>6}", end="")
    print()
    print(f"  {'─'*16}", end="")
    for _ in variants_present:
        print(f"  {'─'*6}", end="")
    print()

    # Build lookup: (app, taskId, variant) -> case
    lookup = {}
    for c in cases:
        key = (c["app"], c["taskId"], c["variant"])
        lookup[key] = c

    task_results = {}  # task_label -> {variant: success_bool}
    for app, tid in tasks:
        tl = task_label(app, tid)
        task_results[tl] = {}
        print(f"  {tl:<16}", end="")
        for v in variants_present:
            c = lookup.get((app, tid, v))
            if c:
                mark = "✓" if c["success"] else "✗"
                task_results[tl][v] = c["success"]
                color = mark
            else:
                color = "—"
                task_results[tl][v] = None
            print(f"  {color:>6}", end="")
        print()

    # ── (b) Overall success rate per variant ──
    print(f"\n  Success Rate by Variant")
    print(f"  {'Variant':<14} {'Success':>8} {'Total':>6} {'Rate':>8}")
    print(f"  {'─'*14} {'─'*8} {'─'*6} {'─'*8}")
    variant_stats = {}
    for v in variants_present:
        v_cases = [c for c in cases if c["variant"] == v]
        succ = sum(1 for c in v_cases if c["success"])
        total = len(v_cases)
        rate = succ / total * 100 if total > 0 else 0
        variant_stats[v] = {"success": succ, "total": total, "rate": rate}
        print(f"  {v:<14} {succ:>8} {total:>6} {rate:>7.1f}%")

    total_succ = sum(1 for c in cases if c["success"])
    total_n = len(cases)
    total_rate = total_succ / total_n * 100 if total_n > 0 else 0
    print(f"  {'─'*14} {'─'*8} {'─'*6} {'─'*8}")
    print(f"  {'OVERALL':<14} {total_succ:>8} {total_n:>6} {total_rate:>7.1f}%")

    # ── (c) Token consumption per variant ──
    print(f"\n  Token Consumption by Variant")
    print(f"  {'Variant':<14} {'Avg Tokens':>12} {'Min':>10} {'Max':>10} {'Avg Steps':>10}")
    print(f"  {'─'*14} {'─'*12} {'─'*10} {'─'*10} {'─'*10}")
    for v in variants_present:
        v_cases = [c for c in cases if c["variant"] == v]
        tokens = [c["totalTokens"] for c in v_cases if c["totalTokens"] > 0]
        steps = [c["totalSteps"] for c in v_cases if c["totalSteps"] > 0]
        avg_tok = sum(tokens) / len(tokens) if tokens else 0
        min_tok = min(tokens) if tokens else 0
        max_tok = max(tokens) if tokens else 0
        avg_steps = sum(steps) / len(steps) if steps else 0
        print(f"  {v:<14} {avg_tok:>12,.0f} {min_tok:>10,} {max_tok:>10,} {avg_steps:>10.1f}")

    # ── (d) Outcome distribution ──
    print(f"\n  Outcome Distribution")
    outcomes = defaultdict(int)
    for c in cases:
        outcomes[c["outcome"]] += 1
    outcome_order = ["success", "failure", "timeout", "partial_success", "unknown"]
    print(f"  {'Outcome':<20} {'Count':>6} {'%':>8}")
    print(f"  {'─'*20} {'─'*6} {'─'*8}")
    for o in outcome_order:
        if o in outcomes:
            pct = outcomes[o] / len(cases) * 100
            print(f"  {o:<20} {outcomes[o]:>6} {pct:>7.1f}%")

    return variant_stats, task_results


# ── Combined Comparison ────────────────────────────────────────────────────

def print_comparison(som_cases, cua_cases, som_stats, cua_stats, som_tasks, cua_tasks):
    """Print side-by-side SoM vs CUA comparison."""
    print_header("COMBINED COMPARISON: SoM (vision-only) vs CUA")

    # ── Side-by-side success rates ──
    print(f"\n  Success Rate Comparison")
    print(f"  {'Variant':<14} {'SoM':>10} {'CUA':>10} {'Δ (CUA-SoM)':>12}")
    print(f"  {'─'*14} {'─'*10} {'─'*10} {'─'*12}")
    for v in VARIANT_ORDER:
        s = som_stats.get(v, {})
        c = cua_stats.get(v, {})
        sr = s.get("rate", 0)
        cr = c.get("rate", 0)
        delta = cr - sr
        delta_str = f"{delta:+.1f}pp"
        print(f"  {v:<14} {sr:>9.1f}% {cr:>9.1f}% {delta_str:>12}")

    som_overall = sum(1 for c in som_cases if c["success"]) / len(som_cases) * 100
    cua_overall = sum(1 for c in cua_cases if c["success"]) / len(cua_cases) * 100
    delta_overall = cua_overall - som_overall
    print(f"  {'─'*14} {'─'*10} {'─'*10} {'─'*12}")
    print(f"  {'OVERALL':<14} {som_overall:>9.1f}% {cua_overall:>9.1f}% {delta_overall:+.1f}pp")

    # ── Side-by-side task matrix ──
    print(f"\n  Task × Variant: SoM / CUA  (✓=success, ✗=fail)")
    all_tasks = sorted(set(list(som_tasks.keys()) + list(cua_tasks.keys())))
    print(f"  {'Task':<16}", end="")
    for v in VARIANT_ORDER:
        vs = VARIANT_SHORT.get(v, v)
        print(f"  {vs:>12}", end="")
    print()
    print(f"  {'─'*16}", end="")
    for _ in VARIANT_ORDER:
        print(f"  {'─'*12}", end="")
    print()

    for tl in all_tasks:
        print(f"  {tl:<16}", end="")
        for v in VARIANT_ORDER:
            s_val = som_tasks.get(tl, {}).get(v)
            c_val = cua_tasks.get(tl, {}).get(v)
            s_mark = "✓" if s_val else ("✗" if s_val is not None else "—")
            c_mark = "✓" if c_val else ("✗" if c_val is not None else "—")
            cell = f"{s_mark}/{c_mark}"
            print(f"  {cell:>12}", end="")
        print()

    # ── Token comparison ──
    print(f"\n  Token Consumption Comparison (avg)")
    print(f"  {'Variant':<14} {'SoM Avg':>12} {'CUA Avg':>12} {'Ratio':>8}")
    print(f"  {'─'*14} {'─'*12} {'─'*12} {'─'*8}")
    for v in VARIANT_ORDER:
        s_cases = [c for c in som_cases if c["variant"] == v and c["totalTokens"] > 0]
        c_cases = [c for c in cua_cases if c["variant"] == v and c["totalTokens"] > 0]
        s_avg = sum(c["totalTokens"] for c in s_cases) / len(s_cases) if s_cases else 0
        c_avg = sum(c["totalTokens"] for c in c_cases) / len(c_cases) if c_cases else 0
        ratio = c_avg / s_avg if s_avg > 0 else float("inf")
        print(f"  {v:<14} {s_avg:>12,.0f} {c_avg:>12,.0f} {ratio:>7.2f}×")

    # ── Steps comparison ──
    print(f"\n  Steps Comparison (avg)")
    print(f"  {'Variant':<14} {'SoM Steps':>12} {'CUA Steps':>12}")
    print(f"  {'─'*14} {'─'*12} {'─'*12}")
    for v in VARIANT_ORDER:
        s_cases = [c for c in som_cases if c["variant"] == v and c["totalSteps"] > 0]
        c_cases = [c for c in cua_cases if c["variant"] == v and c["totalSteps"] > 0]
        s_avg = sum(c["totalSteps"] for c in s_cases) / len(s_cases) if s_cases else 0
        c_avg = sum(c["totalSteps"] for c in c_cases) / len(c_cases) if c_cases else 0
        print(f"  {v:<14} {s_avg:>12.1f} {c_avg:>12.1f}")

    # ── Outcome comparison ──
    print(f"\n  Outcome Distribution Comparison")
    outcome_order = ["success", "failure", "timeout", "partial_success"]
    print(f"  {'Outcome':<20} {'SoM':>6} {'CUA':>6}")
    print(f"  {'─'*20} {'─'*6} {'─'*6}")
    som_outcomes = defaultdict(int)
    cua_outcomes = defaultdict(int)
    for c in som_cases:
        som_outcomes[c["outcome"]] += 1
    for c in cua_cases:
        cua_outcomes[c["outcome"]] += 1
    for o in outcome_order:
        if som_outcomes[o] > 0 or cua_outcomes[o] > 0:
            print(f"  {o:<20} {som_outcomes[o]:>6} {cua_outcomes[o]:>6}")


# ── Anomaly Detection ──────────────────────────────────────────────────────

def detect_anomalies(som_cases, cua_cases, som_tasks, cua_tasks):
    """Flag anomalies in the data."""
    print_header("ANOMALY DETECTION")
    anomalies = []

    all_tasks = sorted(set(list(som_tasks.keys()) + list(cua_tasks.keys())))

    for tl in all_tasks:
        for agent_name, task_results in [("SoM", som_tasks), ("CUA", cua_tasks)]:
            tr = task_results.get(tl, {})

            # Anomaly: low > base (unexpected — degraded a11y outperforms baseline)
            low_val = tr.get("low")
            base_val = tr.get("base")
            if low_val is True and base_val is False:
                anomalies.append(f"  ⚠ {agent_name} {tl}: low SUCCEEDS but base FAILS "
                                 f"(forced simplification or vacuous truth?)")

            # Anomaly: 0% across all variants
            all_fail = all(v is False for v in tr.values() if v is not None)
            if all_fail and len(tr) > 0:
                anomalies.append(f"  ⚠ {agent_name} {tl}: 0% across ALL variants "
                                 f"(model capability issue, not a11y effect)")

            # Anomaly: high < base (enhanced a11y hurts)
            high_val = tr.get("high")
            if high_val is False and base_val is True:
                anomalies.append(f"  ⚠ {agent_name} {tl}: high FAILS but base SUCCEEDS "
                                 f"(possible ARIA over-annotation or reasoning error)")

        # Cross-agent anomaly: SoM succeeds where CUA fails (unexpected)
        for v in VARIANT_ORDER:
            s_val = som_tasks.get(tl, {}).get(v)
            c_val = cua_tasks.get(tl, {}).get(v)
            if s_val is True and c_val is False:
                anomalies.append(f"  ⚠ {tl} {v}: SoM succeeds but CUA fails "
                                 f"(SoM advantage — unusual for coordinate-based agent)")

    # Anomaly: CUA low success > SoM low success (expected — CUA is DOM-independent)
    som_low = [c for c in som_cases if c["variant"] == "low"]
    cua_low = [c for c in cua_cases if c["variant"] == "low"]
    som_low_rate = sum(1 for c in som_low if c["success"]) / len(som_low) * 100 if som_low else 0
    cua_low_rate = sum(1 for c in cua_low if c["success"]) / len(cua_low) * 100 if cua_low else 0
    if cua_low_rate > som_low_rate:
        anomalies.append(f"\n  ✓ EXPECTED: CUA low ({cua_low_rate:.0f}%) > SoM low ({som_low_rate:.0f}%) "
                         f"— CUA is DOM-independent, unaffected by semantic degradation")
    elif som_low_rate > cua_low_rate:
        anomalies.append(f"\n  ⚠ UNEXPECTED: SoM low ({som_low_rate:.0f}%) > CUA low ({cua_low_rate:.0f}%) "
                         f"— SoM should not outperform CUA under degraded DOM")

    if not anomalies:
        print("  No anomalies detected.")
    else:
        for a in anomalies:
            print(a)

    # ── Key Takeaways ──
    print_header("KEY TAKEAWAYS")
    som_overall = sum(1 for c in som_cases if c["success"]) / len(som_cases) * 100
    cua_overall = sum(1 for c in cua_cases if c["success"]) / len(cua_cases) * 100

    print(f"  • SoM overall: {som_overall:.1f}% ({sum(1 for c in som_cases if c['success'])}/{len(som_cases)})")
    print(f"  • CUA overall: {cua_overall:.1f}% ({sum(1 for c in cua_cases if c['success'])}/{len(cua_cases)})")
    print(f"  • CUA advantage: {cua_overall - som_overall:+.1f}pp")

    # Low variant comparison (key causal test)
    print(f"\n  Low variant (key causal test — DOM semantic degradation):")
    print(f"    SoM low: {som_low_rate:.1f}%  |  CUA low: {cua_low_rate:.1f}%  |  Δ: {cua_low_rate - som_low_rate:+.1f}pp")

    # Tasks where both agree vs disagree
    agree_count = 0
    disagree_count = 0
    for tl in all_tasks:
        for v in VARIANT_ORDER:
            s = som_tasks.get(tl, {}).get(v)
            c = cua_tasks.get(tl, {}).get(v)
            if s is not None and c is not None:
                if s == c:
                    agree_count += 1
                else:
                    disagree_count += 1
    total_pairs = agree_count + disagree_count
    print(f"\n  Agreement: {agree_count}/{total_pairs} task×variant pairs ({agree_count/total_pairs*100:.0f}%)")
    print(f"  Disagreement: {disagree_count}/{total_pairs} pairs ({disagree_count/total_pairs*100:.0f}%)")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 90)
    print("  EXPANSION SMOKE TEST ANALYSIS: SoM (vision-only) vs CUA")
    print("  7 tasks × 4 variants × 1 rep per agent type")
    print("=" * 90)

    # Load data
    som_cases = load_cases(SOM_DIR, "SoM")
    cua_cases = load_cases(CUA_DIR, "CUA")

    print(f"\n  Loaded: {len(som_cases)} SoM cases, {len(cua_cases)} CUA cases")

    if not som_cases:
        print(f"  ERROR: No SoM cases found in {SOM_DIR}")
        sys.exit(1)
    if not cua_cases:
        print(f"  ERROR: No CUA cases found in {CUA_DIR}")
        sys.exit(1)

    # Per-agent analysis
    som_stats, som_tasks = analyze_agent(som_cases, "SoM (vision-only)")
    cua_stats, cua_tasks = analyze_agent(cua_cases, "CUA (coordinate-based)")

    # Combined comparison
    print_comparison(som_cases, cua_cases, som_stats, cua_stats, som_tasks, cua_tasks)

    # Anomaly detection
    detect_anomalies(som_cases, cua_cases, som_tasks, cua_tasks)

    print()


if __name__ == "__main__":
    main()

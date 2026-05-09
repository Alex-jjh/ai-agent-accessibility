#!/usr/bin/env python3.11
"""Stage 3 sanity check — completeness, outcome distribution, per-op rates.

Usage:
  python3.11 scripts/stage3/sanity-check.py --data-dir data/stage3-llama --label Llama
  python3.11 scripts/stage3/sanity-check.py --data-dir data/stage3-claude --label Claude
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path

EXPECTED_OPS = [
    "L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12","L13",
    "ML1","ML2","ML3",
    "H1","H2","H3","H4","H5a","H5b","H5c","H6","H7","H8",
]
EXPECTED_APPS = {"ecommerce": 22, "ecommerce_admin": 12, "gitlab": 13, "reddit": 1}
N_REPS = 3

# Mode A Llama bottom-5 reference (from project-context.md)
MODE_A_LLAMA_BOTTOM = {"L1", "L11", "L9", "L5", "L2"}
# Mode A Claude bottom-5 reference
MODE_A_CLAUDE_BOTTOM = {"L1", "L5", "L9", "L12", "ML1"}


def pct(values: list, q: float) -> float:
    if not values:
        return 0.0
    return sorted(values)[min(int(len(values) * q), len(values) - 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True, help="data/stage3-{claude,llama}")
    ap.add_argument("--label", default="Stage 3", help="Label for report ('Llama' or 'Claude')")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(glob.glob(str(data_dir / "*/cases/*.json")))
    print(f"[{args.label}] case files: {len(files)}")

    expected_cases = sum(EXPECTED_APPS.values()) * len(EXPECTED_OPS) * N_REPS
    print(f"[{args.label}] expected: {sum(EXPECTED_APPS.values())} tasks × {len(EXPECTED_OPS)} ops × {N_REPS} reps = {expected_cases}")

    by_app = collections.Counter()
    by_op = collections.Counter()
    outcomes = collections.Counter()
    succ_by_op = collections.Counter()
    total_by_op = collections.Counter()
    succ_by_task: dict[str, int] = collections.defaultdict(int)
    total_by_task: dict[str, int] = collections.defaultdict(int)
    durations: list[float] = []
    steps: list[int] = []
    tokens: list[int] = []
    reps_seen: dict[tuple, set] = collections.defaultdict(set)

    for fp in files:
        try:
            d = json.load(open(fp))
        except Exception as e:
            print(f"  unreadable: {fp}: {e}", file=sys.stderr)
            continue
        cid = d.get("caseId", "")
        parts = cid.split(":")
        if len(parts) < 6:
            continue
        app, _, task, _ci, attempt, op = parts[:6]
        by_app[app] += 1
        by_op[op] += 1
        task_key = f"{app}:{task}"
        reps_seen[(task_key, op)].add(attempt)

        trace = d.get("trace") or {}
        outc = trace.get("outcome") or "unknown"
        outcomes[outc] += 1
        succ = bool(trace.get("success"))
        total_by_op[op] += 1
        total_by_task[task_key] += 1
        if succ:
            succ_by_op[op] += 1
            succ_by_task[task_key] += 1
        if trace.get("durationMs"):
            durations.append(trace["durationMs"] / 1000)
        if trace.get("totalSteps"):
            steps.append(trace["totalSteps"])
        if trace.get("totalTokens"):
            tokens.append(trace["totalTokens"])

    # §1 Completeness
    print("\n=== §1. Completeness ===")
    print(f"  cases parsed: {sum(by_app.values())}")
    print(f"  cases by app: {dict(by_app)}")
    print("  per-app expected:")
    any_mismatch = False
    for a, n in EXPECTED_APPS.items():
        exp_n = n * len(EXPECTED_OPS) * N_REPS
        got = by_app.get(a, 0)
        mark = "✓" if got == exp_n else "✗"
        print(f"    {mark} {a}: got {got}, expected {exp_n}")
        if got != exp_n:
            any_mismatch = True

    missing_ops = [op for op in EXPECTED_OPS if op not in by_op]
    if missing_ops:
        print(f"  ✗ missing operators entirely: {missing_ops}")
        any_mismatch = True
    else:
        print(f"  ✓ all 26 operators present")

    incomplete = [(tk, op, sorted(reps)) for (tk, op), reps in reps_seen.items() if len(reps) != N_REPS]
    if incomplete:
        print(f"  ⚠ {len(incomplete)} (task,op) cells missing reps:")
        for tk, op, seen in incomplete[:10]:
            print(f"    {tk} × {op}: reps present = {seen}")
    else:
        print(f"  ✓ all {len(reps_seen)} (task,op) cells have {N_REPS} reps")

    # §2 Outcome distribution
    print("\n=== §2. Outcome distribution ===")
    total = sum(outcomes.values())
    for k in ["success", "partial_success", "failure", "timeout", "unknown"]:
        v = outcomes.get(k, 0)
        print(f"  {k:<18}: {v:>5}  ({v/max(total,1)*100:5.1f}%)")
    overall_succ = sum(succ_by_op.values())
    print(f"\n  overall success: {overall_succ}/{total} = {overall_succ/max(total,1):.1%}")

    # §3 Performance
    print("\n=== §3. Performance distribution ===")
    print(f"  duration (sec): p50={pct(durations,0.5):.1f}  p90={pct(durations,0.9):.1f}  max={max(durations, default=0):.1f}")
    print(f"  steps:          p50={pct(steps,0.5):.1f}  p90={pct(steps,0.9):.1f}  max={max(steps, default=0)}")
    print(f"  tokens:         p50={pct(tokens,0.5):,.0f}  p90={pct(tokens,0.9):,.0f}  max={max(tokens, default=0):,}")

    # §4 Per-operator success
    print("\n=== §4. Per-operator success rate (ascending) ===")
    op_rows = [(succ_by_op[op]/max(total_by_op[op],1), op, succ_by_op[op], total_by_op[op]) for op in EXPECTED_OPS]
    op_rows.sort()
    for r, op, s, n in op_rows:
        print(f"  {op:<6} {s:>3}/{n:<3}  {r:>5.1%}")

    # §5 Per-task success (spot pathological)
    print("\n=== §5. Per-task success rate (ascending) ===")
    t_rows = [(succ_by_task[tk]/max(total_by_task[tk],1), tk, succ_by_task[tk], total_by_task[tk])
              for tk in sorted(total_by_task)]
    t_rows.sort()
    for r, tk, s, n in t_rows:
        flag = ""
        if r < 0.10:
            flag = " ← very low"
        elif r > 0.95:
            flag = " ← ceiling"
        print(f"  {tk:<25} {s:>3}/{n:<3}  {r:>5.1%}{flag}")

    # §6 Ordering check vs Mode A
    print(f"\n=== §6. Cross-check vs Mode A {args.label} ordering ===")
    stage3_order = [op for op in sorted(EXPECTED_OPS, key=lambda o: succ_by_op[o]/max(total_by_op[o],1))]
    bottom5 = set(stage3_order[:5])
    print(f"  Stage 3 bottom 5:  {stage3_order[:5]}")
    if args.label.lower().startswith("llama"):
        ref = MODE_A_LLAMA_BOTTOM
        print(f"  Mode A Llama ref:  {sorted(ref)}")
    else:
        ref = MODE_A_CLAUDE_BOTTOM
        print(f"  Mode A Claude ref: {sorted(ref)}")
    overlap = bottom5 & ref
    print(f"  Overlap: {len(overlap)}/5 — {sorted(overlap)}")
    print(f"  Top 5:    {stage3_order[-5:]}")

    # Verdict
    print("\n=== §7. Verdict ===")
    if any_mismatch or incomplete:
        print("  ⚠ INCOMPLETE: some cases missing, see above")
        return 1
    print(f"  ✓ Complete ({total} cases)")
    print(f"  ✓ Ordering {'matches' if len(overlap) >= 3 else 'partially matches'} Mode A reference ({len(overlap)}/5 overlap)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3.11
"""Check if the 3/3_consistent + no-infra-failures gate is oversampling
trivial (1-2 step) tasks. If yes, we're selecting for 'click and done'
rather than real navigation where a11y tree parsing matters.

Compares step distribution:
  - All 3/3-passing tasks (candidate set)
  - Tasks that would ALSO pass 2/3 gate (broader pool)
"""
import collections
import glob
import json
import os
import re
import sys
from statistics import median, mean

root = sys.argv[1]
os.chdir(root)


def extract_answer(action: str) -> str | None:
    m = re.search(r'send_msg_to_user\s*\(\s*["\']?(.*?)["\']?\s*\)\s*$', action.strip(), re.DOTALL)
    return m.group(1).strip() if m else None


def find_final_answer(steps):
    for s in reversed(steps or []):
        a = s.get("action", "")
        if "send_msg_to_user" in a:
            return extract_answer(a)
    return None


def has_infra_failure(trace_steps, bridge_log) -> bool:
    for s in trace_steps or []:
        rd = s.get("resultDetail") or ""
        if "Bridge process terminated" in rd:
            return True
        if "Context Window" in rd:
            return True
        if "Target crashed" in rd:
            return True
    if bridge_log and "ui_login for shopping_admin failed" in bridge_log:
        return True
    return False


tasks = collections.defaultdict(lambda: {
    "reps": [],
    "answers": [],
    "steps_per_rep": [],
    "infra_failure_reps": 0,
})

for p in glob.glob("*/cases/*.json"):
    try:
        d = json.load(open(p))
        t = d["trace"]
        key = (d["app"], d["taskId"])
        tasks[key]["reps"].append(t["outcome"])
        tasks[key]["steps_per_rep"].append(t["totalSteps"])
        tasks[key]["answers"].append(find_final_answer(t.get("steps")))
        if has_infra_failure(t.get("steps"), t.get("bridgeLog") or ""):
            tasks[key]["infra_failure_reps"] += 1
    except Exception:
        pass


def describe(n_list, label):
    if not n_list:
        print(f"  {label}: (no tasks)")
        return
    n_list = sorted(n_list)
    n = len(n_list)
    p25 = n_list[n // 4]
    p50 = n_list[n // 2]
    p75 = n_list[(3 * n) // 4]
    p90 = n_list[int(n * 0.9)]
    print(f"  {label:35} n={n:>4}  steps: min={n_list[0]} p25={p25} p50={p50} p75={p75} p90={p90} max={n_list[-1]}  mean={mean(n_list):.1f}")


# Bucket tasks by gate outcome
strict_3_3_steps = []  # passes 3/3 success + 0 infra
permissive_2_3_steps = []  # passes 2/3 success + 0 infra but NOT 3/3
all_any_success_steps = []

strict_by_step = collections.Counter()

for (app, tid), info in tasks.items():
    if len(info["reps"]) < 3:
        continue
    n_success = info["reps"].count("success")
    has_infra = info["infra_failure_reps"] > 0
    median_steps = int(median(info["steps_per_rep"]))

    if n_success == 3 and not has_infra:
        strict_3_3_steps.append(median_steps)
        # Bucket for range inspection
        if median_steps <= 2:
            strict_by_step["trivial (<=2 steps)"] += 1
        elif median_steps <= 5:
            strict_by_step["short (3-5 steps)"] += 1
        elif median_steps <= 10:
            strict_by_step["medium (6-10 steps)"] += 1
        elif median_steps <= 20:
            strict_by_step["long (11-20 steps)"] += 1
        else:
            strict_by_step["very long (>20 steps)"] += 1
    elif n_success == 2 and not has_infra:
        permissive_2_3_steps.append(median_steps)
    if n_success >= 1:
        all_any_success_steps.append(median_steps)

print("Step-count distribution (median across 3 reps):")
describe(strict_3_3_steps, "3/3 success + no infra (strict)")
describe(permissive_2_3_steps, "2/3 success + no infra (permissive-only)")
describe(all_any_success_steps, "any success (very permissive)")

print()
print("Strict 3/3 set: task-complexity bucketing")
total_strict = sum(strict_by_step.values())
for bucket in ["trivial (<=2 steps)", "short (3-5 steps)", "medium (6-10 steps)", "long (11-20 steps)", "very long (>20 steps)"]:
    n = strict_by_step[bucket]
    pct = 100 * n / max(total_strict, 1)
    print(f"  {bucket:28} {n:>4} ({pct:.1f}%)")

print()
print("Concern check: trivial tasks (<=2 steps) as % of strict 3/3 set:")
trivial = strict_by_step["trivial (<=2 steps)"]
print(f"  {trivial}/{total_strict} = {100*trivial/max(total_strict,1):.1f}%")
print()
print("If >30%, strict 3/3 gate is overweighting 'click and answer' tasks")
print("where a11y tree parsing barely matters → variant effects may be muted.")

#!/usr/bin/env python3.11
"""Quick gate comparison: counts task-triples that pass 3/3 vs 2/3 gates
on the live smoker data. Used to decide the filter threshold before all
cases complete.

Usage:
    python3.11 gate-quick.py <shard-root-dir>
"""
import collections
import glob
import json
import os
import re
import sys

root = sys.argv[1]
os.chdir(root)


def extract_answer(action: str) -> str | None:
    m = re.search(r'send_msg_to_user\s*\(\s*["\']?(.*?)["\']?\s*\)\s*$', action.strip(), re.DOTALL)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1).strip().lower()).strip(".,;:!? ")


def find_final_answer(steps):
    for s in reversed(steps or []):
        a = s.get("action", "")
        if "send_msg_to_user" in a:
            return extract_answer(a)
    return None


tasks = collections.defaultdict(lambda: {"reps": [], "answers": [], "steps": []})
for p in glob.glob("*/cases/*.json"):
    try:
        d = json.load(open(p))
        t = d["trace"]
        key = (d["app"], d["taskId"])
        tasks[key]["reps"].append(t["outcome"])
        tasks[key]["steps"].append(t["totalSteps"])
        tasks[key]["answers"].append(find_final_answer(t.get("steps")))
    except Exception:
        pass

buckets = collections.Counter()
by_app_bucket = collections.Counter()
examples = collections.defaultdict(list)

for (app, tid), info in tasks.items():
    if len(info["reps"]) < 3:
        continue
    n_success = info["reps"].count("success")
    n_partial = info["reps"].count("partial_success")
    succ_answers = [a for a, o in zip(info["answers"], info["reps"]) if o == "success" and a]
    consistent = len(set(succ_answers)) <= 1 if succ_answers else False
    if n_success == 3 and consistent:
        bucket = "3/3_consistent"
    elif n_success == 3:
        bucket = "3/3_drift"
    elif n_success == 2 and consistent:
        bucket = "2/3_consistent"
    elif n_success == 2:
        bucket = "2/3_drift"
    elif n_success >= 1 or n_partial >= 1:
        bucket = "1/3_or_partial"
    else:
        bucket = "0/3"
    buckets[bucket] += 1
    by_app_bucket[(app, bucket)] += 1
    if len(examples[bucket]) < 3:
        examples[bucket].append(f"{app}:{tid} reps={info['reps']}")

total = sum(buckets.values())
print(f"\nTotal task-triples (3 reps recorded): {total}")
print()
print(f"{'Bucket':22} {'Count':>6} {'Pct':>7}")
print("-" * 38)
for b in ["3/3_consistent", "3/3_drift", "2/3_consistent", "2/3_drift", "1/3_or_partial", "0/3"]:
    n = buckets[b]
    pct = 100 * n / max(total, 1)
    print(f"  {b:20} {n:>5} {pct:>6.1f}%")

print()
print("Per-app breakdown (bucket totals):")
apps = sorted(set(a for (a, _), _ in by_app_bucket.items()))
bucket_list = ["3/3_consistent", "3/3_drift", "2/3_consistent", "2/3_drift", "1/3_or_partial", "0/3"]
hdr = f"{'app':18} " + " ".join(f"{b:>16}" for b in bucket_list)
print(hdr)
for app in apps:
    row = f"{app:18} " + " ".join(f"{by_app_bucket[(app,b)]:>16}" for b in bucket_list)
    print(row)

print()
print("Gate comparison (count of passing tasks):")
g_3_3_strict = buckets["3/3_consistent"]
g_3_3_permissive = buckets["3/3_consistent"] + buckets["3/3_drift"]
g_2_3_consistent = g_3_3_strict + buckets["2/3_consistent"]
g_2_3_any = g_2_3_consistent + buckets["2/3_drift"]
print(f"  3/3 success + answer consistent: {g_3_3_strict}")
print(f"  3/3 success (any answers):       {g_3_3_permissive}")
print(f"  >=2/3 success + consistent:      {g_2_3_consistent}")
print(f"  >=2/3 success (any answers):     {g_2_3_any}")

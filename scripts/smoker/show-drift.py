#!/usr/bin/env python3.11
"""Show actual answers for 3/3_drift tasks to understand whether the
inconsistency is real (agent gave different answers) or just formatting
differences (agent gave same answer in different string forms)."""
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
    return m.group(1).strip()  # raw, no normalization


def norm(s: str) -> str:
    x = s.strip().lower()
    x = re.sub(r"\s+", " ", x)
    return x.strip(".,;:!? ")


def find_final_answer(steps):
    for s in reversed(steps or []):
        a = s.get("action", "")
        if "send_msg_to_user" in a:
            return extract_answer(a)
    return None


tasks = collections.defaultdict(lambda: {"reps": [], "answers_raw": []})
for p in glob.glob("*/cases/*.json"):
    try:
        d = json.load(open(p))
        t = d["trace"]
        key = (d["app"], d["taskId"])
        tasks[key]["reps"].append(t["outcome"])
        tasks[key]["answers_raw"].append(find_final_answer(t.get("steps")))
    except Exception:
        pass

shown = 0
for (app, tid), info in sorted(tasks.items()):
    if len(info["reps"]) < 3:
        continue
    if info["reps"].count("success") != 3:
        continue
    succ = [a for a, o in zip(info["answers_raw"], info["reps"]) if o == "success" and a]
    norms = [norm(a) for a in succ]
    if len(set(norms)) <= 1:
        continue  # consistent, skip
    # Drift case: show all 3
    print(f"=== {app}:{tid} ===")
    for i, a in enumerate(succ):
        print(f"  rep{i+1}: {a[:150]!r}")
    print()
    shown += 1
    if shown >= 10:
        break

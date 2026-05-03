#!/usr/bin/env python3.11
"""
Re-evaluate Mode A with ground truth corrections for Docker-drift tasks.

Three tasks have ground truth mismatches due to:
  - Task 41, 198: Agent-induced Magento state mutation (search_query table, order data)
  - Task 293: Deployment configuration (GitLab external_url set to private IP)

See scripts/amt/ground-truth-corrections.json for details.

Usage:
  python3.11 scripts/amt/analyze-mode-a-corrected.py [--data-dirs dir1 dir2 ...]
"""
import json, glob, sys, os
from collections import defaultdict, Counter

# Load ground truth corrections
CORRECTIONS_PATH = os.path.join(os.path.dirname(__file__), "ground-truth-corrections.json")
with open(CORRECTIONS_PATH) as f:
    corrections = json.load(f)["corrections"]

# Build lookup: task_id -> list of additional valid answers (lowercase)
ADDITIONAL_GT = {}
for tid, info in corrections.items():
    ADDITIONAL_GT[tid] = [a.lower() for a in info["additional_valid"]]

# Data directories
data_dirs = sys.argv[1:] if len(sys.argv) > 1 else ["data/mode-a-shard-a", "data/mode-a-shard-b"]

# Load all cases
cases = []
for data_dir in data_dirs:
    for f in glob.glob(f"{data_dir}/*/cases/*.json"):
        if "/scan-result" in f or "/trace-attempt" in f or "/classification" in f:
            continue
        with open(f) as fh:
            d = json.load(fh)
        cid = d.get("caseId", "")
        parts = cid.split(":")
        if len(parts) != 6:
            continue
        t = d.get("trace", {})
        tid = parts[2]
        agent = t.get("agentConfig", {}).get("observationMode", "?")
        original_success = t.get("success", False)

        # Extract agent answer
        answer = ""
        for s in t.get("steps", []):
            a = s.get("action", "")
            if "send_msg_to_user" in a:
                answer = a
                break
        # For CUA, extract from bridge log
        if agent == "cua" and not answer:
            bl = t.get("bridgeLog", "")
            for line in bl.split("\n"):
                if "Task complete" in line:
                    # Format: "[cua] Task complete (via tool): <answer>"
                    idx = line.find(":")
                    if idx >= 0:
                        # Find the last colon after "Task complete"
                        tc_idx = line.find("Task complete")
                        if tc_idx >= 0:
                            rest = line[tc_idx:]
                            colon_idx = rest.find(":")
                            if colon_idx >= 0:
                                answer = rest[colon_idx+1:].strip()
                    break

        # Apply correction
        corrected_success = original_success
        if tid in ADDITIONAL_GT and not original_success and answer:
            answer_lower = answer.lower()
            for valid in ADDITIONAL_GT[tid]:
                if valid in answer_lower:
                    corrected_success = True
                    break

        cases.append({
            "caseId": cid, "taskId": tid, "opId": parts[5],
            "agent": agent,
            "success": corrected_success,
            "original_success": original_success,
            "answer": answer[:200],
            "totalTokens": t.get("totalTokens", 0),
            "durationMs": t.get("durationMs", 0),
        })

# === Summary ===
corrected_count = sum(1 for c in cases if c["success"] and not c["original_success"])
print(f"Total cases: {len(cases)}")
print(f"Data dirs: {data_dirs}")
print(f"Corrected false negatives: {corrected_count}")
orig_ok = sum(c["original_success"] for c in cases)
corr_ok = sum(c["success"] for c in cases)
print(f"Original: {orig_ok}/{len(cases)} ({orig_ok/len(cases)*100:.1f}%)")
print(f"Corrected: {corr_ok}/{len(cases)} ({corr_ok/len(cases)*100:.1f}%)")

agents = ["text-only", "vision-only", "cua"]

# Per-agent
print(f"\n{'='*70}")
print("PER-AGENT (corrected)")
print(f"{'='*70}")
for a in agents:
    ac = [c for c in cases if c["agent"] == a]
    ok = sum(1 for c in ac if c["success"])
    orig = sum(1 for c in ac if c["original_success"])
    tokens = sum(c["totalTokens"] for c in ac)
    dur = sum(c["durationMs"] for c in ac)
    print(f"  {a:>12s}: {ok}/{len(ac)} ({ok/len(ac)*100:.1f}%)  [was {orig}/{len(ac)} ({orig/len(ac)*100:.1f}%)]"
          f"  avg_tok={tokens//max(len(ac),1):,}  avg_dur={dur//max(len(ac),1)//1000}s")

# Per-task (text-only)
print(f"\n{'='*70}")
print("PER-TASK (text-only, corrected)")
print(f"{'='*70}")
task_app = {}
for c in cases:
    task_app[c["taskId"]] = c["caseId"].split(":")[0]
tasks = sorted(set(c["taskId"] for c in cases), key=int)
for tid in tasks:
    tc = [c for c in cases if c["taskId"] == tid and c["agent"] == "text-only"]
    ok = sum(1 for c in tc if c["success"])
    orig = sum(1 for c in tc if c["original_success"])
    marker = " *** CORRECTED" if ok != orig else ""
    print(f"  task {tid:>3s} ({task_app.get(tid,'?'):>15s}): {ok}/{len(tc)} ({ok/len(tc)*100:.0f}%){marker}")

# Operator ranking (text-only)
OP_DESC = {
    "L1": "landmark→div", "L2": "remove ARIA+role", "L3": "remove labels",
    "L4": "remove kbd handlers", "L5": "Shadow DOM", "L6": "heading→div",
    "L7": "remove alt/aria-label", "L8": "remove tabindex", "L9": "thead→div",
    "L10": "remove lang", "L11": "link→span", "L12": "dup IDs", "L13": "onfocus blur",
    "ML1": "empty btn→div", "ML2": "clone-replace", "ML3": "remove label+aria",
    "H1": "auto aria-label", "H2": "skip-nav", "H3": "assoc labels",
    "H4": "add landmark", "H5a": "auto alt", "H5b": "add lang=en",
    "H5c": "auto aria-label links", "H6": "aria-required", "H7": "aria-current",
    "H8": "table scope",
}
print(f"\n{'='*70}")
print("OPERATOR RANKING (text-only, corrected)")
print(f"{'='*70}")
op_text = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    if c["agent"] == "text-only":
        op_text[c["opId"]]["total"] += 1
        if c["success"]:
            op_text[c["opId"]]["ok"] += 1
ranked = sorted(op_text.items(), key=lambda x: x[1]["ok"]/x[1]["total"])
h_ops = [d for op, d in op_text.items() if op.startswith("H")]
h_rate = sum(d["ok"] for d in h_ops) / sum(d["total"] for d in h_ops) if h_ops else 0
print(f"  H-operator baseline: {h_rate*100:.1f}%")
print(f"{'Rank':>4s}  {'Op':>5s}  {'Rate':>14s}  {'Drop':>7s}  Description")
print("-" * 65)
for i, (op, d) in enumerate(ranked):
    rate = d["ok"]/d["total"]
    drop = h_rate - rate
    print(f"{i+1:>4d}  {op:>5s}  {d['ok']}/{d['total']} ({rate*100:.1f}%)  {drop*100:+6.1f}pp  {OP_DESC.get(op,'')}")

# Operator × Task heatmap (text-only)
print(f"\n{'='*70}")
print("OPERATOR × TASK HEATMAP (text-only, corrected)")
print(f"{'='*70}")
op_task = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    if c["agent"] == "text-only":
        op_task[(c["opId"], c["taskId"])]["total"] += 1
        if c["success"]:
            op_task[(c["opId"], c["taskId"])]["ok"] += 1

header = f"{'Op':>5s} " + " ".join(f"{t:>4s}" for t in tasks)
print(header)
for op, _ in ranked:
    row = f"{op:>5s} "
    for tid in tasks:
        d = op_task[(op, tid)]
        if d["total"] == 0:
            row += "   - "
        else:
            pct = d["ok"] / d["total"] * 100
            row += f" {pct:3.0f}%"
    print(row)

# Cross-agent per operator
print(f"\n{'='*70}")
print("CROSS-AGENT PER OPERATOR (corrected)")
print(f"{'='*70}")
op_all = defaultdict(lambda: defaultdict(lambda: {"ok": 0, "total": 0}))
for c in cases:
    op_all[c["opId"]][c["agent"]]["total"] += 1
    if c["success"]:
        op_all[c["opId"]][c["agent"]]["ok"] += 1

print(f"{'Op':>5s}  {'text-only':>14s}  {'SoM':>14s}  {'CUA':>14s}")
print("-" * 55)
for op, _ in ranked:
    cells = []
    for a in agents:
        d = op_all[op][a]
        if d["total"]:
            cells.append(f"{d['ok']}/{d['total']} ({d['ok']/d['total']*100:.0f}%)")
        else:
            cells.append("—")
    print(f"{op:>5s}  {cells[0]:>14s}  {cells[1]:>14s}  {cells[2]:>14s}")

print("\nDone.")

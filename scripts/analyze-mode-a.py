#!/usr/bin/env python3.11
"""Analyze Mode A results — per-operator × per-agent × per-task success matrix."""
import json, glob, sys
from collections import defaultdict, Counter

# Load all cases from both shards
cases = []
for pattern in ["data/mode-a-shard-a/*/cases/*.json", "data/mode-a-shard-b/*/cases/*.json"]:
    for f in glob.glob(pattern):
        # Skip non-case files (scan-result, trace-attempt, classification)
        if "/scan-result" in f or "/trace-attempt" in f or "/classification" in f:
            continue
        with open(f) as fh:
            d = json.load(fh)
        cid = d.get("caseId", "")
        parts = cid.split(":")
        if len(parts) != 6:
            continue
        t = d.get("trace", {})
        cases.append({
            "caseId": cid,
            "app": parts[0],
            "taskId": parts[2],
            "attempt": int(parts[4]),
            "opId": parts[5],
            "agent": t.get("agentConfig", {}).get("observationMode", "?"),
            "success": t.get("success", False),
            "outcome": t.get("outcome", "?"),
            "reward": t.get("steps", [{}])[-1].get("result", "") if t.get("steps") else "",
            "totalSteps": t.get("totalSteps", 0),
            "totalTokens": t.get("totalTokens", 0),
            "durationMs": t.get("durationMs", 0),
        })

print(f"Total cases loaded: {len(cases)}")
print(f"Unique operators: {len(set(c['opId'] for c in cases))}")
print(f"Unique tasks: {len(set(c['taskId'] for c in cases))}")
print(f"Unique agents: {set(c['agent'] for c in cases)}")

# === 1. Per-operator success rate by agent ===
print("\n" + "="*80)
print("1. PER-OPERATOR SUCCESS RATE BY AGENT")
print("="*80)
op_agent = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    key = (c["opId"], c["agent"])
    op_agent[key]["total"] += 1
    if c["success"]:
        op_agent[key]["ok"] += 1

ops = sorted(set(c["opId"] for c in cases))
agents = ["text-only", "vision-only", "cua"]
print(f"\n{'Operator':>8s}  {'text-only':>12s}  {'SoM':>12s}  {'CUA':>12s}  {'Overall':>12s}")
print("-" * 65)
for op in ops:
    cells = []
    total_ok, total_n = 0, 0
    for a in agents:
        d = op_agent[(op, a)]
        rate = f"{d['ok']}/{d['total']} ({d['ok']/d['total']*100:.0f}%)" if d['total'] > 0 else "—"
        cells.append(rate)
        total_ok += d['ok']
        total_n += d['total']
    overall = f"{total_ok}/{total_n} ({total_ok/total_n*100:.0f}%)"
    print(f"{op:>8s}  {cells[0]:>12s}  {cells[1]:>12s}  {cells[2]:>12s}  {overall:>12s}")

# === 2. Per-task success rate by agent ===
print("\n" + "="*80)
print("2. PER-TASK SUCCESS RATE BY AGENT (across all operators)")
print("="*80)
task_agent = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    key = (c["taskId"], c["agent"])
    task_agent[key]["total"] += 1
    if c["success"]:
        task_agent[key]["ok"] += 1

tasks = sorted(set(c["taskId"] for c in cases), key=lambda x: int(x))
print(f"\n{'Task':>6s}  {'App':>15s}  {'text-only':>12s}  {'SoM':>12s}  {'CUA':>12s}")
print("-" * 55)
task_app = {}
for c in cases:
    task_app[c["taskId"]] = c["app"]
for tid in tasks:
    cells = []
    for a in agents:
        d = task_agent[(tid, a)]
        rate = f"{d['ok']}/{d['total']} ({d['ok']/d['total']*100:.0f}%)" if d['total'] > 0 else "—"
        cells.append(rate)
    print(f"{tid:>6s}  {task_app.get(tid,'?'):>15s}  {cells[0]:>12s}  {cells[1]:>12s}  {cells[2]:>12s}")

# === 3. Operator × Task heatmap (text-only only, for signature alignment) ===
print("\n" + "="*80)
print("3. OPERATOR × TASK HEATMAP (text-only success rate, 3 reps)")
print("="*80)
op_task_text = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    if c["agent"] == "text-only":
        key = (c["opId"], c["taskId"])
        op_task_text[key]["total"] += 1
        if c["success"]:
            op_task_text[key]["ok"] += 1

header = f"{'Op':>6s} " + " ".join(f"{t:>5s}" for t in tasks)
print(header)
print("-" * len(header))
for op in ops:
    row = f"{op:>6s} "
    for tid in tasks:
        d = op_task_text[(op, tid)]
        if d["total"] == 0:
            row += "    — "
        else:
            pct = d["ok"] / d["total"] * 100
            row += f" {pct:4.0f}%"
    print(row)

# === 4. Top-10 highest-drop operators (text-only) ===
print("\n" + "="*80)
print("4. OPERATOR DROP RANKING (text-only, sorted by success rate)")
print("="*80)
op_text = defaultdict(lambda: {"ok": 0, "total": 0})
for c in cases:
    if c["agent"] == "text-only":
        op_text[c["opId"]]["total"] += 1
        if c["success"]:
            op_text[c["opId"]]["ok"] += 1

ranked = sorted(op_text.items(), key=lambda x: x[1]["ok"]/x[1]["total"] if x[1]["total"] > 0 else 0)
print(f"\n{'Rank':>4s}  {'Operator':>8s}  {'Rate':>12s}  {'Description'}")
print("-" * 70)
OP_DESC = {
    "L1": "landmark→div", "L2": "remove ARIA+role", "L3": "remove labels",
    "L4": "remove keyboard handlers", "L5": "Shadow DOM wrap", "L6": "heading→div",
    "L7": "remove alt/aria-label/title", "L8": "remove tabindex", "L9": "thead→div",
    "L10": "remove lang", "L11": "link→span", "L12": "duplicate IDs", "L13": "onfocus blur",
    "ML1": "empty button→div", "ML2": "clone-replace listeners", "ML3": "remove label+aria",
    "H1": "auto aria-label", "H2": "skip-nav link", "H3": "associate labels",
    "H4": "add landmark role", "H5a": "auto alt text", "H5b": "add lang=en",
    "H5c": "auto aria-label for empty links", "H6": "aria-required", "H7": "aria-current",
    "H8": "table scope",
}
for i, (op, d) in enumerate(ranked):
    rate = f"{d['ok']}/{d['total']} ({d['ok']/d['total']*100:.1f}%)"
    print(f"{i+1:>4d}  {op:>8s}  {rate:>12s}  {OP_DESC.get(op, '')}")

# === 5. Agent comparison summary ===
print("\n" + "="*80)
print("5. AGENT COMPARISON SUMMARY")
print("="*80)
for a in agents:
    ac = [c for c in cases if c["agent"] == a]
    ok = sum(1 for c in ac if c["success"])
    tokens = sum(c["totalTokens"] for c in ac)
    dur = sum(c["durationMs"] for c in ac)
    print(f"  {a:>12s}: {ok}/{len(ac)} ({ok/len(ac)*100:.1f}%), "
          f"avg tokens={tokens//len(ac):,}, avg duration={dur//len(ac)//1000}s")

# === 6. Interesting patterns ===
print("\n" + "="*80)
print("6. INTERESTING PATTERNS")
print("="*80)

# Find operators where CUA > text-only (unexpected — CUA should be less affected by semantic ops)
print("\nOperators where CUA success > text-only success:")
for op in ops:
    t = op_agent[(op, "text-only")]
    c = op_agent[(op, "cua")]
    if t["total"] > 0 and c["total"] > 0:
        t_rate = t["ok"] / t["total"]
        c_rate = c["ok"] / c["total"]
        if c_rate > t_rate + 0.05:  # CUA > text-only by >5pp
            print(f"  {op}: text-only={t_rate*100:.0f}%, CUA={c_rate*100:.0f}% (Δ={c_rate*100-t_rate*100:+.0f}pp)")

# Find operators where SoM > text-only (very unexpected)
print("\nOperators where SoM success > text-only success:")
for op in ops:
    t = op_agent[(op, "text-only")]
    s = op_agent[(op, "vision-only")]
    if t["total"] > 0 and s["total"] > 0:
        t_rate = t["ok"] / t["total"]
        s_rate = s["ok"] / s["total"]
        if s_rate > t_rate + 0.05:
            print(f"  {op}: text-only={t_rate*100:.0f}%, SoM={s_rate*100:.0f}% (Δ={s_rate*100-t_rate*100:+.0f}pp)")

# Find tasks where ALL operators fail (task-level floor)
print("\nTasks where text-only success < 30% across ALL operators:")
for tid in tasks:
    total_ok = sum(1 for c in cases if c["taskId"] == tid and c["agent"] == "text-only" and c["success"])
    total_n = sum(1 for c in cases if c["taskId"] == tid and c["agent"] == "text-only")
    if total_n > 0 and total_ok / total_n < 0.30:
        print(f"  task {tid} ({task_app.get(tid)}): {total_ok}/{total_n} ({total_ok/total_n*100:.1f}%)")

print("\nDone.")

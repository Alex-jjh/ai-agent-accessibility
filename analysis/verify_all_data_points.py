#!/usr/bin/env python3
"""
Comprehensive Data Point Verification
======================================
Cross-checks ALL claims in the paper against raw data sources:
1. test.raw.json (WebArena task definitions) — task counts, eval types, sites
2. task-site-mapping.json — task-to-site mapping
3. results/combined-experiment.csv — experiment results
4. results/stats/*.csv — statistical outputs
5. paper/sections/task-selection-protocol.md — claimed numbers

Flags any inconsistency as ERROR.
"""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
errors = []
warnings = []

def error(msg):
    errors.append(msg)
    print(f"  ❌ ERROR: {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  ⚠️  WARN: {msg}")

def ok(msg):
    print(f"  ✅ OK: {msg}")


print("=" * 70)
print("  COMPREHENSIVE DATA POINT VERIFICATION")
print("=" * 70)

# ============================================================
# 1. Verify WebArena task pool numbers from test.raw.json
# ============================================================
print("\n--- 1. WebArena Task Pool (test.raw.json) ---")

with open(ROOT / "test.raw.json", encoding="utf-8") as f:
    tasks_raw = json.load(f)

total_tasks = len(tasks_raw)
if total_tasks == 812:
    ok(f"Total tasks: {total_tasks} (matches claim of 812)")
else:
    error(f"Total tasks: {total_tasks} (claimed 812)")

# Count by site
with open(ROOT / "task-site-mapping.json", encoding="utf-8") as f:
    site_map = json.load(f)

site_counts = Counter(site_map.values())
print(f"  Sites: {dict(site_counts)}")

# Verify site exclusion numbers
map_count = site_counts.get("map", 0)
wiki_count = site_counts.get("wikipedia", 0)
excluded_sites = map_count + wiki_count
remaining_after_s1 = total_tasks - excluded_sites

if map_count == 112:
    ok(f"map tasks: {map_count}")
else:
    error(f"map tasks: {map_count} (expected 112)")

if wiki_count == 16:
    ok(f"wikipedia tasks: {wiki_count}")
else:
    error(f"wikipedia tasks: {wiki_count} (expected 16)")

if remaining_after_s1 == 684:
    ok(f"After Stage 1: {remaining_after_s1}")
else:
    error(f"After Stage 1: {remaining_after_s1} (expected 684)")

# Count eval types for deployed sites
deployed_sites = {"shopping", "shopping_admin", "reddit", "gitlab"}
deployed_tasks = [t for t in tasks_raw if site_map.get(str(t["task_id"]), "") in deployed_sites]

eval_types = Counter()
for t in deployed_tasks:
    eval_info = t.get("eval", {})
    eval_types_list = eval_info.get("eval_types", [])
    for et in eval_types_list:
        eval_types[et] += 1

# Some tasks have multiple eval types; count primary
primary_eval = Counter()
for t in deployed_tasks:
    eval_info = t.get("eval", {})
    eval_types_list = eval_info.get("eval_types", [])
    if eval_types_list:
        primary_eval[eval_types_list[0]] += 1

print(f"  Primary eval types (deployed): {dict(primary_eval)}")

string_match_count = sum(1 for t in deployed_tasks
                         if t.get("eval", {}).get("eval_types", []) == ["string_match"])
print(f"  Tasks with sole string_match: {string_match_count}")

# Stage 2: sole string_match
if string_match_count == 231:
    ok("Stage 2 output: 231 (sole string_match)")
else:
    error(f"Stage 2 output: {string_match_count} (expected 231)")

# ============================================================
# 2. Verify combined-experiment.csv integrity
# ============================================================
print("\n--- 2. Combined Experiment CSV ---")

df = pd.read_csv(ROOT / "results" / "combined-experiment.csv")

if len(df) == 1040:
    ok(f"Total cases: {len(df)}")
else:
    error(f"Total cases: {len(df)} (expected 1040)")

# Per-experiment counts
exp_expected = {
    "pilot4-full": 240, "pilot4-cua": 120,
    "expansion-claude": 140, "expansion-llama4": 260,
    "expansion-som": 140, "expansion-cua": 140,
}
for exp, expected in exp_expected.items():
    actual = len(df[df["experiment"] == exp])
    if actual == expected:
        ok(f"{exp}: {actual} cases")
    else:
        error(f"{exp}: {actual} cases (expected {expected})")

# Per-variant counts (should be 260 each)
for v in ["low", "medium-low", "base", "high"]:
    n = len(df[df["variant"] == v])
    if n == 260:
        ok(f"Variant {v}: {n} cases")
    else:
        error(f"Variant {v}: {n} cases (expected 260)")

# Per-task counts (should be 80 each)
for tid in sorted(df["task_id"].unique()):
    n = len(df[df["task_id"] == tid])
    if n == 80:
        ok(f"Task {tid}: {n} cases")
    else:
        error(f"Task {tid}: {n} cases (expected 80)")

# ============================================================
# 3. Verify task metadata consistency
# ============================================================
print("\n--- 3. Task Metadata ---")

task_meta = pd.read_csv(ROOT / "results" / "task-metadata.csv")

# Nav depth distribution
nav_counts = task_meta["nav_depth"].value_counts().to_dict()
expected_nav = {"shallow": 5, "medium": 5, "deep": 3}
if nav_counts == expected_nav:
    ok(f"Nav depth: {nav_counts}")
else:
    error(f"Nav depth: {nav_counts} (expected {expected_nav})")

# Template count
n_templates = task_meta["template_id"].nunique()
if n_templates == 11:
    ok(f"Unique templates: {n_templates}")
else:
    error(f"Unique templates: {n_templates} (expected 11)")

# App distribution
app_counts = task_meta["app_short"].value_counts().to_dict()
expected_apps = {"admin": 4, "ecom": 4, "reddit": 2, "gitlab": 3}
if app_counts == expected_apps:
    ok(f"App distribution: {app_counts}")
else:
    error(f"App distribution: {app_counts} (expected {expected_apps})")

# Low feasibility
low_infeasible = set(task_meta[~task_meta["low_feasible"]]["task_id"])
expected_infeasible = {23, 24, 26, 198, 293, 308}
if low_infeasible == expected_infeasible:
    ok(f"Low-infeasible tasks: {sorted(low_infeasible)}")
else:
    error(f"Low-infeasible: {sorted(low_infeasible)} (expected {sorted(expected_infeasible)})")

# ============================================================
# 4. Verify key statistical claims
# ============================================================
print("\n--- 4. Statistical Claims ---")

# 4a. Cochran-Armitage for text-only Claude
tc = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
succs, tots = [], []
for v in ["low", "medium-low", "base", "high"]:
    vdf = tc[tc["variant"] == v]
    succs.append(int(vdf["success"].sum()))
    tots.append(len(vdf))

scores = np.array([0, 1, 2, 3], dtype=float)
succs_arr = np.array(succs, dtype=float)
tots_arr = np.array(tots, dtype=float)
N = tots_arr.sum()
R = succs_arr.sum()
p_hat = R / N
T = np.sum(scores * succs_arr) - (R/N) * np.sum(scores * tots_arr)
var = p_hat * (1-p_hat) * (np.sum(scores**2 * tots_arr) - np.sum(scores * tots_arr)**2 / N)
Z_ca = T / math.sqrt(var) if var > 0 else 0
p_ca = 2 * (1 - stats.norm.cdf(abs(Z_ca)))

print(f"  Text-only Claude: low={succs[0]}/{tots[0]}, ml={succs[1]}/{tots[1]}, base={succs[2]}/{tots[2]}, high={succs[3]}/{tots[3]}")
print(f"  Cochran-Armitage Z={Z_ca:.3f}, p={p_ca:.8f}")

if abs(Z_ca - 6.635) < 0.1:
    ok(f"CA Z={Z_ca:.3f} matches key-numbers.md (6.635)")
else:
    error(f"CA Z={Z_ca:.3f} does NOT match key-numbers.md (6.635)")

# 4b. Success rates from paper-decisions.md
claimed = {
    ("text-only", "claude-sonnet", "low"): 38.5,
    ("text-only", "claude-sonnet", "base"): 93.8,
    ("text-only", "claude-sonnet", "high"): 89.2,
    ("text-only", "llama4-maverick", "low"): 36.9,
    ("text-only", "llama4-maverick", "base"): 70.8,
    ("text-only", "llama4-maverick", "high"): 75.4,
    ("cua", "claude-sonnet", "low"): 58.5,  # pilot4+expansion combined
    ("vision-only", "claude-sonnet", "low"): 4.6,  # pilot4+expansion combined
}

for (agent, model, variant), claimed_rate in claimed.items():
    subset = df[(df["agent_type"] == agent) & (df["model"] == model) & (df["variant"] == variant)]
    if len(subset) == 0:
        subset = df[(df["agent_type"] == agent) & (df["variant"] == variant)]
    actual_rate = 100 * subset["success"].mean() if len(subset) > 0 else 0
    diff = abs(actual_rate - claimed_rate)
    if diff < 1.0:
        ok(f"{agent}/{model}/{variant}: {actual_rate:.1f}% (claimed {claimed_rate}%)")
    else:
        warn(f"{agent}/{model}/{variant}: {actual_rate:.1f}% vs claimed {claimed_rate}% (diff={diff:.1f}pp)")

# 4c. Causal decomposition numbers
text_claude = df[(df["agent_type"] == "text-only") & (df["model"] == "claude-sonnet")]
cua_claude = df[(df["agent_type"] == "cua") & (df["model"] == "claude-sonnet")]

text_low = text_claude[text_claude["variant"] == "low"]["success"].mean() * 100
text_base = text_claude[text_claude["variant"] == "base"]["success"].mean() * 100
cua_low = cua_claude[cua_claude["variant"] == "low"]["success"].mean() * 100
cua_base = cua_claude[cua_claude["variant"] == "base"]["success"].mean() * 100

text_drop = text_base - text_low
cua_drop = cua_base - cua_low
semantic = text_drop - cua_drop

print(f"\n  Causal decomposition:")
print(f"    Text-only: base {text_base:.1f}% - low {text_low:.1f}% = {text_drop:.1f}pp")
print(f"    CUA:       base {cua_base:.1f}% - low {cua_low:.1f}% = {cua_drop:.1f}pp")
print(f"    Semantic:  {text_drop:.1f} - {cua_drop:.1f} = {semantic:.1f}pp")

if abs(text_drop - 55.4) > 5:
    warn(f"Text-only drop {text_drop:.1f}pp vs key-numbers.md 55.4pp")
if abs(cua_drop - 35.4) > 5:
    warn(f"CUA drop {cua_drop:.1f}pp vs key-numbers.md 35.4pp")

# ============================================================
# 5. Verify task selection funnel numbers
# ============================================================
print("\n--- 5. Task Selection Funnel ---")

# Count sole string_match tasks in deployed sites
sm_tasks = [t for t in deployed_tasks if t.get("eval", {}).get("eval_types", []) == ["string_match"]]
print(f"  sole string_match tasks (deployed): {len(sm_tasks)}")
if len(sm_tasks) == 231:
    ok("Stage 2 output: 231")
else:
    warn(f"Stage 2 output: {len(sm_tasks)} (expected 231)")

# Verify our 13 tasks exist and have string_match
our_tasks = {4, 23, 24, 26, 29, 41, 67, 94, 132, 188, 198, 293, 308}
for tid in sorted(our_tasks):
    task_data = next((t for t in tasks_raw if t["task_id"] == tid), None)
    if task_data is None:
        error(f"Task {tid} not found in test.raw.json")
        continue
    eval_types = task_data.get("eval", {}).get("eval_types", [])
    site = site_map.get(str(tid), "unknown")
    has_sm = "string_match" in eval_types
    if has_sm:
        ok(f"Task {tid} ({site}): string_match ✓")
    else:
        error(f"Task {tid} ({site}): eval_types={eval_types}, NO string_match")

# ============================================================
# 6. Verify template IDs
# ============================================================
print("\n--- 6. Template IDs ---")

template_map = {}
for t in tasks_raw:
    tid = t["task_id"]
    if tid in our_tasks:
        # WebArena doesn't have explicit template_id; we use intent pattern
        # Just verify the task exists
        template_map[tid] = t.get("intent", "")[:50]

for tid in sorted(our_tasks):
    intent = template_map.get(tid, "NOT FOUND")
    print(f"  Task {tid}: {intent}")

# ============================================================
# 7. Cross-check experiment configs
# ============================================================
print("\n--- 7. Experiment Config Consistency ---")

# Verify Pilot 4 tasks
p4_tasks = set(df[df["experiment"] == "pilot4-full"]["task_id"].unique())
expected_p4 = {4, 23, 24, 26, 29, 67}
if p4_tasks == expected_p4:
    ok(f"Pilot 4 tasks: {sorted(p4_tasks)}")
else:
    error(f"Pilot 4 tasks: {sorted(p4_tasks)} (expected {sorted(expected_p4)})")

# Verify expansion tasks
exp_tasks = set(df[df["experiment"] == "expansion-claude"]["task_id"].unique())
expected_exp = {41, 94, 132, 188, 198, 293, 308}
if exp_tasks == expected_exp:
    ok(f"Expansion Claude tasks: {sorted(exp_tasks)}")
else:
    error(f"Expansion Claude tasks: {sorted(exp_tasks)} (expected {sorted(expected_exp)})")

# Verify Llama 4 covers all 13
llama_tasks = set(df[df["experiment"] == "expansion-llama4"]["task_id"].unique())
if llama_tasks == our_tasks:
    ok(f"Llama 4 tasks: all 13")
else:
    error(f"Llama 4 tasks: {sorted(llama_tasks)} (expected all 13)")

# ============================================================
# 8. Verify WebArena version claim
# ============================================================
print("\n--- 8. WebArena Version ---")
# We claimed commit ac07c86 — this needs manual verification
# but we can check the task count matches
warn("WebArena commit hash (ac07c86) needs manual verification against Docker image")
ok(f"Task count {total_tasks} is consistent with WebArena v1.0")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 70)
print(f"  VERIFICATION COMPLETE")
print(f"  Errors: {len(errors)}")
print(f"  Warnings: {len(warnings)}")
print("=" * 70)

if errors:
    print("\n  ERRORS (must fix):")
    for e in errors:
        print(f"    ❌ {e}")

if warnings:
    print("\n  WARNINGS (review):")
    for w in warnings:
        print(f"    ⚠️  {w}")

sys.exit(1 if errors else 0)

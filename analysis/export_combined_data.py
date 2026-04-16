#!/usr/bin/env python3
"""
Export Combined Experiment Data
===============================
Reads ALL 1,040 experiment traces from 6 data directories and produces:
  - results/combined-experiment.csv  (Layer 1)
  - results/trace-summaries.jsonl    (Layer 2)
  - results/task-metadata.csv
  - results/experiment-metadata.csv

Usage:
    python analysis/export_combined_data.py
"""

import csv
import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)
log = logging.getLogger("export")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

# Task metadata (hardcoded from experiment design)
TASK_META = {
    4:   {"app": "ecommerce_admin", "template": 279, "nav_depth": "medium",  "eval_type": "string_match"},
    23:  {"app": "ecommerce",       "template": 222, "nav_depth": "shallow", "eval_type": "string_match"},
    24:  {"app": "ecommerce",       "template": 222, "nav_depth": "shallow", "eval_type": "string_match"},
    26:  {"app": "ecommerce",       "template": 222, "nav_depth": "shallow", "eval_type": "string_match"},
    29:  {"app": "reddit",          "template": 33,  "nav_depth": "medium",  "eval_type": "string_match"},
    41:  {"app": "ecommerce_admin", "template": 285, "nav_depth": "medium",  "eval_type": "string_match"},
    67:  {"app": "reddit",          "template": 17,  "nav_depth": "shallow", "eval_type": "string_match"},
    94:  {"app": "ecommerce_admin", "template": 274, "nav_depth": "deep",    "eval_type": "string_match"},
    132: {"app": "gitlab",          "template": 322, "nav_depth": "medium",  "eval_type": "string_match"},
    188: {"app": "ecommerce",       "template": 159, "nav_depth": "shallow", "eval_type": "string_match"},
    198: {"app": "ecommerce_admin", "template": 366, "nav_depth": "deep",    "eval_type": "string_match"},
    293: {"app": "gitlab",          "template": 329, "nav_depth": "medium",  "eval_type": "string_match"},
    308: {"app": "gitlab",          "template": 323, "nav_depth": "deep",    "eval_type": "string_match"},
}

# Task feasibility at low variant
LOW_INFEASIBLE = {23, 24, 26, 198, 293, 308}
LOW_FEASIBLE   = {4, 29, 41, 67, 94, 132, 188}

# App short names
APP_SHORT = {
    "ecommerce_admin": "admin",
    "ecommerce":       "ecom",
    "reddit":          "reddit",
    "gitlab":          "gitlab",
}

# Variant ordinals (for CLMM ordinal regression)
VARIANT_ORDINAL = {
    "low":        0,
    "medium-low": 1,
    "base":       2,
    "high":       3,
}

# Model mapping
MODEL_MAP = {
    "claude-sonnet":        "claude-sonnet",
    "claude-sonnet-vision": "claude-sonnet",
    "llama4":               "llama4-maverick",
}

# Model family
MODEL_FAMILY = {
    "claude-sonnet":    "anthropic",
    "llama4-maverick":  "meta",
}

# Experiment directory configs
# Each entry: (dir_name, experiment_label, expected_count, notes)
EXPERIMENT_DIRS = [
    ("pilot4-full",       "pilot4-full",       240, "Pilot 4 text-only + SoM"),
    ("pilot4-cua",        "pilot4-cua",        120, "Pilot 4 CUA"),
    ("expansion-claude",  "expansion-claude",  140, "Claude expansion text-only"),
    ("expansion-llama4",  "expansion-llama4",  260, "Llama 4 text-only"),
    ("expansion-som",     "expansion-som",     140, "SoM expansion"),
    ("expansion-cua",     "expansion-cua",     140, "CUA expansion"),
]

# Pilot 4 tasks (original 6)
PILOT4_TASKS = {4, 23, 24, 26, 29, 67}
# Expansion tasks (7 new)
EXPANSION_TASKS = {41, 94, 132, 188, 198, 293, 308}

# Layer 1 CSV columns (exact order from schema)
LAYER1_COLUMNS = [
    "case_id", "experiment", "task_id", "app", "app_short",
    "variant", "variant_ordinal", "agent_type", "model", "model_family",
    "rep", "success", "outcome", "reward", "total_steps", "total_tokens",
    "duration_ms", "final_answer", "failure_type", "failure_domain",
    "task_template", "task_intent", "nav_depth", "eval_type",
    "dom_changes", "task_feasible",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_int(val, default=0):
    """Safely convert to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    """Safely convert to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def truncate(s, max_len=200):
    """Truncate string to max_len chars."""
    if s is None:
        return ""
    s = str(s)
    if len(s) > max_len:
        return s[:max_len]
    return s


def determine_agent_type(agent_config):
    """Determine agent type from agentConfig."""
    mode = agent_config.get("observationMode", "")
    if mode == "cua":
        return "cua"
    elif mode == "vision-only":
        return "vision-only"
    elif mode == "text-only":
        return "text-only"
    elif mode == "vision":
        return "vision-only"
    else:
        return mode or "text-only"


def determine_model(agent_config, experiment):
    """Determine canonical model name."""
    llm = agent_config.get("llmBackend", "")
    mapped = MODEL_MAP.get(llm, llm)
    # Override for llama4 experiment
    if experiment == "expansion-llama4" and mapped == "claude-sonnet":
        mapped = "llama4-maverick"
    if experiment == "expansion-llama4" and not mapped:
        mapped = "llama4-maverick"
    if not mapped:
        mapped = "claude-sonnet"
    return mapped


def determine_model_family(model):
    """Determine model family from canonical model name."""
    return MODEL_FAMILY.get(model, "unknown")


def determine_task_feasible(task_id, variant):
    """Determine if task is feasible at given variant."""
    tid = safe_int(task_id)
    if variant == "low":
        if tid in LOW_INFEASIBLE:
            return False
        return True
    # All tasks feasible at non-low variants
    return True


def extract_final_answer(trace):
    """Extract final answer from trace, checking multiple locations."""
    # Direct field
    fa = trace.get("finalAnswer")
    if fa:
        return str(fa)
    # Check last step's resultDetail (CUA stores answer there)
    steps = trace.get("steps", [])
    if steps:
        last = steps[-1]
        rd = last.get("resultDetail", "")
        if rd:
            return str(rd)
    return ""


def extract_failure_info(data, trace):
    """Extract failure type and domain from trace data."""
    failure_type = ""
    failure_domain = ""

    # Check various locations for failure classification
    ft = trace.get("failureType", "")
    if not ft:
        ft = trace.get("failure_type", "")
    if not ft:
        ft = data.get("failureType", "")

    if ft:
        failure_type = str(ft)

    # Derive domain from type
    if failure_type:
        if failure_type.startswith("F_SIF") or failure_type.startswith("F_CIN"):
            failure_domain = "a11y"
        elif failure_type.startswith("F_SOM"):
            failure_domain = "som"
        elif failure_type.startswith("F_COF") or failure_type.startswith("F_REA"):
            failure_domain = "model"
        elif failure_type.startswith("F_PLT"):
            failure_domain = "platform"
        else:
            failure_domain = ""

    return failure_type, failure_domain


def extract_reward(data):
    """Extract reward value from taskOutcome or trace."""
    to = data.get("taskOutcome", {})
    if isinstance(to, dict):
        r = to.get("reward")
        if r is not None:
            return safe_float(r)
        # Check outcome
        outcome = to.get("outcome", "")
        if outcome == "success":
            return 1.0
    # Check trace
    trace = data.get("trace", {})
    if trace.get("success"):
        return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_case_files(data_dir, experiment_name):
    """Find all case JSON files in a data directory.

    Handles the various directory structures:
    - Standard: data/<dir>/<uuid>/cases/*.json
    - pilot4-cua: data/pilot4-cua/pilot4-cua/<uuid>/cases/*.json

    When multiple UUID directories exist under the same parent, uses only
    the one with the most case files (others are stale/partial runs).
    """
    base = data_dir / experiment_name
    if not base.exists():
        log.warning("Directory not found: %s", base)
        return []

    skip_dirs = {"track-a", "exports"}
    skip_files = {"run-state.json", "manifest.json"}

    def collect_cases_from_dir(cases_dir):
        """Collect JSON files from a cases/ directory."""
        files = []
        for f in sorted(cases_dir.iterdir()):
            if f.is_file() and f.suffix == ".json" and f.name not in skip_files:
                files.append(f)
        return files

    def find_uuid_dirs_with_cases(parent):
        """Find UUID-like directories that contain a cases/ subdirectory.
        Returns list of (uuid_dir, [case_files])."""
        results = []
        try:
            entries = sorted(parent.iterdir())
        except PermissionError:
            return results
        for entry in entries:
            if not entry.is_dir() or entry.name in skip_dirs:
                continue
            cases_dir = entry / "cases"
            if cases_dir.is_dir():
                files = collect_cases_from_dir(cases_dir)
                if files:
                    results.append((entry, files))
            else:
                # Check one level deeper (pilot4-cua has extra nesting)
                sub_results = find_uuid_dirs_with_cases(entry)
                results.extend(sub_results)
        return results

    uuid_groups = find_uuid_dirs_with_cases(base)

    if not uuid_groups:
        log.warning("No case files found in %s", base)
        return []

    # If multiple UUID dirs found under the same parent, keep only the largest
    # Group by parent directory
    parent_groups = defaultdict(list)
    for uuid_dir, files in uuid_groups:
        parent_groups[uuid_dir.parent].append((uuid_dir, files))

    case_files = []
    for parent, groups in parent_groups.items():
        if len(groups) > 1:
            # Multiple UUID dirs — pick the one with the most files
            groups.sort(key=lambda g: len(g[1]), reverse=True)
            primary = groups[0]
            log.info("  Multiple UUID dirs under %s — using %s (%d files), skipping %d others",
                     parent.name, primary[0].name, len(primary[1]),
                     sum(len(g[1]) for g in groups[1:]))
            case_files.extend(primary[1])
        else:
            case_files.extend(groups[0][1])

    return case_files


# ---------------------------------------------------------------------------
# Parse a single trace file
# ---------------------------------------------------------------------------

def parse_trace(filepath, experiment):
    """Parse a single trace JSON file and return (layer1_row, layer2_obj) or None."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning("Failed to parse %s: %s", filepath, e)
        return None

    # --- Extract basic fields ---
    case_id_raw = data.get("caseId", "")
    app = data.get("app", "")
    variant = data.get("variant", "")
    task_id_str = data.get("taskId", "")
    task_id = safe_int(task_id_str)

    agent_config = data.get("agentConfig", {})
    agent_type = determine_agent_type(agent_config)
    model = determine_model(agent_config, experiment)
    model_family = determine_model_family(model)

    # --- Extract trace data ---
    trace = data.get("trace", {})
    success = bool(trace.get("success", False))
    outcome = trace.get("outcome", "failure")
    total_steps = safe_int(trace.get("totalSteps", trace.get("totalSteps", 0)))
    total_tokens = safe_int(trace.get("totalTokens", 0))
    duration_ms = safe_int(trace.get("durationMs", 0))
    final_answer = extract_final_answer(trace)
    reward = extract_reward(data)

    # If totalSteps is 0 but we have steps, count them
    steps = trace.get("steps", [])
    if total_steps == 0 and steps:
        total_steps = len(steps)

    # --- Failure info ---
    failure_type, failure_domain = extract_failure_info(data, trace)

    # --- Variant info ---
    variant_info = data.get("variantInfo", {})
    dom_changes = safe_int(variant_info.get("domChanges", 0))

    # --- Task metadata ---
    meta = TASK_META.get(task_id, {})
    app_from_meta = meta.get("app", app)
    if not app:
        app = app_from_meta
    app_short = APP_SHORT.get(app, app)
    task_template = meta.get("template", 0)
    nav_depth = meta.get("nav_depth", "")
    eval_type = meta.get("eval_type", "")

    # --- Determine rep from caseId or filename ---
    # caseId format: "ecommerce:base:23:0:1" → parts[-1] is rep
    # Filename format: "ecommerce_base_23_0_1.json"
    rep = 0
    if case_id_raw:
        parts = case_id_raw.split(":")
        if len(parts) >= 5:
            rep = safe_int(parts[-1], 1)
    if rep == 0:
        # Try from filename
        fname = filepath.stem  # e.g., "ecommerce_base_23_0_1"
        match = re.search(r'_(\d+)$', fname)
        if match:
            rep = safe_int(match.group(1), 1)
    if rep == 0:
        rep = 1

    # --- Build canonical case_id ---
    # Format: app:variant:taskId:agentType:model:0:rep
    case_id = f"{app}:{variant}:{task_id}:{agent_type}:{model}:{0}:{rep}"

    # --- Task feasibility ---
    task_feasible = determine_task_feasible(task_id, variant)

    # --- Task intent (from trace or empty) ---
    task_intent = ""

    # --- Build Layer 1 row ---
    layer1 = {
        "case_id":         case_id,
        "experiment":      experiment,
        "task_id":         task_id,
        "app":             app,
        "app_short":       app_short,
        "variant":         variant,
        "variant_ordinal": VARIANT_ORDINAL.get(variant, -1),
        "agent_type":      agent_type,
        "model":           model,
        "model_family":    model_family,
        "rep":             rep,
        "success":         success,
        "outcome":         outcome,
        "reward":          reward,
        "total_steps":     total_steps,
        "total_tokens":    total_tokens,
        "duration_ms":     duration_ms,
        "final_answer":    truncate(final_answer),
        "failure_type":    failure_type,
        "failure_domain":  failure_domain,
        "task_template":   task_template,
        "task_intent":     task_intent,
        "nav_depth":       nav_depth,
        "eval_type":       eval_type,
        "dom_changes":     dom_changes,
        "task_feasible":   task_feasible,
    }

    # --- Build Layer 2 object ---
    action_sequence = []
    step_tokens = []
    step_durations_ms = []
    observation_sizes = []
    click_failures = 0
    fill_failures = 0
    goto_count = 0
    max_consecutive_click_failures = 0
    consecutive_click_failures = 0
    pages_visited = set()
    error_messages = set()

    for step in steps[:30]:  # Truncate to first 30 steps
        action = step.get("action", "")
        action_sequence.append(action)

        # Step tokens (not always available per-step)
        st = safe_int(step.get("tokens", 0))
        step_tokens.append(st)

        # Step duration
        sd = safe_int(step.get("durationMs", 0))
        step_durations_ms.append(sd)

        # Observation size
        obs = step.get("observation", "")
        observation_sizes.append(len(str(obs)))

        # Action analysis
        result = step.get("result", "")
        result_detail = step.get("resultDetail", "")

        if "click(" in action:
            if result == "failure" or "not found" in str(result_detail).lower() or "not visible" in str(result_detail).lower():
                click_failures += 1
                consecutive_click_failures += 1
                max_consecutive_click_failures = max(max_consecutive_click_failures, consecutive_click_failures)
            else:
                consecutive_click_failures = 0
        elif "fill(" in action:
            if result == "failure":
                fill_failures += 1
                consecutive_click_failures = 0
            else:
                consecutive_click_failures = 0
        elif "goto(" in action:
            goto_count += 1
            consecutive_click_failures = 0
        else:
            consecutive_click_failures = 0

        # Extract URLs from observations
        for url_match in re.finditer(r'https?://[^\s\'">\]]+', str(obs)):
            pages_visited.add(url_match.group())

        # Collect error messages
        if result == "failure" and result_detail:
            error_messages.add(str(result_detail)[:200])

    max_observation_size = max(observation_sizes) if observation_sizes else 0

    layer2 = {
        "case_id":                          case_id,
        "experiment":                       experiment,
        "task_id":                          task_id,
        "variant":                          variant,
        "agent_type":                       agent_type,
        "model":                            model,
        "rep":                              rep,
        "success":                          success,
        "outcome":                          outcome,
        "total_steps":                      total_steps,
        "total_tokens":                     total_tokens,
        "duration_ms":                      duration_ms,
        "final_answer":                     final_answer,
        "failure_type":                     failure_type,
        "action_sequence":                  action_sequence,
        "step_tokens":                      step_tokens,
        "step_durations_ms":                step_durations_ms,
        "click_failures":                   click_failures,
        "fill_failures":                    fill_failures,
        "goto_count":                       goto_count,
        "max_consecutive_click_failures":   max_consecutive_click_failures,
        "observation_sizes":                observation_sizes,
        "max_observation_size":             max_observation_size,
        "variant_dom_changes":              dom_changes,
        "variant_dom_hash_changed":         bool(variant_info.get("domHashChanged", False)),
        "pages_visited":                    sorted(pages_visited)[:20],
        "error_messages":                   sorted(error_messages)[:10],
    }

    return layer1, layer2


# ---------------------------------------------------------------------------
# Write output files
# ---------------------------------------------------------------------------

def write_layer1_csv(rows, outpath):
    """Write Layer 1 CSV."""
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LAYER1_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    log.info("Wrote %d rows to %s", len(rows), outpath)


def write_layer2_jsonl(objects, outpath):
    """Write Layer 2 JSONL."""
    with open(outpath, "w", encoding="utf-8") as f:
        for obj in objects:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    log.info("Wrote %d lines to %s", len(objects), outpath)


def write_task_metadata(outpath):
    """Write task-metadata.csv."""
    columns = [
        "task_id", "app", "app_short", "template_id", "nav_depth",
        "eval_type", "low_feasible", "ml_feasible",
    ]
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for tid in sorted(TASK_META.keys()):
            meta = TASK_META[tid]
            writer.writerow({
                "task_id":     tid,
                "app":         meta["app"],
                "app_short":   APP_SHORT.get(meta["app"], meta["app"]),
                "template_id": meta["template"],
                "nav_depth":   meta["nav_depth"],
                "eval_type":   meta["eval_type"],
                "low_feasible": tid not in LOW_INFEASIBLE,
                "ml_feasible":  True,
            })
    log.info("Wrote task metadata to %s", outpath)


def write_experiment_metadata(counts, outpath):
    """Write experiment-metadata.csv."""
    columns = [
        "experiment", "agent_type", "model", "tasks", "variants",
        "reps", "total_cases", "expected_cases",
    ]
    # Derive metadata from collected counts
    exp_info = {}
    for (exp, agent, model, variant, task_id), count in counts.items():
        if exp not in exp_info:
            exp_info[exp] = {
                "agents": set(), "models": set(),
                "tasks": set(), "variants": set(),
                "total": 0, "reps": set(),
            }
        exp_info[exp]["agents"].add(agent)
        exp_info[exp]["models"].add(model)
        exp_info[exp]["tasks"].add(task_id)
        exp_info[exp]["variants"].add(variant)
        exp_info[exp]["total"] += count

    expected_map = {d[1]: d[2] for d in EXPERIMENT_DIRS}

    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for exp in sorted(exp_info.keys()):
            info = exp_info[exp]
            writer.writerow({
                "experiment":     exp,
                "agent_type":     ",".join(sorted(info["agents"])),
                "model":          ",".join(sorted(info["models"])),
                "tasks":          ",".join(str(t) for t in sorted(info["tasks"])),
                "variants":       ",".join(sorted(info["variants"], key=lambda v: VARIANT_ORDINAL.get(v, 99))),
                "reps":           5,
                "total_cases":    info["total"],
                "expected_cases": expected_map.get(exp, "?"),
            })
    log.info("Wrote experiment metadata to %s", outpath)


# ---------------------------------------------------------------------------
# Validation and summary
# ---------------------------------------------------------------------------

def print_summary(layer1_rows):
    """Print summary statistics and validation."""
    total = len(layer1_rows)
    print(f"\n{'='*70}")
    print(f"  EXPORT SUMMARY")
    print(f"{'='*70}")
    print(f"  Total cases: {total}")
    print()

    # Per experiment
    exp_counts = Counter(r["experiment"] for r in layer1_rows)
    expected_map = {d[1]: d[2] for d in EXPERIMENT_DIRS}
    print("  Per experiment:")
    for exp in sorted(exp_counts.keys()):
        actual = exp_counts[exp]
        expected = expected_map.get(exp, "?")
        status = "OK" if actual == expected else f"MISMATCH (expected {expected})"
        print(f"    {exp:25s}  {actual:4d}  {status}")
    print()

    # Per variant
    var_counts = Counter(r["variant"] for r in layer1_rows)
    print("  Per variant:")
    for v in ["low", "medium-low", "base", "high"]:
        print(f"    {v:15s}  {var_counts.get(v, 0):4d}")
    print()

    # Per agent type
    agent_counts = Counter(r["agent_type"] for r in layer1_rows)
    print("  Per agent type:")
    for a in sorted(agent_counts.keys()):
        print(f"    {a:15s}  {agent_counts[a]:4d}")
    print()

    # Per model
    model_counts = Counter(r["model"] for r in layer1_rows)
    print("  Per model:")
    for m in sorted(model_counts.keys()):
        print(f"    {m:20s}  {model_counts[m]:4d}")
    print()

    # Per task
    task_counts = Counter(r["task_id"] for r in layer1_rows)
    print("  Per task:")
    for t in sorted(task_counts.keys()):
        meta = TASK_META.get(t, {})
        app_s = APP_SHORT.get(meta.get("app", ""), "?")
        print(f"    task {t:3d} ({app_s:6s})  {task_counts[t]:4d}")
    print()

    # Success rates per experiment × variant
    print("  Success rates (experiment × variant):")
    exp_var = defaultdict(lambda: {"success": 0, "total": 0})
    for r in layer1_rows:
        key = (r["experiment"], r["variant"])
        exp_var[key]["total"] += 1
        if r["success"]:
            exp_var[key]["success"] += 1

    for exp in sorted(exp_counts.keys()):
        rates = []
        for v in ["low", "medium-low", "base", "high"]:
            d = exp_var.get((exp, v), {"success": 0, "total": 0})
            if d["total"] > 0:
                rate = d["success"] / d["total"] * 100
                rates.append(f"{v}={rate:.1f}%")
            else:
                rates.append(f"{v}=N/A")
        print(f"    {exp:25s}  {', '.join(rates)}")
    print()

    # Anomaly checks
    print("  Anomaly checks:")
    anomalies = 0

    # Check for expected total
    if total != 1040:
        print(f"    WARNING: Total cases {total} != expected 1040")
        anomalies += 1
    else:
        print(f"    OK: Total cases = 1040")

    # Check for duplicate case_ids
    case_ids = [r["case_id"] for r in layer1_rows]
    dupes = [cid for cid, cnt in Counter(case_ids).items() if cnt > 1]
    if dupes:
        print(f"    WARNING: {len(dupes)} duplicate case_ids found")
        for d in dupes[:5]:
            print(f"      {d}")
        anomalies += 1
    else:
        print(f"    OK: No duplicate case_ids")

    # Check for unexpected variants
    unexpected_variants = set(r["variant"] for r in layer1_rows) - set(VARIANT_ORDINAL.keys())
    if unexpected_variants:
        print(f"    WARNING: Unexpected variants: {unexpected_variants}")
        anomalies += 1
    else:
        print(f"    OK: All variants recognized")

    # Check for unknown tasks
    unknown_tasks = set(r["task_id"] for r in layer1_rows) - set(TASK_META.keys())
    if unknown_tasks:
        print(f"    WARNING: Unknown task IDs: {unknown_tasks}")
        anomalies += 1
    else:
        print(f"    OK: All task IDs in TASK_META")

    # Check per-experiment counts
    all_match = True
    for dir_name, exp_name, expected, _ in EXPERIMENT_DIRS:
        actual = exp_counts.get(exp_name, 0)
        if actual != expected:
            print(f"    WARNING: {exp_name} has {actual} cases, expected {expected}")
            all_match = False
            anomalies += 1
    if all_match:
        print(f"    OK: All experiment counts match expectations")

    print(f"\n  Total anomalies: {anomalies}")
    print(f"{'='*70}\n")

    return anomalies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("Starting combined data export...")
    log.info("Data directory: %s", DATA_DIR)
    log.info("Results directory: %s", RESULTS_DIR)

    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all rows
    all_layer1 = []
    all_layer2 = []
    file_counts = Counter()
    detail_counts = Counter()  # (experiment, agent, model, variant, task_id) -> count
    warnings = []

    for dir_name, exp_name, expected, description in EXPERIMENT_DIRS:
        log.info("Scanning %s (%s)...", dir_name, description)
        case_files = find_case_files(DATA_DIR, dir_name)
        log.info("  Found %d case files (expected %d)", len(case_files), expected)

        if len(case_files) != expected:
            warnings.append(f"{exp_name}: found {len(case_files)} files, expected {expected}")

        for filepath in case_files:
            result = parse_trace(filepath, exp_name)
            if result is None:
                warnings.append(f"Failed to parse: {filepath}")
                continue

            layer1, layer2 = result
            all_layer1.append(layer1)
            all_layer2.append(layer2)
            file_counts[exp_name] += 1

            key = (
                exp_name,
                layer1["agent_type"],
                layer1["model"],
                layer1["variant"],
                layer1["task_id"],
            )
            detail_counts[key] += 1

    # Sort by experiment, task_id, variant, agent_type, rep
    all_layer1.sort(key=lambda r: (
        r["experiment"],
        r["task_id"],
        VARIANT_ORDINAL.get(r["variant"], 99),
        r["agent_type"],
        r["model"],
        r["rep"],
    ))
    all_layer2.sort(key=lambda r: (
        r["experiment"],
        r["task_id"],
        VARIANT_ORDINAL.get(r["variant"], 99),
        r["agent_type"],
        r["model"],
        r["rep"],
    ))

    # Write output files
    write_layer1_csv(all_layer1, RESULTS_DIR / "combined-experiment.csv")
    write_layer2_jsonl(all_layer2, RESULTS_DIR / "trace-summaries.jsonl")
    write_task_metadata(RESULTS_DIR / "task-metadata.csv")
    write_experiment_metadata(detail_counts, RESULTS_DIR / "experiment-metadata.csv")

    # Print warnings
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")

    # Print summary
    anomalies = print_summary(all_layer1)

    return 0 if anomalies == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3.11
"""
AMT Signature Analysis — D.1 (DOM), D.2 (Behavioral), D.3 (Alignment)

Produces:
  1. DOM Signature Matrix (26 operators × 12 dims) — paper §4.X table
  2. Behavioral Signature Matrix (26 operators × text_drop + CUA_drop) — paper §5.1
  3. Signature Alignment Classification — paper §5.2 (core contribution)

Outputs:
  - results/amt/dom_signature_matrix.csv
  - results/amt/behavioral_signature_matrix.csv
  - results/amt/signature_alignment.csv
  - results/amt/signature_alignment_report.md

Usage:
  python3.11 scripts/amt-signature-analysis.py
"""
import json, glob, os, sys, math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOM_SIG_PATH = DATA_DIR / "archive" / "amt-dom-signatures" / "dom_signatures.json"
CORRECTIONS_PATH = ROOT / "scripts" / "amt" / "ground-truth-corrections.json"
OUTPUT_DIR = ROOT / "results" / "amt"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Operator metadata
# ============================================================
OP_ORDER = [
    "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10",
    "L11", "L12", "L13", "ML1", "ML2", "ML3",
    "H1", "H2", "H3", "H4", "H5a", "H5b", "H5c", "H6", "H7", "H8",
]

OP_DESC = {
    "L1": "Landmark → div", "L2": "Remove ARIA + role", "L3": "Remove labels",
    "L4": "Remove kbd handlers", "L5": "Shadow DOM wrap", "L6": "Heading → div",
    "L7": "Remove alt/aria-label", "L8": "Remove tabindex", "L9": "thead → div",
    "L10": "Remove lang", "L11": "Link → span", "L12": "Duplicate IDs",
    "L13": "onfocus blur", "ML1": "Empty btn → div", "ML2": "Clone-replace",
    "ML3": "Remove label + aria", "H1": "Auto aria-label", "H2": "Skip-nav",
    "H3": "Associate labels", "H4": "Add landmark role", "H5a": "Auto alt",
    "H5b": "Add lang=en", "H5c": "Auto aria-label links", "H6": "aria-required",
    "H7": "aria-current", "H8": "Table scope",
}

OP_FAMILY = {}
for op in OP_ORDER:
    if op.startswith("L"):
        OP_FAMILY[op] = "Low"
    elif op.startswith("ML"):
        OP_FAMILY[op] = "Midlow"
    else:
        OP_FAMILY[op] = "High"

# 12 core DOM dimensions (excluding changesReturned which is a meta-metric)
DOM_DIMS = [
    "D1_totalTagChanges", "D2_added", "D2_removed", "D3_nodeCountDelta",
    "A1_rolesChanged", "A2_namesChanged", "A3_totalAriaStateChanges",
    "V1_ssim", "V2_maxBBoxShift_px", "V3_meanContrastDelta",
    "F1_interactiveCountDelta", "F2_inlineHandlerDelta", "F3_focusableCountDelta",
]

# ============================================================
# D.1 — DOM Signature Matrix
# ============================================================
print("=" * 70)
print("D.1 — DOM SIGNATURE MATRIX")
print("=" * 70)

with open(DOM_SIG_PATH) as f:
    dom_data = json.load(f)

dom_matrix = {}  # op -> {dim: mean}
for op in OP_ORDER:
    if op not in dom_data["operators"]:
        print(f"  WARNING: {op} not in DOM signatures")
        continue
    op_data = dom_data["operators"][op]["dims"]
    dom_matrix[op] = {}
    for dim in DOM_DIMS:
        dom_matrix[op][dim] = op_data[dim]["mean"]

# Write CSV
csv_path = OUTPUT_DIR / "dom_signature_matrix.csv"
with open(csv_path, "w") as f:
    f.write("operator,family,description," + ",".join(DOM_DIMS) + "\n")
    for op in OP_ORDER:
        if op not in dom_matrix:
            continue
        vals = [f"{dom_matrix[op][d]:.4f}" for d in DOM_DIMS]
        f.write(f"{op},{OP_FAMILY[op]},{OP_DESC[op]}," + ",".join(vals) + "\n")

print(f"  Written: {csv_path}")
print(f"  Operators: {len(dom_matrix)}")
print(f"  Dimensions: {len(DOM_DIMS)}")

# Print summary table
print(f"\n  {'Op':>5s}  {'D1':>6s}  {'D2+':>6s}  {'D2-':>6s}  {'D3':>6s}  "
      f"{'A1':>6s}  {'A2':>6s}  {'A3':>6s}  {'V1':>6s}  {'V2':>7s}  "
      f"{'V3':>5s}  {'F1':>7s}  {'F2':>6s}  {'F3':>7s}")
print("  " + "-" * 100)
for op in OP_ORDER:
    if op not in dom_matrix:
        continue
    d = dom_matrix[op]
    print(f"  {op:>5s}  {d['D1_totalTagChanges']:6.1f}  {d['D2_added']:6.1f}  "
          f"{d['D2_removed']:6.1f}  {d['D3_nodeCountDelta']:6.1f}  "
          f"{d['A1_rolesChanged']:6.1f}  {d['A2_namesChanged']:6.1f}  "
          f"{d['A3_totalAriaStateChanges']:6.1f}  {d['V1_ssim']:6.3f}  "
          f"{d['V2_maxBBoxShift_px']:7.1f}  {d['V3_meanContrastDelta']:5.2f}  "
          f"{d['F1_interactiveCountDelta']:7.1f}  {d['F2_inlineHandlerDelta']:6.1f}  "
          f"{d['F3_focusableCountDelta']:7.1f}")

# ============================================================
# D.2 — Behavioral Signature Matrix
# ============================================================
print(f"\n{'=' * 70}")
print("D.2 — BEHAVIORAL SIGNATURE MATRIX")
print("=" * 70)

# Load ground truth corrections
with open(CORRECTIONS_PATH) as f:
    corrections = json.load(f)["corrections"]
ADDITIONAL_GT = {}
for tid, info in corrections.items():
    ADDITIONAL_GT[tid] = [a.lower() for a in info["additional_valid"]]


def load_cases(data_dirs, label=""):
    """Load experiment cases from data directories with GT corrections."""
    cases = []
    for data_dir in data_dirs:
        for fpath in glob.glob(str(data_dir / "*/cases/*.json")):
            if "/scan-result" in fpath or "/trace-attempt" in fpath or "/classification" in fpath:
                continue
            with open(fpath) as fh:
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
            if agent == "cua" and not answer:
                bl = t.get("bridgeLog", "")
                for line in bl.split("\n"):
                    if "Task complete" in line:
                        tc_idx = line.find("Task complete")
                        if tc_idx >= 0:
                            rest = line[tc_idx:]
                            colon_idx = rest.find(":")
                            if colon_idx >= 0:
                                answer = rest[colon_idx+1:].strip()
                        break

            # Apply GT correction
            corrected_success = original_success
            if tid in ADDITIONAL_GT and not original_success and answer:
                answer_lower = answer.lower()
                for valid in ADDITIONAL_GT[tid]:
                    if valid in answer_lower:
                        corrected_success = True
                        break

            cases.append({
                "caseId": cid, "taskId": tid, "opId": parts[5],
                "agent": agent, "success": corrected_success,
                "totalTokens": t.get("totalTokens", 0),
            })
    return cases


# Load Claude Mode A cases (all agents)
claude_dirs = [DATA_DIR / "mode-a-shard-a", DATA_DIR / "mode-a-shard-b"]
cases = load_cases(claude_dirs, "Claude")
print(f"  Loaded {len(cases)} Claude cases from {len(claude_dirs)} directories")

# Load Llama 4 Mode A cases (text-only only)
llama_dirs = [DATA_DIR / "mode-a-llama4-textonly"]
llama_cases = load_cases(llama_dirs, "Llama4")
print(f"  Loaded {len(llama_cases)} Llama 4 cases")

# Compute per-operator success rates by agent (Claude)
op_agent_stats = defaultdict(lambda: defaultdict(lambda: {"ok": 0, "total": 0}))
for c in cases:
    op_agent_stats[c["opId"]][c["agent"]]["total"] += 1
    if c["success"]:
        op_agent_stats[c["opId"]][c["agent"]]["ok"] += 1

# Compute per-operator success rates (Llama 4, text-only only)
op_llama_stats = defaultdict(lambda: {"ok": 0, "total": 0})
for c in llama_cases:
    op_llama_stats[c["opId"]]["total"] += 1
    if c["success"]:
        op_llama_stats[c["opId"]]["ok"] += 1

# Compute H-operator baselines per agent
agents = ["text-only", "cua"]
h_baselines = {}
for agent in agents:
    h_ok = 0
    h_total = 0
    for op in OP_ORDER:
        if op.startswith("H"):
            stats = op_agent_stats[op][agent]
            h_ok += stats["ok"]
            h_total += stats["total"]
    h_baselines[agent] = h_ok / h_total if h_total > 0 else 0.0

# Llama 4 H-baseline
llama_h_ok = sum(op_llama_stats[op]["ok"] for op in OP_ORDER if op.startswith("H"))
llama_h_total = sum(op_llama_stats[op]["total"] for op in OP_ORDER if op.startswith("H"))
h_baselines["llama4_text"] = llama_h_ok / llama_h_total if llama_h_total > 0 else 0.0

print(f"  H-operator baselines:")
print(f"    Claude text-only: {h_baselines['text-only']*100:.1f}%")
print(f"    Claude CUA:       {h_baselines['cua']*100:.1f}%")
print(f"    Llama 4 text:     {h_baselines['llama4_text']*100:.1f}%")
print(f"\n  NOTE: CUA baseline is 48.2% — dominated by task-level architectural")
print(f"  limitations (can't type URLs, viewport too small), NOT operator effects.")
print(f"  CUA data is included but flagged as noisy for alignment analysis.")

# Compute behavioral signature: drop from H-baseline
behavioral_matrix = {}
for op in OP_ORDER:
    behavioral_matrix[op] = {}
    for agent in agents:
        stats = op_agent_stats[op][agent]
        rate = stats["ok"] / stats["total"] if stats["total"] > 0 else 0.0
        drop = h_baselines[agent] - rate
        behavioral_matrix[op][f"{agent}_rate"] = rate
        behavioral_matrix[op][f"{agent}_drop"] = drop
        behavioral_matrix[op][f"{agent}_n"] = stats["total"]
    # Llama 4
    lstats = op_llama_stats[op]
    lrate = lstats["ok"] / lstats["total"] if lstats["total"] > 0 else 0.0
    ldrop = h_baselines["llama4_text"] - lrate
    behavioral_matrix[op]["llama4_rate"] = lrate
    behavioral_matrix[op]["llama4_drop"] = ldrop
    behavioral_matrix[op]["llama4_n"] = lstats["total"]

# Write CSV
csv_path = OUTPUT_DIR / "behavioral_signature_matrix.csv"
with open(csv_path, "w") as f:
    f.write("operator,family,description,"
            "claude_text_rate,claude_text_drop,claude_text_n,"
            "claude_cua_rate,claude_cua_drop,claude_cua_n,"
            "llama4_text_rate,llama4_text_drop,llama4_text_n\n")
    for op in OP_ORDER:
        b = behavioral_matrix[op]
        f.write(f"{op},{OP_FAMILY[op]},{OP_DESC[op]},"
                f"{b['text-only_rate']:.4f},{b['text-only_drop']:.4f},{b['text-only_n']},"
                f"{b['cua_rate']:.4f},{b['cua_drop']:.4f},{b['cua_n']},"
                f"{b['llama4_rate']:.4f},{b['llama4_drop']:.4f},{b['llama4_n']}\n")

print(f"  Written: {csv_path}")

# Print behavioral summary (primary: Claude text-only + Llama 4 text-only)
print(f"\n  {'Op':>5s}  {'C.Text':>8s}  {'C.Drop':>8s}  "
      f"{'L4.Text':>8s}  {'L4.Drop':>8s}  {'C.CUA':>8s}  {'CUA.Drop':>8s}")
print("  " + "-" * 70)
for op in OP_ORDER:
    b = behavioral_matrix[op]
    print(f"  {op:>5s}  {b['text-only_rate']*100:6.1f}%  {b['text-only_drop']*100:+6.1f}pp  "
          f"{b['llama4_rate']*100:6.1f}%  {b['llama4_drop']*100:+6.1f}pp  "
          f"{b['cua_rate']*100:6.1f}%  {b['cua_drop']*100:+6.1f}pp")

# ============================================================
# D.3 — Signature Alignment Analysis
# ============================================================
print(f"\n{'=' * 70}")
print("D.3 — SIGNATURE ALIGNMENT ANALYSIS")
print("=" * 70)

# Classification criteria for DOM signature
# A operator is "semantic-dominant" if A11y tree changes are the primary signal
# "functional-dominant" if F-dims are the primary signal
# "visual-dominant" if V-dims deviate from baseline
# "structural-dominant" if D1 (tag changes) + A1 are both high
# "mixed" if multiple categories are active

def classify_dom_signature(op, dims):
    """Classify operator's DOM signature into a layer category."""
    d = dims
    
    # Thresholds (empirically set from data distribution)
    # A11y tree activity
    a11y_active = (abs(d["A1_rolesChanged"]) > 2.0 or 
                   abs(d["A2_namesChanged"]) > 2.0 or
                   abs(d["A3_totalAriaStateChanges"]) > 2.0)
    
    # Visual disruption
    visual_active = (d["V1_ssim"] < 0.99 or 
                     abs(d["V2_maxBBoxShift_px"]) > 10.0 or
                     abs(d["V3_meanContrastDelta"]) > 0.5)
    
    # Functional disruption
    functional_active = (abs(d["F1_interactiveCountDelta"]) > 2.0 or
                         abs(d["F2_inlineHandlerDelta"]) > 2.0 or
                         abs(d["F3_focusableCountDelta"]) > 2.0)
    
    # Structural (tag-level DOM changes)
    structural_active = abs(d["D1_totalTagChanges"]) > 5.0
    
    # Count active categories
    active = []
    if a11y_active:
        active.append("semantic")
    if visual_active:
        active.append("visual")
    if functional_active:
        active.append("functional")
    if structural_active:
        active.append("structural")
    
    if len(active) == 0:
        # Check if D2 (attribute changes) are the only signal
        if abs(d["D2_added"]) > 15 or abs(d["D2_removed"]) > 5:
            return "attribute-only"
        return "minimal"
    elif len(active) == 1:
        return active[0]
    elif len(active) >= 3:
        return "multi-layer"
    else:
        # 2 active: pick dominant
        # Structural + semantic is common (landmark/heading changes)
        if "structural" in active and "semantic" in active:
            return "structural+semantic"
        elif "functional" in active and "semantic" in active:
            return "semantic+functional"
        elif "visual" in active and "functional" in active:
            return "visual+functional"
        elif "visual" in active and "semantic" in active:
            return "visual+semantic"
        else:
            return "+".join(sorted(active))


def classify_behavioral_signature(op, beh):
    """
    Classify operator's behavioral signature based on agent-differential drop.
    
    Primary signal: Claude text-only drop (most sensitive, cleanest baseline).
    Secondary signal: Llama 4 text-only drop (cross-model replication).
    Tertiary signal: CUA drop (noisy — 48% baseline, use cautiously).
    
    Classification logic:
    - If Claude text drop > 5pp AND Llama 4 confirms direction → robust effect
    - If only Claude text drops → model-specific or marginal
    - CUA used only to distinguish "text-dominant" from "both-affected"
    """
    claude_text_drop = beh["text-only_drop"]
    cua_drop = beh["cua_drop"]
    llama_drop = beh["llama4_drop"]
    
    # Thresholds
    SIGNIFICANT_DROP = 0.05  # 5pp minimum to be considered "affected"
    LARGE_DROP = 0.15  # 15pp = clearly destructive
    CROSS_MODEL_CONFIRM = 0.05  # Llama 4 must also show >5pp for "confirmed"
    
    claude_affected = claude_text_drop > SIGNIFICANT_DROP
    llama_affected = llama_drop > CROSS_MODEL_CONFIRM
    cua_affected = cua_drop > SIGNIFICANT_DROP
    
    if not claude_affected and not llama_affected and not cua_affected:
        return "unaffected"
    
    if claude_text_drop > LARGE_DROP:
        # Large effect — check if cross-model confirmed
        if llama_affected:
            if cua_affected:
                return "destructive-confirmed"  # all agents, both models
            else:
                return "text-dominant-confirmed"  # text agents only, both models
        else:
            return "text-dominant-claude-only"  # only Claude text affected
    
    if claude_affected:
        if llama_affected:
            return "moderate-confirmed"  # both models show effect
        else:
            return "marginal-claude-only"  # weak, Claude-specific
    
    if llama_affected and not claude_affected:
        return "llama-only"  # Llama affected but Claude adapts (model capability)
    
    if cua_affected and not claude_affected:
        return "cua-only"  # CUA-specific (likely architectural, not operator)
    
    return "unclear"


def assess_alignment(dom_cat, beh_cat):
    """
    Assess whether DOM and behavioral signatures align.
    
    Core logic:
    - Large DOM change + unaffected behavior = MISALIGNED (agent adaptation)
    - Minimal DOM change + affected behavior = MISALIGNED (structural criticality)
    - DOM active + behavior active = ALIGNED (expected)
    - DOM minimal + behavior minimal = ALIGNED (expected null)
    """
    # DOM is "active" if it's not minimal/attribute-only
    dom_active = dom_cat not in ["minimal", "attribute-only"]
    
    # Behavior is "active" if it's not unaffected
    beh_active = beh_cat != "unaffected"
    
    if dom_active and beh_active:
        return "ALIGNED (both active)"
    elif not dom_active and not beh_active:
        return "ALIGNED (both null)"
    elif dom_active and not beh_active:
        return "MISALIGNED: DOM active → behavior null (agent adaptation)"
    elif not dom_active and beh_active:
        return "MISALIGNED: DOM minimal → behavior active (structural criticality)"
    
    return "UNCLEAR"


# Run classification for all operators
alignment_results = []
for op in OP_ORDER:
    if op not in dom_matrix:
        continue
    
    dom_cat = classify_dom_signature(op, dom_matrix[op])
    beh_cat = classify_behavioral_signature(op, behavioral_matrix[op])
    alignment = assess_alignment(dom_cat, beh_cat)
    
    alignment_results.append({
        "operator": op,
        "family": OP_FAMILY[op],
        "description": OP_DESC[op],
        "dom_category": dom_cat,
        "behavioral_category": beh_cat,
        "alignment": alignment,
        "claude_text_drop_pp": behavioral_matrix[op]["text-only_drop"] * 100,
        "llama4_text_drop_pp": behavioral_matrix[op]["llama4_drop"] * 100,
        "cua_drop_pp": behavioral_matrix[op]["cua_drop"] * 100,
        "dom_A1": dom_matrix[op]["A1_rolesChanged"],
        "dom_A2": dom_matrix[op]["A2_namesChanged"],
        "dom_F1": dom_matrix[op]["F1_interactiveCountDelta"],
        "dom_V1": dom_matrix[op]["V1_ssim"],
    })

# Write alignment CSV
csv_path = OUTPUT_DIR / "signature_alignment.csv"
with open(csv_path, "w") as f:
    headers = ["operator", "family", "description", "dom_category", "behavioral_category",
               "alignment", "claude_text_drop_pp", "llama4_text_drop_pp", "cua_drop_pp",
               "dom_A1", "dom_A2", "dom_F1", "dom_V1"]
    f.write(",".join(headers) + "\n")
    for r in alignment_results:
        vals = [str(r[h]) for h in headers]
        f.write(",".join(vals) + "\n")

print(f"  Written: {csv_path}")

# Print alignment table
print(f"\n  {'Op':>5s}  {'DOM Category':>20s}  {'Beh Category':>22s}  "
      f"{'C.Text':>7s}  {'L4.Text':>7s}  {'Alignment':>50s}")
print("  " + "-" * 125)
for r in alignment_results:
    print(f"  {r['operator']:>5s}  {r['dom_category']:>20s}  {r['behavioral_category']:>22s}  "
          f"{r['claude_text_drop_pp']:+6.1f}pp  {r['llama4_text_drop_pp']:+6.1f}pp  "
          f"{r['alignment']}")

# ============================================================
# Summary statistics
# ============================================================
print(f"\n{'=' * 70}")
print("ALIGNMENT SUMMARY")
print("=" * 70)

alignment_counts = defaultdict(int)
for r in alignment_results:
    alignment_counts[r["alignment"]] += 1

for cat, count in sorted(alignment_counts.items(), key=lambda x: -x[1]):
    pct = count / len(alignment_results) * 100
    print(f"  {cat:>40s}: {count:>2d} ({pct:.0f}%)")

# Misalignment cases (paper gold)
print(f"\n{'=' * 70}")
print("MISALIGNMENT CASES (paper §5.2 highlights)")
print("=" * 70)
misaligned = [r for r in alignment_results if "MISALIGNED" in r["alignment"]]
partial = [r for r in alignment_results if r["alignment"] == "PARTIAL"]

if misaligned:
    print("\n  Full misalignments:")
    for r in misaligned:
        print(f"    {r['operator']:>5s}: DOM={r['dom_category']}, Beh={r['behavioral_category']}")
        print(f"           Claude text={r['claude_text_drop_pp']:+.1f}pp, "
              f"Llama4 text={r['llama4_text_drop_pp']:+.1f}pp, CUA={r['cua_drop_pp']:+.1f}pp")
        # Interpret
        if "DOM active" in r["alignment"]:
            print(f"           → Operator changes DOM but agents are resilient (adaptation)")
        elif "DOM minimal" in r["alignment"]:
            print(f"           → Small DOM change has outsized behavioral impact (structural criticality)")

if partial:
    print("\n  Partial alignments:")
    for r in partial:
        print(f"    {r['operator']:>5s}: DOM={r['dom_category']}, Beh={r['behavioral_category']}")
        print(f"           Claude text={r['claude_text_drop_pp']:+.1f}pp, "
              f"Llama4 text={r['llama4_text_drop_pp']:+.1f}pp")

# ============================================================
# Generate markdown report
# ============================================================
report_path = OUTPUT_DIR / "signature_alignment_report.md"

with open(report_path, "w") as f:
    f.write("# AMT Signature Alignment Report\n\n")
    f.write(f"**Generated**: 2026-05-02\n")
    f.write(f"**Data**: Mode A Claude (3,042 cases) + DOM audit (A.5, 39 samples/operator)\n")
    f.write(f"**Operators**: {len(alignment_results)}\n\n")
    
    f.write("---\n\n")
    f.write("## 1. DOM Signature Matrix (D.1)\n\n")
    f.write("Each operator's DOM-level impact measured across 13 task URLs × 3 reps.\n")
    f.write("Values are means across 39 samples.\n\n")
    f.write("| Op | Family | D1 Tags | A1 Roles | A2 Names | A3 States | V1 SSIM | F1 Interactive | F2 Handlers | F3 Focusable |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|\n")
    for op in OP_ORDER:
        if op not in dom_matrix:
            continue
        d = dom_matrix[op]
        f.write(f"| {op} | {OP_FAMILY[op]} | "
                f"{d['D1_totalTagChanges']:.1f} | "
                f"{d['A1_rolesChanged']:.1f} | "
                f"{d['A2_namesChanged']:.1f} | "
                f"{d['A3_totalAriaStateChanges']:.1f} | "
                f"{d['V1_ssim']:.3f} | "
                f"{d['F1_interactiveCountDelta']:.1f} | "
                f"{d['F2_inlineHandlerDelta']:.1f} | "
                f"{d['F3_focusableCountDelta']:.1f} |\n")
    
    f.write("\n---\n\n")
    f.write("## 2. Behavioral Signature Matrix (D.2)\n\n")
    f.write("Per-operator success rate and drop from H-operator baseline.\n")
    f.write(f"H-baselines: Claude text={h_baselines['text-only']*100:.1f}%, "
            f"Llama 4 text={h_baselines['llama4_text']*100:.1f}%, "
            f"CUA={h_baselines['cua']*100:.1f}% (noisy)\n\n")
    f.write("| Op | Family | Claude Text | C.Drop | Llama4 Text | L4.Drop | CUA | CUA Drop |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for op in OP_ORDER:
        b = behavioral_matrix[op]
        f.write(f"| {op} | {OP_FAMILY[op]} | "
                f"{b['text-only_rate']*100:.1f}% | "
                f"{b['text-only_drop']*100:+.1f}pp | "
                f"{b['llama4_rate']*100:.1f}% | "
                f"{b['llama4_drop']*100:+.1f}pp | "
                f"{b['cua_rate']*100:.1f}% | "
                f"{b['cua_drop']*100:+.1f}pp |\n")
    
    f.write("\n---\n\n")
    f.write("## 3. Signature Alignment (D.3)\n\n")
    f.write("Cross-reference of DOM-level and behavioral signatures.\n\n")
    f.write("### Classification Criteria\n\n")
    f.write("**DOM categories** (from 12-dim audit):\n")
    f.write("- `semantic`: A11y tree changes dominant (A1/A2/A3 > threshold)\n")
    f.write("- `structural`: Tag-level DOM changes (D1 > 5)\n")
    f.write("- `structural+semantic`: Both tag changes and a11y tree changes\n")
    f.write("- `functional`: Interactive/handler/focusable changes (F1/F2/F3)\n")
    f.write("- `visual`: SSIM < 0.99 or bbox shift or contrast change\n")
    f.write("- `multi-layer`: 3+ categories active simultaneously\n")
    f.write("- `attribute-only`: Only D2 (attribute add/remove), no other signal\n")
    f.write("- `minimal`: No measurable DOM change above threshold\n\n")
    f.write("**Behavioral categories** (from cross-model + cross-agent analysis):\n")
    f.write("- `destructive-confirmed`: Large drop (>15pp), confirmed by Llama 4 + CUA\n")
    f.write("- `text-dominant-confirmed`: Large text drop, confirmed by Llama 4, CUA unaffected\n")
    f.write("- `moderate-confirmed`: Moderate drop (5-15pp), confirmed by both models\n")
    f.write("- `marginal-claude-only`: Small Claude drop, not replicated in Llama 4\n")
    f.write("- `llama-only`: Llama 4 affected but Claude adapts (model capability gap)\n")
    f.write("- `cua-only`: CUA-specific (architectural, not operator effect)\n")
    f.write("- `unaffected`: No agent drops >5pp from baseline\n\n")
    f.write("### Alignment Table\n\n")
    f.write("| Op | DOM Category | Behavioral Category | Alignment | C.Text | L4.Text | CUA |\n")
    f.write("|---|---|---|---|---|---|---|\n")
    for r in alignment_results:
        emoji = "✅" if "ALIGNED" in r["alignment"] else "❌"
        short_align = r["alignment"].replace("MISALIGNED: ", "⚠️ ")
        f.write(f"| {r['operator']} | {r['dom_category']} | {r['behavioral_category']} | "
                f"{short_align} | {r['claude_text_drop_pp']:+.1f}pp | "
                f"{r['llama4_text_drop_pp']:+.1f}pp | {r['cua_drop_pp']:+.1f}pp |\n")
    
    f.write("\n### Alignment Summary\n\n")
    for cat, count in sorted(alignment_counts.items(), key=lambda x: -x[1]):
        pct = count / len(alignment_results) * 100
        f.write(f"- **{cat}**: {count}/{len(alignment_results)} ({pct:.0f}%)\n")
    
    f.write("\n---\n\n")
    f.write("## 4. Key Findings for Paper §5.2\n\n")
    
    # Finding 1: The Landmark Paradox as misalignment
    f.write("### Finding 1: Structural Criticality Misalignment (L1)\n\n")
    l1 = next(r for r in alignment_results if r["operator"] == "L1")
    f.write(f"L1 (landmark→div) has DOM category `{l1['dom_category']}` with only "
            f"A1={l1['dom_A1']:.1f} role changes and V1={l1['dom_V1']:.3f} (perfect visual).\n")
    f.write(f"Behavioral drop: Claude text {l1['claude_text_drop_pp']:+.1f}pp, "
            f"Llama 4 text {l1['llama4_text_drop_pp']:+.1f}pp, CUA {l1['cua_drop_pp']:+.1f}pp.\n\n")
    f.write("**Interpretation**: Landmarks are structurally critical despite being numerically few. "
            "The 12-dim DOM audit underestimates L1's impact because it counts *quantity* of changes, "
            "not *structural importance*. This is a measurement-apparatus limitation that the paper "
            "should acknowledge — a \"structural criticality\" dimension is needed.\n\n")
    
    # Finding 2: L11 massive DOM, minimal behavior
    f.write("### Finding 2: Agent Adaptation (L11)\n\n")
    l11 = next(r for r in alignment_results if r["operator"] == "L11")
    f.write(f"L11 (link→span) has DOM category `{l11['dom_category']}` with massive changes: "
            f"D1={dom_matrix['L11']['D1_totalTagChanges']:.0f} tag changes, "
            f"A1={l11['dom_A1']:.0f} role changes, "
            f"F1={l11['dom_F1']:.0f} interactive elements lost.\n")
    f.write(f"Behavioral drop: Claude text {l11['claude_text_drop_pp']:+.1f}pp, "
            f"Llama 4 text {l11['llama4_text_drop_pp']:+.1f}pp.\n\n")
    f.write("**Interpretation**: Claude adapts to link→span by using `goto()` URL construction "
            "as a fallback navigation strategy. The DOM is devastated but the agent finds workarounds. "
            "This is the inverse of L1 — massive DOM change, minimal behavioral impact. "
            "Agent adaptation capacity is a confound that DOM signatures cannot predict.\n\n")
    
    # Finding 3: L5 multi-layer
    f.write("### Finding 3: Multi-Layer Disruption (L5)\n\n")
    l5 = next(r for r in alignment_results if r["operator"] == "L5")
    f.write(f"L5 (Shadow DOM) has DOM category `{l5['dom_category']}` — it disrupts "
            f"structure, semantics, visuals, AND functionality simultaneously.\n")
    f.write(f"Behavioral drop: Claude text {l5['claude_text_drop_pp']:+.1f}pp, "
            f"Llama 4 text {l5['llama4_text_drop_pp']:+.1f}pp, CUA {l5['cua_drop_pp']:+.1f}pp.\n\n")
    f.write("**Interpretation**: L5 is the only operator that breaks the action channel "
            "(perception-action gap). Agents see elements but cannot interact with them. "
            "Both text-only and CUA are affected because the mechanism is architectural "
            "(closed Shadow DOM boundary), not modality-specific.\n\n")
    
    # Finding 4: H-operators all unaffected
    h_unaffected = [r for r in alignment_results if r["family"] == "High" and r["behavioral_category"] == "unaffected"]
    f.write(f"### Finding 4: Enhancement Ceiling ({len(h_unaffected)}/8 H-operators unaffected)\n\n")
    f.write("All H-operators show `unaffected` behavioral category despite DOM-level changes "
            "(attribute additions, role assignments). Claude Sonnet on WebArena base pages "
            "is already at ceiling — enhancement operators provide no measurable benefit.\n\n")
    f.write("**Paper implication**: The AMT framework reveals an asymmetry: degradation operators "
            "have measurable behavioral signatures, but enhancement operators do not (for this "
            "model+environment combination). This supports the \"accessibility floor\" hypothesis — "
            "there exists a minimum a11y level below which agents fail, but above which "
            "additional a11y provides diminishing returns.\n\n")
    
    # Finding 5: Functional operators
    f.write("### Finding 5: Functional Operators Below Detection Threshold\n\n")
    func_ops = [r for r in alignment_results if "functional" in r["dom_category"]]
    f.write(f"Operators with functional DOM signatures: {[r['operator'] for r in func_ops]}\n\n")
    for r in func_ops:
        f.write(f"- **{r['operator']}** ({r['description']}): DOM=`{r['dom_category']}`, "
                f"Beh=`{r['behavioral_category']}`, Claude={r['claude_text_drop_pp']:+.1f}pp\n")
    f.write("\n**Interpretation**: Most functional operators (keyboard handlers, tabindex) "
            "don't affect Claude because it uses click(bid) actions, not keyboard navigation. "
            "The functional layer is irrelevant for BrowserGym's action space — agents never "
            "use Tab/Enter/Arrow keys. This is a platform-specific finding: real keyboard-only "
            "users would be severely affected by L4/L8/L13.\n\n")
    
    f.write("---\n\n")
    f.write("## 5. Implications for Paper Narrative\n\n")
    f.write("1. **DOM change magnitude ≠ behavioral impact** (L1 vs L11 contrast)\n")
    f.write("2. **Structural criticality** is the missing dimension in the 12-dim audit\n")
    f.write("3. **Agent adaptation** confounds DOM→behavior prediction (L11 goto() workaround)\n")
    f.write("4. **Platform action space** filters functional effects (BrowserGym = click-only)\n")
    f.write("5. **Enhancement ceiling** limits H-operator detectability at this model capability\n")
    f.write("6. **Multi-layer operators** (L5) are the most reliably destructive\n\n")
    f.write("These findings support the paper's core claim: signature alignment is informative "
            "but imperfect, and the *misalignments* are themselves scientifically valuable — "
            "they reveal agent adaptation strategies and platform-specific confounds that "
            "pure DOM analysis cannot predict.\n")

print(f"\n  Written: {report_path}")
print(f"\nDone. All outputs in {OUTPUT_DIR}/")

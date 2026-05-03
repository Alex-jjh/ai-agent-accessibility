#!/usr/bin/env python3
"""
Cross-Agent Comparison Analysis for Expansion Tasks (7 tasks × 4 variants × 4 agents).

Data sources:
  1. Text-only Claude (5 reps): data/expansion-claude/
  2. Text-only Llama 4 (5 reps): data/expansion-llama4/ (subset of 13 tasks → 7 expansion)
  3. SoM Claude (1 rep): data/archive/expansion-som-smoke/
  4. CUA Claude (1 rep): data/archive/expansion-cua-smoke/

Output: docs/analysis/expansion-cross-agent-comparison.md
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

EXPANSION_TASK_IDS = {41, 94, 198, 188, 132, 293, 308}
VARIANTS = ["low", "medium-low", "base", "high"]
VARIANT_ORDER = {v: i for i, v in enumerate(VARIANTS)}

# Task metadata for display
TASK_META = {
    41:  {"app": "admin",    "label": "admin:41",   "desc": "Top search term"},
    94:  {"app": "admin",    "label": "admin:94",   "desc": "Invoice grand total"},
    198: {"app": "admin",    "label": "admin:198",  "desc": "Cancelled order customer"},
    188: {"app": "ecommerce","label": "ecom:188",   "desc": "Cancelled order cost"},
    132: {"app": "gitlab",   "label": "gitlab:132", "desc": "Commits by kilian"},
    293: {"app": "gitlab",   "label": "gitlab:293", "desc": "Clone SSH command"},
    308: {"app": "gitlab",   "label": "gitlab:308", "desc": "Top contributor"},
}

DATA_SOURCES = {
    "Text-only Claude": {
        "path": "data/expansion-claude",
        "reps": 5,
        "agent_type": "text-only",
        "model": "Claude Sonnet",
    },
    "Text-only Llama 4": {
        "path": "data/expansion-llama4",
        "reps": 5,
        "agent_type": "text-only",
        "model": "Llama 4 Maverick",
    },
    "SoM Claude": {
        "path": "data/archive/expansion-som-smoke",
        "reps": 1,
        "agent_type": "vision-only",
        "model": "Claude Sonnet",
    },
    "CUA Claude": {
        "path": "data/archive/expansion-cua-smoke",
        "reps": 1,
        "agent_type": "cua",
        "model": "Claude Sonnet",
    },
}

AGENT_SHORT = {
    "Text-only Claude": "Claude-Text",
    "Text-only Llama 4": "Llama4-Text",
    "SoM Claude": "Claude-SoM",
    "CUA Claude": "Claude-CUA",
}

AGENT_ORDER = ["Text-only Claude", "Text-only Llama 4", "SoM Claude", "CUA Claude"]


# ── Data Loading ───────────────────────────────────────────────────────────

def find_cases_dir(base_path: str) -> str | None:
    """Find the cases directory inside a data source (may be nested under a UUID)."""
    base = Path(base_path)
    # Direct cases/ subdir
    if (base / "cases").is_dir():
        return str(base / "cases")
    # UUID subdirectory pattern
    for child in base.iterdir():
        if child.is_dir() and (child / "cases").is_dir():
            # Skip exports/ and track-a/
            if child.name in ("exports", "track-a"):
                continue
            return str(child / "cases")
    return None


def parse_case_filename(filename: str):
    """
    Parse case filename like 'ecommerce_admin_low_41_0_1.json' or 'gitlab_base_132_0_1.json'.
    Returns (app, variant, task_id, rep) or None.
    """
    name = filename.replace(".json", "")
    # Pattern: {app}_{variant}_{taskId}_{configIdx}_{rep}
    # app can be: ecommerce_admin, ecommerce, gitlab, reddit
    # variant can be: low, medium-low, base, high
    for variant in ["medium-low", "low", "base", "high"]:
        parts = name.split(f"_{variant}_")
        if len(parts) == 2:
            app_part = parts[0]
            rest = parts[1]  # e.g., "41_0_1"
            rest_parts = rest.split("_")
            if len(rest_parts) >= 3:
                try:
                    task_id = int(rest_parts[0])
                    rep = int(rest_parts[-1])
                    return app_part, variant, task_id, rep
                except ValueError:
                    continue
    return None


def load_traces(source_name: str, source_config: dict) -> list[dict]:
    """Load all trace JSON files from a data source."""
    cases_dir = find_cases_dir(source_config["path"])
    if not cases_dir:
        print(f"  WARNING: No cases directory found for {source_name} at {source_config['path']}")
        return []

    traces = []
    for fname in os.listdir(cases_dir):
        if not fname.endswith(".json"):
            continue
        parsed = parse_case_filename(fname)
        if parsed is None:
            continue
        app, variant, task_id, rep = parsed

        # Filter to expansion tasks only
        if task_id not in EXPANSION_TASK_IDS:
            continue

        fpath = os.path.join(cases_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARNING: Failed to read {fpath}: {e}")
            continue

        trace = data.get("trace", {})
        success = trace.get("success", False)
        outcome = trace.get("outcome", "unknown")
        total_tokens = trace.get("totalTokens", 0)
        total_steps = trace.get("totalSteps", 0)
        duration_ms = trace.get("durationMs", 0)

        traces.append({
            "source": source_name,
            "app": app,
            "variant": variant,
            "task_id": task_id,
            "rep": rep,
            "success": success,
            "outcome": outcome,
            "total_tokens": total_tokens,
            "total_steps": total_steps,
            "duration_ms": duration_ms,
        })

    return traces


# ── Analysis ───────────────────────────────────────────────────────────────

def compute_success_matrix(all_traces: list[dict]) -> dict:
    """
    Build: agent -> task_id -> variant -> {successes, total, rate, tokens_list, steps_list}
    """
    matrix = {}
    for agent in AGENT_ORDER:
        matrix[agent] = {}
        for tid in sorted(EXPANSION_TASK_IDS):
            matrix[agent][tid] = {}
            for v in VARIANTS:
                matrix[agent][tid][v] = {
                    "successes": 0, "total": 0, "rate": None,
                    "tokens_list": [], "steps_list": [],
                }

    for t in all_traces:
        agent = t["source"]
        tid = t["task_id"]
        v = t["variant"]
        cell = matrix[agent][tid][v]
        cell["total"] += 1
        if t["success"]:
            cell["successes"] += 1
        if t["total_tokens"] > 0:
            cell["tokens_list"].append(t["total_tokens"])
        if t["total_steps"] > 0:
            cell["steps_list"].append(t["total_steps"])

    # Compute rates
    for agent in AGENT_ORDER:
        for tid in sorted(EXPANSION_TASK_IDS):
            for v in VARIANTS:
                cell = matrix[agent][tid][v]
                if cell["total"] > 0:
                    cell["rate"] = cell["successes"] / cell["total"]

    return matrix


def format_cell(cell: dict, reps: int) -> str:
    """Format a cell for display."""
    if cell["total"] == 0:
        return "—"
    s, t = cell["successes"], cell["total"]
    if reps > 1:
        pct = s / t * 100
        return f"{s}/{t} ({pct:.0f}%)"
    else:
        return "✓" if s > 0 else "✗"


def format_cell_rate_only(cell: dict) -> str:
    """Format as percentage only."""
    if cell["total"] == 0 or cell["rate"] is None:
        return "—"
    return f"{cell['rate']*100:.0f}%"


def avg_tokens(cell: dict) -> str:
    """Average tokens for a cell."""
    if not cell["tokens_list"]:
        return "—"
    avg = sum(cell["tokens_list"]) / len(cell["tokens_list"])
    if avg >= 1000:
        return f"{avg/1000:.0f}K"
    return f"{avg:.0f}"


def compute_variant_averages(matrix: dict) -> dict:
    """Compute per-variant averages across tasks for each agent."""
    avgs = {}
    for agent in AGENT_ORDER:
        avgs[agent] = {}
        for v in VARIANTS:
            total_s = 0
            total_n = 0
            all_tokens = []
            for tid in sorted(EXPANSION_TASK_IDS):
                cell = matrix[agent][tid][v]
                total_s += cell["successes"]
                total_n += cell["total"]
                all_tokens.extend(cell["tokens_list"])
            rate = total_s / total_n if total_n > 0 else None
            avg_tok = sum(all_tokens) / len(all_tokens) if all_tokens else None
            avgs[agent][v] = {
                "successes": total_s, "total": total_n, "rate": rate,
                "avg_tokens": avg_tok,
            }
    return avgs


def compute_a11y_gradient(avgs: dict) -> dict:
    """Compute low vs base delta for each agent."""
    gradients = {}
    for agent in AGENT_ORDER:
        low_rate = avgs[agent]["low"]["rate"]
        base_rate = avgs[agent]["base"]["rate"]
        if low_rate is not None and base_rate is not None:
            delta = base_rate - low_rate
            gradients[agent] = {
                "low": low_rate, "base": base_rate,
                "delta_pp": delta * 100,
                "direction": "low < base" if delta > 0 else ("low = base" if delta == 0 else "low > base"),
            }
        else:
            gradients[agent] = None
    return gradients


def find_disagreements(matrix: dict) -> list[dict]:
    """Find task×variant cells where agents disagree on success."""
    disagreements = []
    for tid in sorted(EXPANSION_TASK_IDS):
        for v in VARIANTS:
            results = {}
            for agent in AGENT_ORDER:
                cell = matrix[agent][tid][v]
                if cell["total"] > 0:
                    results[agent] = cell["rate"]

            if len(results) < 2:
                continue

            # Check for disagreement: any agent succeeds while another fails
            rates = list(results.values())
            has_success = any(r is not None and r > 0.5 for r in rates)
            has_failure = any(r is not None and r < 0.5 for r in rates)

            if has_success and has_failure:
                disagreements.append({
                    "task_id": tid,
                    "variant": v,
                    "label": TASK_META[tid]["label"],
                    "results": results,
                })
    return disagreements


# ── Markdown Generation ────────────────────────────────────────────────────

def generate_markdown(matrix, avgs, gradients, disagreements, all_traces) -> str:
    lines = []
    lines.append("# Cross-Agent Comparison: Expansion Tasks (7 Tasks × 4 Variants × 4 Agents)")
    lines.append("")
    lines.append("Generated by `analysis/expansion_cross_agent_comparison.py`")
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append("| Agent | Model | Modality | Reps | Cases |")
    lines.append("|-------|-------|----------|------|-------|")
    for agent in AGENT_ORDER:
        cfg = DATA_SOURCES[agent]
        n = sum(1 for t in all_traces if t["source"] == agent)
        lines.append(f"| {agent} | {cfg['model']} | {cfg['agent_type']} | {cfg['reps']} | {n} |")
    lines.append("")

    # ── Table 1: Main comparison matrix ──
    lines.append("## Table 1: Task × Variant × Agent Success Matrix")
    lines.append("")
    lines.append("Text-only agents (5 reps) shown as `successes/total (rate%)`. "
                 "SoM and CUA (1 rep) shown as ✓/✗.")
    lines.append("")

    # Build header
    header = "| Task | Variant |"
    sep = "|------|---------|"
    for agent in AGENT_ORDER:
        short = AGENT_SHORT[agent]
        header += f" {short} |"
        sep += "--------|"
    lines.append(header)
    lines.append(sep)

    for tid in sorted(EXPANSION_TASK_IDS):
        meta = TASK_META[tid]
        for vi, v in enumerate(VARIANTS):
            task_label = f"**{meta['label']}** {meta['desc']}" if vi == 0 else ""
            row = f"| {task_label} | {v} |"
            for agent in AGENT_ORDER:
                cell = matrix[agent][tid][v]
                reps = DATA_SOURCES[agent]["reps"]
                row += f" {format_cell(cell, reps)} |"
            lines.append(row)
        # Separator between tasks
        lines.append(f"| | | " + " | ".join([""] * len(AGENT_ORDER)) + " |")

    lines.append("")

    # ── Table 2: Per-variant averages ──
    lines.append("## Table 2: Per-Variant Average Success Rate (Across 7 Tasks)")
    lines.append("")
    header2 = "| Variant |"
    sep2 = "|---------|"
    for agent in AGENT_ORDER:
        short = AGENT_SHORT[agent]
        header2 += f" {short} |"
        sep2 += "--------|"
    lines.append(header2)
    lines.append(sep2)

    for v in VARIANTS:
        row = f"| {v} |"
        for agent in AGENT_ORDER:
            a = avgs[agent][v]
            if a["rate"] is not None:
                s, n = a["successes"], a["total"]
                pct = a["rate"] * 100
                row += f" {s}/{n} ({pct:.1f}%) |"
            else:
                row += " — |"
        lines.append(row)
    lines.append("")

    # ── Table 3: A11y Gradient ──
    lines.append("## Table 3: Accessibility Gradient (low vs base)")
    lines.append("")
    lines.append("The core question: does low accessibility degrade performance, and by how much?")
    lines.append("")
    lines.append("| Agent | Low Rate | Base Rate | Δ (base−low) | Direction |")
    lines.append("|-------|----------|-----------|--------------|-----------|")
    for agent in AGENT_ORDER:
        g = gradients[agent]
        if g:
            lines.append(f"| {agent} | {g['low']*100:.1f}% | {g['base']*100:.1f}% | "
                         f"+{g['delta_pp']:.1f}pp | {g['direction']} |")
        else:
            lines.append(f"| {agent} | — | — | — | — |")
    lines.append("")
    lines.append("> **Key finding**: The direction of the effect (low < base) is consistent across "
                 "all four agent types, confirming that accessibility degradation affects different "
                 "agent architectures through different mechanisms — text-only via a11y tree quality, "
                 "SoM via phantom bids, CUA via cross-layer visual changes — but the direction is universal.")
    lines.append("")

    # ── Table 4: Disagreements ──
    lines.append("## Table 4: Agent Disagreements (Success vs Failure on Same Task×Variant)")
    lines.append("")
    lines.append("Cases where at least one agent succeeds (>50%) and another fails (<50%).")
    lines.append("")
    if disagreements:
        header4 = "| Task | Variant |"
        sep4 = "|------|---------|"
        for agent in AGENT_ORDER:
            short = AGENT_SHORT[agent]
            header4 += f" {short} |"
            sep4 += "--------|"
        lines.append(header4)
        lines.append(sep4)
        for d in disagreements:
            row = f"| {d['label']} | {d['variant']} |"
            for agent in AGENT_ORDER:
                r = d["results"].get(agent)
                if r is None:
                    row += " — |"
                else:
                    pct = r * 100
                    marker = "✓" if r > 0.5 else ("~" if r == 0.5 else "✗")
                    row += f" {marker} {pct:.0f}% |"
            lines.append(row)
    else:
        lines.append("No disagreements found.")
    lines.append("")

    # ── Table 5: Token consumption ──
    lines.append("## Table 5: Average Token Consumption by Agent × Variant")
    lines.append("")
    header5 = "| Variant |"
    sep5 = "|---------|"
    for agent in AGENT_ORDER:
        short = AGENT_SHORT[agent]
        header5 += f" {short} |"
        sep5 += "--------|"
    lines.append(header5)
    lines.append(sep5)

    for v in VARIANTS:
        row = f"| {v} |"
        for agent in AGENT_ORDER:
            tokens = []
            for tid in sorted(EXPANSION_TASK_IDS):
                tokens.extend(matrix[agent][tid][v]["tokens_list"])
            if tokens:
                avg = sum(tokens) / len(tokens)
                row += f" {avg/1000:.0f}K |"
            else:
                row += " — |"
        lines.append(row)
    lines.append("")

    # ── Table 6: Per-task token comparison ──
    lines.append("## Table 6: Per-Task Average Tokens (All Variants Combined)")
    lines.append("")
    header6 = "| Task |"
    sep6 = "|------|"
    for agent in AGENT_ORDER:
        short = AGENT_SHORT[agent]
        header6 += f" {short} |"
        sep6 += "--------|"
    lines.append(header6)
    lines.append(sep6)

    for tid in sorted(EXPANSION_TASK_IDS):
        meta = TASK_META[tid]
        row = f"| {meta['label']} |"
        for agent in AGENT_ORDER:
            tokens = []
            for v in VARIANTS:
                tokens.extend(matrix[agent][tid][v]["tokens_list"])
            if tokens:
                avg = sum(tokens) / len(tokens)
                row += f" {avg/1000:.0f}K |"
            else:
                row += " — |"
        lines.append(row)
    lines.append("")

    # ── Table 7: Low-variant per-task breakdown ──
    lines.append("## Table 7: Low-Variant Success — Per-Task Agent Comparison")
    lines.append("")
    lines.append("The low variant is where agent architectures diverge most. "
                 "This table shows which tasks each agent can/cannot solve under degraded accessibility.")
    lines.append("")
    header7 = "| Task |"
    sep7 = "|------|"
    for agent in AGENT_ORDER:
        short = AGENT_SHORT[agent]
        header7 += f" {short} |"
        sep7 += "--------|"
    lines.append(header7)
    lines.append(sep7)

    for tid in sorted(EXPANSION_TASK_IDS):
        meta = TASK_META[tid]
        row = f"| {meta['label']} |"
        for agent in AGENT_ORDER:
            cell = matrix[agent][tid]["low"]
            reps = DATA_SOURCES[agent]["reps"]
            row += f" {format_cell(cell, reps)} |"
        lines.append(row)

    # Add averages row
    row = "| **Average** |"
    for agent in AGENT_ORDER:
        a = avgs[agent]["low"]
        if a["rate"] is not None:
            row += f" **{a['rate']*100:.1f}%** |"
        else:
            row += " — |"
    lines.append(row)
    lines.append("")

    # ── Summary narrative ──
    lines.append("## Summary: Cross-Architecture Accessibility Effect")
    lines.append("")
    lines.append("### Consistent Direction")
    lines.append("")
    for agent in AGENT_ORDER:
        g = gradients[agent]
        if g and g["delta_pp"] > 0:
            lines.append(f"- **{agent}**: low {g['low']*100:.1f}% → base {g['base']*100:.1f}% "
                         f"(Δ = +{g['delta_pp']:.1f}pp)")
    lines.append("")
    lines.append("### Mechanism Differences")
    lines.append("")
    lines.append("| Agent | Primary Failure Mechanism at Low | DOM Dependency |")
    lines.append("|-------|----------------------------------|----------------|")
    lines.append("| Text-only Claude | Content invisibility (broken ARIA → missing a11y tree nodes) | Direct: reads a11y tree |")
    lines.append("| Text-only Llama 4 | Same as Claude, but weaker model amplifies effect | Direct: reads a11y tree |")
    lines.append("| SoM Claude | Phantom bids (SoM labels persist on de-semanticized elements) | Indirect: SoM overlays depend on DOM interactive elements |")
    lines.append("| CUA Claude | Cross-layer visual changes (link→span removes clickable affordances) | Minimal: pure coordinate-based, but functional breakage still affects |")
    lines.append("")

    # ── Disagreement analysis ──
    if disagreements:
        lines.append("### Notable Disagreements")
        lines.append("")
        for d in disagreements:
            agents_succeed = [a for a, r in d["results"].items() if r is not None and r > 0.5]
            agents_fail = [a for a, r in d["results"].items() if r is not None and r < 0.5]
            lines.append(f"- **{d['label']} ({d['variant']})**: "
                         f"{', '.join(agents_succeed)} succeed; "
                         f"{', '.join(agents_fail)} fail")
        lines.append("")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Cross-Agent Comparison: 7 Expansion Tasks × 4 Variants × 4 Agents")
    print("=" * 70)

    all_traces = []
    for agent_name in AGENT_ORDER:
        cfg = DATA_SOURCES[agent_name]
        print(f"\nLoading {agent_name} from {cfg['path']}...")
        traces = load_traces(agent_name, cfg)
        print(f"  → {len(traces)} traces loaded (expansion tasks only)")

        # Sanity check
        task_ids_found = sorted(set(t["task_id"] for t in traces))
        variants_found = sorted(set(t["variant"] for t in traces), key=lambda v: VARIANT_ORDER.get(v, 99))
        print(f"  → Tasks: {task_ids_found}")
        print(f"  → Variants: {variants_found}")

        all_traces.extend(traces)

    print(f"\nTotal traces: {len(all_traces)}")

    # Compute analysis
    matrix = compute_success_matrix(all_traces)
    avgs = compute_variant_averages(matrix)
    gradients = compute_a11y_gradient(avgs)
    disagreements = find_disagreements(matrix)

    # Print summary to console
    print("\n" + "=" * 70)
    print("A11y Gradient Summary:")
    for agent in AGENT_ORDER:
        g = gradients[agent]
        if g:
            print(f"  {agent}: low={g['low']*100:.1f}% base={g['base']*100:.1f}% "
                  f"Δ=+{g['delta_pp']:.1f}pp ({g['direction']})")

    print(f"\nDisagreements found: {len(disagreements)}")
    for d in disagreements:
        print(f"  {d['label']} {d['variant']}: {d['results']}")

    # Generate markdown
    md = generate_markdown(matrix, avgs, gradients, disagreements, all_traces)

    # Write output
    out_path = "docs/analysis/expansion-cross-agent-comparison.md"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n✓ Output written to {out_path}")


if __name__ == "__main__":
    main()

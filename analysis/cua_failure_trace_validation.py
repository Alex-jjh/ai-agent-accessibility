#!/usr/bin/env python3
"""
CUA Failure Trace Validation — Cross-checks CUA low-variant failure traces
for the link→span signature:

  1. Agent executed a left_click action at some coordinate (x, y)
  2. Click succeeded (no Playwright error)
  3. URL did not change between before-click and after-click steps
  4. No scroll action between them (pure click)

If the URL doesn't change after a click, the click landed on either:
  (a) an inert pixel (no handler, no <a href>) — link→span signature
  (b) a handler that doesn't navigate (e.g. menu toggle)

We count signature (a) per failure and report the fraction. Plus we cross-check
against `last_action_error` in the trace to confirm no Playwright-level error.

Usage:
  python3 analysis/cua_failure_trace_validation.py \\
      --traces data/expansion-cua data/pilot4-cua \\
      --output results/visual-equivalence/cua-failure-signature.md

Output:
  - results/visual-equivalence/cua-failure-signature.md (writeup)
  - results/visual-equivalence/cua-failure-signature.csv (per-trace classification)
"""

import argparse
import csv
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import Optional

URL_RE = re.compile(r"\[cua screenshot\]\s*(\S+)")


def extract_url(observation: str) -> Optional[str]:
    if not observation:
        return None
    m = URL_RE.search(observation)
    return m.group(1) if m else None


def parse_action(action_str: str) -> dict:
    """Parse cua action strings like:
        cua:left_click({"action":"left_click","coordinate":[248,157]})
        cua:scroll({...})
        cua:key({...})
    Returns {'kind': 'left_click'|'scroll'|'key'|'type'|..., 'payload': {...}} or
    {'kind': 'unknown', 'raw': action_str}."""
    if not action_str:
        return {"kind": "none"}
    m = re.match(r"cua:(\w+)\((.*)\)\s*$", action_str.strip(), re.DOTALL)
    if not m:
        return {"kind": "unknown", "raw": action_str[:200]}
    kind = m.group(1)
    try:
        payload = json.loads(m.group(2))
    except json.JSONDecodeError:
        payload = {"_parse_error": True}
    return {"kind": kind, "payload": payload}


def _case_id_from(case_meta: dict, trace: dict, path: pathlib.Path) -> str:
    """Best-effort case ID. Falls back to filename / parent dir if nothing else."""
    cid = case_meta.get("caseId") or (trace or {}).get("caseId") or ""
    if cid:
        return cid
    # Case A: pilot4-cua and expansion layouts:
    #   .../cases/<app>_<variant>_<task>_<sub>_<rep>.json
    # Case B: pilot4-full layout:
    #   .../cases/<app>_<variant>_<task>_<sub>_<rep>/trace-attempt-N.json
    stem = path.stem
    parent = path.parent.name  # either "cases" (case A) or the case dir (case B)
    if parent != "cases" and "_" in parent:
        # Case B — use parent dir name (has the semantic case id), append attempt
        parts = parent.split("_")
        if len(parts) >= 5:
            return ":".join(parts) + ":" + stem  # e.g. "ecommerce_admin:low:198:0:1:trace-attempt-1"
        return parent + ":" + stem
    parts = stem.split("_")
    if len(parts) >= 5:
        return ":".join(parts)
    return stem


def classify_trace(trace: dict, case_meta: dict) -> dict:
    """Examine a single CUA trace and count 'click → URL unchanged' events.

    Returns a classification record suitable for aggregation.
    """
    steps = trace.get("steps", []) or []
    variant = case_meta.get("variant", trace.get("variant", "?"))
    outcome = trace.get("outcome") or ("success" if trace.get("success") else "failure")

    clicks = []  # {coord, url_before, url_after, error, inert}
    scrolls = 0
    keystrokes = 0
    types = 0
    total = len(steps)
    playwright_errors = 0

    for i, step in enumerate(steps):
        obs = step.get("observation", "")
        url_this = extract_url(obs)
        action = parse_action(step.get("action", ""))
        result = step.get("result", "")
        result_detail = step.get("resultDetail", "") or step.get("last_action_error", "") or ""
        if result == "failure":
            playwright_errors += 1
        if action["kind"] == "scroll":
            scrolls += 1
        elif action["kind"] in ("key", "hold_key"):
            keystrokes += 1
        elif action["kind"] in ("type", "double_click"):
            types += 1
        elif action["kind"] == "left_click":
            coord = (action.get("payload") or {}).get("coordinate")
            url_after = None
            for j in range(i + 1, min(i + 3, len(steps))):
                next_url = extract_url(steps[j].get("observation", ""))
                if next_url:
                    url_after = next_url
                    break
            click_rec = {
                "step": step.get("stepNum", i + 1),
                "coord": coord,
                "url_before": url_this,
                "url_after": url_after,
                "result": result,
                "result_detail": result_detail[:200] if result_detail else "",
                "url_unchanged": (url_this is not None and url_after is not None
                                  and url_this == url_after and result == "success"),
            }
            clicks.append(click_rec)

    total_clicks = len(clicks)
    inert_clicks = sum(1 for c in clicks if c["url_unchanged"])
    successful_clicks = sum(1 for c in clicks if c["result"] == "success")
    inert_fraction = (inert_clicks / successful_clicks) if successful_clicks else 0.0

    # Click-loop detection: how many distinct (x±15, y±15) regions did the agent
    # click vs total clicks? A "loop" is when agent hammers the same region >= 3 times.
    distinct_regions: list[tuple[int, int]] = []
    for c in clicks:
        coord = c.get("coord")
        if not coord or len(coord) != 2:
            continue
        x, y = coord
        # Bucket to 30x30 grid
        bx, by = int(x) // 30, int(y) // 30
        distinct_regions.append((bx, by))
    region_counter = Counter(distinct_regions)
    max_loop = max(region_counter.values()) if region_counter else 0
    looping_clicks = sum(c for c in region_counter.values() if c >= 3)
    loop_fraction = (looping_clicks / total_clicks) if total_clicks else 0.0

    # Strengthened link→span signature (strict, focuses on the catastrophic
    # pattern seen in expansion-cua admin:198, reddit:29 low failures):
    #   1. variant = low
    #   2. outcome = failure/timeout (agent couldn't complete)
    #   3. >= 8 successful clicks total (enough data to distinguish from short traces)
    #   4. inert_fraction >= 0.90 (almost every click failed to navigate)
    #   5. agent revisited some region >= 3 times (clicking loop)
    link_span_signature = (
        variant == "low"
        and outcome != "success"
        and successful_clicks >= 8
        and inert_fraction >= 0.90
        and max_loop >= 3
    )

    return {
        "caseId": case_meta.get("caseId", "?"),
        "app": case_meta.get("app", "?"),
        "taskId": case_meta.get("taskId", "?"),
        "variant": variant,
        "outcome": outcome,
        "total_steps": total,
        "total_clicks": total_clicks,
        "successful_clicks": successful_clicks,
        "inert_clicks": inert_clicks,
        "inert_fraction": round(inert_fraction, 3),
        "max_region_loop": max_loop,
        "loop_fraction": round(loop_fraction, 3),
        "scrolls": scrolls,
        "types": types,
        "keystrokes": keystrokes,
        "playwright_errors": playwright_errors,
        "link_span_signature": link_span_signature,
    }


def iter_trace_files(roots: list[pathlib.Path]):
    """Yield (path, case_json) for every CUA case file under the given roots."""
    for root in roots:
        if not root.exists():
            print(f"WARN: trace root {root} does not exist", file=sys.stderr)
            continue
        for p in root.rglob("*.json"):
            # Filter to cases/ directories (not run-state.json, not exports)
            if "cases" not in p.parts:
                continue
            try:
                # Explicit UTF-8 — Windows default cp1252 chokes on emoji/CJK in traces
                with p.open(encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"WARN: could not parse {p}: {e}", file=sys.stderr)
                continue
            # Only process CUA traces
            agent_cfg = data.get("agentConfig") or (data.get("trace") or {}).get("agentConfig") or {}
            if agent_cfg.get("observationMode") != "cua":
                continue
            yield p, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", nargs="+", required=True,
                    help="Directories to scan for CUA trace JSON files")
    ap.add_argument("--output", default="results/visual-equivalence/cua-failure-signature.md")
    args = ap.parse_args()

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for path, case in iter_trace_files([pathlib.Path(r) for r in args.traces]):
        trace = case.get("trace") or case  # some files nest under "trace", some don't
        cid = _case_id_from(case, trace, path)
        case["caseId"] = cid
        # Also ensure variant, task, app are surfaced in case_meta for the report
        case.setdefault("variant", trace.get("variant") if isinstance(trace, dict) else None)
        case.setdefault("taskId", trace.get("taskId") if isinstance(trace, dict) else None)
        # Derive app from case id (first one or two tokens before the variant)
        if not case.get("app"):
            parts = cid.split(":")
            if len(parts) >= 3:
                # e.g. "ecommerce_admin:low:198:0:1" → "ecommerce_admin"
                case["app"] = parts[0]
        rec = classify_trace(trace, case)
        rec["source_file"] = str(path)
        records.append(rec)

    # Write CSV
    csv_path = output_path.with_suffix(".csv")
    cols = ["caseId", "app", "taskId", "variant", "outcome",
            "total_steps", "total_clicks", "successful_clicks",
            "inert_clicks", "inert_fraction",
            "max_region_loop", "loop_fraction",
            "scrolls", "types", "keystrokes",
            "playwright_errors", "link_span_signature", "source_file"]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in cols})

    # Aggregate for report
    low_recs = [r for r in records if r["variant"] == "low"]
    low_failures = [r for r in low_recs if r["outcome"] != "success"]
    low_successes = [r for r in low_recs if r["outcome"] == "success"]
    base_recs = [r for r in records if r["variant"] == "base"]
    base_failures = [r for r in base_recs if r["outcome"] != "success"]

    sig_in_low_failures = sum(1 for r in low_failures if r["link_span_signature"])
    sig_in_low_successes = sum(1 for r in low_successes if r["inert_clicks"] >= 2)
    sig_in_base_failures = sum(1 for r in base_failures if r["inert_clicks"] >= 2)

    def safe_div(a, b):
        return (a / b) if b else 0.0

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    lines = [
        "# CUA Failure Trace Validation — link→span signature\n",
        f"Scanned {len(records)} CUA traces.\n",
        f"- Low variant: {len(low_recs)} ({len(low_failures)} failures, {len(low_successes)} successes)",
        f"- Base variant: {len(base_recs)} ({len(base_failures)} failures)\n",
        "## Signature definition\n",
        "A trace shows the link→span signature (strict) when:",
        "- variant = low",
        "- outcome != success (timeout or explicit failure)",
        "- >= 8 successful left_click actions in the trace",
        "- >= 90% of those clicks produced NO url change (inert)",
        "- agent clicked the same 30x30 px region >= 3 times (loop)",
        "",
        "This matches the predicted cross-layer failure: CUA clicks on blue-underlined",
        "pixels (which LOOK like links because patch 11 preserves inline style + cursor",
        "on <span>), but the DOM a[href]->span substitution means the click does nothing,",
        "the URL never updates, and the agent loops on the same coordinates.\n",
        "Why the strict threshold: many intra-app interactions (dropdowns, filters, form",
        "fills) legitimately don't change URL. A loose `inert_clicks >= 2` test fires",
        "on successful base-variant runs too. Requiring >= 90% inert + loop + outcome=fail",
        "isolates the specific failure mode where every click on a former link is silent.\n",
        "## Signature prevalence\n",
        f"| Subset | Total | With signature | Fraction |",
        f"|--------|-------|----------------|----------|",
        f"| Low failures | {len(low_failures)} | {sig_in_low_failures} | "
        f"{safe_div(sig_in_low_failures, len(low_failures)):.1%} |",
        f"| Low successes (≥2 inert clicks) | {len(low_successes)} | {sig_in_low_successes} | "
        f"{safe_div(sig_in_low_successes, len(low_successes)):.1%} |",
        f"| Base failures (≥2 inert clicks) | {len(base_failures)} | {sig_in_base_failures} | "
        f"{safe_div(sig_in_base_failures, len(base_failures)):.1%} |\n",
        "## Inert click fraction by variant & outcome\n",
    ]

    buckets = defaultdict(list)
    for r in records:
        key = (r["variant"], r["outcome"])
        buckets[key].append(r["inert_fraction"])
    lines.append("| Variant | Outcome | N | Mean inert fraction | Mean inert clicks |")
    lines.append("|---------|---------|---|--------------------|-------------------|")
    for (v, o), xs in sorted(buckets.items()):
        inert_counts = [r["inert_clicks"] for r in records
                        if r["variant"] == v and r["outcome"] == o]
        lines.append(f"| {v} | {o} | {len(xs)} | {mean(xs):.2%} | {mean(inert_counts):.2f} |")

    # Breakdown of low failures by task
    lines.append("\n## Low-variant failure breakdown by task\n")
    task_buckets = defaultdict(lambda: {"n": 0, "sig": 0, "inert_total": 0,
                                         "clicks_total": 0})
    for r in low_failures:
        b = task_buckets[r["taskId"]]
        b["n"] += 1
        if r["link_span_signature"]:
            b["sig"] += 1
        b["inert_total"] += r["inert_clicks"]
        b["clicks_total"] += r["successful_clicks"]
    lines.append("| Task | Low failures | Link→span sig | Signature rate | "
                 "Total inert / total clicks |")
    lines.append("|------|--------------|---------------|----------------|"
                 "----------------------------|")
    for tid in sorted(task_buckets, key=lambda x: int(x) if x.isdigit() else 0):
        b = task_buckets[tid]
        sig_rate = safe_div(b["sig"], b["n"])
        lines.append(f"| {tid} | {b['n']} | {b['sig']} | {sig_rate:.1%} | "
                     f"{b['inert_total']} / {b['clicks_total']} |")

    # Known smoking-gun examples
    lines.append("\n## Representative signature cases (first 5)\n")
    for r in [x for x in low_failures if x["link_span_signature"]][:5]:
        lines.append(f"- **{r['caseId']}** (task {r['taskId']}): "
                     f"{r['inert_clicks']}/{r['successful_clicks']} clicks inert, "
                     f"{r['total_steps']} total steps")

    lines.append(f"\n---\nCSV: `{csv_path}`\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_path} and {csv_path}", file=sys.stderr)
    print(f"Low failures with signature: {sig_in_low_failures} / {len(low_failures)} "
          f"({safe_div(sig_in_low_failures, len(low_failures)):.1%})", file=sys.stderr)


if __name__ == "__main__":
    main()

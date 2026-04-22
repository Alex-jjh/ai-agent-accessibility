#!/usr/bin/env python3
"""Extract all URLs visited by agents during experimental runs.

Walks every CUA and text-only trace on disk and emits a per-case URL list,
plus an aggregate de-duplicated list suitable for URL-replay visual equivalence
validation.

Output:
  results/visual-equivalence/agent-urls.csv    — one row per (case, step, url)
  results/visual-equivalence/agent-urls-dedup.csv — unique (app, url, count)
  results/visual-equivalence/agent-urls-summary.md — aggregate report

Usage:
  python3 scripts/extract_agent_urls.py \\
    --traces data/expansion-cua data/pilot4-cua data/pilot4-full data/expansion-claude data/expansion-llama4 data/expansion-som \\
    --output results/visual-equivalence
"""

import argparse
import csv
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import Iterator

# Match "[cua screenshot] http://..." or ("url": "...") style URLs
CUA_URL_RE = re.compile(r"\[cua screenshot\]\s*(\S+)")
# BrowserGym a11y obs starts with "RootWebArea '...', focused" — URL not inline
# but action goto(url) lines carry URLs
GOTO_URL_RE = re.compile(r"""goto\(\s*["']([^"']+)["']""")


def iter_traces(roots: list[pathlib.Path]) -> Iterator[tuple[pathlib.Path, dict]]:
    """Yield (path, parsed_json) for every case trace under the given roots."""
    for root in roots:
        if not root.exists():
            print(f"WARN: missing trace root {root}", file=sys.stderr)
            continue
        for p in root.rglob("*.json"):
            # Skip manifests / run-state / exports
            if p.name in ("run-state.json", "manifest.json"):
                continue
            if "cases" not in p.parts:
                continue
            if "exports" in p.parts:
                continue
            try:
                with p.open(encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                # Silent — a few files have encoding issues on Windows
                continue
            yield p, data


def case_metadata(path: pathlib.Path, data: dict) -> dict:
    """Best-effort case metadata extraction."""
    trace = data.get("trace") or data
    # Normalize case id from path or from embedded fields
    agent_cfg = data.get("agentConfig") or trace.get("agentConfig") or {}
    cid = data.get("caseId") or trace.get("caseId") or ""
    if not cid:
        stem = path.stem
        parent = path.parent.name
        # Two layouts: .../cases/<case>.json  or  .../cases/<case_dir>/<file>.json
        if parent != "cases" and "_" in parent:
            cid = parent  # e.g. "ecommerce_admin_low_198_0_1"
        else:
            cid = stem

    # Parse case id: "ecommerce_admin_low_198_0_1" → app=ecommerce_admin variant=low task=198 sub=0 rep=1
    # Note: app name may contain underscores (ecommerce_admin)
    app = ""
    variant = ""
    task_id = data.get("taskId") or trace.get("taskId") or ""
    parts = cid.split("_") if cid else []
    # Try different splits
    for candidate_app_len in (2, 1):  # try 2-word apps first (ecommerce_admin)
        if len(parts) >= candidate_app_len + 3:
            maybe_app = "_".join(parts[:candidate_app_len])
            maybe_variant = parts[candidate_app_len]
            if maybe_variant in ("low", "base", "high", "medium-low", "pure-semantic-low"):
                app = maybe_app
                variant = maybe_variant
                if not task_id:
                    task_id = parts[candidate_app_len + 1]
                break

    return {
        "case_id": cid,
        "app": app,
        "variant": data.get("variant") or trace.get("variant") or variant,
        "task_id": str(task_id),
        "observation_mode": agent_cfg.get("observationMode", ""),
        "outcome": trace.get("outcome") or ("success" if trace.get("success") else "failure"),
        "source_file": str(path),
    }


def extract_step_urls(trace: dict) -> list[tuple[int, str, str]]:
    """Return list of (step_num, url, action) tuples. URL is per-step if detectable."""
    out = []
    steps = trace.get("steps") or []
    for i, step in enumerate(steps):
        step_num = step.get("stepNum", i + 1)
        obs = step.get("observation", "") or ""
        action = step.get("action", "") or ""
        url = ""
        m = CUA_URL_RE.search(obs)
        if m:
            url = m.group(1)
        else:
            # Text-only traces: URL sometimes in "url" field or from prior goto
            url = step.get("url", "") or ""
        if not url:
            # Try to pull from goto action
            gm = GOTO_URL_RE.search(action)
            if gm:
                url = gm.group(1)
        if url:
            out.append((step_num, url, action))
    return out


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication:
    - strip fragment
    - strip trailing slash
    - lowercase host
    Keep query string (important for product pages, search, etc.)."""
    if not url:
        return ""
    # Remove fragment
    url = url.split("#", 1)[0]
    # Trim trailing whitespace
    url = url.strip()
    return url


def looks_replayable(url: str) -> bool:
    """Heuristic: is this URL safely replayable via a fresh GET?"""
    if not url:
        return False
    lu = url.lower()
    # Reject anything that suggests POST-only or state-changing
    if any(bad in lu for bad in ("/loginpost", "/checkout/onepage", "/logout",
                                  "/customer/account/logoutsuccess",
                                  "about:blank", "chrome-error://",
                                  "data:", "javascript:")):
        return False
    if not lu.startswith(("http://", "https://")):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", nargs="+", required=True,
                    help="Directories to scan for trace JSON")
    ap.add_argument("--output", default="results/visual-equivalence")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_step_rows = []
    url_counter: Counter = Counter()
    app_url_counter: dict[str, Counter] = defaultdict(Counter)
    case_count = 0
    case_by_mode: Counter = Counter()
    case_by_variant: Counter = Counter()

    for path, data in iter_traces([pathlib.Path(t) for t in args.traces]):
        meta = case_metadata(path, data)
        trace = data.get("trace") or data
        steps = extract_step_urls(trace)
        case_count += 1
        case_by_mode[meta["observation_mode"]] += 1
        case_by_variant[meta["variant"]] += 1
        for step_num, url, action in steps:
            nu = normalize_url(url)
            if not nu:
                continue
            per_step_rows.append({
                "case_id": meta["case_id"],
                "app": meta["app"],
                "variant": meta["variant"],
                "task_id": meta["task_id"],
                "observation_mode": meta["observation_mode"],
                "outcome": meta["outcome"],
                "step": step_num,
                "url": nu,
                "action_prefix": action[:80].replace("\n", " "),
                "replayable": looks_replayable(nu),
            })
            url_counter[nu] += 1
            if meta["app"]:
                app_url_counter[meta["app"]][nu] += 1

    # Write per-step CSV
    per_step_csv = out_dir / "agent-urls.csv"
    with per_step_csv.open("w", newline="", encoding="utf-8") as f:
        if per_step_rows:
            w = csv.DictWriter(f, fieldnames=list(per_step_rows[0].keys()))
            w.writeheader()
            for row in per_step_rows:
                w.writerow(row)

    # Write dedup CSV
    dedup_csv = out_dir / "agent-urls-dedup.csv"
    with dedup_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "app", "visits", "replayable"])
        # Assign URL to the app that visited it most
        for url, count in url_counter.most_common():
            best_app = max(app_url_counter.keys(),
                           key=lambda a: app_url_counter[a].get(url, 0),
                           default="")
            w.writerow([url, best_app, count, looks_replayable(url)])

    # Summary report
    total_urls = len(url_counter)
    replayable_urls = sum(1 for u in url_counter if looks_replayable(u))
    per_app_urls = {a: len(c) for a, c in app_url_counter.items()}

    lines = [
        "# Agent URL Extraction — for URL-replay visual equivalence",
        "",
        f"Scanned traces under: {', '.join(args.traces)}",
        f"- Total cases: {case_count}",
        f"- Total step-URL pairs: {len(per_step_rows)}",
        f"- Unique URLs: {total_urls}",
        f"- Replayable URLs: {replayable_urls} ({replayable_urls / max(total_urls, 1):.1%})",
        "",
        "## Cases by observation mode",
    ]
    for mode, n in sorted(case_by_mode.items(), key=lambda x: -x[1]):
        lines.append(f"- {mode or '(unknown)'}: {n}")
    lines.append("")
    lines.append("## Cases by variant")
    for v, n in sorted(case_by_variant.items(), key=lambda x: -x[1]):
        lines.append(f"- {v or '(unknown)'}: {n}")
    lines.append("")
    lines.append("## Unique URLs by app")
    for app, n in sorted(per_app_urls.items(), key=lambda x: -x[1]):
        lines.append(f"- {app}: {n}")
    lines.append("")
    lines.append("## Top 20 most-visited URLs")
    lines.append("| Visits | Replayable | URL |")
    lines.append("|--------|------------|-----|")
    for url, count in url_counter.most_common(20):
        rp = "YES" if looks_replayable(url) else "no"
        lines.append(f"| {count} | {rp} | `{url[:120]}` |")

    summary = out_dir / "agent-urls-summary.md"
    summary.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {per_step_csv}", file=sys.stderr)
    print(f"Wrote {dedup_csv}", file=sys.stderr)
    print(f"Wrote {summary}", file=sys.stderr)
    print(f"Total cases: {case_count}, unique URLs: {total_urls}, "
          f"replayable: {replayable_urls}", file=sys.stderr)


if __name__ == "__main__":
    main()

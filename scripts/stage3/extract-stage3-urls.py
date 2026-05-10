#!/usr/bin/env python3.11
"""Extract URLs agents observed in Stage 3 traces, for trace-URL SSIM replay.

Companion to scripts/visual-equiv/replay-url-screenshots.py but for Stage 3
data (individual-operator cases, not composite variants).

Input : data/stage3-{claude,llama}/*/cases/*.json
Output:
  results/stage3/visual-equiv/stage3-urls.csv         — per-step URL records
  results/stage3/visual-equiv/stage3-urls-dedup.csv   — unique URLs + visits
  results/stage3/visual-equiv/stage3-urls-summary.md  — replay-cost report
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

# Text-only observation contains "Current URL: ..." (from executor.ts
# buildUserMessage).  Vision mode uses "[screenshot only] {url}".
# goto(...) actions also carry URLs.
CURRENT_URL_RE = re.compile(r"Current URL:\s*(\S+)")
SCREENSHOT_URL_RE = re.compile(r"\[screenshot only\]\s*(\S+)")
GOTO_URL_RE = re.compile(r"""goto\(\s*["']([^"']+)["']""")
AXTREE_URL_RE = re.compile(r"\[screenshot \+ axtree\]\s*(\S+)")

# Port → app mapping (matches Phase 7 replay harness)
PORT_APP = {
    7770: "shopping",         # ecommerce storefront
    7780: "shopping_admin",   # ecommerce admin
    9999: "reddit",
    8023: "gitlab",
}
APP_PORT = {v: k for k, v in PORT_APP.items()}

# Stage 3 case ID format: {app}:individual:{taskId}:{ci}:{attempt}:{opIds}
# app names in config are: ecommerce, ecommerce_admin, gitlab, reddit
# We normalize ecommerce -> shopping, ecommerce_admin -> shopping_admin for
# consistency with the port/login mapping.
APP_NORMALIZE = {
    "ecommerce":       "shopping",
    "ecommerce_admin": "shopping_admin",
    "gitlab":          "gitlab",
    "reddit":          "reddit",
}


def normalize_url(url: str) -> str:
    """Strip fragment and whitespace; keep query string."""
    if not url:
        return ""
    return url.split("#", 1)[0].strip()


def is_webarena_url(url: str) -> bool:
    """Only internal WebArena URLs are replayable — external ones (github.com
    etc.) are Llama hallucinations; not our concern for visual-equivalence."""
    if not url.startswith("http://"):
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or 0
        return re.match(r"^\d+\.\d+\.\d+\.\d+$", host) is not None and port in PORT_APP
    except Exception:
        return False


def looks_replayable(url: str) -> bool:
    """Is this URL safely replayable via fresh GET?

    Rejects login POST endpoints, logout, and other state-mutating paths.
    """
    if not is_webarena_url(url):
        return False
    lu = url.lower()
    denylist = (
        "/loginpost", "/logout", "/customer/account/logoutsuccess",
        "/checkout/onepage",
    )
    return not any(bad in lu for bad in denylist)


def extract_urls_from_trace(trace: dict) -> list[tuple[int, str, str]]:
    """Return list of (step_num, url, action) tuples from the agent trace."""
    out: list[tuple[int, str, str]] = []
    steps = trace.get("steps") or []
    for i, step in enumerate(steps):
        step_num = step.get("stepNum", i + 1)
        obs = step.get("observation") or ""
        act = step.get("action") or ""

        # Collect every URL mentioned in the observation (most steps have 1)
        urls: list[str] = []
        for m in CURRENT_URL_RE.finditer(obs):
            urls.append(m.group(1))
        for m in SCREENSHOT_URL_RE.finditer(obs):
            urls.append(m.group(1))
        for m in AXTREE_URL_RE.finditer(obs):
            urls.append(m.group(1))
        m = GOTO_URL_RE.search(act)
        if m:
            urls.append(m.group(1))

        for u in urls:
            u = normalize_url(u)
            if u:
                out.append((step_num, u, act[:80].replace("\n", " ")))
    return out


def case_metadata(path: pathlib.Path, data: dict) -> dict:
    cid = data.get("caseId") or ""
    parts = cid.split(":") if cid else []
    # Format: {app}:individual:{task}:{ci}:{attempt}:{opIds}
    if len(parts) >= 6 and parts[1] == "individual":
        app_raw = parts[0]
        task = parts[2]
        attempt = parts[4]
        op_ids = parts[5]
    else:
        app_raw = task = attempt = op_ids = ""

    app = APP_NORMALIZE.get(app_raw, app_raw)
    trace = data.get("trace") or {}
    return {
        "case_id": cid,
        "app": app,
        "app_raw": app_raw,
        "task_id": task,
        "attempt": attempt,
        "operator": op_ids,
        "observation_mode": (data.get("agentConfig") or {}).get("observationMode", ""),
        "llm": (data.get("agentConfig") or {}).get("llmBackend", ""),
        "success": bool(trace.get("success")),
        "outcome": trace.get("outcome", "unknown"),
        "source_file": str(path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--data-dir", nargs="+", required=True,
        help="Stage 3 data directories (data/stage3-claude and/or data/stage3-llama)",
    )
    ap.add_argument(
        "--output", default="results/stage3/visual-equiv",
        help="Output directory for CSVs and summary",
    )
    ap.add_argument(
        "--min-visits", type=int, default=1,
        help="Only include URLs visited >= N times (default 1)",
    )
    args = ap.parse_args()

    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_step_rows: list[dict] = []
    url_counter: Counter = Counter()
    app_url_counter: dict[str, Counter] = defaultdict(Counter)
    # operator × url — to understand if any URL is operator-specific
    op_url_counter: dict[str, Counter] = defaultdict(Counter)
    case_count = 0
    case_by_app_model: Counter = Counter()
    cases_with_urls = 0

    for data_dir in (pathlib.Path(d) for d in args.data_dir):
        if not data_dir.exists():
            print(f"WARN: missing {data_dir}", file=sys.stderr)
            continue
        files = sorted(data_dir.glob("*/cases/*.json"))
        for fp in files:
            try:
                with fp.open(encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            meta = case_metadata(fp, data)
            if not meta["case_id"]:
                continue
            case_count += 1
            case_by_app_model[(meta["app"], meta["llm"])] += 1
            trace = data.get("trace") or {}
            urls = extract_urls_from_trace(trace)
            if urls:
                cases_with_urls += 1
            for step_num, url, action in urls:
                per_step_rows.append({
                    **meta,
                    "step": step_num,
                    "url": url,
                    "action_prefix": action,
                    "replayable": looks_replayable(url),
                    "is_webarena": is_webarena_url(url),
                })
                url_counter[url] += 1
                app_url_counter[meta["app"]][url] += 1
                if meta["operator"]:
                    op_url_counter[meta["operator"]][url] += 1

    # Per-step CSV
    per_step_csv = out_dir / "stage3-urls.csv"
    if per_step_rows:
        with per_step_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(per_step_rows[0].keys()))
            w.writeheader()
            w.writerows(per_step_rows)

    # Dedup CSV: one row per URL
    dedup_csv = out_dir / "stage3-urls-dedup.csv"
    with dedup_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "app", "visits", "replayable", "is_webarena"])
        for url, count in url_counter.most_common():
            if count < args.min_visits:
                continue
            best_app = max(
                app_url_counter.keys(),
                key=lambda a: app_url_counter[a].get(url, 0),
                default="",
            )
            w.writerow([url, best_app, count, looks_replayable(url), is_webarena_url(url)])

    # Summary
    total_urls = len(url_counter)
    webarena_urls = sum(1 for u in url_counter if is_webarena_url(u))
    replayable_urls = sum(1 for u in url_counter if looks_replayable(u))
    replay_visits_min = {}
    for threshold in (1, 2, 3, 5, 10):
        replay_visits_min[threshold] = sum(
            1 for u, n in url_counter.items()
            if looks_replayable(u) and n >= threshold
        )

    per_app_urls = {a: len(c) for a, c in app_url_counter.items()}

    # Build wall-time estimates
    lines = [
        "# Stage 3 URL Extraction — for trace-URL SSIM replay",
        "",
        "## Scope",
        "",
        f"- Cases scanned: **{case_count}**",
        f"- Cases with ≥1 URL: **{cases_with_urls}**",
        f"- Total step-URL pairs: **{len(per_step_rows)}**",
        f"- **Unique URLs**: **{total_urls}**",
        f"- Internal WebArena URLs: **{webarena_urls}** ({webarena_urls / max(total_urls,1):.1%})",
        f"- Replayable WebArena URLs: **{replayable_urls}** ({replayable_urls / max(total_urls,1):.1%})",
        "",
        "## URL-frequency filter (replayable URLs only)",
        "",
        "| min visits | URLs |",
        "|---:|---:|",
    ]
    for thr, n in replay_visits_min.items():
        lines.append(f"| ≥{thr} | {n} |")
    lines.append("")

    lines.append("## URLs per app (replayable)")
    lines.append("")
    lines.append("| app | unique URLs | total visits |")
    lines.append("|---|---:|---:|")
    for app, c in sorted(app_url_counter.items(), key=lambda x: -len(x[1])):
        replayable_n = sum(1 for u in c if looks_replayable(u))
        lines.append(f"| {app} | {replayable_n} | {sum(c.values())} |")
    lines.append("")

    # Wall-time projection
    lines.append("## Replay cost estimate")
    lines.append("")
    lines.append(
        "Each capture = Playwright new context + cookie inject + navigate + "
        "wait-for-settle (1.5s) + optional operator inject + screenshot. "
        "Measured in Phase 7 at ~4-6 s/capture on burner EC2 with WebArena "
        "on a local IP."
    )
    lines.append("")
    lines.append(
        "Stage 3 has 26 operators. Full matrix = `N_urls × (1 base + 26 ops) "
        "× reps`. Baseline-noise estimate requires `reps ≥ 2` for at least "
        "the base variant (one real base, one \"base2\" in its own context)."
    )
    lines.append("")
    lines.append("| scenario | URLs | variants | reps | captures | ~h at 5s/capture |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    def est(urls_n: int, variants: int, reps: int, sec: float = 5.0) -> tuple[int, float]:
        total = urls_n * variants * reps
        return total, total * sec / 3600.0

    for thr, tag in [(1, "all replayable"), (2, "visits ≥ 2"), (5, "visits ≥ 5")]:
        urls_n = replay_visits_min[thr]
        # Full matrix
        total, hours = est(urls_n, 1 + 26, 1)
        lines.append(f"| {tag}: full 27 variants ×1 rep  | {urls_n} | 27 | 1 | {total:,} | {hours:.1f} |")
        # Top-6 destructive only
        total, hours = est(urls_n, 1 + 6, 2)
        lines.append(f"| {tag}: top-6 ops ×2 reps       | {urls_n} | 7 | 2 | {total:,} | {hours:.1f} |")

    lines.append("")
    lines.append(
        "**Recommended minimal setup**: visits≥2 URLs × (base + L1 L5 L9 "
        "L11 L12 ML1) × 2 reps. This targets the operators where the "
        "visual-confound question actually matters (bottom-5 most "
        "destructive + ML1). Budget: ~1-2h wall, trivial S3 output."
    )
    lines.append("")
    lines.append(
        "**Paper-maximal setup**: all 27 variants × visits≥1 URLs × 1 rep. "
        "Produces per-operator SSIM distribution for every AMT operator. "
        "Budget: ~10-15h wall; fine to run unattended on burner B."
    )
    lines.append("")

    lines.append("## Top 20 most-visited URLs")
    lines.append("")
    for url, n in url_counter.most_common(20):
        marker = "" if is_webarena_url(url) else "  ⚠ external"
        lines.append(f"- `{url[:140]}` — {n} visits{marker}")
    lines.append("")

    summary_md = out_dir / "stage3-urls-summary.md"
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[extract] cases scanned: {case_count}")
    print(f"[extract] unique URLs: {total_urls} ({webarena_urls} WebArena, {replayable_urls} replayable)")
    print(f"[extract] outputs:")
    print(f"  {per_step_csv}")
    print(f"  {dedup_csv}")
    print(f"  {summary_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3.11
"""Audit Stage 3 data for rate-limit-induced confounds.

A Bedrock 429 / ThrottlingException can corrupt Stage 3 in two ways:

  1. HARD confound — 4 retries all fail → executor records an error step
     → wastes a step from the 30-step budget → case may fail for infra
     reasons, not a11y reasons. Detectable in case JSON
     (steps[].result == "error" AND resultDetail contains "429" or
     "Too many tokens" or "ThrottlingException").

  2. SOFT confound — a retry succeeds, so the case JSON has no error
     step. But the retry+backoff added latency and, crucially, if some
     operators (e.g. L2 wipes ARIA → larger a11y tree → more prompt
     tokens) are more likely to hit TPM limits, the RETRY RATE becomes
     correlated with operator identity. That is a real confound even if
     every retry succeeds. Detectable only in the runner log
     (data/stage3-{claude,llama}/stage3.log with "LLM call attempt N/4
     failed ... Retrying" lines interleaved with "[Pipeline] Running
     test case: ..." markers).

This script reports both, per-operator. Null-hypothesis test: operator
has no effect on retry rate. Significant correlation → note in paper
limitations AND consider re-running affected operators.

Usage:
  # Against downloaded local data (post-experiment):
  python3.11 scripts/amt/audit-rate-limit-confound.py \\
      --data-dir data/stage3-claude \\
      --log-file data/stage3-claude/stage3.log \\
      --label "Stage 3 Claude" \\
      --out results/stage3/rate-limit-audit-claude.md

  # Multiple shards (Claude + Llama):
  python3.11 scripts/amt/audit-rate-limit-confound.py \\
      --data-dir data/stage3-claude data/stage3-llama \\
      --log-file data/stage3-claude/stage3.log data/stage3-llama/stage3.log \\
      --label "Stage 3 Claude+Llama" \\
      --out results/stage3/rate-limit-audit.md

Output: Markdown report with tables + verdict.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Iterable

# ---------------------------------------------------------------------------
# Patterns used to parse the runner log
# ---------------------------------------------------------------------------

# Every case start emits one of these lines in stage3.log (runner console),
# from scheduler.ts. Example:
#   [Pipeline] Running test case: ecommerce_admin:individual:187:0:1:H4
RE_CASE_START = re.compile(r"\[Pipeline\] Running test case:\s+(\S+)")

# LLM retry warning, emitted by llm.ts on 4xx/5xx failures. Example:
#   LLM call attempt 1/4 failed: LLM API returned 429: {"error":{"message":"litellm.RateLimitError ...
# We consider a line to be a "rate-limit retry" iff it matches both patterns:
#   - "LLM call attempt N/... failed"   (retry happened)
#   - "429" OR "Too many tokens" OR "ThrottlingException" OR "RateLimitError"
RE_LLM_RETRY = re.compile(r"LLM call attempt (\d+)/(\d+) failed:")
RE_RATE_LIMIT_TOKEN = re.compile(
    r"429|Too many tokens|ThrottlingException|RateLimitError", re.IGNORECASE
)

# Case ID format: {app}:individual:{taskId}:{ci}:{attempt}:{opId1+opId2...}
RE_CASE_ID = re.compile(
    r"^(?P<app>[^:]+):individual:(?P<task>[^:]+):(?P<ci>[^:]+):(?P<attempt>[^:]+):(?P<op>.+)$"
)


# ---------------------------------------------------------------------------
# Log parsing: which cases saw retries (soft confound)
# ---------------------------------------------------------------------------


def parse_log_retries(log_paths: Iterable[Path]) -> dict[str, dict]:
    """Scan runner logs and attribute retry events to cases.

    The runner log interleaves:
        [Pipeline] Running test case: <case_id>
        ... many lines ...
        LLM call attempt 1/4 failed: ... 429 ...
        LLM call attempt 2/4 failed: ... 429 ...
        ...
        [Pipeline] Running test case: <next_case_id>

    Rate-limit retries are attributed to the most recent case_id seen.

    Returns: {case_id: {"retries_429": int, "retries_other": int,
                        "max_attempt": int, "final_failures_429": int,
                        "final_failures_other": int}}
    """
    per_case: dict[str, dict] = defaultdict(
        lambda: {
            "retries_429": 0,
            "retries_other": 0,
            "max_attempt": 0,
            "final_failures_429": 0,
            "final_failures_other": 0,
        }
    )

    for log_path in log_paths:
        if not log_path.exists():
            print(f"  [warn] log not found: {log_path}", file=sys.stderr)
            continue

        current_case: str | None = None
        with log_path.open("r", errors="replace") as f:
            for line in f:
                m_case = RE_CASE_START.search(line)
                if m_case:
                    current_case = m_case.group(1)
                    continue

                m_retry = RE_LLM_RETRY.search(line)
                if m_retry and current_case is not None:
                    attempt = int(m_retry.group(1))
                    total = int(m_retry.group(2))
                    rec = per_case[current_case]
                    rec["max_attempt"] = max(rec["max_attempt"], attempt)
                    if RE_RATE_LIMIT_TOKEN.search(line):
                        rec["retries_429"] += 1
                        if attempt == total:
                            rec["final_failures_429"] += 1
                    else:
                        rec["retries_other"] += 1
                        if attempt == total:
                            rec["final_failures_other"] += 1

    return dict(per_case)


# ---------------------------------------------------------------------------
# Case JSON parsing: outcomes + hard confound detection
# ---------------------------------------------------------------------------


def load_cases(data_dirs: Iterable[Path]) -> list[dict]:
    """Load every case JSON under */cases/*.json into a list of summaries.

    Each summary has: case_id, app, task, ci, attempt, op, success,
    outcome, total_steps, total_tokens, duration_sec, has_error_step,
    error_is_rate_limit, error_detail_sample.
    """
    summaries: list[dict] = []
    for data_dir in data_dirs:
        # Each data_dir has subdirs <runId>/cases/*.json (and track-a/... symlinks)
        pattern = str(data_dir / "*" / "cases" / "*.json")
        import glob

        for fp in sorted(glob.glob(pattern)):
            try:
                with open(fp) as f:
                    d = json.load(f)
            except Exception:
                continue

            trace = d.get("trace") or {}
            steps = trace.get("steps") or []
            error_steps = [s for s in steps if s.get("result") == "error"]
            error_is_rl = False
            error_detail_sample = None
            for s in error_steps:
                rd = s.get("resultDetail") or ""
                if RE_RATE_LIMIT_TOKEN.search(rd):
                    error_is_rl = True
                    if error_detail_sample is None:
                        error_detail_sample = rd[:200]
                    break

            case_id = d.get("caseId") or trace.get("caseId") or ""
            m = RE_CASE_ID.match(case_id)
            parts = m.groupdict() if m else {}

            summaries.append(
                {
                    "case_id": case_id,
                    "app": parts.get("app"),
                    "task": parts.get("task"),
                    "ci": parts.get("ci"),
                    "attempt": parts.get("attempt"),
                    "op": parts.get("op"),
                    "success": bool(trace.get("success")),
                    "outcome": trace.get("outcome") or "unknown",
                    "total_steps": trace.get("totalSteps") or 0,
                    "total_tokens": trace.get("totalTokens") or 0,
                    "duration_sec": (trace.get("durationMs") or 0) / 1000.0,
                    "has_error_step": bool(error_steps),
                    "error_is_rate_limit": error_is_rl,
                    "error_detail_sample": error_detail_sample,
                }
            )

    return summaries


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------


def chi2_2x2(a: int, b: int, c: int, d: int) -> tuple[float, float] | None:
    """2x2 chi-square via scipy if available, else None.

    Layout:
                      success    failure
        retried       a          b
        not_retried   c          d
    """
    try:
        from scipy.stats import chi2_contingency

        _, p, _, _ = chi2_contingency([[a, b], [c, d]])
        return (0.0, p)
    except Exception:
        return None


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(len(s) * q)
    idx = min(idx, len(s) - 1)
    return s[idx]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(
    label: str,
    cases: list[dict],
    retries_by_case: dict[str, dict],
) -> str:
    lines: list[str] = []
    lines.append(f"# Rate-Limit Confound Audit — {label}")
    lines.append("")
    lines.append(f"Generated by `scripts/amt/audit-rate-limit-confound.py`.")
    lines.append("")
    lines.append(f"Total cases analysed: **{len(cases)}**")
    lines.append(
        f"Total cases with attributable log retry events: **{len(retries_by_case)}**"
    )
    lines.append("")

    # ---------- Hard confound ----------
    hard_rl = [c for c in cases if c["error_is_rate_limit"]]
    hard_other_err = [
        c for c in cases if c["has_error_step"] and not c["error_is_rate_limit"]
    ]
    lines.append("## §1. Hard confound (final 429 escaping to case JSON)")
    lines.append("")
    lines.append(
        f"Cases with `resultDetail` containing 429/ThrottlingException/Too many tokens: "
        f"**{len(hard_rl)}** ({len(hard_rl)/max(len(cases),1):.1%})"
    )
    lines.append(
        f"Cases with other error steps (bridge crash, LLM other, etc.): "
        f"**{len(hard_other_err)}** ({len(hard_other_err)/max(len(cases),1):.1%})"
    )
    lines.append("")
    if hard_rl:
        lines.append("Sample hard-confound cases (first 5):")
        lines.append("")
        for c in hard_rl[:5]:
            lines.append(
                f"- `{c['case_id']}` → success={c['success']}, steps={c['total_steps']}, "
                f"detail: `{c['error_detail_sample']}`"
            )
        lines.append("")
        lines.append(
            "> **Action required**: these cases are contaminated. Consider excluding "
            "from primary analysis or re-running."
        )
    else:
        lines.append(
            "> ✅ No hard confound detected. The 4-retry loop absorbed every rate limit."
        )
    lines.append("")

    # ---------- Soft confound ----------
    lines.append("## §2. Soft confound (retries absorbed but attributed to cases)")
    lines.append("")
    per_op_retry_429 = defaultdict(int)
    per_op_retry_count = defaultdict(int)
    per_op_total = Counter()
    per_op_succ = Counter()
    per_op_tokens: dict[str, list[int]] = defaultdict(list)
    per_op_duration: dict[str, list[float]] = defaultdict(list)
    per_op_has_retry = defaultdict(int)

    for c in cases:
        op = c["op"] or "?"
        per_op_total[op] += 1
        if c["success"]:
            per_op_succ[op] += 1
        per_op_tokens[op].append(c["total_tokens"])
        per_op_duration[op].append(c["duration_sec"])
        rec = retries_by_case.get(c["case_id"])
        if rec:
            per_op_retry_429[op] += rec["retries_429"]
            per_op_retry_count[op] += rec["retries_429"] + rec["retries_other"]
            if rec["retries_429"] > 0:
                per_op_has_retry[op] += 1

    total_retry_429 = sum(per_op_retry_429.values())
    total_retry_other = sum(r["retries_other"] for r in retries_by_case.values())
    lines.append(
        f"Total 429-retry events in log: **{total_retry_429}** "
        f"(across {sum(1 for r in retries_by_case.values() if r['retries_429']>0)} cases)"
    )
    lines.append(f"Total other-retry events in log: **{total_retry_other}**")
    lines.append(
        f"Cases with ≥1 429 retry: "
        f"**{sum(per_op_has_retry.values())}** "
        f"({sum(per_op_has_retry.values())/max(len(cases),1):.1%} of all cases)"
    )
    lines.append("")

    # Per-operator retry table
    lines.append("### Per-operator 429 retry rate")
    lines.append("")
    lines.append("| Operator | N | Cases w/ 429 retry | % | 429 events | success |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    rows = []
    for op in sorted(per_op_total):
        n = per_op_total[op]
        has_rl = per_op_has_retry[op]
        events = per_op_retry_429[op]
        succ = per_op_succ[op] / n if n else 0
        rows.append((has_rl / n if n else 0, op, n, has_rl, events, succ))
    for pct, op, n, has_rl, events, succ in sorted(rows, reverse=True):
        lines.append(
            f"| `{op}` | {n} | {has_rl} | {pct:.1%} | {events} | {succ:.1%} |"
        )
    lines.append("")

    # Correlation test: is retry rate per operator correlated with success?
    # We do it two ways:
    #  (a) Within-operator: cases that hit 429 vs cases that didn't, does
    #      success rate differ? (tests whether the retry itself is predictive)
    #  (b) Across operators: Spearman corr between operator retry_rate and
    #      operator success_rate. (tests whether operators with more
    #      throttling are the same ones that drop success — that's the
    #      confound scenario)
    lines.append("### §2.1 Within-operator confound test")
    lines.append("")
    lines.append("For each operator with ≥5 cases hitting 429: does hitting a 429")
    lines.append("retry correlate with lower success? (If yes → the 429 added an")
    lines.append("infra-failure mode on top of the semantic effect.)")
    lines.append("")
    lines.append("| Op | retried&succ | retried&fail | clean&succ | clean&fail | χ² p-value |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    any_sig = False
    for op in sorted(per_op_total):
        # Need to recompute per-op contingency using case-level data
        a = b = c = d = 0
        for case in cases:
            if case["op"] != op:
                continue
            rec = retries_by_case.get(case["case_id"])
            hit429 = rec is not None and rec["retries_429"] > 0
            if hit429 and case["success"]:
                a += 1
            elif hit429 and not case["success"]:
                b += 1
            elif not hit429 and case["success"]:
                c += 1
            elif not hit429 and not case["success"]:
                d += 1
        if a + b < 5:
            continue
        test = chi2_2x2(a, b, c, d)
        p_str = "n/a (scipy missing)"
        if test is not None:
            p = test[1]
            p_str = f"{p:.3f}"
            if p < 0.05:
                any_sig = True
                p_str += " **SIG**"
        lines.append(f"| `{op}` | {a} | {b} | {c} | {d} | {p_str} |")
    lines.append("")
    if any_sig:
        lines.append(
            "> ⚠ **At least one operator shows retries ↔ outcome correlation.** "
            "Inspect those cases manually before trusting per-operator drops."
        )
    else:
        lines.append(
            "> ✅ No operator shows a significant retries ↔ outcome correlation "
            "(at α=0.05, two-sided). Retries absorbed without affecting outcomes."
        )
    lines.append("")

    lines.append("### §2.2 Across-operator confound test (rank correlation)")
    lines.append("")
    lines.append(
        "If operators with more 429 retries are *also* the ones with lower "
        "success rates, that's a confound: we can't cleanly attribute the drop "
        "to the operator vs to throttling."
    )
    lines.append("")
    ops = [op for op in sorted(per_op_total) if per_op_total[op] >= 10]
    retry_pcts = [per_op_has_retry[op] / per_op_total[op] for op in ops]
    succ_pcts = [per_op_succ[op] / per_op_total[op] for op in ops]
    try:
        from scipy.stats import spearmanr

        rho, pval = spearmanr(retry_pcts, succ_pcts)
        lines.append(f"Spearman ρ = **{rho:+.3f}**, p = **{pval:.3f}** (N={len(ops)} operators)")
        if pval < 0.05:
            if rho < 0:
                lines.append(
                    "> ⚠ **Negative correlation detected**: operators with more "
                    "429 retries tend to have lower success. This is the classic "
                    "confound scenario. Check whether high-retry operators are "
                    "the same ones you want to call out as destructive."
                )
            else:
                lines.append(
                    "> ⚠ Positive correlation (unexpected): high-retry operators "
                    "have higher success. Review manually."
                )
        else:
            lines.append(
                "> ✅ No significant rank correlation between retry rate and "
                "success rate."
            )
    except ImportError:
        lines.append("scipy not available — install to get Spearman p-value.")
    lines.append("")

    # ---------- Token burden ----------
    lines.append("## §3. Token burden per operator (input into rate-limit pressure)")
    lines.append("")
    lines.append(
        "Operators that produce larger a11y trees cause larger prompts and are "
        "intrinsically more likely to hit TPM limits. This table shows mean "
        "total tokens per case by operator — use as a sanity check on whether "
        "the retry rates in §2 track the token-burden ranking."
    )
    lines.append("")
    lines.append("| Operator | N | tokens p50 | tokens p90 | tokens max | success |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    tok_rows = []
    for op in sorted(per_op_total):
        toks = per_op_tokens[op]
        if not toks:
            continue
        tok_rows.append(
            (
                percentile(toks, 0.5),
                op,
                len(toks),
                percentile(toks, 0.5),
                percentile(toks, 0.9),
                max(toks),
                per_op_succ[op] / per_op_total[op],
            )
        )
    for _, op, n, p50, p90, mx, succ in sorted(tok_rows, reverse=True):
        lines.append(
            f"| `{op}` | {n} | {p50:,.0f} | {p90:,.0f} | {mx:,.0f} | {succ:.1%} |"
        )
    lines.append("")

    # ---------- Verdict ----------
    lines.append("## §4. Verdict")
    lines.append("")
    n_hard = len(hard_rl)
    n_soft_cases = sum(per_op_has_retry.values())
    if n_hard == 0 and n_soft_cases == 0:
        lines.append("✅ **Clean**: no rate-limit confound detected.")
    elif n_hard == 0 and not any_sig:
        lines.append(
            f"🟢 **Acceptable**: {n_soft_cases} cases saw 429 retries but all "
            "were absorbed by the retry loop. No per-operator correlation with "
            "success rate. Safe to proceed, but mention in paper limitations."
        )
    elif n_hard == 0 and any_sig:
        lines.append(
            f"🟡 **Inspect**: {n_soft_cases} cases saw retries absorbed, and "
            "at least one operator shows a retries↔success correlation. "
            "Investigate the flagged operator(s) above. Consider: (a) excluding "
            "affected cases, (b) re-running, or (c) documenting as limitation."
        )
    else:
        lines.append(
            f"🔴 **Contaminated**: {n_hard} cases have final 429 failures in "
            "the case JSON. These cases cannot be cleanly attributed to the "
            "operator. Re-run or exclude."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Regenerate: rerun this script with the same args.*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--data-dir",
        nargs="+",
        required=True,
        help="One or more data/stage3-* directories containing <runId>/cases/*.json",
    )
    ap.add_argument(
        "--log-file",
        nargs="*",
        default=[],
        help="One or more runner log files (stage3.log) to extract retry events from. "
        "If omitted, only hard confounds are detected (case JSON only).",
    )
    ap.add_argument("--label", default="Stage 3", help="Label for report header")
    ap.add_argument("--out", required=True, help="Output markdown path")
    args = ap.parse_args()

    data_dirs = [Path(p) for p in args.data_dir]
    log_files = [Path(p) for p in args.log_file]

    for p in data_dirs:
        if not p.exists():
            print(f"[error] data dir missing: {p}", file=sys.stderr)
            return 2

    print(f"[audit] loading cases from {len(data_dirs)} dir(s)...")
    cases = load_cases(data_dirs)
    print(f"[audit] loaded {len(cases)} cases")

    print(f"[audit] scanning {len(log_files)} log(s) for retry events...")
    retries = parse_log_retries(log_files)
    print(f"[audit] attributed retries to {len(retries)} cases")

    report = build_report(args.label, cases, retries)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(f"[audit] report written to {out}")

    # Also print a compact verdict on stdout
    # (extract the §4 verdict paragraph for easy eyeballing)
    after = report.split("## §4. Verdict", 1)[1] if "## §4. Verdict" in report else ""
    verdict = after.split("---", 1)[0].strip()
    print()
    print("--- VERDICT ---")
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Case-JSON loaders shared across stage verifiers.

Two on-disk layouts are supported:

  (A) "Flat" layout — used by composite (pilot4-*, expansion-*),
      Mode A (mode-a-shard-{a,b}, mode-a-llama4-textonly), and
      C.2 (c2-composition-shard-{a,b}):
          <data_dir>/<run-uuid>/cases/<casename>.json     # case JSON inline

  (B) "Per-case directory" layout — used by Stage 3
      (stage3-claude, stage3-llama):
          <data_dir>/<uuid>/cases/<casedir>/trace-attempt-*.json
          <data_dir>/track-a/runs/<uuid>/cases/<casedir>/{trace-attempt-N.json,
                                                          scan-result.json}

When multiple UUID-named subdirectories exist under the same parent, we keep
only the one with the most case files (others are stale partial runs).
This matches `export_combined_data.py:find_case_files`.

GT corrections (Docker-drift tasks 41 / 198 / 293) are applied uniformly via
`apply_gt_corrections`.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from analysis._constants import GT_CORRECTIONS

SKIP_DIR_NAMES = {"track-a", "exports"}
SKIP_FILE_NAMES = {"run-state.json", "manifest.json"}


# ---------------------------------------------------------------------------
# Layout-A loader (flat: <run-uuid>/cases/*.json)
# ---------------------------------------------------------------------------

def _find_uuid_groups_flat(parent: Path) -> list[tuple[Path, list[Path]]]:
    """Walk `parent`, yield (uuid_dir, [json_files]) for every dir containing a
    populated `cases/`. Recurses one level for the pilot4-cua-style nesting."""
    out: list[tuple[Path, list[Path]]] = []
    if not parent.is_dir():
        return out
    for entry in sorted(parent.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIR_NAMES:
            continue
        cases = entry / "cases"
        if cases.is_dir():
            files = sorted(
                f for f in cases.iterdir()
                if f.is_file() and f.suffix == ".json" and f.name not in SKIP_FILE_NAMES
            )
            if files:
                out.append((entry, files))
        else:
            # one level deeper (pilot4-cua/pilot4-cua/<uuid>/cases/...)
            out.extend(_find_uuid_groups_flat(entry))
    return out


def _select_largest_uuid(groups: list[tuple[Path, list[Path]]]) -> list[Path]:
    """When multiple UUIDs share a parent, keep the one with the most files.

    Mirrors `export_combined_data.find_case_files` so verifier counts agree with
    the CSV produced by export.
    """
    by_parent: dict[Path, list[tuple[Path, list[Path]]]] = defaultdict(list)
    for uuid_dir, files in groups:
        by_parent[uuid_dir.parent].append((uuid_dir, files))
    chosen: list[Path] = []
    for groups_in_parent in by_parent.values():
        groups_in_parent.sort(key=lambda g: len(g[1]), reverse=True)
        chosen.extend(groups_in_parent[0][1])
    return chosen


def load_cases_flat(data_dirs: Iterable[Path]) -> list[dict]:
    """Load cases from layout-A directories (composite / Mode A / C.2).

    Returns a list of normalized dicts:
      {caseId, taskId, opId, agent, success, totalTokens, totalSteps,
       answer (str), trace_path (Path)}

    Unparseable file names (caseId without 6 colon-separated parts) are
    silently skipped — same behavior as `amt_statistics.load_cases`.

    Expected case totals (designed N's, see analysis/_constants.py):

        Phase 1 — Composite (N=1,040)
            pilot4-full(240) + pilot4-cua(120) + expansion-claude(140)
            + expansion-llama4(260) + expansion-som(140) + expansion-cua(140)
            Note: pilot4-cua has 121 files on disk; one is a hung-bridge
            retry from a stale UUID. `_select_largest_uuid` picks the full
            run (120 files) yielding the design N=1,040.

        Phase 2 — Mode A (N=4,056)
            mode-a-shard-a(1,638) + mode-a-shard-b(1,404) = 3,042 (Claude × 3 archs)
            + mode-a-llama4-textonly(1,014) = 4,056

        Phase 3 — C.2 composition (N=2,184)
            c2-composition-shard-a(1,092) + c2-composition-shard-b(1,092) = 2,184
            ⚠ The paper §4.122, several handoffs, and pre-2026-05-15 docs
            misstate this as 2,188 due to an arithmetic error
            (28 pairs × 13 tasks × 2 archs × 3 reps = 2,184, not 2,188).
            The data on disk has always matched the design exactly.
    """
    cases: list[dict] = []
    for data_dir in data_dirs:
        groups = _find_uuid_groups_flat(Path(data_dir))
        files = _select_largest_uuid(groups)
        for fpath in files:
            # Skip non-trace files that may slip into cases/
            if any(skip in fpath.name for skip in ("scan-result", "trace-attempt", "classification")):
                continue
            try:
                with fpath.open() as fh:
                    d = json.load(fh)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            cid = d.get("caseId", "")
            parts = cid.split(":")
            if len(parts) != 6:
                continue
            t = d.get("trace", {})
            answer = _extract_answer(t)
            cases.append({
                "caseId": cid,
                "taskId": parts[2],
                "opId": parts[5],
                "variant": parts[1],
                "agent": t.get("agentConfig", {}).get("observationMode", "?"),
                "success": t.get("success", False),
                "outcome": t.get("outcome", ""),
                "totalTokens": t.get("totalTokens", 0),
                "totalSteps": t.get("totalSteps", 0),
                "answer": answer,
                "trace_path": fpath,
            })
    return cases


# ---------------------------------------------------------------------------
# Layout-B loader (Stage 3: per-case directory)
# ---------------------------------------------------------------------------

def load_cases_stage3(data_dir: Path) -> list[dict]:
    """Load Stage 3 cases (per-case directory layout).

    Each case is a directory `<app>_individual_<taskId>_<ci>_<attempt>_<opId>/`
    containing `trace-attempt-N.json` and `scan-result.json`. We use the
    highest-numbered attempt as the final result.
    """
    data_dir = Path(data_dir)
    case_dirs = list(data_dir.glob("*/runs/*/cases/*/"))
    if not case_dirs:
        case_dirs = list(data_dir.glob("*/cases/*/"))
    cases: list[dict] = []
    for case_dir in case_dirs:
        name = case_dir.name
        if "_individual_" not in name:
            continue
        app, rest = name.split("_individual_", 1)
        after = rest.split("_")
        if len(after) < 4:
            continue
        tid = after[0]
        opId = after[3]

        trace_files = sorted(case_dir.glob("trace-attempt-*.json"))
        if not trace_files:
            continue
        try:
            with trace_files[-1].open() as f:
                t = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        answer = _extract_answer(t)
        cases.append({
            "caseId": name,
            "taskId": tid,
            "opId": opId,
            "app": app,
            "variant": "individual",
            "agent": t.get("agentConfig", {}).get("observationMode", "text-only"),
            "success": t.get("success", False),
            "outcome": t.get("outcome", ""),
            "totalTokens": t.get("totalTokens", 0),
            "totalSteps": t.get("totalSteps", 0),
            "answer": answer,
            "trace_path": trace_files[-1],
        })
    return cases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_answer(trace: dict) -> str:
    """Extract the final agent answer from a trace dict.

    Looks for the first `send_msg_to_user(...)` action, falling back to a
    `Task complete: ...` line in the bridge log for CUA agents.
    """
    for s in trace.get("steps", []):
        a = s.get("action", "")
        if "send_msg_to_user" in a:
            return a
    # CUA fallback
    bl = trace.get("bridgeLog", "")
    for line in bl.split("\n"):
        if "Task complete" in line:
            tc_idx = line.find("Task complete")
            if tc_idx >= 0:
                rest = line[tc_idx:]
                colon_idx = rest.find(":")
                if colon_idx >= 0:
                    return rest[colon_idx + 1:].strip()
    return ""


def apply_gt_corrections(cases: list[dict], corrections: dict[str, list[str]] | None = None) -> list[dict]:
    """Mutate `cases` in place: for any case in `corrections` whose original
    answer matches a valid string, flip success → True. Returns the list.

    Idempotent. `corrections` defaults to `analysis._constants.GT_CORRECTIONS`.
    """
    corr = corrections if corrections is not None else GT_CORRECTIONS
    for c in cases:
        tid = str(c.get("taskId", ""))
        if tid not in corr:
            continue
        if c.get("success"):
            continue
        ans = (c.get("answer") or "").lower()
        if not ans:
            continue
        for valid in corr[tid]:
            if valid in ans:
                c["success"] = True
                break
    return cases


def dedup_attempts(cases: list[dict], max_attempts: int = 5) -> list[dict]:
    """Defensive dedup: per (caseId-without-attempt) cell keep at most
    `max_attempts` entries (the lowest-numbered ones).

    Currently a no-op for our data (export already picks the largest UUID
    so duplicates collapse there). Kept as a safety net for future re-imports.
    """
    by_cell: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        # composite caseId = "<app>:<variant>:<task>:<agent>:<model>:<rep>" — strip rep
        # stage3 caseId = "<app>_individual_<task>_<ci>_<attempt>_<op>" — strip _<attempt>_<op>
        cid = c.get("caseId", "")
        if ":" in cid:
            key = ":".join(cid.split(":")[:-1])
        else:
            parts = cid.rsplit("_", 2)
            key = parts[0] if len(parts) >= 2 else cid
        by_cell[key].append(c)
    kept: list[dict] = []
    for key, group in by_cell.items():
        kept.extend(sorted(group, key=lambda c: c.get("caseId", ""))[:max_attempts])
    return kept


# ---------------------------------------------------------------------------
# Convenience aggregator
# ---------------------------------------------------------------------------

def count_by(cases: list[dict], key: str) -> dict[str, int]:
    """Count cases grouped by `key` (e.g. 'opId', 'agent', 'variant')."""
    out: dict[str, int] = defaultdict(int)
    for c in cases:
        out[c.get(key, "")] += 1
    return dict(out)


def success_rate(cases: list[dict]) -> float:
    """Fraction of cases with success=True. Returns 0.0 on empty input."""
    if not cases:
        return 0.0
    return sum(1 for c in cases if c.get("success")) / len(cases)

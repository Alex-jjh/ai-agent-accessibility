"""
Phase 2 — Mode A depth verifier.

Reads case JSONs from `data/mode-a-shard-{a,b}/` (Claude × 3 archs) and
`data/mode-a-llama4-textonly/` (Llama 4 text-only). Asserts the count
totals from `_constants.py` and confirms the per-architecture split.

Heavier statistics (Fisher exact per operator, Holm-Bonferroni, signature
alignment) live in `analysis.amt_statistics`; this module is the pre-flight
sanity layer that runs in `make verify-all`.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import StageReport, expect_count
from analysis.lib.load import apply_gt_corrections, load_cases_flat
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"

CLAUDE_DIRS = [DATA / "mode-a-shard-a", DATA / "mode-a-shard-b"]
LLAMA_DIRS = [DATA / "mode-a-llama4-textonly"]


class Verifier(StageVerifier):
    stage_id = "phase2_mode_a"
    label = "Mode A depth (13 tasks × 26 ops × 3 archs Claude + Llama 4 text)"

    def audit(self, report: StageReport) -> None:
        for d in CLAUDE_DIRS + LLAMA_DIRS:
            if not d.exists():
                report.add(expect_count(
                    f"{self.stage_id}.dir.{d.name}",
                    f"{d.relative_to(REPO_ROOT)} exists",
                    1, 0,
                ))
                return  # cannot continue without data

        claude_cases = apply_gt_corrections(load_cases_flat(CLAUDE_DIRS))
        llama_cases = apply_gt_corrections(load_cases_flat(LLAMA_DIRS))

        report.add(expect_count(
            f"{self.stage_id}.claude.N",
            "Mode A Claude case count (3 archs × 26 ops × 13 tasks × 3 reps)",
            C.N_MODE_A_CLAUDE, len(claude_cases),
        ))
        report.add(expect_count(
            f"{self.stage_id}.llama.N",
            "Mode A Llama 4 case count (text × 26 ops × 13 tasks × 3 reps)",
            C.N_MODE_A_LLAMA, len(llama_cases),
        ))
        report.add(expect_count(
            f"{self.stage_id}.total.N",
            "Mode A total = Claude + Llama 4",
            C.N_MODE_A, len(claude_cases) + len(llama_cases),
        ))

        # Per-arch split for Claude (text-only / vision-only / cua)
        agents = Counter(c.get("agent") for c in claude_cases)
        expected_per_arch = C.N_MODE_A_CLAUDE // 3  # 1014 each
        for agent_label in ("text-only", "vision-only", "cua"):
            report.add(expect_count(
                f"{self.stage_id}.claude.arch.{agent_label}",
                f"Claude {agent_label} share of Mode A",
                expected_per_arch, agents.get(agent_label, 0),
            ))

        # Operator coverage: each of 26 ops should appear in Claude text-only
        text_ops = Counter(c["opId"] for c in claude_cases if c["agent"] == "text-only")
        ops_seen = set(text_ops)
        ops_expected = set(C.ALL_OPS)
        missing = ops_expected - ops_seen
        unexpected = ops_seen - ops_expected
        report.add(expect_count(
            f"{self.stage_id}.claude.text.ops_missing",
            "operators absent from Claude text-only Mode A",
            0, len(missing),
        ))
        report.add(expect_count(
            f"{self.stage_id}.claude.text.ops_unexpected",
            "operators present beyond the 26-op AMT taxonomy",
            0, len(unexpected),
        ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

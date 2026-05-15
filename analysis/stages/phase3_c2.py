"""
Phase 3 — C.2 compositional study verifier.

Design size: 28 pairs × 13 tasks × 2 archs (text-only + CUA) × 3 reps = **2,184**.

Note: Pre-2026-05-15 the paper, handoffs, and several docs incorrectly
stated 2,188 due to an arithmetic error (2,184 was correct from day one).
The data on disk has always matched 2,184 exactly.
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

C2_DIRS = [DATA / "c2-composition-shard-a", DATA / "c2-composition-shard-b"]


class Verifier(StageVerifier):
    stage_id = "phase3_c2"
    label = "C.2 compositional study (28 pairs × 13 tasks × 2 archs × 3 reps)"

    def audit(self, report: StageReport) -> None:
        for d in C2_DIRS:
            if not d.exists():
                report.add(expect_count(
                    f"{self.stage_id}.dir.{d.name}",
                    f"{d.relative_to(REPO_ROOT)} exists",
                    1, 0,
                ))
                return

        cases = apply_gt_corrections(load_cases_flat(C2_DIRS))

        report.add(expect_count(
            f"{self.stage_id}.N",
            "C.2 total = 28 × 13 × 2 × 3",
            C.N_C2, len(cases),
        ))

        # Each shard should hold half (1092 each)
        for d in C2_DIRS:
            shard_cases = apply_gt_corrections(load_cases_flat([d]))
            report.add(expect_count(
                f"{self.stage_id}.shard.{d.name}",
                f"{d.name} case count",
                C.N_C2 // 2, len(shard_cases),
            ))

        # Per-arch split (text-only + cua, ~1092 each)
        agents = Counter(c.get("agent") for c in cases)
        expected_per_arch = C.N_C2 // 2
        for agent_label in ("text-only", "cua"):
            report.add(expect_count(
                f"{self.stage_id}.arch.{agent_label}",
                f"{agent_label} share of C.2",
                expected_per_arch, agents.get(agent_label, 0),
            ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

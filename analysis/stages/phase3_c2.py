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
from analysis.lib.assertions import Assertion, StageReport, expect_count, expect_pp
from analysis.lib.load import apply_gt_corrections, load_cases_flat
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"

C2_DIRS = [DATA / "c2-composition-shard-a", DATA / "c2-composition-shard-b"]
MODE_A_DIRS = [DATA / "mode-a-shard-a", DATA / "mode-a-shard-b"]


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

        # Super-additivity finding (paper §5.4): of 28 pairs, 15 super / 9 additive
        # / 4 sub, binomial p=0.019 (super vs sub, H0 p=0.5). Reproduced via the
        # canonical amt_statistics path (Mode A singletons + C.2 pairs, text-only).
        if all(d.exists() for d in MODE_A_DIRS):
            from analysis.amt_statistics import test_compositional_interaction
            claude_singletons = apply_gt_corrections(load_cases_flat(MODE_A_DIRS))
            _, summ = test_compositional_interaction(claude_singletons, cases, agent="text-only")
            report.add(expect_count(
                f"{self.stage_id}.super_additive",
                "C.2 super-additive pair count (paper §5.4: 15/28)",
                C.C2_SUPER_ADDITIVE, summ["super"],
            ))
            report.add(expect_count(
                f"{self.stage_id}.additive",
                "C.2 additive pair count (paper §5.4: 9/28)",
                C.C2_ADDITIVE, summ["additive"],
            ))
            report.add(expect_count(
                f"{self.stage_id}.sub_additive",
                "C.2 sub-additive pair count (paper §5.4: 4/28)",
                C.C2_SUB_ADDITIVE, summ["sub"],
            ))
            report.add(Assertion(
                name=f"{self.stage_id}.binomial_p",
                description="C.2 super-vs-sub binomial p (paper §5.4: 0.019)",
                expected=C.C2_BINOMIAL_P,
                actual=round(summ["binomial_p"], 3),
                passed=abs(summ["binomial_p"] - C.C2_BINOMIAL_P) <= 0.001,
                tolerance="±0.001",
            ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

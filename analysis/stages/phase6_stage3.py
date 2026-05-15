"""
Phase 6 — Stage 3 breadth verifier (primary dataset).

48 tasks × 26 ops × 3 reps × 2 models = 7,488 cases. Reads case JSONs
from `data/stage3-{claude,llama}/` and asserts:
  * Per-model case counts (3,744 each)
  * Operator coverage (all 26 present, both models)
  * Overall success rates (Claude 89.5%, Llama 67.4%)
  * Headline per-operator drops vs paper (L1 −28pp Claude, L11 +2.3 Claude / +14.1 Llama)
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import (
    StageReport, expect_count, expect_rate, expect_pp,
)
from analysis.lib.load import apply_gt_corrections, load_cases_stage3, success_rate
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
CLAUDE_DIR = DATA / "stage3-claude"
LLAMA_DIR = DATA / "stage3-llama"


def _per_op_rate(cases: list[dict]) -> dict[str, float]:
    """opId → success rate."""
    by_op: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        by_op[c["opId"]].append(c)
    return {op: success_rate(cs) for op, cs in by_op.items()}


def _h_baseline(cases: list[dict]) -> float:
    """Pooled success rate across all H-family operators."""
    h_cases = [c for c in cases if c.get("opId", "").startswith("H")]
    return success_rate(h_cases)


class Verifier(StageVerifier):
    stage_id = "phase6_stage3"
    label = "Stage 3 breadth (48 tasks × 26 ops × 3 reps × 2 models)"

    def audit(self, report: StageReport) -> None:
        for d in (CLAUDE_DIR, LLAMA_DIR):
            if not d.exists():
                report.add(expect_count(
                    f"{self.stage_id}.dir.{d.name}",
                    f"{d.relative_to(REPO_ROOT)} exists",
                    1, 0,
                ))
                return

        claude = apply_gt_corrections(load_cases_stage3(CLAUDE_DIR))
        llama = apply_gt_corrections(load_cases_stage3(LLAMA_DIR))

        # 1. N counts
        report.add(expect_count(
            f"{self.stage_id}.claude.N",
            "Stage 3 Claude case count (48 × 26 × 3)",
            C.N_STAGE3_CLAUDE, len(claude),
        ))
        report.add(expect_count(
            f"{self.stage_id}.llama.N",
            "Stage 3 Llama case count (48 × 26 × 3)",
            C.N_STAGE3_LLAMA, len(llama),
        ))
        report.add(expect_count(
            f"{self.stage_id}.total.N",
            "Stage 3 total",
            C.N_STAGE3, len(claude) + len(llama),
        ))

        # 2. Overall success rates
        report.add(expect_rate(
            f"{self.stage_id}.claude.overall_rate",
            "Stage 3 Claude overall success rate",
            C.STAGE3_OVERALL_CLAUDE, success_rate(claude),
            tol_frac=0.005,
        ))
        report.add(expect_rate(
            f"{self.stage_id}.llama.overall_rate",
            "Stage 3 Llama overall success rate",
            C.STAGE3_OVERALL_LLAMA, success_rate(llama),
            tol_frac=0.005,
        ))

        # 3. H-baseline + per-op drops vs paper claims
        h_claude = _h_baseline(claude)
        report.add(expect_rate(
            f"{self.stage_id}.claude.h_baseline",
            "Stage 3 Claude H-operator baseline",
            C.STAGE3_H_BASELINE_CLAUDE, h_claude,
            tol_frac=0.01,
        ))

        per_op_claude = _per_op_rate(claude)
        for op, expected_drop_pp in C.STAGE3_DROPS_BREADTH_CLAUDE.items():
            rate = per_op_claude.get(op)
            if rate is None:
                continue
            actual_drop_pp = (rate - h_claude) * 100
            report.add(expect_pp(
                f"{self.stage_id}.claude.drop.{op}",
                f"Claude {op} drop vs H-baseline",
                expected_drop_pp, actual_drop_pp,
                tol_pp=1.5,  # rate is rounded to 1pp in paper; allow 1.5pp slack
            ))

        # 4. L11 cross-model gap (sign: negative = below H-baseline)
        rate_l11_claude = per_op_claude.get("L11")
        if rate_l11_claude is not None:
            actual_pp = (rate_l11_claude - h_claude) * 100
            report.add(expect_pp(
                f"{self.stage_id}.claude.L11",
                "Claude L11 drop (adaptive recovery — small drop ~−2.3pp)",
                C.L11_DROP_BREADTH_CLAUDE, actual_pp,
                tol_pp=1.5,
            ))

        per_op_llama = _per_op_rate(llama)
        rate_l11_llama = per_op_llama.get("L11")
        h_llama = _h_baseline(llama)
        if rate_l11_llama is not None:
            actual_pp = (rate_l11_llama - h_llama) * 100
            report.add(expect_pp(
                f"{self.stage_id}.llama.L11",
                "Llama 4 L11 drop (no adaptation — large drop ~−14.1pp)",
                C.L11_DROP_BREADTH_LLAMA, actual_pp,
                tol_pp=1.5,
            ))

        # 5. Operator coverage
        ops_claude = set(per_op_claude)
        ops_llama = set(per_op_llama)
        report.add(expect_count(
            f"{self.stage_id}.claude.ops_seen",
            "Claude Stage 3 operator coverage",
            26, len(ops_claude),
        ))
        report.add(expect_count(
            f"{self.stage_id}.llama.ops_seen",
            "Llama Stage 3 operator coverage",
            26, len(ops_llama),
        ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

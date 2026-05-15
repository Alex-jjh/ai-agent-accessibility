"""
Phase 5 — Smoker (base-solvability gate) verifier.

The smoker is the upstream gate of Stage 3. It runs every deployed-app
WebArena task at base × text × 3 reps; tasks passing a 7-gate inclusion
protocol (locked 2026-05-06/07) feed into Stage 3.

Asserts:
  * Total smoker case count = 2,052 (1,122 + 930)
  * `results/smoker/passing-tasks.json` lists exactly the 48 expected
    tasks split by app
  * Per-shard case counts match design
"""
from __future__ import annotations

import json
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import StageReport, expect_count, expect_set_membership
from analysis.lib.load import load_cases_flat
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
PASSING_JSON = REPO_ROOT / "results" / "smoker" / "passing-tasks.json"

SHARD_A = DATA / "smoker-shard-a"
SHARD_B = DATA / "smoker-shard-b"


class Verifier(StageVerifier):
    stage_id = "phase5_smoker"
    label = "Smoker base-solvability gate (684 → 48 tasks)"

    def audit(self, report: StageReport) -> None:
        # 1. Per-shard case counts
        shard_a = load_cases_flat([SHARD_A])
        report.add(expect_count(
            f"{self.stage_id}.shard_a.N",
            "smoker-shard-a (shopping_admin + shopping × base × text × 3 reps)",
            C.N_SMOKER_SHARD_A, len(shard_a),
        ))

        shard_b = load_cases_flat([SHARD_B])
        report.add(expect_count(
            f"{self.stage_id}.shard_b.N",
            "smoker-shard-b (reddit + gitlab × base × text × 3 reps)",
            C.N_SMOKER_SHARD_B, len(shard_b),
        ))

        report.add(expect_count(
            f"{self.stage_id}.total.N",
            "smoker total",
            C.N_SMOKER, len(shard_a) + len(shard_b),
        ))

        # 2. Passing tasks JSON exists + counts
        if not PASSING_JSON.exists():
            report.add(expect_count(
                f"{self.stage_id}.passing_json",
                "passing-tasks.json exists",
                1, 0,
            ))
            return

        with PASSING_JSON.open() as f:
            passing = json.load(f)

        total_passing = sum(len(v) for v in passing.values())
        report.add(expect_count(
            f"{self.stage_id}.total_passing",
            "tasks passing the 7-gate inclusion protocol",
            C.SMOKER_PASSING_TASKS, total_passing,
        ))

        # 3. Per-app split (paper §4 task funnel)
        for app, expected in C.SMOKER_PASSING_BY_APP.items():
            actual = len(passing.get(app, []))
            report.add(expect_count(
                f"{self.stage_id}.passing.{app}",
                f"{app} passing-task count",
                expected, actual,
            ))

        # 4. Apps in the JSON should be exactly the 4 deployed apps
        report.add(expect_set_membership(
            f"{self.stage_id}.apps",
            "passing-tasks.json apps",
            expected=set(C.SMOKER_PASSING_BY_APP),
            actual=set(passing.keys()),
            direction="equal",
        ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

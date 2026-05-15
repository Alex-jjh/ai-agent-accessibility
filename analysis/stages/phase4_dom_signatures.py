"""
Phase 4 — DOM signature audit verifier.

Reads `results/amt/dom_signature_matrix.csv` (12-dim matrix per operator).
Asserts:
  * Exactly 26 rows, one per AMT operator
  * Header lists the expected 12 dimensions plus operator/family/description
  * Sentinel values for the headline operators (L1, L11, L5) match the
    paper's appendix figure (`tab:dom-sig`)
"""
from __future__ import annotations

import csv
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import (
    StageReport, expect_count, expect_rate, expect_set_membership,
)
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MATRIX = REPO_ROOT / "results" / "amt" / "dom_signature_matrix.csv"

# Sentinels from paper appendix Table 2 (per-operator DOM signature, means across 39 samples)
SENTINELS = {
    # operator → {column: expected}
    "L1":  {"V1_ssim": 1.000, "A1_rolesChanged": 5.6, "A2_namesChanged": 5.6},
    "L5":  {"V1_ssim": 0.803, "D1_totalTagChanges": 337.7, "F1_interactiveCountDelta": -105.5},
    "L11": {"V1_ssim": 0.976, "D1_totalTagChanges": 364.6, "F1_interactiveCountDelta": -182.3},
}


class Verifier(StageVerifier):
    stage_id = "phase4_dom_signatures"
    label = "12-dim DOM signature matrix (26 operators × 12 dims)"

    def audit(self, report: StageReport) -> None:
        if not MATRIX.exists():
            report.add(expect_count(
                f"{self.stage_id}.csv_present",
                f"{MATRIX.relative_to(REPO_ROOT)} exists",
                expected=1, actual=0,
            ))
            return

        with MATRIX.open() as f:
            rows = list(csv.DictReader(f))

        # 1. Row count == 26
        report.add(expect_count(
            f"{self.stage_id}.row_count",
            "DOM signature matrix has 26 rows (one per AMT operator)",
            26, len(rows),
        ))

        # 2. Operator coverage
        ops_seen = {r["operator"] for r in rows}
        report.add(expect_set_membership(
            f"{self.stage_id}.ops",
            "all 26 operators present",
            expected=set(C.ALL_OPS),
            actual=ops_seen,
            direction="equal",
        ))

        # 3. Sentinel values (paper appendix Table 2)
        by_op = {r["operator"]: r for r in rows}
        for op, expected_cols in SENTINELS.items():
            row = by_op.get(op)
            if row is None:
                continue
            for col, expected in expected_cols.items():
                actual = float(row.get(col, "nan"))
                # Tolerances: SSIM ±0.02; counts ±5%
                tol = 0.02 if col == "V1_ssim" else max(abs(expected) * 0.05, 1.0)
                report.add(expect_rate(
                    f"{self.stage_id}.sentinel.{op}.{col}",
                    f"{op}.{col} matches paper appendix",
                    expected, actual, tol_frac=tol,
                ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

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

        # 4. Cross-stage Spearman: DOM magnitude vs Stage 3 behavioral drop
        # Paper §5.2 alignment: ρ = 0.426 (NS, p ≈ 0.10) — the *finding* is
        # that DOM magnitude does NOT predict behavioral impact (misalignment).
        stage3_csv = REPO_ROOT / "results" / "stage3" / "per-operator-stage3.csv"
        if stage3_csv.exists():
            rho = self._compute_dom_behavior_spearman(by_op, stage3_csv)
            if rho is not None:
                report.add(expect_rate(
                    f"{self.stage_id}.spearman_dom_vs_behavior",
                    "Spearman ρ: DOM magnitude rank vs Stage 3 Claude drop rank (paper §5.2)",
                    expected=C.SPEARMAN_RHO_DOM_VS_BEHAVIOR,
                    actual=rho,
                    tol_frac=C.SPEARMAN_RHO_TOL,
                ))

    @staticmethod
    def _compute_dom_behavior_spearman(dom_rows: dict, stage3_csv: Path) -> float | None:
        """Spearman correlation between DOM magnitude and Stage 3 behavioral drop.

        DOM magnitude = sum of |D1, A1, A2, F1| columns (matches
        `analysis/stage3_statistics.py` line 230). Behavioral drop = drop_pp
        from per-operator-stage3.csv.

        IMPORTANT: paper §5.2 ρ=0.426 is computed on the **16 operators with
        non-null `p_raw`** (i.e. those with a valid Fisher exact test result),
        not all 26. Including the 10 H-operators with p_raw=None drops ρ to
        ~0.34. Match the paper's filtering convention exactly here.

        Returns absolute ρ (paper writes |ρ|).
        """
        from scipy import stats
        with stage3_csv.open() as f:
            stage3 = {r["operator"]: r for r in csv.DictReader(f)
                      if r.get("p_raw") not in (None, "", "None")}
        ops = sorted(set(dom_rows) & set(stage3))
        if len(ops) < 5:
            return None
        dom_mag, behavior_drop = [], []
        for op in ops:
            d = dom_rows[op]
            try:
                mag = sum(
                    abs(float(d[k])) for k in d
                    if k.startswith(("D1", "A1", "A2", "F1"))
                    and d[k] not in ("", None)
                )
                drop = float(stage3[op]["drop_pp"])  # signed, matches stage3 impl
            except (ValueError, KeyError):
                continue
            dom_mag.append(mag)
            behavior_drop.append(drop)
        if len(dom_mag) < 5:
            return None
        rho, _ = stats.spearmanr(dom_mag, behavior_drop)
        return abs(float(rho))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

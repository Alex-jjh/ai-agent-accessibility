"""
Phase 1 — Composite variant verifier.

Reads `results/combined-experiment.csv` (produced by `make export-data`) and
asserts:
  * Total rows == N_COMPOSITE
  * Per-experiment counts match the design matrix
  * Per-(variant, agent, model) success rates match paper claims within tolerance

This phase does NOT re-read raw case JSONs — that's the export step's job.
We trust the CSV; if it's wrong we want a re-export, not a band-aid here.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import (
    StageReport, expect_count, expect_rate,
)
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO_ROOT / "results" / "combined-experiment.csv"

EXPECTED_PER_EXPERIMENT = {
    "pilot4-full": 240,
    "pilot4-cua": 120,
    "expansion-claude": 140,
    "expansion-llama4": 260,
    "expansion-som": 140,
    "expansion-cua": 140,
}


class Verifier(StageVerifier):
    stage_id = "phase1_composite"
    label = "Composite variant study (4 variants × 13 tasks)"

    def audit(self, report: StageReport) -> None:
        if not CSV_PATH.exists():
            report.add(expect_count(
                f"{self.stage_id}.csv_present",
                f"{CSV_PATH.relative_to(REPO_ROOT)} exists",
                expected=1, actual=0,
            ))
            return

        with CSV_PATH.open() as f:
            rows = list(csv.DictReader(f))

        # 1. Total N
        report.add(expect_count(
            f"{self.stage_id}.N",
            "total rows in combined-experiment.csv",
            C.N_COMPOSITE, len(rows),
        ))

        # 2. Per-experiment counts
        exp_counts = Counter(r["experiment"] for r in rows)
        for exp, expected in EXPECTED_PER_EXPERIMENT.items():
            report.add(expect_count(
                f"{self.stage_id}.exp.{exp}",
                f"{exp} row count",
                expected, exp_counts.get(exp, 0),
            ))

        # 3. Claude × text-only success rates per variant
        rates = self._rates_by(rows, agent="text-only", model="claude-sonnet")
        for variant, expected_rate in C.COMPOSITE_TEXT_ONLY_CLAUDE.items():
            actual = rates.get(variant)
            if actual is None:
                report.add(expect_rate(
                    f"{self.stage_id}.claude_text.{variant}",
                    f"Claude text-only {variant} success rate (no data)",
                    expected_rate, 0.0,
                ))
            else:
                report.add(expect_rate(
                    f"{self.stage_id}.claude_text.{variant}",
                    f"Claude text-only {variant} success rate",
                    expected_rate, actual, tol_frac=C.RATE_TOL_FRAC,
                ))

        # 4. Llama 4 × text-only success rates per variant
        rates = self._rates_by(rows, agent="text-only", model="llama4-maverick")
        for variant, expected_rate in C.COMPOSITE_TEXT_ONLY_LLAMA.items():
            actual = rates.get(variant)
            if actual is None:
                continue
            report.add(expect_rate(
                f"{self.stage_id}.llama_text.{variant}",
                f"Llama 4 text-only {variant} success rate",
                expected_rate, actual, tol_frac=C.RATE_TOL_FRAC,
            ))

        # 5. CUA × Claude success rates
        rates = self._rates_by(rows, agent="cua", model="claude-sonnet")
        for variant, expected_rate in C.COMPOSITE_CUA_CLAUDE.items():
            actual = rates.get(variant)
            if actual is None:
                continue
            report.add(expect_rate(
                f"{self.stage_id}.cua_claude.{variant}",
                f"CUA Claude {variant} success rate",
                expected_rate, actual, tol_frac=C.RATE_TOL_FRAC,
            ))

        # 6. SoM × Claude success rates
        rates = self._rates_by(rows, agent="vision-only", model="claude-sonnet")
        for variant, expected_rate in C.COMPOSITE_SOM_CLAUDE.items():
            actual = rates.get(variant)
            if actual is None:
                continue
            report.add(expect_rate(
                f"{self.stage_id}.som_claude.{variant}",
                f"SoM Claude {variant} success rate",
                expected_rate, actual, tol_frac=C.RATE_TOL_FRAC,
            ))

    @staticmethod
    def _rates_by(rows: list[dict], *, agent: str, model: str) -> dict[str, float]:
        agg = defaultdict(lambda: [0, 0])  # [success, total]
        for r in rows:
            if r.get("agent_type") != agent or r.get("model") != model:
                continue
            v = r["variant"]
            agg[v][1] += 1
            if r.get("success", "").lower() in ("true", "1"):
                agg[v][0] += 1
        return {v: s / t if t else 0.0 for v, (s, t) in agg.items()}


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

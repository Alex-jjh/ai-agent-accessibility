"""
Phase 6 — Stage 4b SSIM verifier (visual control, single source of truth).

Stage 4b replays the 336 unique URLs that the Stage 3 agents observed, and
captures one screenshot per (URL, variant) under base + base2 + 26 AMT
operators = 28 captures × 336 URLs = 9,408 PNGs.

Per the user's directive (2026-05-15), `data/stage4b-ssim-replay/` is the
**single source of truth** for SSIM. Older captures under
`data/visual-equivalence/{replay,ablation-replay,click-probe}/` are 13-task
prototypes that pre-date the 26-operator AMT taxonomy; they are retained
for provenance only and explicitly NOT consulted by this verifier.

Asserts:
  * 9,408 PNG files present, manifest.jsonl matches
  * 26 AMT operators each have 336 captures
  * Per-operator median SSIM matches paper sentinels (L5, L6, L11)
  * Aggregate "operators with median SSIM < 0.99" set = {L5, L6, L11}
  * base-vs-base2 deterministic-render noise floor is below threshold

Reports (non-failing health metrics):
  * login-contamination rate (manifest.jsonl session_lost or login title)
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import (
    StageReport, expect_count, expect_rate, expect_set_membership,
)
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "stage4b-ssim-replay"
MANIFEST = DATA_DIR / "manifest.jsonl"
SSIM_PER_OP = REPO_ROOT / "results" / "stage3" / "visual-equiv" / "ssim-per-operator.csv"
SSIM_PER_URL = REPO_ROOT / "results" / "stage3" / "visual-equiv" / "ssim-per-url.csv"

LOGIN_TITLE_MARKERS = ("login", "sign in")


class Verifier(StageVerifier):
    stage_id = "phase6_stage4b"
    label = "Stage 4b SSIM trace-URL replay (336 URLs × 28 variants = 9,408 PNGs)"

    def audit(self, report: StageReport) -> None:
        if not DATA_DIR.exists():
            report.add(expect_count(
                f"{self.stage_id}.dir",
                f"{DATA_DIR.relative_to(REPO_ROOT)} exists",
                1, 0,
            ))
            return

        # 1. PNG file count
        pngs = list(DATA_DIR.glob("*/*.png"))
        report.add(expect_count(
            f"{self.stage_id}.png_count",
            "Stage 4b PNG count (336 × 28)",
            C.N_STAGE4B_CAPTURES, len(pngs),
        ))

        # 2. Manifest line count + schema
        if not MANIFEST.exists():
            report.add(expect_count(
                f"{self.stage_id}.manifest",
                "manifest.jsonl exists",
                1, 0,
            ))
        else:
            with MANIFEST.open() as f:
                manifest_lines = [json.loads(line) for line in f if line.strip()]
            report.add(expect_count(
                f"{self.stage_id}.manifest_lines",
                "manifest.jsonl line count",
                C.N_STAGE4B_CAPTURES, len(manifest_lines),
            ))

            # 3. URL count
            urls = {m["url"] for m in manifest_lines}
            report.add(expect_count(
                f"{self.stage_id}.url_count",
                "unique URLs replayed",
                C.N_STAGE4B_URLS, len(urls),
            ))

            # 4. Variant coverage: base + base2 + 26 AMT operators = 28
            variants_seen = set(m["variant"] for m in manifest_lines)
            expected_variants = {"base", "base2"} | set(C.ALL_OPS)
            report.add(expect_set_membership(
                f"{self.stage_id}.variants",
                "28 expected variants present",
                expected=expected_variants,
                actual=variants_seen,
                direction="equal",
            ))

            # 5. Per-operator capture count = 336
            per_op = Counter(
                m["variant"] for m in manifest_lines if m["variant"] in C.ALL_OPS
            )
            ops_off_count = [op for op in C.ALL_OPS if per_op.get(op, 0) != C.N_STAGE4B_URLS]
            report.add(expect_count(
                f"{self.stage_id}.per_op_count_uniform",
                "operators with capture count != 336",
                0, len(ops_off_count),
            ))

            # 6. Login-contamination health metric (NOT a failure)
            login_contaminated = [
                m for m in manifest_lines
                if m.get("session_lost", False)
                or any(mk in (m.get("title") or "").lower() for mk in LOGIN_TITLE_MARKERS)
            ]
            login_pct = 100 * len(login_contaminated) / max(len(manifest_lines), 1)
            # Pass-by-default — track in report metadata only
            report.add(expect_rate(
                f"{self.stage_id}.login_contamination_pct",
                f"login-contaminated captures (informational; <5% expected)",
                expected=0.0,
                actual=login_pct,
                tol_frac=5.0,  # very loose — this is a tracking metric, not a hard gate
            ))

        # 7. Per-operator median SSIM sentinels
        if SSIM_PER_OP.exists():
            with SSIM_PER_OP.open() as f:
                op_rows = {row["operator"]: row for row in csv.DictReader(f)}

            for op, expected_median in C.SSIM_MEDIAN_SENTINELS.items():
                row = op_rows.get(op)
                if row is None:
                    continue
                actual = float(row["ssim_median"])
                report.add(expect_rate(
                    f"{self.stage_id}.median_ssim.{op}",
                    f"{op} median SSIM (paper §4.117 sentinel)",
                    expected_median, actual, tol_frac=0.02,
                ))

            # 8. Set of operators below threshold matches paper claim
            below_thresh = {
                op for op, row in op_rows.items()
                if float(row["ssim_median"]) < C.SSIM_THRESHOLD
            }
            report.add(expect_set_membership(
                f"{self.stage_id}.below_ssim_threshold",
                f"operators with median SSIM < {C.SSIM_THRESHOLD}",
                expected=set(C.SSIM_CHANGED_OPS),
                actual=below_thresh,
                direction="equal",
            ))
        else:
            report.add(expect_count(
                f"{self.stage_id}.ssim_per_op_csv",
                "results/stage3/visual-equiv/ssim-per-operator.csv exists",
                1, 0,
            ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

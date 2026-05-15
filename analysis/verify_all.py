#!/usr/bin/env python3.11
"""
Top-level V&V runner — invokes every stage verifier and aggregates results.

Each stage in `analysis.stages.*` exposes a `Verifier` class with a
`run() -> StageReport` method. We collect the reports, print a summary,
and exit non-zero if any stage failed.

Usage:
    python -m analysis.verify_all
    make verify-all
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from analysis.stages import (
    phase1_composite,
    phase2_mode_a,
    phase3_c2,
    phase4_dom_signatures,
    phase5_smoker,
    phase6_stage3,
    phase6_stage4b,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
KEY_NUMBERS_OUT = REPO_ROOT / "results" / "key-numbers.json"


STAGES = [
    phase5_smoker,        # gate that produced Stage 3 — runs first
    phase1_composite,
    phase2_mode_a,
    phase3_c2,
    phase4_dom_signatures,
    phase6_stage3,
    phase6_stage4b,
]


def main() -> int:
    print("═" * 78)
    print("V&V — verifying all paper-critical numbers across 7 stages")
    print("═" * 78)

    reports = []
    for module in STAGES:
        report = module.Verifier().run()
        reports.append(report)

    print("\n" + "═" * 78)
    print("SUMMARY")
    print("═" * 78)
    for r in reports:
        print(r.summary_line())

    total_pass = sum(r.n_passed for r in reports)
    total_fail = sum(r.n_failed for r in reports)
    print(f"\nTotal: {total_pass} passed, {total_fail} failed across {len(reports)} stages")

    # Always emit results/key-numbers.json — even on failure, so failing run is debuggable
    KEY_NUMBERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": total_fail == 0,
        "stages": {r.stage_id: {
            "label": r.label,
            "passed": r.passed,
            "n_passed": r.n_passed,
            "n_failed": r.n_failed,
            "assertions": [a.to_dict() for a in r.assertions],
        } for r in reports},
    }
    KEY_NUMBERS_OUT.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nDetail: {KEY_NUMBERS_OUT.relative_to(REPO_ROOT)}")

    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())

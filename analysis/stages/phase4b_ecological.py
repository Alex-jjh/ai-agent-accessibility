"""
Phase 4b — Ecological probe verifier.

Reads the 34 per-site axe-core scan JSONs in `scan-a11y-audit/results/`
and recomputes the headline ecological claim (paper §4): the fraction of
real-world sites carrying at least one Tier-3 (structural) accessibility
violation. Paper reports 28/34 = 82.4%.

Tier-3 classification is loaded directly from `scan-a11y-audit/analysis.py`
(PATCH_SEVERITY + patch_affected) so the verifier and the table generator
share one source of truth. A site is Tier-3-affected if it triggers any of
the three structural patches: P7 (landmark→div), P9 (thead→div),
P11 (link→span).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from analysis import _constants as C
from analysis.lib.assertions import Assertion, StageReport, expect_count, expect_pp
from analysis.stages._base import StageVerifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = REPO_ROOT / "scan-a11y-audit"
AUDIT_ANALYSIS = AUDIT_DIR / "analysis.py"


def _load_audit_module():
    """Import scan-a11y-audit/analysis.py as a standalone module."""
    spec = importlib.util.spec_from_file_location("_scan_a11y_analysis", AUDIT_ANALYSIS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Verifier(StageVerifier):
    stage_id = "phase4b_ecological"
    label = "Ecological probe (34-site Tier-3 prevalence)"

    def audit(self, report: StageReport) -> None:
        if not AUDIT_ANALYSIS.exists():
            report.add(expect_count(
                f"{self.stage_id}.analysis_present",
                f"{AUDIT_ANALYSIS.relative_to(REPO_ROOT)} exists",
                expected=1, actual=0,
            ))
            return

        am = _load_audit_module()
        sites = am.load_results()

        # 1. Site count == 34 (the audited corpus, incl. 4 WebArena calibration sites)
        report.add(expect_count(
            f"{self.stage_id}.site_count",
            "audited site count (paper §4: 34)",
            C.ECOLOGICAL_AUDIT_SITES, len(sites),
        ))

        # 2. Tier-3 prevalence == 82.4% (28/34)
        tier3_patches = [p for p, sev in am.PATCH_SEVERITY.items()
                         if sev == "L3_structural"]
        affected = 0
        for data in sites.values():
            axe = am.get_axe_violations(data)
            custom = am.get_custom_results(data)
            if any(am.patch_affected(p, axe, custom)[0] for p in tier3_patches):
                affected += 1

        pct = round(100 * affected / len(sites), 1) if sites else 0.0
        report.add(expect_pp(
            f"{self.stage_id}.tier3_pct",
            f"Tier-3 prevalence (paper §4: {C.ECOLOGICAL_TIER3_PCT}% = 28/34)",
            C.ECOLOGICAL_TIER3_PCT, pct,
            tol_pp=0.1,
        ))
        report.add(Assertion(
            name=f"{self.stage_id}.tier3_count",
            description="sites with ≥1 Tier-3 violation (paper §4: 28)",
            expected=28,
            actual=affected,
            passed=(affected == 28),
            tolerance="exact",
        ))


if __name__ == "__main__":
    import sys
    rep = Verifier().run()
    sys.exit(0 if rep.passed else 1)

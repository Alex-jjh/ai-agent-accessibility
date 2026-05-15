"""Stage verifier base class.

Subclasses override `audit()` to populate a `StageReport` with assertions.
The default `run()` wraps that with a header and returns the report.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from analysis.lib.assertions import StageReport


class StageVerifier(ABC):
    stage_id: str = "phaseX"
    label: str = "(unspecified)"

    @abstractmethod
    def audit(self, report: StageReport) -> None:
        """Populate `report` with Assertion objects."""
        raise NotImplementedError

    def run(self, *, verbose: bool = True) -> StageReport:
        report = StageReport(stage_id=self.stage_id, label=self.label)
        if verbose:
            print(f"\n══ {self.stage_id} — {self.label} ══")
        try:
            self.audit(report)
        except Exception as exc:  # noqa: BLE001 — verifier should never crash the harness
            from analysis.lib.assertions import Assertion
            report.add(Assertion(
                name=f"{self.stage_id}.exception",
                description="audit raised exception",
                expected="no exception",
                actual=f"{type(exc).__name__}: {exc}",
                passed=False,
                tolerance="exact",
            ))
        if verbose:
            for a in report.assertions:
                print(a)
            print(report.summary_line())
        return report

"""
Lightweight assertion / report primitive for stage verifiers.

Each verifier returns a list of `Assertion` so the top-level `verify_all`
runner can summarize PASS/FAIL across all phases.

Design notes:
  * No dependency on pytest — these are not unit-test assertions, they
    cross-check disk vs paper claims at runtime.
  * `passed=False` does NOT raise; the runner aggregates and exits non-zero
    once all stages have run, so a single FAIL doesn't abort the others.
  * `expected` and `actual` are kept as primitives so JSON serialization is
    trivial (`asdict(a)` works out of the box).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Assertion:
    name: str                       # short identifier, e.g. "phase6_stage3.N"
    description: str                # human-readable
    expected: Any
    actual: Any
    passed: bool
    tolerance: str = ""             # e.g. "exact", "±0.5pp"

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        body = f"  [{mark}] {self.name}: {self.description}"
        if not self.passed:
            body += f"\n         expected={self.expected!r} actual={self.actual!r} tol={self.tolerance}"
        return body


def expect_count(name: str, description: str, expected: int, actual: int) -> Assertion:
    """Exact-equality count assertion (e.g. N case counts)."""
    return Assertion(
        name=name,
        description=description,
        expected=expected,
        actual=actual,
        passed=(expected == actual),
        tolerance="exact",
    )


def expect_rate(
    name: str,
    description: str,
    expected: float,
    actual: float,
    tol_frac: float = 0.005,
) -> Assertion:
    """Within-tolerance comparison for fractional rates (e.g. 0.895 ± 0.005)."""
    return Assertion(
        name=name,
        description=description,
        expected=expected,
        actual=actual,
        passed=abs(expected - actual) <= tol_frac,
        tolerance=f"±{tol_frac}",
    )


def expect_pp(
    name: str,
    description: str,
    expected_pp: float,
    actual_pp: float,
    tol_pp: float = 0.5,
) -> Assertion:
    """Within-tolerance comparison for percentage-point drops (e.g. -28pp ±0.5)."""
    return Assertion(
        name=name,
        description=description,
        expected=expected_pp,
        actual=actual_pp,
        passed=abs(expected_pp - actual_pp) <= tol_pp,
        tolerance=f"±{tol_pp}pp",
    )


def expect_set_membership(
    name: str,
    description: str,
    expected: set,
    actual: set,
    direction: str = "subset",
) -> Assertion:
    """Compare two sets. `direction='subset'` → actual ⊆ expected;
    `direction='equal'` → actual == expected; `direction='superset'` → actual ⊇ expected."""
    if direction == "subset":
        passed = actual.issubset(expected)
    elif direction == "superset":
        passed = actual.issuperset(expected)
    else:
        passed = actual == expected
    return Assertion(
        name=name,
        description=description,
        expected=sorted(expected),
        actual=sorted(actual),
        passed=passed,
        tolerance=direction,
    )


@dataclass
class StageReport:
    """Container for one stage's audit results."""
    stage_id: str
    label: str
    assertions: list[Assertion] = field(default_factory=list)

    def add(self, a: Assertion) -> None:
        self.assertions.append(a)

    @property
    def passed(self) -> bool:
        return all(a.passed for a in self.assertions)

    @property
    def n_passed(self) -> int:
        return sum(1 for a in self.assertions if a.passed)

    @property
    def n_failed(self) -> int:
        return sum(1 for a in self.assertions if not a.passed)

    def summary_line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"[{mark}] {self.stage_id}: {self.n_passed} passed, {self.n_failed} failed — {self.label}"

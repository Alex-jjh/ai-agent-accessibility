"""Shared, side-effect-free building blocks for stage verifiers.

Three modules:
  load        — case-JSON loaders, GT correction, attempt dedup
  stats       — wilson_ci, odds_ratio_ci, cohens_h, mantel_haenszel_or, breslow_day
  assertions  — Assertion dataclass, expect_count / expect_rate / within_tolerance helpers
"""

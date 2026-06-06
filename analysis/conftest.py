"""Pytest collection guard for optional-dependency test modules.

analysis/models/__init__.py eagerly re-exports analysis.models.secondary,
which imports scikit-learn at module top. On the *core* install (sklearn +
shap absent) pytest's package-import step runs models/__init__.py before any
test-module body, so a module-level pytest.importorskip("sklearn") inside the
test files cannot fire — collection errors out at the package import instead.

We therefore ignore the sklearn-dependent test modules here, before the
models package is ever imported, when scikit-learn is not installed. The
modules retain their own importorskip("sklearn") guard for the optional
install (requirements-optional.txt) where the package import succeeds.
"""

from __future__ import annotations

import importlib.util

collect_ignore: list[str] = []

if importlib.util.find_spec("sklearn") is None:
    collect_ignore += [
        "models/test_primary.py",
        "models/test_secondary.py",
    ]

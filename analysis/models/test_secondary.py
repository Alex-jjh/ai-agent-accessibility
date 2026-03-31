"""Unit tests for analysis.models.secondary — SecondaryAnalysis class.

Tests Random Forest training, SHAP computation, and partial dependence
plots with synthetic WCAG criterion data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from analysis.models.secondary import (
    PDPResult,
    RFResult,
    SHAPResult,
    SecondaryAnalysis,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic WCAG criterion data
# ---------------------------------------------------------------------------

WCAG_COLS = ["1.1.1", "1.3.1", "2.1.1", "4.1.2"]


def _make_wcag_data(
    n: int = 200, seed: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    """Generate synthetic WCAG criterion data.

    Columns '1.1.1' and '4.1.2' are strongly correlated with success,
    while '1.3.1' and '2.1.1' are near-random noise.
    """
    rng = np.random.default_rng(seed)

    data: dict[str, np.ndarray] = {}
    # Predictive features
    data["1.1.1"] = rng.integers(0, 2, size=n)
    data["4.1.2"] = rng.integers(0, 2, size=n)
    # Noise features
    data["1.3.1"] = rng.integers(0, 2, size=n)
    data["2.1.1"] = rng.integers(0, 2, size=n)

    # Success strongly depends on 1.1.1 and 4.1.2
    p = 0.15 + 0.35 * data["1.1.1"] + 0.35 * data["4.1.2"]
    y = rng.binomial(1, np.clip(p, 0.05, 0.95), size=n)

    X = pd.DataFrame(data)
    return X, pd.Series(y, name="agent_success")


# ---------------------------------------------------------------------------
# Tests — train_random_forest
# ---------------------------------------------------------------------------


class TestTrainRandomForest:
    """Tests for SecondaryAnalysis.train_random_forest."""

    def test_returns_rf_result(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y)

        assert isinstance(result, RFResult)
        assert isinstance(result.model, RandomForestClassifier)

    def test_correct_fields(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y)

        assert result.n_samples == len(X)
        assert result.n_features == len(WCAG_COLS)
        assert set(result.feature_names) == set(WCAG_COLS)

    def test_feature_importances_for_all_features(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y)

        assert set(result.feature_importances.keys()) == set(WCAG_COLS)
        for imp in result.feature_importances.values():
            assert 0.0 <= imp <= 1.0

    def test_accuracy_between_0_and_1(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y)

        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.precision <= 1.0
        assert 0.0 <= result.recall <= 1.0
        assert 0.0 <= result.f1 <= 1.0

    def test_cv_scores_computed(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y, cv_folds=3)

        assert len(result.cv_scores) == 3
        for s in result.cv_scores:
            assert 0.0 <= s <= 1.0
        assert 0.0 <= result.cv_mean <= 1.0
        assert result.cv_std >= 0.0

    def test_predictive_features_rank_higher(self):
        """Features correlated with success should have higher importance."""
        X, y = _make_wcag_data(n=500, seed=99)
        sa = SecondaryAnalysis()
        result = sa.train_random_forest(X, y)

        predictive_imp = result.feature_importances["1.1.1"] + result.feature_importances["4.1.2"]
        noise_imp = result.feature_importances["1.3.1"] + result.feature_importances["2.1.1"]
        assert predictive_imp > noise_imp

    def test_empty_data_raises(self):
        sa = SecondaryAnalysis()
        with pytest.raises(ValueError, match="must not be empty"):
            sa.train_random_forest(pd.DataFrame(), pd.Series(dtype=int))


# ---------------------------------------------------------------------------
# Tests — compute_shap
# ---------------------------------------------------------------------------


class TestComputeShap:
    """Tests for SecondaryAnalysis.compute_shap."""

    def test_returns_shap_result(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.compute_shap(rf.model, X)

        assert isinstance(result, SHAPResult)

    def test_correct_shape(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.compute_shap(rf.model, X)

        assert result.shap_values.shape == (len(X), len(WCAG_COLS))
        assert result.n_samples == len(X)
        assert set(result.feature_names) == set(WCAG_COLS)

    def test_shap_ranks_features_by_importance(self):
        X, y = _make_wcag_data(n=500, seed=99)
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.compute_shap(rf.model, X)

        # Ranked features should be sorted descending by mean_abs_shap
        for i in range(len(result.ranked_features) - 1):
            assert (
                result.ranked_features[i]["mean_abs_shap"]
                >= result.ranked_features[i + 1]["mean_abs_shap"]
            )

    def test_mean_abs_shap_all_features(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.compute_shap(rf.model, X)

        assert set(result.mean_abs_shap.keys()) == set(WCAG_COLS)
        for v in result.mean_abs_shap.values():
            assert v >= 0.0

    def test_empty_data_raises(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        with pytest.raises(ValueError, match="must not be empty"):
            sa.compute_shap(rf.model, pd.DataFrame())


# ---------------------------------------------------------------------------
# Tests — partial_dependence_plots
# ---------------------------------------------------------------------------


class TestPartialDependencePlots:
    """Tests for SecondaryAnalysis.partial_dependence_plots."""

    def test_returns_pdp_result(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.partial_dependence_plots(rf.model, X, top_n=3)

        assert isinstance(result, PDPResult)

    def test_top_n_features(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.partial_dependence_plots(rf.model, X, top_n=3)

        assert result.n_features_computed == 3
        assert len(result.top_features) == 3
        assert len(result.pdp_data) == 3

    def test_pdp_data_structure(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        result = sa.partial_dependence_plots(rf.model, X, top_n=2)

        for entry in result.pdp_data:
            assert "feature" in entry
            assert "grid_values" in entry
            assert "average_response" in entry
            assert "importance" in entry
            assert isinstance(entry["grid_values"], list)
            assert isinstance(entry["average_response"], list)

    def test_empty_data_raises(self):
        X, y = _make_wcag_data()
        sa = SecondaryAnalysis()
        rf = sa.train_random_forest(X, y)
        with pytest.raises(ValueError, match="must not be empty"):
            sa.partial_dependence_plots(rf.model, pd.DataFrame(), top_n=2)

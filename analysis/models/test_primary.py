"""Unit tests for analysis.models.primary — PrimaryAnalysis class.

Tests CLMM (GEE fallback), GEE, interaction_effect, sensitivity_analysis,
and post_hoc_power with synthetic data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.models.primary import (
    COMPOSITE_COL,
    TIER1_COLS,
    TIER2_COLS,
    CLMMResult,
    CoefficientInfo,
    GEEResult,
    InteractionResult,
    PowerResult,
    PrimaryAnalysis,
    SensitivityResult,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic data generators
# ---------------------------------------------------------------------------

def _make_track_a_data(n_per_cell: int = 30, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic Track A data with a clear variant gradient.

    Higher variant levels → higher success probability.
    """
    rng = np.random.default_rng(seed)
    rows = []
    levels = ["low", "medium-low", "base", "high"]
    apps = ["reddit", "gitlab", "cms", "ecommerce"]
    backends = ["claude-opus", "gpt-4o"]
    modes = ["text-only", "vision"]

    # Success probabilities per variant level (strong gradient for text-only)
    p_success = {"low": 0.15, "medium-low": 0.35, "base": 0.55, "high": 0.80}

    for level in levels:
        for app in apps:
            for backend in backends:
                for mode in modes:
                    p = p_success[level]
                    # Vision agents are less affected by variant
                    if mode == "vision":
                        p = 0.45 + 0.05 * levels.index(level)
                    successes = rng.binomial(1, p, size=n_per_cell)
                    for s in successes:
                        rows.append({
                            "agent_success": int(s),
                            "a11y_variant_level": level,
                            "app": app,
                            "llm_backend": backend,
                            "observation_mode": mode,
                        })
    return pd.DataFrame(rows)



def _make_track_b_data(n_sites: int = 20, n_per_site: int = 10, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic Track B data with Tier 1+2 feature columns."""
    rng = np.random.default_rng(seed)
    rows = []
    backends = ["claude-opus", "gpt-4o"]

    for site_idx in range(n_sites):
        site_name = f"site_{site_idx:03d}"
        # Each site has a base accessibility quality
        site_quality = rng.uniform(0.2, 0.9)

        for backend in backends:
            for _ in range(n_per_site):
                # Generate feature values correlated with site quality
                features = {}
                features["axe_violation_count"] = max(0, rng.normal(20 * (1 - site_quality), 5))
                features["lighthouse_score"] = min(1.0, max(0.0, rng.normal(site_quality, 0.1)))
                for col in TIER2_COLS:
                    features[col] = min(1.0, max(0.0, rng.normal(site_quality, 0.15)))
                features["composite_score"] = min(1.0, max(0.0, site_quality + rng.normal(0, 0.05)))

                # Success probability depends on features
                p = min(0.95, max(0.05, site_quality + rng.normal(0, 0.1)))
                success = rng.binomial(1, p)

                row = {
                    "agent_success": int(success),
                    "website": site_name,
                    "llm_backend": backend,
                    **features,
                }
                rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFitClmm:
    """Tests for PrimaryAnalysis.fit_clmm (Track A)."""

    def test_returns_clmm_result(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        assert isinstance(result, CLMMResult)
        assert result.method == "statsmodels_gee"  # pymer4 unlikely installed
        assert result.n_observations == len(data)
        assert result.converged is True

    def test_has_coefficients(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        assert len(result.coefficients) >= 2  # intercept + variant_ordinal
        names = [c.name for c in result.coefficients]
        assert "const" in names or "Intercept" in names
        assert "variant_ordinal" in names

    def test_coefficient_fields_populated(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        for coef in result.coefficients:
            assert isinstance(coef, CoefficientInfo)
            assert isinstance(coef.estimate, float)
            assert isinstance(coef.std_error, float)
            assert coef.ci_lower <= coef.estimate <= coef.ci_upper
            assert 0.0 <= coef.p_value <= 1.0
            assert coef.odds_ratio > 0

    def test_variant_effect_positive(self):
        """Higher variant ordinal → higher success → positive coefficient."""
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        variant_coef = next(
            c for c in result.coefficients if c.name == "variant_ordinal"
        )
        # With our synthetic data, higher variant = higher success
        assert variant_coef.estimate > 0

    def test_n_groups_reported(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        assert result.n_groups["app"] == 4
        assert result.n_groups["llm_backend"] == 2

    def test_gee_fallback_warning(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.fit_clmm(data)

        # Without pymer4, should have a fallback warning
        if result.method == "statsmodels_gee":
            assert len(result.warnings) > 0
            assert "pymer4 unavailable" in result.warnings[0]



class TestFitGee:
    """Tests for PrimaryAnalysis.fit_gee (Track B)."""

    def test_returns_gee_result(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.fit_gee(data)

        assert isinstance(result, GEEResult)
        assert result.n_observations == len(data)
        assert result.converged is True

    def test_uses_criterion_level_features(self):
        """IVs should be Tier 1+2 features, NOT composite_score."""
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.fit_gee(data)

        coef_names = [c.name for c in result.coefficients]
        # Should include tier 1+2 feature columns
        for col in TIER1_COLS + TIER2_COLS:
            assert col in coef_names, f"Missing feature column: {col}"
        # Should NOT include composite_score
        assert COMPOSITE_COL not in coef_names

    def test_clusters_on_website(self):
        data = _make_track_b_data(n_sites=15)
        pa = PrimaryAnalysis()
        result = pa.fit_gee(data)

        assert result.n_clusters["website"] == 15

    def test_reports_confidence_intervals(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.fit_gee(data)

        for coef in result.coefficients:
            assert coef.ci_lower <= coef.estimate <= coef.ci_upper

    def test_raises_on_missing_features(self):
        data = pd.DataFrame({
            "agent_success": [1, 0, 1],
            "website": ["a", "b", "c"],
        })
        pa = PrimaryAnalysis()
        with pytest.raises(ValueError, match="No Tier 1/Tier 2 feature columns"):
            pa.fit_gee(data)


class TestInteractionEffect:
    """Tests for PrimaryAnalysis.interaction_effect."""

    def test_returns_interaction_result(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.interaction_effect(data)

        assert isinstance(result, InteractionResult)
        assert result.n_observations == len(data)

    def test_text_only_stronger_gradient(self):
        """Text-only agents should show a stronger a11y gradient than vision."""
        data = _make_track_a_data(n_per_cell=50, seed=123)
        pa = PrimaryAnalysis()
        result = pa.interaction_effect(data)

        # With our synthetic data, text-only has a steeper gradient
        assert abs(result.text_only_gradient) > abs(result.vision_gradient)

    def test_gradient_difference_equals_interaction(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.interaction_effect(data)

        # gradient_difference should equal text_only - vision
        assert abs(result.gradient_difference - (result.text_only_gradient - result.vision_gradient)) < 1e-10

    def test_has_interaction_coefficients(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.interaction_effect(data)

        assert len(result.interaction_coefficients) >= 1
        assert any("variant_x_obs" in c.name for c in result.interaction_coefficients)

    def test_interpretation_present(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.interaction_effect(data)

        assert isinstance(result.interpretation, str)
        assert len(result.interpretation) > 0



class TestSensitivityAnalysis:
    """Tests for PrimaryAnalysis.sensitivity_analysis."""

    def test_returns_sensitivity_result(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        assert isinstance(result, SensitivityResult)
        assert isinstance(result.tier1_only, GEEResult)
        assert isinstance(result.tier2_only, GEEResult)
        assert isinstance(result.composite_only, GEEResult)

    def test_tier1_only_uses_tier1_cols(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        coef_names = [c.name for c in result.tier1_only.coefficients]
        for col in TIER1_COLS:
            assert col in coef_names
        for col in TIER2_COLS:
            assert col not in coef_names

    def test_tier2_only_uses_tier2_cols(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        coef_names = [c.name for c in result.tier2_only.coefficients]
        for col in TIER2_COLS:
            assert col in coef_names
        for col in TIER1_COLS:
            assert col not in coef_names

    def test_composite_only_uses_composite(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        coef_names = [c.name for c in result.composite_only.coefficients]
        assert COMPOSITE_COL in coef_names

    def test_comparison_summary_populated(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        summary = result.comparison_summary
        assert "tier1_significant" in summary
        assert "tier2_significant" in summary
        assert "composite_significant" in summary
        assert summary["tier1_n_predictors"] == len(TIER1_COLS)
        assert summary["tier2_n_predictors"] == len(TIER2_COLS)
        assert summary["composite_n_predictors"] == 1

    def test_all_three_modes_converge(self):
        data = _make_track_b_data()
        pa = PrimaryAnalysis()
        result = pa.sensitivity_analysis(data)

        assert result.tier1_only.converged is True
        assert result.tier2_only.converged is True
        assert result.composite_only.converged is True

    def test_raises_on_missing_columns(self):
        data = pd.DataFrame({
            "agent_success": [1, 0, 1],
            "website": ["a", "b", "c"],
        })
        pa = PrimaryAnalysis()
        with pytest.raises(ValueError, match="none of the expected"):
            pa.sensitivity_analysis(data)


class TestPostHocPower:
    """Tests for PrimaryAnalysis.post_hoc_power."""

    def test_returns_power_result(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        assert isinstance(result, PowerResult)
        assert result.current_n == len(data)
        assert result.target_effect_size == 0.5
        assert result.alpha == 0.05

    def test_power_between_0_and_1(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        assert 0.0 <= result.achieved_power <= 1.0

    def test_large_sample_high_power(self):
        """With a large sample and strong effect, power should be high."""
        data = _make_track_a_data(n_per_cell=100)
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=1.0)

        assert result.achieved_power > 0.5  # Should be reasonably powered

    def test_is_sufficient_flag(self):
        data = _make_track_a_data(n_per_cell=100)
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=1.0)

        assert result.is_sufficient == (result.achieved_power >= 0.80)

    def test_recommendations_present(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        assert len(result.recommendations) > 0

    def test_required_n_positive(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        assert result.required_n > 0

    def test_observed_effect_computed(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        # With our synthetic data, there should be a non-zero observed effect
        assert result.observed_effect_size != 0.0

    def test_custom_alpha(self):
        data = _make_track_a_data()
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5, alpha=0.01)

        assert result.alpha == 0.01

    def test_without_variant_column(self):
        """Should handle data without a11y_variant_level gracefully."""
        data = _make_track_b_data(n_sites=5, n_per_site=5)
        pa = PrimaryAnalysis()
        result = pa.post_hoc_power(data, target_effect=0.5)

        assert isinstance(result, PowerResult)
        assert result.observed_effect_size == 0.0

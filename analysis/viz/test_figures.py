"""Unit tests for analysis.viz.figures — FigureGenerator class.

Uses matplotlib Agg backend for headless rendering.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.figure
import numpy as np
import pandas as pd
import pytest

from analysis.viz.figures import FigureGenerator


# ---------------------------------------------------------------------------
# Fixtures — minimal DataFrames
# ---------------------------------------------------------------------------


def _make_heatmap_data() -> pd.DataFrame:
    """Minimal data for variant_success_heatmap."""
    rows = []
    for level in ["low", "base", "high"]:
        for app in ["reddit", "gitlab"]:
            for success in [0, 1, 1]:
                rows.append({
                    "a11y_variant_level": level,
                    "app": app,
                    "agent_success": success,
                })
    return pd.DataFrame(rows)


def _make_interaction_data() -> pd.DataFrame:
    """Minimal data for interaction_effect_plot."""
    rows = []
    for level in ["low", "base", "high"]:
        for mode in ["text-only", "vision"]:
            for success in [0, 1]:
                rows.append({
                    "a11y_variant_level": level,
                    "observation_mode": mode,
                    "agent_success": success,
                })
    return pd.DataFrame(rows)


def _make_sankey_data() -> pd.DataFrame:
    """Minimal data for failure_taxonomy_sankey."""
    return pd.DataFrame({
        "primary_domain": ["accessibility", "accessibility", "model", "environmental"],
        "primary_type": ["F_ENF", "F_WEA", "F_HAL", "F_ABB"],
    })


def _make_shap_data() -> tuple[np.ndarray, pd.DataFrame]:
    """Minimal SHAP values and features for shap_summary_plot."""
    rng = np.random.default_rng(42)
    features = pd.DataFrame({
        "1.1.1": rng.random(20),
        "4.1.2": rng.random(20),
    })
    shap_values = rng.standard_normal((20, 2))
    return shap_values, features


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVariantSuccessHeatmap:
    def test_returns_figure(self):
        fg = FigureGenerator()
        fig = fg.variant_success_heatmap(_make_heatmap_data())
        assert isinstance(fig, matplotlib.figure.Figure)
        matplotlib.pyplot.close(fig)

    def test_missing_columns_raises(self):
        fg = FigureGenerator()
        bad_df = pd.DataFrame({"a11y_variant_level": ["low"], "app": ["x"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            fg.variant_success_heatmap(bad_df)


class TestShapSummaryPlot:
    def test_returns_figure(self):
        fg = FigureGenerator()
        shap_vals, features = _make_shap_data()
        fig = fg.shap_summary_plot(shap_vals, features)
        assert isinstance(fig, matplotlib.figure.Figure)
        matplotlib.pyplot.close(fig)


class TestInteractionEffectPlot:
    def test_returns_figure(self):
        fg = FigureGenerator()
        fig = fg.interaction_effect_plot(_make_interaction_data())
        assert isinstance(fig, matplotlib.figure.Figure)
        matplotlib.pyplot.close(fig)

    def test_missing_columns_raises(self):
        fg = FigureGenerator()
        bad_df = pd.DataFrame({"a11y_variant_level": ["low"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            fg.interaction_effect_plot(bad_df)


class TestFailureTaxonomySankey:
    def test_returns_figure(self):
        fg = FigureGenerator()
        fig = fg.failure_taxonomy_sankey(_make_sankey_data())
        assert isinstance(fig, matplotlib.figure.Figure)
        matplotlib.pyplot.close(fig)

    def test_missing_columns_raises(self):
        fg = FigureGenerator()
        bad_df = pd.DataFrame({"primary_domain": ["accessibility"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            fg.failure_taxonomy_sankey(bad_df)

    def test_empty_data_returns_figure(self):
        fg = FigureGenerator()
        empty_df = pd.DataFrame({"primary_domain": [], "primary_type": []})
        fig = fg.failure_taxonomy_sankey(empty_df)
        assert isinstance(fig, matplotlib.figure.Figure)
        matplotlib.pyplot.close(fig)

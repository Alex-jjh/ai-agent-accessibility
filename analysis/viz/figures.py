"""Paper-ready visualization engine for CHI/ASSETS submission.

Generates publication-quality figures using matplotlib and seaborn:
- Variant × App success rate heatmap (Req 13.3)
- SHAP summary beeswarm plot (Req 14.2)
- Interaction effect plot: Text-Only vs Vision gradient (Req 13.3)
- Failure taxonomy Sankey diagram (Req 14.4)

All functions return matplotlib Figure objects for flexible downstream use
(save to PDF/PNG, embed in notebooks, etc.).

Requirements: 13.3, 14.2, 14.4
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns


# ---------------------------------------------------------------------------
# Consistent styling for paper-ready figures
# ---------------------------------------------------------------------------

_PAPER_STYLE = {
    "context": "paper",
    "style": "whitegrid",
    "font_scale": 1.2,
    "rc": {
        "font.family": "serif",
        "axes.edgecolor": "0.2",
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "figure.dpi": 300,
    },
}

# Ordered variant levels for consistent axis ordering
_VARIANT_ORDER = ["low", "medium-low", "base", "high"]

# Failure taxonomy: domain → failure types
_FAILURE_DOMAINS: Dict[str, List[str]] = {
    "accessibility": ["F_ENF", "F_WEA", "F_KBT", "F_PCT", "F_SDI"],
    "model": ["F_HAL", "F_COF", "F_REA"],
    "environmental": ["F_ABB", "F_NET"],
    "task": ["F_AMB"],
}

# Domain colors for consistent palette
_DOMAIN_COLORS: Dict[str, str] = {
    "accessibility": "#d62728",
    "model": "#1f77b4",
    "environmental": "#ff7f0e",
    "task": "#2ca02c",
}


def _apply_paper_style() -> None:
    """Apply consistent seaborn/matplotlib styling for publication."""
    sns.set_context(_PAPER_STYLE["context"], font_scale=_PAPER_STYLE["font_scale"])
    sns.set_style(_PAPER_STYLE["style"], rc=_PAPER_STYLE["rc"])



# ---------------------------------------------------------------------------
# FigureGenerator class
# ---------------------------------------------------------------------------


class FigureGenerator:
    """Paper-ready figures for CHI/ASSETS submission.

    All methods return matplotlib Figure objects. Figures use seaborn's
    ``paper`` context with serif fonts and 300 DPI for publication quality.

    Validates: Requirements 13.3, 14.2, 14.4
    """

    def __init__(self) -> None:
        _apply_paper_style()

    # ------------------------------------------------------------------
    # variant_success_heatmap
    # ------------------------------------------------------------------

    def variant_success_heatmap(self, data: pd.DataFrame) -> matplotlib.figure.Figure:
        """Heatmap of agent success rates by variant level × app.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain columns: ``a11y_variant_level``, ``app``,
            ``agent_success`` (binary 0/1).

        Returns
        -------
        matplotlib.figure.Figure
            Annotated heatmap with success rates as percentages.

        Validates: Requirements 13.3
        """
        required_cols = {"a11y_variant_level", "app", "agent_success"}
        missing = required_cols - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        _apply_paper_style()

        # Compute success rate pivot table
        pivot = data.pivot_table(
            values="agent_success",
            index="a11y_variant_level",
            columns="app",
            aggfunc="mean",
        )

        # Reorder rows by variant level
        ordered_idx = [v for v in _VARIANT_ORDER if v in pivot.index]
        pivot = pivot.reindex(ordered_idx)

        fig, ax = plt.subplots(figsize=(max(6, len(pivot.columns) * 1.5), 4))

        sns.heatmap(
            pivot,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            vmin=0.0,
            vmax=1.0,
            linewidths=0.5,
            linecolor="white",
            cbar_kws={"label": "Success Rate"},
            ax=ax,
        )

        ax.set_xlabel("Application")
        ax.set_ylabel("Accessibility Variant Level")
        ax.set_title("Agent Success Rate by Variant Level and Application")

        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # shap_summary_plot
    # ------------------------------------------------------------------

    def shap_summary_plot(
        self,
        shap_values: np.ndarray,
        features: pd.DataFrame,
    ) -> matplotlib.figure.Figure:
        """SHAP summary beeswarm plot.

        Uses the ``shap`` library's built-in ``summary_plot`` rendered
        onto a matplotlib Figure.

        Parameters
        ----------
        shap_values : np.ndarray
            SHAP values array of shape ``(n_samples, n_features)``,
            as returned by ``SecondaryAnalysis.compute_shap``.
        features : pd.DataFrame
            Feature values DataFrame with column names matching the
            SHAP values.

        Returns
        -------
        matplotlib.figure.Figure
            Beeswarm plot showing feature importance and direction.

        Validates: Requirements 14.2
        """
        import shap

        _apply_paper_style()

        fig, ax = plt.subplots(figsize=(8, max(4, len(features.columns) * 0.4)))

        # shap.summary_plot draws on the current axes
        shap.summary_plot(
            shap_values,
            features,
            show=False,
            plot_size=None,
        )

        # Grab the current figure that shap drew on (it may create its own)
        shap_fig = plt.gcf()

        # If shap created a separate figure, close ours and return theirs
        if shap_fig is not fig:
            plt.close(fig)
            fig = shap_fig

        fig.set_dpi(300)
        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # interaction_effect_plot
    # ------------------------------------------------------------------

    def interaction_effect_plot(self, data: pd.DataFrame) -> matplotlib.figure.Figure:
        """Text-Only vs Vision accessibility gradient comparison.

        Shows agent success rate across variant levels, split by
        observation mode. Expected pattern: Text-Only shows a strong
        positive gradient; Vision shows a weak/null gradient.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain columns: ``a11y_variant_level``,
            ``observation_mode`` (``'text-only'`` or ``'vision'``),
            ``agent_success`` (binary 0/1).

        Returns
        -------
        matplotlib.figure.Figure
            Line plot with confidence bands comparing gradients.

        Validates: Requirements 13.3
        """
        required_cols = {"a11y_variant_level", "observation_mode", "agent_success"}
        missing = required_cols - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        _apply_paper_style()

        # Map variant levels to numeric for x-axis ordering
        variant_num = {v: i for i, v in enumerate(_VARIANT_ORDER)}
        df = data.copy()
        df["variant_num"] = df["a11y_variant_level"].map(variant_num)
        df = df.dropna(subset=["variant_num"])

        fig, ax = plt.subplots(figsize=(7, 5))

        palette = {"text-only": "#d62728", "vision": "#1f77b4"}

        # Aggregate: mean success rate per variant × mode
        grouped = (
            df.groupby(["observation_mode", "a11y_variant_level", "variant_num"])
            ["agent_success"]
            .agg(["mean", "sem", "count"])
            .reset_index()
        )

        for mode, color in palette.items():
            mode_data = grouped[grouped["observation_mode"] == mode].sort_values(
                "variant_num"
            )
            if mode_data.empty:
                continue

            x = mode_data["variant_num"].values
            y = mode_data["mean"].values
            se = mode_data["sem"].fillna(0).values

            ax.plot(x, y, "o-", color=color, label=mode.replace("-", " ").title(),
                    linewidth=2, markersize=6)
            ax.fill_between(x, y - 1.96 * se, y + 1.96 * se, alpha=0.15, color=color)

        ax.set_xticks(range(len(_VARIANT_ORDER)))
        ax.set_xticklabels([v.replace("-", "\n") for v in _VARIANT_ORDER])
        ax.set_xlabel("Accessibility Variant Level")
        ax.set_ylabel("Agent Success Rate")
        ax.set_title("Interaction Effect: Observation Mode × Accessibility Level")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(title="Observation Mode", frameon=True)

        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # failure_taxonomy_sankey
    # ------------------------------------------------------------------

    def failure_taxonomy_sankey(
        self, classifications: pd.DataFrame
    ) -> matplotlib.figure.Figure:
        """Sankey diagram of failure type distribution across domains.

        Draws flows from failure domains (left) to individual failure
        types (right), with flow width proportional to count.

        Parameters
        ----------
        classifications : pd.DataFrame
            Must contain columns: ``primary_domain`` and ``primary_type``.
            Optionally ``count``; if absent, rows are counted.

        Returns
        -------
        matplotlib.figure.Figure
            Sankey-style diagram showing failure distribution.

        Validates: Requirements 14.4
        """
        required_cols = {"primary_domain", "primary_type"}
        missing = required_cols - set(classifications.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        _apply_paper_style()

        # Aggregate counts
        if "count" in classifications.columns:
            agg = (
                classifications.groupby(["primary_domain", "primary_type"])["count"]
                .sum()
                .reset_index()
            )
        else:
            agg = (
                classifications.groupby(["primary_domain", "primary_type"])
                .size()
                .reset_index(name="count")
            )

        if agg.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No failure data", ha="center", va="center",
                    fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
            return fig

        total = agg["count"].sum()

        # Build domain and type ordering
        domains = [d for d in _FAILURE_DOMAINS if d in agg["primary_domain"].values]
        all_types = []
        for d in domains:
            domain_types = [
                t for t in _FAILURE_DOMAINS[d] if t in agg["primary_type"].values
            ]
            all_types.extend(domain_types)

        # Compute positions for left (domains) and right (types) nodes
        n_domains = len(domains)
        n_types = len(all_types)

        if n_domains == 0 or n_types == 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No classifiable failures", ha="center",
                    va="center", fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
            return fig

        fig, ax = plt.subplots(figsize=(10, max(6, n_types * 0.7)))

        # Y positions for domain nodes (left side)
        domain_counts = {
            d: agg[agg["primary_domain"] == d]["count"].sum() for d in domains
        }
        domain_heights = {d: c / total for d, c in domain_counts.items()}

        # Y positions for type nodes (right side)
        type_counts = {
            t: agg[agg["primary_type"] == t]["count"].sum() for t in all_types
        }
        type_heights = {t: c / total for t, c in type_counts.items()}

        # Layout: stack nodes vertically with gaps
        gap = 0.02
        left_x = 0.15
        right_x = 0.85
        node_width = 0.08

        # Compute domain y-positions
        domain_y: Dict[str, tuple] = {}
        y_cursor = 1.0
        for d in domains:
            h = domain_heights[d]
            domain_y[d] = (y_cursor - h, y_cursor)
            y_cursor -= h + gap

        # Compute type y-positions
        type_y: Dict[str, tuple] = {}
        y_cursor = 1.0
        for t in all_types:
            h = type_heights[t]
            type_y[t] = (y_cursor - h, y_cursor)
            y_cursor -= h + gap

        # Draw flows (curved bands from domain to type)
        for _, row in agg.iterrows():
            domain = row["primary_domain"]
            ftype = row["primary_type"]
            count = row["count"]

            if domain not in domain_y or ftype not in type_y:
                continue

            flow_height = count / total
            color = _DOMAIN_COLORS.get(domain, "#999999")

            # Find vertical position within domain node for this flow
            d_bottom, d_top = domain_y[domain]
            t_bottom, t_top = type_y[ftype]

            # Center the flow band
            d_mid = (d_bottom + d_top) / 2
            t_mid = (t_bottom + t_top) / 2

            # Draw curved path using fill_between on a bezier-like curve
            n_points = 50
            xs = np.linspace(left_x + node_width, right_x, n_points)
            # Sigmoid-like curve for smooth transition
            t_param = (xs - xs[0]) / (xs[-1] - xs[0])
            smooth = 3 * t_param**2 - 2 * t_param**3  # smoothstep

            y_center = d_mid + (t_mid - d_mid) * smooth
            half_h = flow_height / 2

            ax.fill_between(
                xs,
                y_center - half_h,
                y_center + half_h,
                alpha=0.4,
                color=color,
                edgecolor="none",
            )

        # Draw domain nodes (left rectangles)
        for d in domains:
            bottom, top = domain_y[d]
            color = _DOMAIN_COLORS.get(d, "#999999")
            rect = mpatches.FancyBboxPatch(
                (left_x, bottom),
                node_width,
                top - bottom,
                boxstyle="round,pad=0.005",
                facecolor=color,
                edgecolor="white",
                linewidth=1,
            )
            ax.add_patch(rect)
            ax.text(
                left_x - 0.02,
                (bottom + top) / 2,
                d.title(),
                ha="right",
                va="center",
                fontsize=10,
                fontweight="bold",
            )

        # Draw type nodes (right rectangles)
        for t in all_types:
            bottom, top = type_y[t]
            # Find domain for this type
            t_domain = None
            for d, types in _FAILURE_DOMAINS.items():
                if t in types:
                    t_domain = d
                    break
            color = _DOMAIN_COLORS.get(t_domain or "", "#999999")
            rect = mpatches.FancyBboxPatch(
                (right_x, bottom),
                node_width,
                top - bottom,
                boxstyle="round,pad=0.005",
                facecolor=color,
                edgecolor="white",
                linewidth=1,
            )
            ax.add_patch(rect)

            count_val = type_counts.get(t, 0)
            label = f"{t} ({count_val})"
            ax.text(
                right_x + node_width + 0.02,
                (bottom + top) / 2,
                label,
                ha="left",
                va="center",
                fontsize=9,
            )

        ax.set_xlim(-0.05, 1.15)
        y_min = min(
            min(v[0] for v in domain_y.values()) if domain_y else 0,
            min(v[0] for v in type_y.values()) if type_y else 0,
        )
        ax.set_ylim(y_min - 0.05, 1.05)
        ax.set_axis_off()
        ax.set_title("Failure Taxonomy Distribution", fontsize=13, fontweight="bold",
                      pad=15)

        fig.tight_layout()
        return fig

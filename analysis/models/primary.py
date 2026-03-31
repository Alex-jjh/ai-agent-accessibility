"""Primary Analysis models for the AI Agent Accessibility Platform.

Implements CLMM and GEE models for the primary research question:
Is web accessibility a statistically significant predictor of AI agent task success?

Track A: Controlled experiments on WebArena (4 variant levels).
Track B: Ecological survey of 50+ real-world websites via HAR replay.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 8.6
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.genmod.families import Binomial
from statsmodels.genmod.families.links import Logit
from statsmodels.genmod.cov_struct import Exchangeable

# Try importing pymer4 for mixed-effects logistic regression (preferred path).
# Falls back to statsmodels GEE with ordinal coding if unavailable.
try:
    from pymer4.models import Lmer

    _HAS_PYMER4 = True
except ImportError:
    _HAS_PYMER4 = False


# ---------------------------------------------------------------------------
# Column constants
# ---------------------------------------------------------------------------

TIER1_COLS: List[str] = ["axe_violation_count", "lighthouse_score"]
TIER2_COLS: List[str] = [
    "semantic_html_ratio",
    "accessible_name_coverage",
    "keyboard_navigability",
    "aria_correctness",
    "pseudo_compliance_ratio",
    "form_labeling_completeness",
    "landmark_coverage",
]
COMPOSITE_COL: str = "composite_score"


# Ordinal mapping for a11y_variant_level
_VARIANT_ORDER = {"low": 0, "medium-low": 1, "base": 2, "high": 3}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CoefficientInfo:
    """Single predictor coefficient with inference statistics."""

    name: str
    estimate: float
    std_error: float
    ci_lower: float
    ci_upper: float
    z_value: float
    p_value: float
    odds_ratio: float


@dataclass
class CLMMResult:
    """Result of fit_clmm (Track A mixed-effects logistic regression)."""

    method: str  # 'pymer4' or 'statsmodels_gee'
    coefficients: List[CoefficientInfo]
    random_effects: Dict[str, Any]
    n_observations: int
    n_groups: Dict[str, int]
    aic: Optional[float] = None
    bic: Optional[float] = None
    log_likelihood: Optional[float] = None
    converged: bool = True
    warnings: List[str] = field(default_factory=list)


@dataclass
class GEEResult:
    """Result of fit_gee (Track B GEE with logit link)."""

    coefficients: List[CoefficientInfo]
    n_observations: int
    n_clusters: Dict[str, int]
    qic: Optional[float] = None
    scale: Optional[float] = None
    converged: bool = True
    warnings: List[str] = field(default_factory=list)


@dataclass
class InteractionResult:
    """Result of interaction_effect test."""

    interaction_coefficients: List[CoefficientInfo]
    text_only_gradient: float
    vision_gradient: float
    gradient_difference: float
    gradient_difference_p: float
    interpretation: str
    n_observations: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class SensitivityResult:
    """Result of sensitivity_analysis across tier subsets."""

    tier1_only: GEEResult
    tier2_only: GEEResult
    composite_only: GEEResult
    comparison_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PowerResult:
    """Result of post_hoc_power analysis."""

    observed_effect_size: float
    target_effect_size: float
    achieved_power: float
    required_n: int
    current_n: int
    is_sufficient: bool
    alpha: float = 0.05
    recommendations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _extract_coefficients(
    params: pd.Series,
    bse: pd.Series,
    pvalues: pd.Series,
    conf_int: pd.DataFrame,
) -> List[CoefficientInfo]:
    """Build CoefficientInfo list from statsmodels-style result arrays."""
    coeffs: List[CoefficientInfo] = []
    for name in params.index:
        est = float(params[name])
        se = float(bse[name])
        p = float(pvalues[name])
        ci_lo = float(conf_int.loc[name].iloc[0])
        ci_hi = float(conf_int.loc[name].iloc[1])
        z = est / se if se > 0 else 0.0
        coeffs.append(
            CoefficientInfo(
                name=str(name),
                estimate=est,
                std_error=se,
                ci_lower=ci_lo,
                ci_upper=ci_hi,
                z_value=z,
                p_value=p,
                odds_ratio=float(np.exp(est)),
            )
        )
    return coeffs


def _safe_qic(result: Any) -> Optional[float]:
    """Safely compute QIC, returning None on failure."""
    try:
        if hasattr(result, "qic"):
            qic_val = result.qic(result.params)
            if hasattr(qic_val, "__getitem__"):
                return float(qic_val[0])
            return float(qic_val)
    except Exception:
        pass
    return None


def _encode_variant_ordinal(data: pd.DataFrame) -> pd.DataFrame:
    """Add ordinal-coded variant column using polynomial contrasts."""
    df = data.copy()
    if "a11y_variant_level" in df.columns:
        df["variant_ordinal"] = (
            df["a11y_variant_level"].map(_VARIANT_ORDER).astype(float)
        )
    return df


# ---------------------------------------------------------------------------
# PrimaryAnalysis class
# ---------------------------------------------------------------------------


class PrimaryAnalysis:
    """CLMM and GEE models for the primary research question.

    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 8.6
    """

    # ------------------------------------------------------------------
    # fit_clmm — Track A mixed-effects logistic regression
    # ------------------------------------------------------------------

    def fit_clmm(self, data: pd.DataFrame) -> CLMMResult:
        """Fit mixed-effects logistic regression for Track A.

        DV: agent_success (binary 0/1)
        IV: a11y_variant_level (ordinal, 4 levels)
        Random effects: (1|app), (1|llm_backend)

        Uses pymer4 (R's lme4) when available, otherwise falls back to
        statsmodels GEE with exchangeable correlation and ordinal coding.

        Validates: Requirements 13.1
        """
        df = _encode_variant_ordinal(data)

        if _HAS_PYMER4:
            return self._fit_clmm_pymer4(df)
        return self._fit_clmm_gee_fallback(df)

    def _fit_clmm_pymer4(self, df: pd.DataFrame) -> CLMMResult:
        """Fit via pymer4 Lmer (preferred path)."""
        model = Lmer(
            "agent_success ~ variant_ordinal + (1|app) + (1|llm_backend)",
            data=df,
            family="binomial",
        )
        model.fit()

        # Extract fixed effects
        fe = model.coefs
        coefficients: List[CoefficientInfo] = []
        for idx, row in fe.iterrows():
            est = float(row["Estimate"])
            se = float(row["SE"])
            p = float(row.get("P-val", row.get("Pr(>|z|)", 0.0)))
            ci_lo = float(row.get("2.5_ci", est - 1.96 * se))
            ci_hi = float(row.get("97.5_ci", est + 1.96 * se))
            z = est / se if se > 0 else 0.0
            coefficients.append(
                CoefficientInfo(
                    name=str(idx),
                    estimate=est,
                    std_error=se,
                    ci_lower=ci_lo,
                    ci_upper=ci_hi,
                    z_value=z,
                    p_value=p,
                    odds_ratio=float(np.exp(est)),
                )
            )

        # Extract random effects
        random_effects: Dict[str, Any] = {}
        if hasattr(model, "ranef_var"):
            random_effects = model.ranef_var.to_dict()
        elif hasattr(model, "ranef"):
            random_effects = {"ranef": str(model.ranef)}

        return CLMMResult(
            method="pymer4",
            coefficients=coefficients,
            random_effects=random_effects,
            n_observations=len(df),
            n_groups={
                "app": int(df["app"].nunique()),
                "llm_backend": int(df["llm_backend"].nunique()),
            },
            aic=float(model.AIC) if hasattr(model, "AIC") else None,
            bic=float(model.BIC) if hasattr(model, "BIC") else None,
            log_likelihood=(
                float(model.logLike) if hasattr(model, "logLike") else None
            ),
            converged=True,
        )

    def _fit_clmm_gee_fallback(self, df: pd.DataFrame) -> CLMMResult:
        """Fallback: statsmodels GEE with exchangeable correlation.

        GEE estimates population-averaged effects (not subject-specific).
        The paper must acknowledge this distinction.
        """
        warnings_list: List[str] = [
            "pymer4 unavailable — using statsmodels GEE fallback. "
            "GEE estimates population-averaged effects; conditional "
            "(subject-specific) effect sizes may differ."
        ]

        # Build groups column for GEE clustering (cluster on app)
        df = df.copy()
        df["_gee_group"] = pd.Categorical(df["app"]).codes

        endog = df["agent_success"].astype(float)
        exog = sm.add_constant(df[["variant_ordinal"]])

        model = sm.GEE(
            endog=endog,
            exog=exog,
            groups=df["_gee_group"],
            family=Binomial(link=Logit()),
            cov_struct=Exchangeable(),
        )
        result = model.fit()

        coefficients = _extract_coefficients(
            result.params, result.bse, result.pvalues, result.conf_int()
        )

        return CLMMResult(
            method="statsmodels_gee",
            coefficients=coefficients,
            random_effects={"correlation": float(result.cov_struct.dep_params)},
            n_observations=len(df),
            n_groups={
                "app": int(df["app"].nunique()),
                "llm_backend": int(df["llm_backend"].nunique()),
            },
            converged=bool(result.converged),
            warnings=warnings_list,
        )


    # ------------------------------------------------------------------
    # fit_gee — Track B GEE with logit link
    # ------------------------------------------------------------------

    def fit_gee(self, data: pd.DataFrame) -> GEEResult:
        """Fit GEE with logit link for Track B.

        DV: agent_success (binary 0/1)
        IV: criterion-level Tier 1+2 feature vector (NOT Composite_Score)
        Clustering: website (primary), llm_backend acknowledged via
        exchangeable working correlation.

        Validates: Requirements 13.2, 13.3
        """
        df = data.copy()

        feature_cols = [c for c in TIER1_COLS + TIER2_COLS if c in df.columns]
        if not feature_cols:
            raise ValueError(
                "No Tier 1/Tier 2 feature columns found in data. "
                f"Expected some of: {TIER1_COLS + TIER2_COLS}"
            )

        # Cluster on website
        df["_gee_group"] = pd.Categorical(df["website"]).codes

        endog = df["agent_success"].astype(float)
        exog = sm.add_constant(df[feature_cols].astype(float))

        model = sm.GEE(
            endog=endog,
            exog=exog,
            groups=df["_gee_group"],
            family=Binomial(link=Logit()),
            cov_struct=Exchangeable(),
        )
        result = model.fit()

        coefficients = _extract_coefficients(
            result.params, result.bse, result.pvalues, result.conf_int()
        )

        n_clusters: Dict[str, int] = {
            "website": int(df["website"].nunique()),
        }
        if "llm_backend" in df.columns:
            n_clusters["llm_backend"] = int(df["llm_backend"].nunique())

        qic_val = _safe_qic(result)

        return GEEResult(
            coefficients=coefficients,
            n_observations=len(df),
            n_clusters=n_clusters,
            qic=qic_val,
            scale=float(result.scale) if hasattr(result, "scale") else None,
            converged=bool(result.converged),
        )

    # ------------------------------------------------------------------
    # interaction_effect — a11y_variant × observation_mode
    # ------------------------------------------------------------------

    def interaction_effect(self, data: pd.DataFrame) -> InteractionResult:
        """Test a11y_variant × observation_mode interaction.

        Expected: Text-Only agents show a strong accessibility gradient;
        Vision agents show a weak/null gradient (they bypass the A11y Tree).
        If confirmed, this is the strongest evidence for the A11y Tree as
        the causal mechanism.

        Validates: Requirements 13.3, 8.6
        """
        df = _encode_variant_ordinal(data).copy()

        # Encode observation_mode as binary: text-only=1, vision=0
        df["obs_text_only"] = (df["observation_mode"] == "text-only").astype(float)

        # Interaction term
        df["variant_x_obs"] = df["variant_ordinal"] * df["obs_text_only"]

        # Cluster on app for GEE
        df["_gee_group"] = pd.Categorical(df["app"]).codes

        feature_cols = ["variant_ordinal", "obs_text_only", "variant_x_obs"]
        endog = df["agent_success"].astype(float)
        exog = sm.add_constant(df[feature_cols].astype(float))

        model = sm.GEE(
            endog=endog,
            exog=exog,
            groups=df["_gee_group"],
            family=Binomial(link=Logit()),
            cov_struct=Exchangeable(),
        )
        result = model.fit()

        coefficients = _extract_coefficients(
            result.params, result.bse, result.pvalues, result.conf_int()
        )

        # Compute per-mode gradients:
        # For text-only (obs_text_only=1): gradient = variant_ordinal + variant_x_obs
        # For vision (obs_text_only=0): gradient = variant_ordinal
        variant_coef = float(result.params.get("variant_ordinal", 0.0))
        interaction_coef = float(result.params.get("variant_x_obs", 0.0))

        text_only_gradient = variant_coef + interaction_coef
        vision_gradient = variant_coef
        gradient_diff = text_only_gradient - vision_gradient  # == interaction_coef

        interaction_p = float(result.pvalues.get("variant_x_obs", 1.0))

        # Interpret
        if interaction_p < 0.05 and abs(text_only_gradient) > abs(vision_gradient):
            interpretation = (
                "Significant interaction: Text-Only agents show a stronger "
                "accessibility gradient than Vision agents, supporting the "
                "A11y Tree as the causal mechanism."
            )
        elif interaction_p < 0.05:
            interpretation = (
                "Significant interaction detected, but the gradient pattern "
                "does not match the expected direction. Further investigation needed."
            )
        else:
            interpretation = (
                "No significant interaction between accessibility variant "
                "and observation mode detected (p={:.4f}).".format(interaction_p)
            )

        # Filter to interaction-specific coefficients for the result
        interaction_coefficients = [
            c for c in coefficients if "variant_x_obs" in c.name
        ]

        return InteractionResult(
            interaction_coefficients=interaction_coefficients,
            text_only_gradient=text_only_gradient,
            vision_gradient=vision_gradient,
            gradient_difference=gradient_diff,
            gradient_difference_p=interaction_p,
            interpretation=interpretation,
            n_observations=len(df),
        )


    # ------------------------------------------------------------------
    # sensitivity_analysis — tier1-only, tier2-only, composite
    # ------------------------------------------------------------------

    def sensitivity_analysis(self, data: pd.DataFrame) -> SensitivityResult:
        """Fit GEE models with tier1-only, tier2-only, and composite.

        Primary analysis always uses the full criterion-level feature vector.
        Sensitivity analysis checks robustness by fitting reduced models.

        Validates: Requirements 13.4
        """
        tier1_result = self._fit_gee_subset(data, TIER1_COLS, "tier1_only")
        tier2_result = self._fit_gee_subset(data, TIER2_COLS, "tier2_only")
        composite_result = self._fit_gee_subset(
            data, [COMPOSITE_COL], "composite_only"
        )

        # Build comparison summary
        def _sig_predictors(res: GEEResult) -> List[str]:
            return [c.name for c in res.coefficients if c.p_value < 0.05]

        comparison = {
            "tier1_significant": _sig_predictors(tier1_result),
            "tier2_significant": _sig_predictors(tier2_result),
            "composite_significant": _sig_predictors(composite_result),
            "tier1_n_predictors": len(TIER1_COLS),
            "tier2_n_predictors": len(TIER2_COLS),
            "composite_n_predictors": 1,
        }

        return SensitivityResult(
            tier1_only=tier1_result,
            tier2_only=tier2_result,
            composite_only=composite_result,
            comparison_summary=comparison,
        )

    def _fit_gee_subset(
        self,
        data: pd.DataFrame,
        feature_cols: List[str],
        label: str,
    ) -> GEEResult:
        """Fit a GEE model on a subset of feature columns."""
        df = data.copy()

        available_cols = [c for c in feature_cols if c in df.columns]
        if not available_cols:
            raise ValueError(
                f"Sensitivity analysis '{label}': none of the expected "
                f"columns {feature_cols} found in data."
            )

        df["_gee_group"] = pd.Categorical(df["website"]).codes

        endog = df["agent_success"].astype(float)
        exog = sm.add_constant(df[available_cols].astype(float))

        model = sm.GEE(
            endog=endog,
            exog=exog,
            groups=df["_gee_group"],
            family=Binomial(link=Logit()),
            cov_struct=Exchangeable(),
        )
        result = model.fit()

        coefficients = _extract_coefficients(
            result.params, result.bse, result.pvalues, result.conf_int()
        )

        n_clusters: Dict[str, int] = {
            "website": int(df["website"].nunique()),
        }
        if "llm_backend" in df.columns:
            n_clusters["llm_backend"] = int(df["llm_backend"].nunique())

        qic_val = _safe_qic(result)

        return GEEResult(
            coefficients=coefficients,
            n_observations=len(df),
            n_clusters=n_clusters,
            qic=qic_val,
            scale=float(result.scale) if hasattr(result, "scale") else None,
            converged=bool(result.converged),
            warnings=[f"Sensitivity mode: {label}"],
        )

    # ------------------------------------------------------------------
    # post_hoc_power — power analysis after pilot
    # ------------------------------------------------------------------

    def post_hoc_power(
        self,
        data: pd.DataFrame,
        target_effect: float,
        alpha: float = 0.05,
    ) -> PowerResult:
        """Post-hoc power analysis after pilot phase.

        Estimates achieved power given the observed data and a target
        effect size (log-odds ratio). Uses normal approximation for
        the power of a two-proportion z-test as a conservative estimate.

        Validates: Requirements 13.5
        """
        n = len(data)
        p_success = float(data["agent_success"].mean())

        # Observed effect: log-odds difference between highest and lowest
        # variant levels (or across the accessibility gradient)
        if "a11y_variant_level" in data.columns:
            grouped = data.groupby("a11y_variant_level")["agent_success"].mean()
            if "high" in grouped.index and "low" in grouped.index:
                p_high = float(grouped["high"])
                p_low = float(grouped["low"])
            else:
                levels = sorted(
                    grouped.index, key=lambda x: _VARIANT_ORDER.get(x, 0)
                )
                p_high = float(grouped[levels[-1]])
                p_low = float(grouped[levels[0]])

            # Observed effect size as log-odds ratio
            eps = 1e-8
            odds_high = (p_high + eps) / (1 - p_high + eps)
            odds_low = (p_low + eps) / (1 - p_low + eps)
            observed_effect = float(np.log(odds_high / odds_low))
        else:
            observed_effect = 0.0
            p_high = p_success
            p_low = p_success

        # Power calculation using normal approximation for two-proportion z-test
        # H0: p1 = p2, H1: p1 - p2 = delta
        # where delta is derived from the target log-odds ratio
        p_bar = (p_high + p_low) / 2.0
        eps = 1e-8
        p_bar = max(eps, min(1 - eps, p_bar))

        # Convert target log-odds to probability difference
        odds_base = p_bar / (1 - p_bar)
        odds_target = odds_base * np.exp(target_effect)
        p_target = odds_target / (1 + odds_target)
        delta = abs(p_target - p_bar)

        # Sample size per group
        n_per_group = n // 2 if n > 1 else 1

        # Standard error under H0
        se_h0 = np.sqrt(2 * p_bar * (1 - p_bar) / max(n_per_group, 1))
        # Standard error under H1
        se_h1 = np.sqrt(
            (p_bar * (1 - p_bar) + p_target * (1 - p_target)) / max(n_per_group, 1)
        )

        z_alpha = stats.norm.ppf(1 - alpha / 2)

        if se_h1 > 0:
            z_power = (delta - z_alpha * se_h0) / se_h1
            achieved_power = float(stats.norm.cdf(z_power))
        else:
            achieved_power = 0.0

        # Required N for 80% power
        z_beta = stats.norm.ppf(0.80)
        if delta > 0:
            required_per_group = (
                (z_alpha * np.sqrt(2 * p_bar * (1 - p_bar))
                 + z_beta * np.sqrt(p_bar * (1 - p_bar) + p_target * (1 - p_target)))
                / delta
            ) ** 2
            required_n = int(np.ceil(required_per_group * 2))
        else:
            required_n = n  # Can't compute — keep current

        recommendations: List[str] = []
        if achieved_power < 0.80:
            recommendations.append(
                f"Current power ({achieved_power:.2f}) is below 0.80. "
                f"Consider increasing sample size to at least {required_n}."
            )
        if achieved_power >= 0.80:
            recommendations.append(
                f"Achieved power ({achieved_power:.2f}) is sufficient "
                f"for the target effect size."
            )

        return PowerResult(
            observed_effect_size=observed_effect,
            target_effect_size=target_effect,
            achieved_power=achieved_power,
            required_n=required_n,
            current_n=n,
            is_sufficient=achieved_power >= 0.80,
            alpha=alpha,
            recommendations=recommendations,
        )

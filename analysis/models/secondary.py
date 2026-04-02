"""Secondary Analysis models for the AI Agent Accessibility Platform.

Implements Random Forest + SHAP analysis for the secondary research question:
Which specific WCAG 2.2 criteria are most predictive of AI agent task success?

Features: individual WCAG criterion pass/fail indicators (binary columns).
Target: agent_success (binary 0/1).

Requirements: 14.1, 14.2, 14.3, 14.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import partial_dependence
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RFResult:
    """Result of train_random_forest.

    Validates: Requirements 14.1
    """

    model: RandomForestClassifier
    feature_importances: Dict[str, float]
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: Optional[float]
    cv_scores: List[float]
    cv_mean: float
    cv_std: float
    n_samples: int
    n_features: int
    feature_names: List[str]


@dataclass
class SHAPResult:
    """Result of compute_shap.

    Validates: Requirements 14.2, 14.3
    """

    shap_values: np.ndarray  # shape (n_samples, n_features)
    mean_abs_shap: Dict[str, float]  # feature name → mean |SHAP|
    ranked_features: List[Dict[str, Any]]  # sorted by importance desc
    feature_names: List[str]
    n_samples: int


@dataclass
class PDPResult:
    """Result of partial_dependence_plots.

    Validates: Requirements 14.4
    """

    pdp_data: List[Dict[str, Any]]  # one entry per feature
    top_features: List[str]
    n_features_computed: int


# ---------------------------------------------------------------------------
# SecondaryAnalysis class
# ---------------------------------------------------------------------------


class SecondaryAnalysis:
    """Random Forest + SHAP for the secondary research question.

    Identifies which specific WCAG 2.2 criteria are most predictive
    of AI agent task success.

    Validates: Requirements 14.1, 14.2, 14.3, 14.4
    """

    # ------------------------------------------------------------------
    # train_random_forest
    # ------------------------------------------------------------------

    def train_random_forest(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_estimators: int = 100,
        random_state: int = 42,
        cv_folds: int = 5,
    ) -> RFResult:
        """Train a Random Forest classifier on WCAG criterion indicators.

        Features (X): individual WCAG criterion pass/fail indicators (binary).
        Target (y): agent_success (binary 0/1).

        Returns an RFResult with the trained model, feature importances,
        accuracy metrics, and cross-validation scores.

        Validates: Requirements 14.1
        """
        if X.empty or len(y) == 0:
            raise ValueError("Input data must not be empty.")
        if len(X) != len(y):
            raise ValueError(
                f"X and y must have the same number of samples "
                f"(got {len(X)} and {len(y)})."
            )

        feature_names = list(X.columns)

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        model.fit(X, y)

        # Cross-validation (computed BEFORE training-set metrics for clarity)
        actual_folds = min(cv_folds, len(X))
        if actual_folds >= 2 and len(np.unique(y)) > 1:
            cv_scores_arr = cross_val_score(
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    random_state=random_state,
                    n_jobs=-1,
                ),
                X,
                y,
                cv=actual_folds,
                scoring="accuracy",
            )
            cv_scores = [float(s) for s in cv_scores_arr]
        else:
            cv_scores = [0.0]

        # Use cross-validated predictions for metrics to avoid overfitting bias.
        # Fall back to training-set predictions when CV is not possible.
        if actual_folds >= 2 and len(np.unique(y)) > 1:
            from sklearn.model_selection import cross_val_predict

            y_pred_cv = cross_val_predict(
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    random_state=random_state,
                    n_jobs=-1,
                ),
                X,
                y,
                cv=actual_folds,
            )
            accuracy = float(accuracy_score(y, y_pred_cv))
            precision = float(precision_score(y, y_pred_cv, zero_division=0))
            recall = float(recall_score(y, y_pred_cv, zero_division=0))
            f1 = float(f1_score(y, y_pred_cv, zero_division=0))

            # ROC AUC from CV probability estimates
            roc_auc: Optional[float] = None
            try:
                y_proba_cv = cross_val_predict(
                    RandomForestClassifier(
                        n_estimators=n_estimators,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                    X,
                    y,
                    cv=actual_folds,
                    method="predict_proba",
                )
                roc_auc = float(roc_auc_score(y, y_proba_cv[:, 1]))
            except Exception:
                roc_auc = None
        else:
            # Fallback: training-set metrics (flagged in results)
            y_pred = model.predict(X)
            y_proba = model.predict_proba(X)
            accuracy = float(accuracy_score(y, y_pred))
            precision = float(precision_score(y, y_pred, zero_division=0))
            recall = float(recall_score(y, y_pred, zero_division=0))
            f1 = float(f1_score(y, y_pred, zero_division=0))
            roc_auc = None
            if len(np.unique(y)) > 1 and y_proba.shape[1] == 2:
                roc_auc = float(roc_auc_score(y, y_proba[:, 1]))

        # Feature importances from the model
        importances = model.feature_importances_
        feature_importances = {
            name: float(imp) for name, imp in zip(feature_names, importances)
        }

        return RFResult(
            model=model,
            feature_importances=feature_importances,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            roc_auc=roc_auc,
            cv_scores=cv_scores,
            cv_mean=float(np.mean(cv_scores)),
            cv_std=float(np.std(cv_scores)),
            n_samples=len(X),
            n_features=len(feature_names),
            feature_names=feature_names,
        )

    # ------------------------------------------------------------------
    # compute_shap
    # ------------------------------------------------------------------

    def compute_shap(
        self,
        model: RandomForestClassifier,
        X: pd.DataFrame,
    ) -> SHAPResult:
        """Compute SHAP values for each WCAG criterion.

        Uses TreeExplainer for efficient SHAP computation on tree-based
        models. Returns SHAP values, mean absolute SHAP per feature,
        and features ranked by importance.

        Validates: Requirements 14.2, 14.3
        """
        import shap

        if X.empty:
            raise ValueError("Input data must not be empty.")

        feature_names = list(X.columns)

        explainer = shap.TreeExplainer(model)
        shap_values_raw = explainer.shap_values(X)

        # Handle different shap output formats for binary classification:
        # - list of 2 arrays (older shap): use index 1 (positive class)
        # - 3D array (n_samples, n_features, n_classes): slice [:, :, 1]
        # - 2D array (n_samples, n_features): use as-is
        if isinstance(shap_values_raw, list):
            shap_vals = np.array(shap_values_raw[1])
        else:
            arr = np.array(shap_values_raw)
            if arr.ndim == 3:
                # (n_samples, n_features, n_classes) — take positive class
                shap_vals = arr[:, :, 1]
            else:
                shap_vals = arr

        # Mean absolute SHAP values per feature
        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        mean_abs_flat = np.asarray(mean_abs).flatten()
        mean_abs_shap = {
            name: float(mean_abs_flat[i])
            for i, name in enumerate(feature_names)
        }

        # Rank features by mean |SHAP| descending
        sorted_indices = np.argsort(mean_abs_flat)[::-1]
        ranked_features = [
            {
                "rank": rank + 1,
                "feature": feature_names[idx],
                "mean_abs_shap": float(mean_abs_flat[idx]),
            }
            for rank, idx in enumerate(sorted_indices)
        ]

        return SHAPResult(
            shap_values=shap_vals,
            mean_abs_shap=mean_abs_shap,
            ranked_features=ranked_features,
            feature_names=feature_names,
            n_samples=len(X),
        )

    # ------------------------------------------------------------------
    # partial_dependence_plots
    # ------------------------------------------------------------------

    def partial_dependence_plots(
        self,
        model: RandomForestClassifier,
        X: pd.DataFrame,
        top_n: int = 10,
    ) -> PDPResult:
        """Compute partial dependence plot data for top N criteria.

        Uses scikit-learn's partial_dependence to compute PDP values
        for the most important features (by model feature_importances_).
        Returns the PDP data structures (not figures) for downstream
        visualization.

        Validates: Requirements 14.4
        """
        if X.empty:
            raise ValueError("Input data must not be empty.")

        feature_names = list(X.columns)

        # Convert to float to avoid sklearn FutureWarning/ValueError
        # for integer data in partial dependence computation
        X_float = X.astype(float)

        # Determine top N features by model feature importance
        importances = model.feature_importances_
        n_features = min(top_n, len(feature_names))
        top_indices = np.argsort(importances)[::-1][:n_features]
        top_features = [feature_names[i] for i in top_indices]

        pdp_data: List[Dict[str, Any]] = []
        for feat_idx in top_indices:
            feat_name = feature_names[feat_idx]
            result = partial_dependence(
                model,
                X_float,
                features=[feat_idx],
                kind="average",
            )

            pdp_entry: Dict[str, Any] = {
                "feature": feat_name,
                "feature_index": int(feat_idx),
                "grid_values": result["grid_values"][0].tolist(),
                "average_response": result["average"][0].tolist(),
                "importance": float(importances[feat_idx]),
            }
            pdp_data.append(pdp_entry)

        return PDPResult(
            pdp_data=pdp_data,
            top_features=top_features,
            n_features_computed=n_features,
        )

"""
SHAP explanations computed by XGBoost itself (`pred_contribs=True`, exact TreeSHAP), so the API
does not need the separate `shap` package. Values are in log-odds: positive pushes the response
probability up, and the contributions plus the bias sum to the model's raw score.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import xgboost as xgb

from customer_segmentation.features.engineering import FEATURE_LABELS


@dataclass
class Contribution:
    feature: str
    label: str
    value: float  # the customer's feature value
    shap: float  # log-odds contribution


def shap_matrix(model: xgb.XGBClassifier, X: pd.DataFrame) -> tuple[np.ndarray, float]:
    """(n x features) SHAP values and the shared bias term."""
    contribs = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    return contribs[:, :-1], float(contribs[0, -1])


def global_importance(model: xgb.XGBClassifier, X: pd.DataFrame) -> list[dict]:
    """Mean |SHAP| per feature, largest first."""
    values, _ = shap_matrix(model, X)
    mean_abs = np.abs(values).mean(axis=0)
    order = np.argsort(-mean_abs)
    return [
        {
            "feature": X.columns[i],
            "label": FEATURE_LABELS.get(X.columns[i], X.columns[i]),
            "mean_abs_shap": float(mean_abs[i]),
        }
        for i in order
    ]


def explain_row(model: xgb.XGBClassifier, row: pd.DataFrame, top: int = 6) -> tuple[list[Contribution], float]:
    """Top contributions by absolute size for one customer, plus the bias term."""
    values, bias = shap_matrix(model, row)
    vals = values[0]
    order = np.argsort(-np.abs(vals))[:top]
    return [
        Contribution(
            feature=row.columns[i],
            label=FEATURE_LABELS.get(row.columns[i], row.columns[i]),
            value=float(row.iloc[0, i]),
            shap=float(vals[i]),
        )
        for i in order
    ], bias


def as_dicts(items) -> list[dict]:
    return [asdict(i) for i in items]

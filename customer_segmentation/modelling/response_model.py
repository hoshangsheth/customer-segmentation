"""
XGBoost model for `Response` (accepted the last campaign), with a logistic-regression baseline.

Probabilities are left uncalibrated by class weights (no scale_pos_weight) so they can be read as
response rates; the calibration check in evaluation/metrics.py measures how close they are.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

XGB_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 2,
    "reg_lambda": 1.0,
    "eval_metric": "logloss",
    "n_jobs": 1,
}


def make_model(random_state: int) -> XGBClassifier:
    return XGBClassifier(**XGB_PARAMS, random_state=random_state)


def make_baseline() -> object:
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))


@dataclass
class CVScores:
    folds: int
    roc_auc_mean: float
    roc_auc_std: float
    pr_auc_mean: float
    pr_auc_std: float

    def to_dict(self) -> dict:
        return asdict(self)


def cross_validate(model_factory, X: pd.DataFrame, y: pd.Series, folds: int, random_state: int) -> CVScores:
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    roc, pr = [], []
    for train_idx, test_idx in cv.split(X, y):
        model = model_factory()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        p = model.predict_proba(X.iloc[test_idx])[:, 1]
        roc.append(roc_auc_score(y.iloc[test_idx], p))
        pr.append(average_precision_score(y.iloc[test_idx], p))
    return CVScores(folds, float(np.mean(roc)), float(np.std(roc)), float(np.mean(pr)), float(np.std(pr)))


def out_of_fold_scores(X: pd.DataFrame, y: pd.Series, folds: int, random_state: int) -> np.ndarray:
    """Each customer scored by a model that never saw them. Used for the lift curve."""
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    return cross_val_predict(make_model(random_state), X, y, cv=cv, method="predict_proba")[:, 1]

"""
Shared context for every evaluation section.

Rebuilds exactly what training saw (same cleaning, features, stratified split and seed) and loads the
shipped artifact bundle, so every number here describes the model the API actually serves.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from customer_segmentation.artifacts import store
from customer_segmentation.config import Settings, get_settings
from customer_segmentation.data.cleaning import clean
from customer_segmentation.data.loader import load_raw
from customer_segmentation.data.schema import COST_CONTACT, REVENUE, TARGET
from customer_segmentation.features.engineering import RESPONSE_FEATURES, build_features
from customer_segmentation.modelling.response_model import out_of_fold_scores

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"


@dataclass
class Context:
    settings: Settings
    raw: pd.DataFrame
    df: pd.DataFrame
    features: pd.DataFrame
    X: pd.DataFrame
    y: pd.Series
    idx_train: np.ndarray
    idx_test: np.ndarray
    bundle: store.Bundle
    labels: np.ndarray
    oof: np.ndarray
    cost: float
    revenue: float

    @property
    def rs(self) -> int:
        return self.settings.random_state

    @property
    def X_train(self) -> pd.DataFrame:  # noqa: N802 (ML convention)
        return self.X.iloc[self.idx_train]

    @property
    def X_test(self) -> pd.DataFrame:  # noqa: N802 (ML convention)
        return self.X.iloc[self.idx_test]

    @property
    def y_train(self) -> pd.Series:
        return self.y.iloc[self.idx_train]

    @property
    def y_test(self) -> pd.Series:
        return self.y.iloc[self.idx_test]

    @property
    def model(self):
        return self.bundle.response_model

    def holdout_scores(self) -> np.ndarray:
        return self.model.predict_proba(self.X_test)[:, 1]


def load_context(data_path: Path | None = None, artifacts_dir: Path | None = None) -> Context:
    settings = get_settings()
    raw = load_raw(data_path or settings.data_path)
    df, _ = clean(raw)
    bundle = store.load(artifacts_dir or settings.artifacts_dir)
    ref_date = pd.Timestamp(bundle.report["meta"]["reference_date"])
    features = build_features(df, ref_date)
    X = features[RESPONSE_FEATURES]
    y = df[TARGET].astype(int).reset_index(drop=True)
    X = X.reset_index(drop=True)
    idx_train, idx_test = train_test_split(
        np.arange(len(X)), test_size=settings.test_size, stratify=y, random_state=settings.random_state
    )
    labels = bundle.segmenter.predict(features)
    oof = out_of_fold_scores(X, y, settings.cv_folds, settings.random_state)
    return Context(
        settings=settings,
        raw=raw,
        df=df.reset_index(drop=True),
        features=features.reset_index(drop=True),
        X=X,
        y=y,
        idx_train=idx_train,
        idx_test=idx_test,
        bundle=bundle,
        labels=labels,
        oof=oof,
        cost=float(df[COST_CONTACT].iloc[0]),
        revenue=float(df[REVENUE].iloc[0]),
    )


def top_share_lift(y, scores, share: float) -> float:
    """Response rate in the top `share` of customers by score, divided by the overall rate."""
    y, scores = np.asarray(y), np.asarray(scores)
    n = max(1, int(round(len(y) * share)))
    top = y[np.argsort(-scores, kind="stable")[:n]]
    base = y.mean()
    return float(top.mean() / base) if base else 0.0


def bootstrap_ci(stat, arrays: tuple[np.ndarray, ...], n_boot: int, seed: int, stratify: np.ndarray | None = None):
    """Percentile 95% interval of `stat(*resampled_arrays)`; resamples within each class if `stratify` is given."""
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    groups = [np.flatnonzero(stratify == g) for g in np.unique(stratify)] if stratify is not None else [np.arange(n)]
    values = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        values.append(stat(*(a[idx] for a in arrays)))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(lo), float(hi)


def environment() -> dict:
    pkgs = ["numpy", "pandas", "scikit-learn", "xgboost", "fastapi"]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": __import__("os").cpu_count(),
        "packages": {p: version(p) for p in pkgs},
    }


def to_jsonable(obj):
    """Recursively convert numpy types so results can be written as JSON."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    return obj


def write_json(name: str, data: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / name
    path.write_text(json.dumps(to_jsonable(data), indent=2), encoding="utf-8")
    return path

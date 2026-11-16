"""
4. Performance benchmarking.

- Model benchmark: the shipped XGBoost against no-model business rules and other learners, all on the
  same 3x5 repeated stratified folds, with paired win rates.
- Compute benchmark: training time for the full pipeline, single-customer scoring latency, batch
  throughput, API endpoint latency and artifact size.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

from customer_segmentation import train
from customer_segmentation.api.app import create_app
from customer_segmentation.explainability.shap_values import explain_row
from customer_segmentation.features.engineering import RESPONSE_FEATURES, build_features
from customer_segmentation.modelling.response_model import make_baseline, make_model
from customer_segmentation.scoring import CustomerRecord, score_customer, to_raw_frame
from model_evaluation.common import Context, top_share_lift


class RuleScorer:
    """A scoring rule with no fitting, wrapped so it runs through the same benchmark loop."""

    def __init__(self, fn):
        self.fn = fn

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        s = np.asarray(self.fn(X), dtype=float)
        return np.column_stack([1 - s, s])


def _pct(v: pd.Series) -> pd.Series:
    return v.rank(pct=True)


def rfm_rule(X: pd.DataFrame) -> pd.Series:
    """Classic RFM score: recent, frequent, high-spending customers first."""
    return (_pct(-X["recency"]) + _pct(X["frequency"]) + _pct(X["monetary"])) / 3


def history_rule(X: pd.DataFrame) -> pd.Series:
    """Marketer's rule: customers who accepted earlier offers first, then the most recent buyers."""
    return (X["prior_accepts"] + _pct(-X["recency"])) / 6


CANDIDATES = {
    "Dummy (base rate)": lambda rs: DummyClassifier(strategy="prior"),
    "Rule: RFM score": lambda rs: RuleScorer(rfm_rule),
    "Rule: past acceptances + recency": lambda rs: RuleScorer(history_rule),
    "Logistic regression": lambda rs: make_baseline(),
    "Random forest": lambda rs: RandomForestClassifier(n_estimators=300, min_samples_leaf=3, n_jobs=1, random_state=rs),
    "Hist gradient boosting": lambda rs: HistGradientBoostingClassifier(random_state=rs),
    "XGBoost (shipped)": lambda rs: make_model(rs),
}
SHIPPED = "XGBoost (shipped)"


def model_benchmark(ctx: Context, n_splits: int = 5, n_repeats: int = 3) -> dict:
    cv = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=ctx.rs)
    folds = list(cv.split(ctx.X, ctx.y))
    per_model: dict[str, dict[str, list[float]]] = {}
    for name, factory in CANDIDATES.items():
        m = {"roc_auc": [], "pr_auc": [], "top10_lift": [], "fit_s": [], "predict_ms_per_1k": []}
        for tr, te in folds:
            model = factory(ctx.rs)
            t0 = time.perf_counter()
            model.fit(ctx.X.iloc[tr], ctx.y.iloc[tr])
            t1 = time.perf_counter()
            p = model.predict_proba(ctx.X.iloc[te])[:, 1]
            t2 = time.perf_counter()
            y = ctx.y.iloc[te].to_numpy()
            m["roc_auc"].append(roc_auc_score(y, p))
            m["pr_auc"].append(average_precision_score(y, p))
            m["top10_lift"].append(top_share_lift(y, p, 0.1))
            m["fit_s"].append(t1 - t0)
            m["predict_ms_per_1k"].append((t2 - t1) * 1000 / len(te) * 1000)
        per_model[name] = m

    ship = np.array(per_model[SHIPPED]["roc_auc"])
    rows = []
    for name, m in per_model.items():
        auc = np.array(m["roc_auc"])
        rows.append(
            {
                "model": name,
                "roc_auc_mean": float(auc.mean()),
                "roc_auc_std": float(auc.std()),
                "pr_auc_mean": float(np.mean(m["pr_auc"])),
                "top10_lift_mean": float(np.mean(m["top10_lift"])),
                "fit_seconds_mean": float(np.mean(m["fit_s"])),
                "predict_ms_per_1k_rows": float(np.mean(m["predict_ms_per_1k"])),
                "shipped_minus_this_auc": float((ship - auc).mean()),
                "shipped_wins_folds": int((ship > auc).sum()),
            }
        )
    rows.sort(key=lambda r: -r["roc_auc_mean"])
    return {
        "scheme": f"{n_repeats}x{n_splits} repeated stratified K-fold, all customers",
        "folds": len(folds),
        "rows": rows,
    }


def _latency(fn, n: int, warmup: int = 20) -> dict:
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    t = np.array(times)
    return {
        "calls": n,
        "p50_ms": float(np.percentile(t, 50)),
        "p95_ms": float(np.percentile(t, 95)),
        "p99_ms": float(np.percentile(t, 99)),
        "mean_ms": float(t.mean()),
    }


def score_breakdown(ctx: Context, record: CustomerRecord) -> dict:
    """Median time of each step inside score_customer, to show where single-row latency goes."""
    ref = pd.Timestamp(ctx.bundle.report["meta"]["reference_date"])
    raw = to_raw_frame(record)
    feats = build_features(raw, ref)
    X = feats[RESPONSE_FEATURES]
    steps = {
        "input_to_frame": lambda: to_raw_frame(record),
        "feature_engineering": lambda: build_features(raw, ref),
        "segment_assignment": lambda: ctx.bundle.segmenter.predict(feats),
        "response_probability": lambda: ctx.model.predict_proba(X),
        "shap_explanation": lambda: explain_row(ctx.model, X, 6),
    }
    return {name: _latency(fn, 200)["p50_ms"] for name, fn in steps.items()}


def compute_benchmark(ctx: Context) -> dict:
    # Full offline training pipeline (cleaning, k search, clustering, CV, model, OOF lift, artifacts)
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        train.run(ctx.settings, ctx.settings.data_path, Path(tmp))
        train_s = time.perf_counter() - t0

    defaults = ctx.bundle.report["score_defaults"]
    record = CustomerRecord(**{**defaults, "customer_since": pd.Timestamp(defaults["customer_since"]).date()})
    single = _latency(lambda: score_customer(ctx.bundle, record), 300)
    single["breakdown_p50_ms"] = score_breakdown(ctx, record)

    big = pd.concat([ctx.X] * 10, ignore_index=True)
    t0 = time.perf_counter()
    ctx.model.predict_proba(big)
    batch_s = time.perf_counter() - t0

    client = TestClient(create_app(ctx.settings, bundle=ctx.bundle, provider=None))
    api = {
        "GET /api/health": _latency(lambda: client.get("/api/health"), 200),
        "GET /api/overview": _latency(lambda: client.get("/api/overview"), 200),
        "GET /api/lift": _latency(lambda: client.get("/api/lift"), 200),
        "POST /api/score": _latency(lambda: client.post("/api/score", json=defaults), 200),
    }
    assert client.post("/api/score", json=defaults).status_code == 200

    folder = Path(ctx.settings.artifacts_dir) / ctx.bundle.version
    sizes = {p.name: p.stat().st_size for p in sorted(folder.iterdir())}
    return {
        "training_pipeline_seconds": train_s,
        "single_customer_score": single,
        "batch_scoring": {"rows": len(big), "seconds": batch_s, "rows_per_second": len(big) / batch_s},
        "api_latency_in_process": api,
        "artifact_version": ctx.bundle.version,
        "artifact_bytes": sizes,
        "artifact_total_kb": sum(sizes.values()) / 1024,
        "notes": "Latency is in-process (FastAPI TestClient), single thread, no network; real deployments add transport time.",
    }


def run(ctx: Context) -> dict:
    return {"models": model_benchmark(ctx), "compute": compute_benchmark(ctx)}

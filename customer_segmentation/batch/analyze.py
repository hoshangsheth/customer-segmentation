"""
Segment, score and explain every customer of a prepared upload, and summarise the result.

Model choice: the full model when campaign history was provided, otherwise the behaviour-only model
(trained without history columns), so customers are never scored as if they had refused every offer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from customer_segmentation.artifacts.store import Bundle
from customer_segmentation.batch.prepare import Prepared
from customer_segmentation.explainability.shap_values import shap_matrix
from customer_segmentation.features.engineering import (
    BEHAVIOUR_FEATURES,
    FEATURE_LABELS,
    RESPONSE_FEATURES,
    build_features,
)

HIST_EDGES = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
TOP_REASONS = 3
DATA_FIT_WARN = 0.15  # flag a feature when this share of customers falls outside the training range


@dataclass
class Analysis:
    table: pd.DataFrame  # one row per customer, sorted by rank
    features: pd.DataFrame  # model features, same order as table
    shap: np.ndarray  # SHAP values for the model features, same order as table
    bias: float
    feature_names: list[str]
    summary: dict


def _model_info(bundle: Bundle, use_history: bool) -> dict:
    m = bundle.report["model"]
    if use_history or bundle.response_model_no_history is None:
        return {
            "kind": "full",
            "name": "Full model (with campaign history)",
            "reference_roc_auc": m["holdout"]["roc_auc"],
            "reference_pr_auc": m["holdout"]["pr_auc"],
            "reference_top_decile_lift": bundle.report["lift"]["deciles"][0]["lift"],
        }
    nh = m["no_history"]
    return {
        "kind": "behaviour",
        "name": "Behaviour-only model (no campaign history)",
        "reference_roc_auc": nh["holdout"]["roc_auc"],
        "reference_pr_auc": nh["holdout"]["pr_auc"],
        "reference_top_decile_lift": nh["top_decile_lift"],
    }


def _reasons(values: np.ndarray, names: list[str]) -> list[list[dict]]:
    order = np.argsort(-np.abs(values), axis=1)[:, :TOP_REASONS]
    return [
        [
            {"label": FEATURE_LABELS.get(names[j], names[j]), "direction": "up" if values[i, j] > 0 else "down"}
            for j in row
        ]
        for i, row in enumerate(order)
    ]


def _data_fit(bundle: Bundle, features: pd.DataFrame, names: list[str]) -> dict:
    ranges = bundle.report.get("meta", {}).get("feature_ranges", {})
    flagged = []
    for f in names:
        if f not in ranges:
            continue
        lo, hi = ranges[f]
        outside = float(((features[f] < lo) | (features[f] > hi)).mean())
        if outside >= DATA_FIT_WARN:
            flagged.append(
                {"feature": f, "label": FEATURE_LABELS.get(f, f), "share_outside": outside, "training_range": [lo, hi]}
            )
    flagged.sort(key=lambda r: -r["share_outside"])
    return {"checked": bool(ranges), "flagged": flagged, "threshold": DATA_FIT_WARN}


def _evaluation(prob: np.ndarray, outcome: pd.Series | None) -> dict | None:
    if outcome is None:
        return None
    known = outcome.notna().to_numpy()
    y, p = outcome.to_numpy()[known].astype(int), prob[known]
    if len(y) < 20 or y.min() == y.max():
        return {
            "available": False,
            "reason": "Needs at least 20 known outcomes including both responders and non-responders.",
            "known": int(known.sum()),
        }
    order = np.argsort(-p, kind="stable")
    ranked = y[order]
    base = y.mean()
    deciles = []
    for i, chunk in enumerate(np.array_split(ranked, 10), start=1):
        deciles.append(
            {
                "decile": i,
                "customers": int(len(chunk)),
                "response_rate": float(chunk.mean()),
                "lift": float(chunk.mean() / base) if base else 0.0,
            }
        )
    top = max(1, math.ceil(0.1 * len(y)))
    return {
        "available": True,
        "known": int(len(y)),
        "responders": int(y.sum()),
        "response_rate": float(base),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "top10_lift": float(ranked[:top].mean() / base),
        "mean_predicted": float(p.mean()),
        "deciles": deciles,
    }


def analyze(bundle: Bundle, prepared: Prepared) -> Analysis:
    info = _model_info(bundle, prepared.report.uses_history)
    model = bundle.response_model if info["kind"] == "full" else bundle.response_model_no_history
    names = RESPONSE_FEATURES if info["kind"] == "full" else BEHAVIOUR_FEATURES

    features = build_features(prepared.raw, prepared.as_of)
    segments = bundle.segmenter.predict(features).astype(int)
    X = features[names]
    prob = model.predict_proba(X)[:, 1]
    values, bias = shap_matrix(model, X)

    seg_meta = {s["segment_id"]: s for s in bundle.report["segmentation"]["segments"]}
    order = np.argsort(-prob, kind="stable")
    n = len(prob)
    rank = np.empty(n, dtype=int)
    rank[order] = np.arange(1, n + 1)

    table = pd.DataFrame(
        {
            "customer_id": prepared.ids,
            "segment_id": segments,
            "segment_name": [seg_meta.get(s, {}).get("name", f"Segment {s + 1}") for s in segments],
            "probability": prob,
            "rank": rank,
            "top_percent": rank / n,
            "income": features["income"],
            "age": features["age"],
            "recency": features["recency"],
            "frequency": features["frequency"],
            "monetary": features["monetary"],
            "prior_accepts": features["prior_accepts"],
        }
    )
    table["reasons"] = _reasons(values, names)
    if prepared.outcome is not None:
        table["outcome"] = prepared.outcome.to_numpy()

    table = table.iloc[order].reset_index(drop=True)
    features_sorted = features.iloc[order].reset_index(drop=True)
    shap_sorted = values[order]

    sorted_p = prob[order]
    cum = np.cumsum(sorted_p)
    curve = []
    for pct in range(1, 101):
        k = max(1, math.ceil(n * pct / 100))
        curve.append({"share": pct / 100, "customers": k, "expected_responders": float(cum[k - 1])})

    seg_rows = []
    for sid, meta in sorted(seg_meta.items()):
        mask = segments == sid
        row = {
            "segment_id": sid,
            "name": meta["name"],
            "tagline": meta.get("tagline", ""),
            "customers": int(mask.sum()),
            "share": float(mask.mean()),
            "mean_probability": float(prob[mask].mean()) if mask.any() else 0.0,
            "expected_responders": float(prob[mask].sum()),
            "reference_response_rate": meta["response_rate"],
            "avg_spend": float(features.loc[mask, "monetary"].mean()) if mask.any() else 0.0,
            "avg_income": float(features.loc[mask, "income"].mean()) if mask.any() else 0.0,
        }
        if prepared.outcome is not None:
            known = mask & prepared.outcome.notna().to_numpy()
            row["observed_response_rate"] = float(prepared.outcome.to_numpy()[known].mean()) if known.any() else None
        seg_rows.append(row)

    hist, _ = np.histogram(prob, bins=HIST_EDGES)
    mean_abs = np.abs(values).mean(axis=0)
    drivers = [
        {"feature": names[i], "label": FEATURE_LABELS.get(names[i], names[i]), "mean_abs_shap": float(mean_abs[i])}
        for i in np.argsort(-mean_abs)[:8]
    ]

    summary = {
        "model": info,
        "customers": n,
        "expected_responders": float(prob.sum()),
        "mean_probability": float(prob.mean()),
        "segments": seg_rows,
        "histogram": [
            {"from": HIST_EDGES[i], "to": HIST_EDGES[i + 1], "customers": int(c)} for i, c in enumerate(hist)
        ],
        "curve": curve,
        "drivers": drivers,
        "data_fit": _data_fit(bundle, features, names),
        "evaluation": _evaluation(prob, prepared.outcome),
        "preparation": prepared.report.to_dict(),
        "defaults": {
            "cost_per_contact": bundle.report["data"]["cost_per_contact"],
            "revenue_per_response": bundle.report["data"]["revenue_per_response"],
        },
    }
    return Analysis(table, features_sorted[names], shap_sorted, bias, list(names), summary)


def customer_detail(analysis: Analysis, customer_id: str, top: int = 8) -> dict | None:
    idx = analysis.table.index[analysis.table["customer_id"] == customer_id]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    row = analysis.table.iloc[i]
    vals = analysis.shap[i]
    order = np.argsort(-np.abs(vals))[:top]
    reasons = [
        {
            "feature": analysis.feature_names[j],
            "label": FEATURE_LABELS.get(analysis.feature_names[j], analysis.feature_names[j]),
            "value": float(analysis.features.iloc[i, j]),
            "shap": float(vals[j]),
        }
        for j in order
    ]
    out = {
        "customer_id": row["customer_id"],
        "segment_id": int(row["segment_id"]),
        "segment_name": row["segment_name"],
        "probability": float(row["probability"]),
        "rank": int(row["rank"]),
        "top_percent": float(row["top_percent"]),
        "reasons": reasons,
        "profile": {k: float(row[k]) for k in ("income", "age", "recency", "frequency", "monetary", "prior_accepts")},
    }
    if "outcome" in analysis.table.columns:
        o = row["outcome"]
        out["outcome"] = None if pd.isna(o) else int(o)
    return out

"""
3. Model testing: behavioural, robustness and integrity checks on the shipped models.

Each check returns its measured value; pass or fail is decided in assessment.py against fixed gates.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score, roc_auc_score

from customer_segmentation.explainability.shap_values import shap_matrix
from customer_segmentation.modelling.response_model import make_model
from customer_segmentation.scoring import CustomerRecord, score_customer
from customer_segmentation.segmentation.clustering import fit_segmenter
from model_evaluation.common import Context

BINARY = ["partnered", "complain", "acceptedcmp1", "acceptedcmp2", "acceptedcmp3", "acceptedcmp4", "acceptedcmp5"]
COUNTS = ["children", "household_size", "education_level", "prior_accepts"]
CAMPAIGNS = ["acceptedcmp1", "acceptedcmp2", "acceptedcmp3", "acceptedcmp4", "acceptedcmp5"]


def reproducibility(ctx: Context) -> dict:
    a = make_model(ctx.rs).fit(ctx.X_train, ctx.y_train).predict_proba(ctx.X_test)[:, 1]
    b = make_model(ctx.rs).fit(ctx.X_train, ctx.y_train).predict_proba(ctx.X_test)[:, 1]
    shipped = ctx.holdout_scores()
    return {
        "same_seed_max_abs_diff": float(np.abs(a - b).max()),
        "artifact_vs_retrain_max_abs_diff": float(np.abs(a - shipped).max()),
    }


def label_shuffle(ctx: Context, repeats: int = 5) -> dict:
    """With shuffled labels there is nothing to learn; a holdout AUC far from 0.5 would point to leakage."""
    rng = np.random.default_rng(ctx.rs)
    aucs = []
    for _ in range(repeats):
        y_perm = rng.permutation(ctx.y_train.to_numpy())
        p = make_model(ctx.rs).fit(ctx.X_train, y_perm).predict_proba(ctx.X_test)[:, 1]
        aucs.append(roc_auc_score(ctx.y_test, p))
    return {
        "repeats": repeats,
        "mean_roc_auc": float(np.mean(aucs)),
        "max_abs_dev_from_0.5": float(np.max(np.abs(np.array(aucs) - 0.5))),
    }


def noise_robustness(ctx: Context, scale: float = 0.05) -> dict:
    """Gaussian noise of `scale` x each continuous feature's std; binary and count features untouched."""
    rng = np.random.default_rng(ctx.rs)
    X = ctx.X_test.copy()
    continuous = [c for c in X.columns if c not in BINARY + COUNTS]
    stds = ctx.X_train[continuous].std()
    noisy = X.copy()
    noisy[continuous] = X[continuous] + rng.normal(0, 1, size=(len(X), len(continuous))) * (stds.to_numpy() * scale)
    noisy[continuous] = noisy[continuous].clip(lower=0)
    p, q = ctx.model.predict_proba(X)[:, 1], ctx.model.predict_proba(noisy)[:, 1]
    top = int(round(0.1 * len(p)))
    kept = len(set(np.argsort(-p)[:top]) & set(np.argsort(-q)[:top])) / top
    return {
        "noise_scale_of_std": scale,
        "continuous_features": len(continuous),
        "spearman": float(spearmanr(p, q).statistic),
        "mean_abs_prob_change": float(np.abs(p - q).mean()),
        "top_decile_overlap": float(kept),
        "noisy_roc_auc": float(roc_auc_score(ctx.y_test, q)),
    }


def directional(ctx: Context) -> dict:
    X = ctx.X_test.reset_index(drop=True)
    base = ctx.model.predict_proba(X)[:, 1]

    # One more accepted earlier campaign should raise the chance of accepting the next one.
    more = X.copy()
    eligible = more["prior_accepts"] < 5
    for i in np.flatnonzero(eligible):
        first_free = next(c for c in CAMPAIGNS if more.at[i, c] == 0)
        more.at[i, first_free] = 1
        more.at[i, "prior_accepts"] += 1
    up = ctx.model.predict_proba(more)[:, 1][eligible] - base[eligible]

    # Thirty more days since the last purchase should lower it.
    stale = X.copy()
    stale["recency"] = stale["recency"] + 30
    down = ctx.model.predict_proba(stale)[:, 1] - base

    return {
        "extra_prior_acceptance": {
            "customers": int(eligible.sum()),
            "share_increased": float((up > 0).mean()),
            "share_not_decreased": float((up >= 0).mean()),
            "mean_change": float(up.mean()),
        },
        "recency_plus_30_days": {
            "customers": int(len(X)),
            "share_decreased": float((down < 0).mean()),
            "share_not_increased": float((down <= 0).mean()),
            "mean_change": float(down.mean()),
        },
    }


def batch_invariance(ctx: Context) -> dict:
    X = ctx.X_test
    batch = ctx.model.predict_proba(X)[:, 1]
    single = np.array([ctx.model.predict_proba(X.iloc[[i]])[0, 1] for i in range(len(X))])
    shuffled_idx = np.random.default_rng(ctx.rs).permutation(len(X))
    shuffled = ctx.model.predict_proba(X.iloc[shuffled_idx])[:, 1]
    return {
        "batch_vs_single_max_abs_diff": float(np.abs(batch - single).max()),
        "row_order_max_abs_diff": float(np.abs(batch[shuffled_idx] - shuffled).max()),
    }


def shap_additivity(ctx: Context) -> dict:
    values, bias = shap_matrix(ctx.model, ctx.X_test)
    margin = ctx.model.predict(ctx.X_test, output_margin=True)
    return {"max_abs_error_logit": float(np.abs(values.sum(axis=1) + bias - margin).max())}


def edge_inputs(ctx: Context) -> dict:
    """Valid but extreme customers must score without errors, NaNs or out-of-range values."""
    d = ctx.bundle.report["score_defaults"]
    base = {**d, "customer_since": date.fromisoformat(d["customer_since"])}
    zero_spend = {k: 0 for k in d["spend"]}
    zero_buys = {k: 0 for k in d["purchases"]}
    cases = {
        "median_customer": base,
        "no_spend_no_purchases": {**base, "spend": zero_spend, "purchases": zero_buys},
        "very_high_spender": {**base, "income": 199_000, "spend": {k: 3000 for k in d["spend"]}},
        "accepted_all_campaigns": {**base, "accepted_campaigns": [1, 2, 3, 4, 5]},
        "brand_new_customer": {
            **base,
            "customer_since": date.fromisoformat(ctx.bundle.report["meta"]["reference_date"][:10]),
            "recency": 0,
        },
        "oldest_allowed_birth_year": {**base, "year_birth": 1920},
    }
    out = {}
    for name, fields in cases.items():
        try:
            r = score_customer(ctx.bundle, CustomerRecord(**fields))
            ok = 0.0 <= r.probability <= 1.0 and not np.isnan(r.probability)
            out[name] = {"ok": bool(ok), "probability": r.probability, "segment": r.segment_name}
        except Exception as e:  # report, do not crash the suite
            out[name] = {"ok": False, "error": repr(e)}
    return {"cases": out, "all_ok": all(v["ok"] for v in out.values())}


def segmentation_stability(ctx: Context, seeds: int = 10, subsamples: int = 10) -> dict:
    k = int(len(np.unique(ctx.labels)))
    seed_ari = [
        adjusted_rand_score(ctx.labels, fit_segmenter(ctx.features, k, s).predict(ctx.features))
        for s in range(1, seeds + 1)
    ]
    rng = np.random.default_rng(ctx.rs)
    boot_ari = []
    for _ in range(subsamples):
        idx = rng.choice(len(ctx.features), size=int(0.8 * len(ctx.features)), replace=False)
        refit = fit_segmenter(ctx.features.iloc[idx], k, ctx.rs)
        boot_ari.append(adjusted_rand_score(ctx.labels, refit.predict(ctx.features)))
    return {
        "k": k,
        "seed_ari_mean": float(np.mean(seed_ari)),
        "seed_ari_min": float(np.min(seed_ari)),
        "subsample_ari_mean": float(np.mean(boot_ari)),
        "subsample_ari_min": float(np.min(boot_ari)),
        "subsample_share": 0.8,
    }


def slices(ctx: Context, min_class: int = 10) -> dict:
    """Out-of-fold performance by customer group, to spot groups where the model is weak or miscalibrated."""
    f, y, s = ctx.features, ctx.y.to_numpy(), ctx.oof
    names = {r["segment_id"]: r["name"] for r in ctx.bundle.report["segmentation"]["segments"]}
    groups = {
        "age": pd.cut(
            f["age"], [0, 40, 55, 70, 200], right=False, labels=["under 40", "40 to 54", "55 to 69", "70 plus"]
        ),
        "income": pd.qcut(f["income"], 3, labels=["lower third", "middle third", "upper third"]),
        "education": f["education_level"].map({0: "Undergraduate", 1: "Graduate", 2: "Postgraduate"}),
        "household": f["partnered"].map({0: "Single", 1: "Partnered"}),
        "segment": pd.Series(ctx.labels).map(names),
    }
    out = {}
    for gname, g in groups.items():
        rows = []
        for level in pd.Series(g).dropna().unique():
            m = (pd.Series(g) == level).to_numpy()
            pos, neg = int(y[m].sum()), int((1 - y[m]).sum())
            rows.append(
                {
                    "group": str(level),
                    "customers": int(m.sum()),
                    "responders": pos,
                    "response_rate": float(y[m].mean()),
                    "mean_predicted": float(s[m].mean()),
                    "roc_auc": float(roc_auc_score(y[m], s[m])) if pos >= min_class and neg >= min_class else None,
                }
            )
        out[gname] = sorted(rows, key=lambda r: r["group"])
    aucs = [r["roc_auc"] for rows in out.values() for r in rows if r["roc_auc"] is not None]
    return {"groups": out, "min_slice_roc_auc": float(min(aucs)), "max_slice_roc_auc": float(max(aucs))}


def run(ctx: Context) -> dict:
    return {
        "reproducibility": reproducibility(ctx),
        "label_shuffle": label_shuffle(ctx),
        "noise_robustness": noise_robustness(ctx),
        "directional": directional(ctx),
        "batch_invariance": batch_invariance(ctx),
        "shap_additivity": shap_additivity(ctx),
        "edge_inputs": edge_inputs(ctx),
        "segmentation_stability": segmentation_stability(ctx),
        "slices": slices(ctx),
    }

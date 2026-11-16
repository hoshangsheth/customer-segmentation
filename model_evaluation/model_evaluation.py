"""
1. Model evaluation: how good is the shipped response model and segmentation, measured on data the
model never trained on.

- Response model: ranking (ROC AUC, PR AUC), probability quality (log loss, Brier), and threshold
  metrics (precision, recall, F1, MCC, confusion matrix). Thresholds are picked on out-of-fold scores
  from the training split only, then applied once to the holdout, so nothing is tuned on test data.
- Bootstrap 95% intervals for the holdout ranking metrics.
- Segmentation: silhouette, Davies-Bouldin and Calinski-Harabasz for the chosen k.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    calinski_harabasz_score,
    confusion_matrix,
    davies_bouldin_score,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)

from customer_segmentation.modelling.response_model import out_of_fold_scores
from model_evaluation.common import Context, bootstrap_ci

N_BOOT = 1000


def threshold_metrics(y, p, threshold: float) -> dict:
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "flagged_share": float(pred.mean()),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def choose_thresholds(ctx: Context) -> dict[str, float]:
    """All thresholds come from out-of-fold scores on the training split."""
    y_tr = ctx.y_train.to_numpy()
    p_tr = out_of_fold_scores(ctx.X_train.reset_index(drop=True), ctx.y_train.reset_index(drop=True), 5, ctx.rs)
    grid = np.unique(np.round(p_tr, 3))
    f1s = [f1_score(y_tr, (p_tr >= t).astype(int), zero_division=0) for t in grid]
    profit = [ctx.revenue * int(((p_tr >= t) & (y_tr == 1)).sum()) - ctx.cost * int((p_tr >= t).sum()) for t in grid]
    return {
        "default_0.5": 0.5,
        "best_f1_on_train": float(grid[int(np.argmax(f1s))]),
        "best_profit_on_train": float(grid[int(np.argmax(profit))]),
        "break_even": ctx.cost / ctx.revenue,  # contact when expected revenue p * 11 exceeds the $3 cost
    }


def response_model(ctx: Context) -> dict:
    y = ctx.y_test.to_numpy()
    p = ctx.holdout_scores()
    ranking = {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "base_rate": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "log_loss": float(log_loss(y, p)),
        "log_loss_base_rate": float(log_loss(y, np.full_like(p, ctx.y_train.mean()))),
        "brier": float(brier_score_loss(y, p)),
        "brier_base_rate": float(brier_score_loss(y, np.full_like(p, ctx.y_train.mean()))),
    }
    ranking["brier_skill_score"] = 1 - ranking["brier"] / ranking["brier_base_rate"]
    ranking["roc_auc_ci95"] = bootstrap_ci(roc_auc_score, (y, p), N_BOOT, ctx.rs, stratify=y)
    ranking["pr_auc_ci95"] = bootstrap_ci(average_precision_score, (y, p), N_BOOT, ctx.rs, stratify=y)

    thresholds = choose_thresholds(ctx)
    return {
        "ranking": ranking,
        "thresholds": {name: threshold_metrics(y, p, t) for name, t in thresholds.items()},
        "artifact_report_holdout_roc_auc": float(ctx.bundle.report["model"]["holdout"]["roc_auc"]),
    }


def segmentation(ctx: Context) -> dict:
    scaled = ctx.bundle.segmenter[:-1].transform(ctx.features)
    labels = ctx.labels
    sizes = np.bincount(labels)
    rng = np.random.default_rng(ctx.rs)
    sample = rng.choice(len(labels), size=min(len(labels), 5000), replace=False)
    return {
        "k": int(len(sizes)),
        "silhouette": float(silhouette_score(scaled[sample], labels[sample])),
        "davies_bouldin": float(davies_bouldin_score(scaled, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(scaled, labels)),
        "sizes": sizes.tolist(),
        "smallest_share": float(sizes.min() / sizes.sum()),
        "k_selection": ctx.bundle.report["segmentation"]["k_selection"],
    }


def run(ctx: Context) -> dict:
    return {"response_model": response_model(ctx), "segmentation": segmentation(ctx)}

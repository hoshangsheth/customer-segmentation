"""
2. Model performance evaluation: what the model is worth for campaign targeting, and how stable that is.

- Lift, cumulative gains, KS statistic and campaign profit on out-of-fold scores for every customer.
- Bootstrap 95% intervals for top-10% and top-20% lift.
- Calibration: expected calibration error and reliability bins on the holdout.
- Stability: ROC AUC and PR AUC over 5x5 repeated stratified cross-validation.
- Segment targeting: segments ranked on the training split, measured on the test split.
- Resume claim check: is a 20% lift in targeted campaign conversion supported by this data?
"""

from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

from customer_segmentation.evaluation import lift
from customer_segmentation.evaluation.metrics import holdout_metrics
from customer_segmentation.modelling.response_model import make_model
from model_evaluation.common import Context, bootstrap_ci, top_share_lift

N_BOOT = 1000


def targeting(ctx: Context) -> dict:
    y, s = ctx.y.to_numpy(), ctx.oof
    deciles = lift.as_dicts(lift.decile_table(y, s))
    curve = lift.as_dicts(lift.targeting_curve(y, s, ctx.cost, ctx.revenue))
    best = max(curve, key=lambda c: c["profit"])
    ks = ks_2samp(s[y == 1], s[y == 0]).statistic
    return {
        "method": "out-of-fold scores, stratified 5-fold over all customers",
        "customers": int(len(y)),
        "base_rate": float(y.mean()),
        "oof_roc_auc": float(roc_auc_score(y, s)),
        "oof_pr_auc": float(average_precision_score(y, s)),
        "ks_statistic": float(ks),
        "deciles": deciles,
        "curve": curve,
        "best_profit_point": best,
        "contact_everyone": curve[-1],
        "top10_lift_ci95": bootstrap_ci(lambda a, b: top_share_lift(a, b, 0.1), (y, s), N_BOOT, ctx.rs),
        "top20_lift_ci95": bootstrap_ci(lambda a, b: top_share_lift(a, b, 0.2), (y, s), N_BOOT, ctx.rs),
    }


def calibration(ctx: Context) -> dict:
    m = holdout_metrics(ctx.y_test, ctx.holdout_scores())
    return {
        "expected_calibration_error": m.expected_calibration_error,
        "brier": m.brier,
        "mean_predicted": float(ctx.holdout_scores().mean()),
        "observed_rate": float(ctx.y_test.mean()),
        "bins": [b.__dict__ for b in m.calibration],
    }


def stability(ctx: Context, n_splits: int = 5, n_repeats: int = 5) -> dict:
    cv = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=ctx.rs)
    roc, pr, top10 = [], [], []
    for tr, te in cv.split(ctx.X, ctx.y):
        model = make_model(ctx.rs).fit(ctx.X.iloc[tr], ctx.y.iloc[tr])
        p = model.predict_proba(ctx.X.iloc[te])[:, 1]
        y = ctx.y.iloc[te].to_numpy()
        roc.append(roc_auc_score(y, p))
        pr.append(average_precision_score(y, p))
        top10.append(top_share_lift(y, p, 0.1))

    def summary(v):
        return {"mean": float(np.mean(v)), "std": float(np.std(v)), "min": float(np.min(v)), "max": float(np.max(v))}

    return {
        "scheme": f"{n_repeats}x{n_splits} repeated stratified K-fold, all customers",
        "fits": len(roc),
        "roc_auc": summary(roc),
        "pr_auc": summary(pr),
        "top10_lift": summary(top10),
    }


def segment_targeting(ctx: Context) -> dict:
    names = {s["segment_id"]: s["name"] for s in ctx.bundle.report["segmentation"]["segments"]}
    rows = lift.segment_targeting(ctx.labels[ctx.idx_train], ctx.y_train, ctx.labels[ctx.idx_test], ctx.y_test, names)
    per_segment = []
    for sid, name in names.items():
        mask = ctx.labels == sid
        per_segment.append(
            {
                "segment_id": sid,
                "name": name,
                "customers": int(mask.sum()),
                "response_rate": float(ctx.y[mask].mean()),
                "lift": float(ctx.y[mask].mean() / ctx.y.mean()),
            }
        )
    return {
        "method": "segments ranked on the training split, measured on the test split",
        "test_base_rate": float(ctx.y_test.mean()),
        "rows": lift.as_dicts(rows),
        "per_segment_all_customers": sorted(per_segment, key=lambda r: -r["response_rate"]),
    }


def claim_check(target: dict, seg: dict) -> dict:
    """The resume says the segmentation 'contributed to a 20% lift in targeted campaign conversion'."""
    best_seg = seg["rows"][0]
    top20 = next(c for c in target["curve"] if abs(c["share_targeted"] - 0.2) < 1e-9)
    return {
        "claim": "20% lift in targeted campaign conversion",
        "required_lift": 1.2,
        "segment_only_lift": best_seg["lift"],
        "segment_only_supported": best_seg["lift"] >= 1.2,
        "model_top20_lift": top20["lift"],
        "model_top20_lift_ci95_low": target["top20_lift_ci95"][0],
        "model_supported": target["top20_lift_ci95"][0] >= 1.2,
        "caveat": "Measured on public data as a rebuild; it does not reproduce the original company's campaign.",
    }


def run(ctx: Context) -> dict:
    target = targeting(ctx)
    seg = segment_targeting(ctx)
    return {
        "targeting": target,
        "calibration": calibration(ctx),
        "stability": stability(ctx),
        "segment_targeting": seg,
        "claim_check": claim_check(target, seg),
    }

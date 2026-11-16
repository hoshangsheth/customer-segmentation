"""
Offline training. Reads the raw CSV, fits the segmenter and the response model, measures
everything, and writes a new artifact version.

    python -m customer_segmentation.train [--data PATH] [--out DIR]
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from customer_segmentation.artifacts import store
from customer_segmentation.config import Settings, get_settings
from customer_segmentation.data.cleaning import clean
from customer_segmentation.data.loader import load_raw
from customer_segmentation.data.schema import COST_CONTACT, ID, PRIOR_CAMPAIGNS, REVENUE, TARGET
from customer_segmentation.evaluation import lift
from customer_segmentation.evaluation.metrics import holdout_metrics
from customer_segmentation.explainability.shap_values import global_importance
from customer_segmentation.features.engineering import (
    BEHAVIOUR_FEATURES,
    RESPONSE_FEATURES,
    build_features,
    reference_date_for,
)
from customer_segmentation.modelling.response_model import (
    cross_validate,
    make_baseline,
    make_model,
    out_of_fold_scores,
)
from customer_segmentation.segmentation.clustering import fit_projection, fit_segmenter, project
from customer_segmentation.segmentation.profiling import PROFILE_METRICS, profile_segments
from customer_segmentation.segmentation.selection import choose_k, score_k_range

log = logging.getLogger("train")


def score_defaults(df: pd.DataFrame) -> dict:
    """Median customer, used to prefill the score form."""
    med = df.median(numeric_only=True)
    return {
        "year_birth": int(med["Year_Birth"]),
        "education": df["Education"].mode()[0],
        "marital_status": df["Marital_Status"].mode()[0],
        "income": round(float(med["Income"])),
        "kids": int(med["Kidhome"]),
        "teens": int(med["Teenhome"]),
        "customer_since": df["Dt_Customer"].median().date().isoformat(),
        "recency": int(med["Recency"]),
        "spend": {
            k: int(med[c])
            for k, c in {
                "wine": "MntWines",
                "fruit": "MntFruits",
                "meat": "MntMeatProducts",
                "fish": "MntFishProducts",
                "sweet": "MntSweetProducts",
                "gold": "MntGoldProds",
            }.items()
        },
        "purchases": {
            "web": int(med["NumWebPurchases"]),
            "catalog": int(med["NumCatalogPurchases"]),
            "store": int(med["NumStorePurchases"]),
            "deals": int(med["NumDealsPurchases"]),
        },
        "web_visits": int(med["NumWebVisitsMonth"]),
        "accepted_campaigns": [],
        "complain": False,
    }


def run(settings: Settings, data_path: Path | None = None, out_dir: Path | None = None) -> store.Bundle:
    rs = settings.random_state
    raw = load_raw(data_path or settings.data_path)
    df, cleaning = clean(raw)
    ref_date = reference_date_for(df)
    features = build_features(df, ref_date)
    y = df[TARGET].astype(int)
    log.info("cleaned %d -> %d rows; response rate %.3f", cleaning.rows_in, cleaning.rows_out, y.mean())

    # Segmentation (unsupervised, no campaign columns)
    k_scores = score_k_range(features, settings.k_min, settings.k_max, rs)
    selection = choose_k(k_scores, settings.n_segments)
    segmenter = fit_segmenter(features, selection.chosen_k, rs)
    labels = segmenter.predict(features)
    pca = fit_projection(segmenter, features, rs)
    coords = project(segmenter, pca, features)
    profiles = profile_segments(features, df, labels, y)
    names = {p.segment_id: p.name for p in profiles}
    log.info("k=%d (%s): %s", selection.chosen_k, selection.rule, ", ".join(names.values()))

    # Response model
    X = features[RESPONSE_FEATURES]
    idx_train, idx_test = train_test_split(np.arange(len(X)), test_size=settings.test_size, stratify=y, random_state=rs)
    X_train, X_test, y_train, y_test = X.iloc[idx_train], X.iloc[idx_test], y.iloc[idx_train], y.iloc[idx_test]
    cv_xgb = cross_validate(lambda: make_model(rs), X_train, y_train, settings.cv_folds, rs)
    cv_base = cross_validate(make_baseline, X_train, y_train, settings.cv_folds, rs)
    model = make_model(rs).fit(X_train, y_train)
    holdout = holdout_metrics(y_test, model.predict_proba(X_test)[:, 1])
    baseline_holdout = holdout_metrics(y_test, make_baseline().fit(X_train, y_train).predict_proba(X_test)[:, 1])
    log.info(
        "holdout ROC AUC %.3f, PR AUC %.3f (baseline %.3f)", holdout.roc_auc, holdout.pr_auc, baseline_holdout.roc_auc
    )

    # Behaviour-only model for customer files without campaign history (same split, seed and settings)
    Xb_train, Xb_test = X_train[BEHAVIOUR_FEATURES], X_test[BEHAVIOUR_FEATURES]
    cv_nh = cross_validate(lambda: make_model(rs), Xb_train, y_train, settings.cv_folds, rs)
    model_nh = make_model(rs).fit(Xb_train, y_train)
    holdout_nh = holdout_metrics(y_test, model_nh.predict_proba(Xb_test)[:, 1])
    oof_nh = out_of_fold_scores(X[BEHAVIOUR_FEATURES], y, settings.cv_folds, rs)
    log.info("behaviour-only model: holdout ROC AUC %.3f, PR AUC %.3f", holdout_nh.roc_auc, holdout_nh.pr_auc)

    # Lift: out-of-fold scores for every customer, segment ranking learned on train, measured on test
    oof = out_of_fold_scores(X, y, settings.cv_folds, rs)
    cost, revenue = float(df[COST_CONTACT].iloc[0]), float(df[REVENUE].iloc[0])
    deciles = lift.decile_table(y, oof)
    curve = lift.targeting_curve(y, oof, cost, revenue)
    seg_rows = lift.segment_targeting(labels[idx_train], y.iloc[idx_train], labels[idx_test], y.iloc[idx_test], names)
    best_profit = max(curve, key=lambda p: p.profit)

    report = {
        "version": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data": {
            "source": "Kaggle: Customer Personality Analysis (marketing_campaign.csv)",
            "customers": int(len(df)),
            "responders": int(y.sum()),
            "response_rate": float(y.mean()),
            "reference_date": ref_date.date().isoformat(),
            "cleaning": cleaning.to_dict(),
            "cost_per_contact": cost,
            "revenue_per_response": revenue,
        },
        "segmentation": {
            "k_selection": selection.to_dict(),
            "segments": [p.to_dict() for p in profiles],
            "population": {
                **{m: float(features[m].mean()) for m in PROFILE_METRICS},
                "response_rate": float(y.mean()),
            },
            "projection": {
                "explained_variance": [float(v) for v in pca.explained_variance_ratio_],
                "points": [
                    {"id": int(i), "x": round(float(a), 3), "y": round(float(b), 3), "segment": int(s)}
                    for i, a, b, s in zip(df[ID], coords[:, 0], coords[:, 1], labels, strict=True)
                ],
            },
        },
        "model": {
            "features": RESPONSE_FEATURES,
            "prior_campaign_columns": PRIOR_CAMPAIGNS,
            "train_size": int(len(idx_train)),
            "test_size": int(len(idx_test)),
            "cv": {"xgboost": cv_xgb.to_dict(), "logistic_baseline": cv_base.to_dict()},
            "holdout": holdout.to_dict(),
            "baseline_holdout": {"roc_auc": baseline_holdout.roc_auc, "pr_auc": baseline_holdout.pr_auc},
            "global_importance": global_importance(model, X_test),
            "no_history": {
                "features": BEHAVIOUR_FEATURES,
                "cv": cv_nh.to_dict(),
                "holdout": {k: v for k, v in holdout_nh.to_dict().items() if k != "calibration"},
                "top_decile_lift": lift.decile_table(y, oof_nh)[0].lift,
                "global_importance": global_importance(model_nh, Xb_test),
            },
        },
        "lift": {
            "method": "out-of-fold scores from stratified K-fold over all customers",
            "base_rate": float(y.mean()),
            "deciles": lift.as_dicts(deciles),
            "curve": lift.as_dicts(curve),
            "best_profit_point": lift.as_dicts([best_profit])[0],
            "segment_targeting": {
                "method": "segments ranked by response rate on the training split, measured on the test split",
                "test_base_rate": float(y.iloc[idx_test].mean()),
                "rows": lift.as_dicts(seg_rows),
            },
        },
        "score_defaults": score_defaults(df),
        "meta": {
            "reference_date": ref_date.isoformat(),
            "income_median": cleaning.income_median,
            # 1st to 99th percentile of each model feature, used to flag uploads that look unlike the training data
            "feature_ranges": {
                f: [float(features[f].quantile(0.01)), float(features[f].quantile(0.99))] for f in RESPONSE_FEATURES
            },
        },
    }
    bundle = store.Bundle(store.new_version(), segmenter, pca, model, report, response_model_no_history=model_nh)
    bundle.report["version"] = bundle.version
    folder = store.save(bundle, out_dir or settings.artifacts_dir)
    log.info("saved artifacts to %s", folder)
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the segmentation and response models.")
    parser.add_argument("--data", type=Path, default=None, help="path to marketing_campaign.csv")
    parser.add_argument("--out", type=Path, default=None, help="artifacts directory")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run(get_settings(), args.data, args.out)


if __name__ == "__main__":
    main()

"""
Model quality gates as pytest tests, run against the real data and the shipped artifacts.

    python -m pytest model_evaluation -q

Thresholds come from assessment.GATES so the tests and the report never disagree. The tests skip
when the Kaggle CSV or the trained artifacts are not present (for example in CI).
"""

from __future__ import annotations

import operator

import pytest
from sklearn.metrics import roc_auc_score

from customer_segmentation.artifacts.store import ArtifactsNotFound
from customer_segmentation.data.loader import DatasetNotFound
from customer_segmentation.evaluation.metrics import holdout_metrics
from model_evaluation import model_testing
from model_evaluation.assessment import GATES, OPS
from model_evaluation.common import load_context, top_share_lift

GATE = {g.id: g for g in GATES}


def check(gate_id: str, value: float) -> None:
    g = GATE[gate_id]
    assert OPS[g.op](value, g.threshold), f"{g.id} {g.check}: {value:.6g} is not {g.op} {g.threshold}"


@pytest.fixture(scope="module")
def ctx():
    try:
        return load_context()
    except (DatasetNotFound, ArtifactsNotFound, FileNotFoundError) as e:
        pytest.skip(f"real data or artifacts not available: {e}")


def test_holdout_roc_auc(ctx):
    check("E1", roc_auc_score(ctx.y_test, ctx.holdout_scores()))


def test_holdout_calibration(ctx):
    check("P3", holdout_metrics(ctx.y_test, ctx.holdout_scores()).expected_calibration_error)


def test_top_decile_lift_beats_contacting_everyone(ctx):
    assert operator.gt(top_share_lift(ctx.y.to_numpy(), ctx.oof, 0.1), GATE["P1"].threshold)


def test_artifact_matches_retrain_and_is_deterministic(ctx):
    r = model_testing.reproducibility(ctx)
    check("T1", r["same_seed_max_abs_diff"])
    check("T2", r["artifact_vs_retrain_max_abs_diff"])


def test_no_leakage_under_label_shuffle(ctx):
    check("T3", model_testing.label_shuffle(ctx, repeats=2)["max_abs_dev_from_0.5"])


def test_robust_to_small_feature_noise(ctx):
    check("T4", model_testing.noise_robustness(ctx)["spearman"])


def test_directional_expectations(ctx):
    d = model_testing.directional(ctx)
    check("T5", d["extra_prior_acceptance"]["share_not_decreased"])
    check("T6", d["recency_plus_30_days"]["share_not_increased"])


def test_batch_and_single_scoring_agree(ctx):
    check("T7", model_testing.batch_invariance(ctx)["batch_vs_single_max_abs_diff"])


def test_shap_values_add_up(ctx):
    check("T8", model_testing.shap_additivity(ctx)["max_abs_error_logit"])


def test_edge_case_customers_score_cleanly(ctx):
    result = model_testing.edge_inputs(ctx)
    assert result["all_ok"], result["cases"]

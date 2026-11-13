import numpy as np
import pytest

from customer_segmentation.explainability.shap_values import explain_row, global_importance, shap_matrix
from customer_segmentation.features.engineering import RESPONSE_FEATURES
from customer_segmentation.modelling.response_model import cross_validate, make_model, out_of_fold_scores


@pytest.fixture(scope="module")
def xy(cleaned, features):
    df, _ = cleaned
    return features[RESPONSE_FEATURES], df["Response"].astype(int)


def test_cross_validation_beats_chance(xy):
    X, y = xy
    cv = cross_validate(lambda: make_model(0), X, y, folds=3, random_state=0)
    assert cv.folds == 3 and cv.roc_auc_mean > 0.6


def test_out_of_fold_scores_cover_every_row(xy):
    X, y = xy
    oof = out_of_fold_scores(X, y, folds=3, random_state=0)
    assert oof.shape == (len(X),) and ((oof >= 0) & (oof <= 1)).all()


def test_shap_values_add_up_to_the_model_margin(xy):
    X, y = xy
    model = make_model(0).fit(X, y)
    values, bias = shap_matrix(model, X.head(20))
    margin = model.predict(X.head(20), output_margin=True)
    assert np.allclose(values.sum(axis=1) + bias, margin, atol=1e-4)


def test_explanations_are_sorted_and_labelled(xy):
    X, y = xy
    model = make_model(0).fit(X, y)
    reasons, _ = explain_row(model, X.iloc[[0]], top=5)
    sizes = [abs(r.shap) for r in reasons]
    assert len(reasons) == 5 and sizes == sorted(sizes, reverse=True)
    assert all(r.label and r.feature in RESPONSE_FEATURES for r in reasons)
    importance = global_importance(model, X)
    assert importance[0]["mean_abs_shap"] >= importance[-1]["mean_abs_shap"]

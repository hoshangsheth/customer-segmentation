import numpy as np
import pytest

from customer_segmentation.evaluation.lift import decile_table, segment_targeting, targeting_curve
from customer_segmentation.evaluation.metrics import calibration_bins, expected_calibration_error, holdout_metrics

# 20 customers, 4 responders; the scores put 3 of them in the top 4.
Y = np.array([1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
S = np.linspace(1, 0, 20)


def test_decile_table_by_hand():
    rows = decile_table(Y, S, n_bins=5)  # 5 bins of 4
    assert [r.responders for r in rows] == [3, 0, 0, 0, 1]
    assert rows[0].response_rate == 0.75
    assert rows[0].lift == pytest.approx(0.75 / 0.2)
    assert rows[0].cumulative_capture == 0.75 and rows[-1].cumulative_capture == 1.0


def test_targeting_curve_by_hand():
    curve = targeting_curve(Y, S, cost_per_contact=3, revenue_per_response=11, step=0.2)
    assert [p.customers for p in curve] == [4, 8, 12, 16, 20]
    first, last = curve[0], curve[-1]
    assert first.responders == 3 and first.lift == pytest.approx(3.75)
    assert first.profit == 3 * 11 - 4 * 3
    assert last.lift == pytest.approx(1.0) and last.capture == 1.0
    assert last.profit == 4 * 11 - 20 * 3


def test_random_scores_give_lift_near_one():
    rng = np.random.default_rng(0)
    y = (rng.random(20000) < 0.15).astype(int)
    rows = decile_table(y, rng.random(20000))
    assert all(abs(r.lift - 1) < 0.15 for r in rows)


def test_segment_targeting_ranks_on_train_and_measures_on_test():
    train_labels = np.array([0, 0, 1, 1, 2, 2])
    train_y = np.array([1, 1, 1, 0, 0, 0])  # rank: 0 > 1 > 2
    test_labels = np.array([0, 0, 1, 1, 2, 2, 2, 2])
    test_y = np.array([1, 0, 1, 0, 0, 0, 0, 0])  # base 0.25
    rows = segment_targeting(train_labels, train_y, test_labels, test_y, {0: "A", 1: "B", 2: "C"})
    assert rows[0].names == ["A"] and rows[0].response_rate == 0.5 and rows[0].lift == pytest.approx(2.0)
    assert rows[1].segments == [0, 1] and rows[1].capture == 1.0
    assert rows[-1].lift == pytest.approx(1.0) and rows[-1].share_targeted == 1.0


def test_holdout_metrics_perfect_separation():
    y = np.array([0] * 80 + [1] * 20)
    p = np.where(y == 1, 0.9, 0.1)
    m = holdout_metrics(y, p)
    assert m.roc_auc == 1.0 and m.pr_auc == pytest.approx(1.0)
    assert m.base_rate == 0.2 and m.positives == 20


def test_calibration_error_is_small_when_predictions_match_rates():
    y = np.array([0, 0, 0, 1] * 25)
    p = np.full(100, 0.25)
    bins = calibration_bins(y, p, n_bins=4)
    assert sum(b.count for b in bins) == 100
    assert expected_calibration_error(bins) == pytest.approx(0.0, abs=0.05)

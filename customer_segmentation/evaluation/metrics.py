"""Holdout metrics for a probability model: ranking quality and calibration."""

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


@dataclass
class CalibrationBin:
    mean_predicted: float
    observed_rate: float
    count: int


@dataclass
class HoldoutMetrics:
    n: int
    positives: int
    base_rate: float
    roc_auc: float
    pr_auc: float
    brier: float
    expected_calibration_error: float
    calibration: list[CalibrationBin]

    def to_dict(self) -> dict:
        return asdict(self)


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> list[CalibrationBin]:
    """Quantile bins, so each bin holds about the same number of customers."""
    order = np.argsort(p)
    bins = []
    for chunk in np.array_split(order, n_bins):
        if len(chunk):
            bins.append(CalibrationBin(float(p[chunk].mean()), float(y[chunk].mean()), int(len(chunk))))
    return bins


def expected_calibration_error(bins: list[CalibrationBin]) -> float:
    total = sum(b.count for b in bins)
    return float(sum(b.count * abs(b.mean_predicted - b.observed_rate) for b in bins) / total) if total else 0.0


def holdout_metrics(y, p, n_bins: int = 10) -> HoldoutMetrics:
    y, p = np.asarray(y), np.asarray(p)
    bins = calibration_bins(y, p, n_bins)
    return HoldoutMetrics(
        n=int(len(y)),
        positives=int(y.sum()),
        base_rate=float(y.mean()),
        roc_auc=float(roc_auc_score(y, p)),
        pr_auc=float(average_precision_score(y, p)),
        brier=float(brier_score_loss(y, p)),
        expected_calibration_error=expected_calibration_error(bins),
        calibration=bins,
    )

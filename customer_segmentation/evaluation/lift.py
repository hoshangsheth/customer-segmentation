"""
Measured lift: response rate of a targeted group divided by the response rate of everyone.

- decile_table      customers ranked by model score, cut into tenths
- targeting_curve   for each share of customers contacted: response rate, lift, share of all
                    responders reached, and campaign profit from the dataset's own economics
                    (cost per contact and revenue per response)
- segment_targeting segments ranked on one sample, measured on another (no peeking)
"""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class DecileRow:
    decile: int
    customers: int
    responders: int
    response_rate: float
    lift: float
    cumulative_capture: float


@dataclass
class CurvePoint:
    share_targeted: float
    customers: int
    responders: int
    response_rate: float
    lift: float
    capture: float
    profit: float


@dataclass
class SegmentTargetingRow:
    segments: list[int]
    names: list[str]
    customers: int
    share_targeted: float
    response_rate: float
    lift: float
    capture: float


def _ranked(y, scores) -> np.ndarray:
    y, scores = np.asarray(y), np.asarray(scores)
    # stable sort on -score so ties keep their original order
    return y[np.argsort(-scores, kind="stable")]


def decile_table(y, scores, n_bins: int = 10) -> list[DecileRow]:
    ranked = _ranked(y, scores)
    base, total_pos = ranked.mean(), ranked.sum()
    rows, captured = [], 0
    for i, chunk in enumerate(np.array_split(ranked, n_bins), start=1):
        captured += int(chunk.sum())
        rate = float(chunk.mean()) if len(chunk) else 0.0
        rows.append(
            DecileRow(
                i,
                int(len(chunk)),
                int(chunk.sum()),
                rate,
                float(rate / base) if base else 0.0,
                float(captured / total_pos) if total_pos else 0.0,
            )
        )
    return rows


def targeting_curve(y, scores, cost_per_contact: float, revenue_per_response: float, step: float = 0.05):
    ranked = _ranked(y, scores)
    n, base, total_pos = len(ranked), ranked.mean(), ranked.sum()
    cum = np.cumsum(ranked)
    points = []
    for share in np.round(np.arange(step, 1.0 + 1e-9, step), 4):
        k = max(1, int(round(share * n)))
        hits = int(cum[k - 1])
        rate = float(hits / k)
        points.append(
            CurvePoint(
                share_targeted=float(share),
                customers=k,
                responders=hits,
                response_rate=rate,
                lift=float(rate / base) if base else 0.0,
                capture=float(hits / total_pos) if total_pos else 0.0,
                profit=hits * revenue_per_response - k * cost_per_contact,
            )
        )
    return points


def segment_targeting(train_labels, train_y, test_labels, test_y, names: dict[int, str]) -> list[SegmentTargetingRow]:
    """Rank segments by response rate on the training sample, then target the top 1, 2, ... on the test sample."""
    train_labels, train_y = np.asarray(train_labels), np.asarray(train_y)
    test_labels, test_y = np.asarray(test_labels), np.asarray(test_y)
    segs = sorted(set(train_labels.tolist()), key=lambda s: -train_y[train_labels == s].mean())
    base, total_pos = test_y.mean(), test_y.sum()
    rows = []
    for i in range(1, len(segs) + 1):
        chosen = segs[:i]
        mask = np.isin(test_labels, chosen)
        rate = float(test_y[mask].mean()) if mask.any() else 0.0
        rows.append(
            SegmentTargetingRow(
                segments=[int(s) for s in chosen],
                names=[names.get(int(s), str(s)) for s in chosen],
                customers=int(mask.sum()),
                share_targeted=float(mask.mean()),
                response_rate=rate,
                lift=float(rate / base) if base else 0.0,
                capture=float(test_y[mask].sum() / total_pos) if total_pos else 0.0,
            )
        )
    return rows


def as_dicts(rows) -> list[dict]:
    return [asdict(r) for r in rows]

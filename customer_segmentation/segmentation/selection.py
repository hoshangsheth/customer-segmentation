"""
Choosing k: K-Means inertia (elbow) and silhouette score for each candidate k.

Rule: the k with the best silhouette among k >= 3 (k = 2 almost always wins on silhouette by
splitting high and low spenders, which is too coarse to target). The elbow is reported alongside.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score

from customer_segmentation.segmentation.clustering import preprocessing

MIN_USEFUL_K = 3


@dataclass
class KScore:
    k: int
    inertia: float
    silhouette: float
    davies_bouldin: float


@dataclass
class KSelection:
    scores: list[KScore]
    chosen_k: int
    elbow_k: int
    rule: str

    def to_dict(self) -> dict:
        return asdict(self)


def score_k_range(features: pd.DataFrame, k_min: int, k_max: int, random_state: int) -> list[KScore]:
    X = preprocessing().fit_transform(features)
    scores = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit(X)
        scores.append(
            KScore(
                k=k,
                inertia=float(km.inertia_),
                silhouette=float(silhouette_score(X, km.labels_, random_state=random_state)),
                davies_bouldin=float(davies_bouldin_score(X, km.labels_)),
            )
        )
    return scores


def elbow_k(scores: list[KScore]) -> int:
    """Point of maximum curvature: the largest second difference of inertia."""
    if len(scores) < 3:
        return scores[0].k
    inertia = np.array([s.inertia for s in scores])
    second_diff = inertia[:-2] - 2 * inertia[1:-1] + inertia[2:]
    return scores[int(np.argmax(second_diff)) + 1].k


def choose_k(scores: list[KScore], forced_k: int = 0) -> KSelection:
    elbow = elbow_k(scores)
    if forced_k:
        return KSelection(scores, forced_k, elbow, f"k={forced_k} set by N_SEGMENTS")
    useful = [s for s in scores if s.k >= MIN_USEFUL_K] or scores
    best = max(useful, key=lambda s: s.silhouette)
    return KSelection(scores, best.k, elbow, f"best silhouette among k >= {MIN_USEFUL_K}")

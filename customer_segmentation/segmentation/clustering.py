"""K-Means pipeline: log1p on skewed columns, standard scaling, then K-Means. PCA gives a 2-D view."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from customer_segmentation.features.engineering import LOG_FEATURES, SEGMENTATION_FEATURES


class Log1pColumns(BaseEstimator, TransformerMixin):
    """Applies log1p to the named columns of a DataFrame and returns a numpy array in `columns` order."""

    def __init__(self, columns: list[str], log_columns: list[str]):
        self.columns = columns
        self.log_columns = log_columns

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        out = X[self.columns].astype(float).copy()
        for col in self.log_columns:
            out[col] = np.log1p(out[col].clip(lower=0))
        return out.to_numpy()


def preprocessing() -> Pipeline:
    return Pipeline([("log", Log1pColumns(SEGMENTATION_FEATURES, LOG_FEATURES)), ("scale", StandardScaler())])


def fit_segmenter(features: pd.DataFrame, k: int, random_state: int) -> Pipeline:
    pipe = Pipeline(
        [
            *preprocessing().steps,
            ("kmeans", KMeans(n_clusters=k, n_init=20, random_state=random_state)),
        ]
    )
    pipe.fit(features)
    return pipe


def fit_projection(segmenter: Pipeline, features: pd.DataFrame, random_state: int) -> PCA:
    """PCA fitted on the same scaled space the clusters live in."""
    scaled = segmenter[:-1].transform(features)
    return PCA(n_components=2, random_state=random_state).fit(scaled)


def project(segmenter: Pipeline, pca: PCA, features: pd.DataFrame) -> np.ndarray:
    return pca.transform(segmenter[:-1].transform(features))

"""
Versioned model artifacts on disk.

    artifacts/
      LATEST                    name of the newest version
      20261113-101500/
        segmenter.joblib        log1p + scaler + K-Means pipeline
        projection.joblib       2-D PCA for the scatter plot
        response_model.joblib   XGBoost classifier (uses campaign history)
        response_model_no_history.joblib   XGBoost on behaviour only, for files without history
        report.json             metrics, profiles, lift, metadata (everything the API serves)
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

LATEST = "LATEST"
NO_HISTORY_FILE = "response_model_no_history.joblib"


class ArtifactsNotFound(FileNotFoundError):
    pass


@dataclass
class Bundle:
    version: str
    segmenter: Pipeline
    projection: PCA
    response_model: XGBClassifier
    report: dict[str, Any]
    response_model_no_history: XGBClassifier | None = None


def new_version(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d-%H%M%S")


def save(bundle: Bundle, root: Path) -> Path:
    folder = root / bundle.version
    folder.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle.segmenter, folder / "segmenter.joblib")
    joblib.dump(bundle.projection, folder / "projection.joblib")
    joblib.dump(bundle.response_model, folder / "response_model.joblib")
    if bundle.response_model_no_history is not None:
        joblib.dump(bundle.response_model_no_history, folder / NO_HISTORY_FILE)
    (folder / "report.json").write_text(json.dumps(bundle.report, indent=2), encoding="utf-8")
    (root / LATEST).write_text(bundle.version, encoding="utf-8")
    return folder


def resolve_version(root: Path, version: str = "") -> str:
    if version:
        return version
    pointer = root / LATEST
    if not pointer.exists():
        raise ArtifactsNotFound(f"no trained model in {root}. Run: python -m customer_segmentation.train")
    return pointer.read_text(encoding="utf-8").strip()


def load(root: Path, version: str = "") -> Bundle:
    version = resolve_version(root, version)
    folder = root / version
    if not folder.exists():
        raise ArtifactsNotFound(f"artifact version {version} not found in {root}")
    return Bundle(
        version=version,
        segmenter=joblib.load(folder / "segmenter.joblib"),
        projection=joblib.load(folder / "projection.joblib"),
        response_model=joblib.load(folder / "response_model.joblib"),
        report=json.loads((folder / "report.json").read_text(encoding="utf-8")),
        response_model_no_history=joblib.load(folder / NO_HISTORY_FILE) if (folder / NO_HISTORY_FILE).exists() else None,
    )

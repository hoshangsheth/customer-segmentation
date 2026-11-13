"""Reads the raw CSV and checks it has the expected columns."""

from pathlib import Path

import pandas as pd

from customer_segmentation.data.schema import REQUIRED_COLUMNS

KAGGLE_URL = "https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis"


class DatasetNotFound(FileNotFoundError):
    pass


def load_raw(path: Path) -> pd.DataFrame:
    """Load the tab-separated Kaggle file. Raises DatasetNotFound with download instructions."""
    if not path.exists():
        raise DatasetNotFound(
            f"{path} not found. Download marketing_campaign.csv from {KAGGLE_URL} and place it there."
        )
    df = pd.read_csv(path, sep="\t")
    if len(df.columns) == 1:  # some mirrors re-save it comma-separated
        df = pd.read_csv(path)
    validate_columns(df)
    return df


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"dataset is missing columns: {', '.join(missing)}")

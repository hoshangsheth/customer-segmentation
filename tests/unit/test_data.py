import pandas as pd
import pytest

from customer_segmentation.data.cleaning import clean
from customer_segmentation.data.loader import DatasetNotFound, load_raw, validate_columns
from tests.synthetic import write_csv


def test_load_raw_reads_tab_separated(tmp_path):
    write_csv(tmp_path / "m.csv", n=50)
    df = load_raw(tmp_path / "m.csv")
    assert len(df) == 50 and "Response" in df.columns


def test_load_raw_accepts_comma_separated(tmp_path, raw):
    raw.head(20).to_csv(tmp_path / "m.csv", index=False)
    assert len(load_raw(tmp_path / "m.csv")) == 20


def test_missing_file_explains_how_to_get_it(tmp_path):
    with pytest.raises(DatasetNotFound, match="kaggle.com"):
        load_raw(tmp_path / "nope.csv")


def test_missing_columns_are_reported(raw):
    with pytest.raises(ValueError, match="Income"):
        validate_columns(raw.drop(columns=["Income"]))


def test_cleaning_rules(raw):
    df, report = clean(raw)
    assert report.rows_in == 400
    assert report.dropped_birth_year == 1
    assert report.dropped_income_outlier == 1
    assert report.imputed_income == 3
    assert report.rows_out == len(df) == 398
    assert df["Income"].notna().all()
    assert set(df["Marital_Status"]) <= {"Partnered", "Single"}
    assert set(df["Education"]) <= {"Undergraduate", "Graduate", "Postgraduate"}
    assert pd.api.types.is_datetime64_any_dtype(df["Dt_Customer"])

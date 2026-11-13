"""
Cleaning rules for the raw file. Each rule is counted so the training report shows what changed.

- Birth years before 1920 are data-entry errors (ages over 94 in 2014): rows dropped.
- Income above 200,000 is a single placeholder-like value (666,666): row dropped.
- Missing income (24 rows in the original file) is filled with the median.
- Rare or joke marital statuses ("Alone", "Absurd", "YOLO") are folded into "Single".
- Education is grouped into three levels.
"""

from dataclasses import asdict, dataclass

import pandas as pd

from customer_segmentation.data.schema import DATE_FORMAT

MIN_BIRTH_YEAR = 1920
MAX_INCOME = 200_000

MARITAL_GROUPS = {
    "Married": "Partnered",
    "Together": "Partnered",
    "Single": "Single",
    "Divorced": "Single",
    "Widow": "Single",
    "Alone": "Single",
    "Absurd": "Single",
    "YOLO": "Single",
}
EDUCATION_GROUPS = {
    "Basic": "Undergraduate",
    "2n Cycle": "Undergraduate",
    "Graduation": "Graduate",
    "Master": "Postgraduate",
    "PhD": "Postgraduate",
}


@dataclass
class CleaningReport:
    rows_in: int
    dropped_birth_year: int
    dropped_income_outlier: int
    imputed_income: int
    income_median: float
    rows_out: int

    def to_dict(self) -> dict:
        return asdict(self)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    df = raw.copy()
    rows_in = len(df)

    bad_birth = df["Year_Birth"] < MIN_BIRTH_YEAR
    df = df[~bad_birth]
    bad_income = df["Income"] > MAX_INCOME
    df = df[~bad_income]

    missing_income = df["Income"].isna()
    median = float(df["Income"].median())
    df["Income"] = df["Income"].fillna(median)

    df["Marital_Status"] = df["Marital_Status"].map(MARITAL_GROUPS).fillna("Single")
    df["Education"] = df["Education"].map(EDUCATION_GROUPS).fillna("Graduate")
    df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"], format=DATE_FORMAT)

    df = df.reset_index(drop=True)
    report = CleaningReport(
        rows_in=rows_in,
        dropped_birth_year=int(bad_birth.sum()),
        dropped_income_outlier=int(bad_income.sum()),
        imputed_income=int(missing_income.sum()),
        income_median=median,
        rows_out=len(df),
    )
    return df, report

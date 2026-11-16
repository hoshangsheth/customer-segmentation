"""
Turns cleaned customer rows into model features. Used by training and by the score endpoint,
so a new customer goes through exactly the same transformations.

RFM:
    recency    days since last purchase (the dataset's `Recency`)
    frequency  web + catalog + store purchases
    monetary   total spend over the six categories (two years)
"""

import numpy as np
import pandas as pd

from customer_segmentation.data.schema import DEALS, PRIOR_CAMPAIGNS, PURCHASE_CHANNELS, SPEND_COLUMNS, WEB_VISITS

EDUCATION_LEVEL = {"Undergraduate": 0, "Graduate": 1, "Postgraduate": 2}


def _share(part: pd.Series, total: pd.Series) -> pd.Series:
    return (part / total.where(total > 0)).fillna(0.0)


def build_features(df: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    """Engineered features, one row per customer, same index as `df`."""
    out = pd.DataFrame(index=df.index)

    monetary = sum(df[c] for c in SPEND_COLUMNS.values())
    frequency = sum(df[c] for c in PURCHASE_CHANNELS.values())
    children = df["Kidhome"] + df["Teenhome"]
    partnered = (df["Marital_Status"] == "Partnered").astype(int)

    out["income"] = df["Income"].astype(float)
    out["age"] = reference_date.year - df["Year_Birth"]
    out["children"] = children
    out["household_size"] = 1 + partnered + children
    out["partnered"] = partnered
    out["education_level"] = df["Education"].map(EDUCATION_LEVEL).fillna(1).astype(int)
    out["tenure_days"] = (reference_date - df["Dt_Customer"]).dt.days

    out["recency"] = df["Recency"]
    out["frequency"] = frequency
    out["monetary"] = monetary
    out["avg_order_value"] = (monetary / frequency.where(frequency > 0)).fillna(0.0)

    for name, col in SPEND_COLUMNS.items():
        out[f"{name}_share"] = _share(df[col], monetary)
    for name, col in PURCHASE_CHANNELS.items():
        out[f"{name}_share"] = _share(df[col], frequency)
    out["deal_share"] = _share(df[DEALS], frequency).clip(upper=1.0)
    out["web_visits"] = df[WEB_VISITS]

    for col in PRIOR_CAMPAIGNS:
        out[col.lower()] = df[col]
    out["prior_accepts"] = df[PRIOR_CAMPAIGNS].sum(axis=1)
    out["complain"] = df["Complain"]
    return out.astype(float).replace([np.inf, -np.inf], 0.0)


def reference_date_for(df: pd.DataFrame) -> pd.Timestamp:
    """Snapshot date: the day after the newest enrolment. Stored with the model for scoring."""
    return df["Dt_Customer"].max() + pd.Timedelta(days=1)


# Behaviour and household features used for clustering. Campaign history is left out on purpose
# so segment response rates are an honest test of targeting by segment.
SEGMENTATION_FEATURES = [
    "income",
    "age",
    "children",
    "tenure_days",
    "recency",
    "frequency",
    "monetary",
    "avg_order_value",
    "wine_share",
    "meat_share",
    "gold_share",
    "web_share",
    "catalog_share",
    "store_share",
    "deal_share",
    "web_visits",
]
# Heavy right tails: log1p before scaling.
LOG_FEATURES = ["income", "monetary", "avg_order_value"]

RESPONSE_FEATURES = [
    "income",
    "age",
    "children",
    "household_size",
    "partnered",
    "education_level",
    "tenure_days",
    "recency",
    "frequency",
    "monetary",
    "avg_order_value",
    "wine_share",
    "fruit_share",
    "meat_share",
    "fish_share",
    "sweet_share",
    "gold_share",
    "web_share",
    "catalog_share",
    "store_share",
    "deal_share",
    "web_visits",
    *[c.lower() for c in PRIOR_CAMPAIGNS],
    "prior_accepts",
    "complain",
]

# Campaign-history columns. Many customer files do not have them, so a second model is trained without them.
HISTORY_FEATURES = [*[c.lower() for c in PRIOR_CAMPAIGNS], "prior_accepts"]
BEHAVIOUR_FEATURES = [f for f in RESPONSE_FEATURES if f not in HISTORY_FEATURES]

FEATURE_LABELS = {
    "income": "Household income",
    "age": "Age",
    "children": "Children at home",
    "household_size": "Household size",
    "partnered": "Married or living together",
    "education_level": "Education level",
    "tenure_days": "Days as a customer",
    "recency": "Days since last purchase",
    "frequency": "Number of purchases",
    "monetary": "Total spend",
    "avg_order_value": "Average order value",
    "wine_share": "Share of spend on wine",
    "fruit_share": "Share of spend on fruit",
    "meat_share": "Share of spend on meat",
    "fish_share": "Share of spend on fish",
    "sweet_share": "Share of spend on sweets",
    "gold_share": "Share of spend on gold",
    "web_share": "Share of purchases online",
    "catalog_share": "Share of purchases by catalog",
    "store_share": "Share of purchases in store",
    "deal_share": "Share of purchases on discount",
    "web_visits": "Website visits last month",
    "acceptedcmp1": "Accepted campaign 1",
    "acceptedcmp2": "Accepted campaign 2",
    "acceptedcmp3": "Accepted campaign 3",
    "acceptedcmp4": "Accepted campaign 4",
    "acceptedcmp5": "Accepted campaign 5",
    "prior_accepts": "Earlier campaigns accepted",
    "complain": "Complained in last 2 years",
}

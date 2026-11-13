import pandas as pd
import pytest

from customer_segmentation.data.cleaning import clean
from customer_segmentation.features.engineering import (
    FEATURE_LABELS,
    RESPONSE_FEATURES,
    SEGMENTATION_FEATURES,
    build_features,
    reference_date_for,
)


def test_rfm_and_mix_for_a_known_row(raw):
    df, _ = clean(raw)
    ref = reference_date_for(df)
    f = build_features(df, ref)
    row, src = f.iloc[10], df.iloc[10]
    spend = src[["MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts", "MntSweetProducts", "MntGoldProds"]]
    purchases = src[["NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases"]].sum()
    assert row["monetary"] == spend.sum()
    assert row["frequency"] == purchases
    assert row["recency"] == src["Recency"]
    assert row["age"] == ref.year - src["Year_Birth"]
    assert row["tenure_days"] == (ref - src["Dt_Customer"]).days
    assert row["household_size"] == 1 + (src["Marital_Status"] == "Partnered") + src["Kidhome"] + src["Teenhome"]
    if row["monetary"] > 0:
        assert row["wine_share"] == pytest.approx(src["MntWines"] / spend.sum())


def test_shares_sum_to_one_and_handle_zero_spend(features):
    spend_cols = [f"{c}_share" for c in ["wine", "fruit", "meat", "fish", "sweet", "gold"]]
    sums = features.loc[features["monetary"] > 0, spend_cols].sum(axis=1)
    assert sums.round(6).eq(1).all()


def test_zero_activity_customer_has_finite_features(raw):
    df, _ = clean(raw.head(10))
    df.loc[
        0,
        [
            "MntWines",
            "MntFruits",
            "MntMeatProducts",
            "MntFishProducts",
            "MntSweetProducts",
            "MntGoldProds",
            "NumWebPurchases",
            "NumCatalogPurchases",
            "NumStorePurchases",
            "NumDealsPurchases",
        ],
    ] = 0
    f = build_features(df, pd.Timestamp("2014-07-01"))
    assert f.iloc[0]["avg_order_value"] == 0 and f.iloc[0]["wine_share"] == 0
    assert f.notna().all().all()


def test_feature_lists_are_built_and_labelled(features):
    for col in set(SEGMENTATION_FEATURES) | set(RESPONSE_FEATURES):
        assert col in features.columns
        assert col in FEATURE_LABELS
    # campaign history must not leak into segmentation
    assert not any(c.startswith("accepted") or c == "prior_accepts" for c in SEGMENTATION_FEATURES)

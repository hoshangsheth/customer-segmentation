"""
Synthetic customers with the same columns as the Kaggle file. For tests only: the numbers mean
nothing, they just have enough structure (spend tied to income, response tied to spend) for the
pipeline to fit. A few rows carry the known data problems so the cleaning rules are exercised.
"""

import numpy as np
import pandas as pd


def make_raw(n: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    income = rng.normal(52_000, 20_000, n).clip(2_000, 160_000)
    wealth = (income - income.mean()) / income.std()
    kids = rng.integers(0, 3, n)
    teens = rng.integers(0, 3, n)

    def spend(scale: float) -> np.ndarray:
        return np.maximum(0, rng.gamma(2.0, scale * np.exp(0.8 * wealth - 0.3 * kids))).round()

    web = rng.poisson(np.exp(1.2 + 0.2 * wealth))
    catalog = rng.poisson(np.exp(0.6 + 0.6 * wealth))
    store = rng.poisson(np.exp(1.6 + 0.3 * wealth))
    deals = np.minimum(rng.poisson(1 + kids), web + catalog + store)
    prior = rng.random((n, 5)) < (0.05 + 0.08 * (wealth > 1)[:, None])
    recency = rng.integers(0, 100, n)
    logit = -2.2 + 0.9 * wealth + 1.2 * prior.sum(axis=1) - 0.02 * recency
    response = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    start = pd.Timestamp("2012-07-30")
    joined = start + pd.to_timedelta(rng.integers(0, 700, n), unit="D")

    df = pd.DataFrame(
        {
            "ID": np.arange(1, n + 1),
            "Year_Birth": rng.integers(1945, 1997, n),
            "Education": rng.choice(["Graduation", "PhD", "Master", "2n Cycle", "Basic"], n),
            "Marital_Status": rng.choice(["Married", "Together", "Single", "Divorced", "Widow"], n),
            "Income": income.round(),
            "Kidhome": kids,
            "Teenhome": teens,
            "Dt_Customer": joined.strftime("%d-%m-%Y"),
            "Recency": recency,
            "MntWines": spend(150),
            "MntFruits": spend(12),
            "MntMeatProducts": spend(80),
            "MntFishProducts": spend(18),
            "MntSweetProducts": spend(13),
            "MntGoldProds": spend(22),
            "NumDealsPurchases": deals,
            "NumWebPurchases": web,
            "NumCatalogPurchases": catalog,
            "NumStorePurchases": store,
            "NumWebVisitsMonth": rng.integers(0, 10, n),
            "AcceptedCmp3": prior[:, 2].astype(int),
            "AcceptedCmp4": prior[:, 3].astype(int),
            "AcceptedCmp5": prior[:, 4].astype(int),
            "AcceptedCmp1": prior[:, 0].astype(int),
            "AcceptedCmp2": prior[:, 1].astype(int),
            "Complain": (rng.random(n) < 0.01).astype(int),
            "Z_CostContact": 3,
            "Z_Revenue": 11,
            "Response": response,
        }
    )
    # Known problems from the real file
    df.loc[0, "Year_Birth"] = 1893
    df.loc[1, "Income"] = 666_666
    df.loc[2:4, "Income"] = np.nan
    df.loc[5, "Marital_Status"] = "YOLO"
    return df


def write_csv(path, n: int = 400, seed: int = 0) -> None:
    make_raw(n, seed).to_csv(path, sep="\t", index=False)

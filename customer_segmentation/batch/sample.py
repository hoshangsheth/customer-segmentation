"""
Synthetic demo files for "try with sample data" and the downloadable template.

The rows are generated, not real customers: column names and value formats look like a typical CRM
export, and a few rows are deliberately broken to show the validation report. Outcomes are simulated,
so any accuracy shown on this sample is illustrative only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SAMPLE_SIZE = 1500
SEED = 7

EDUCATION = ["High school", "Bachelor", "Bachelor", "Bachelor", "Master", "PhD"]
MARITAL = ["Married", "Married", "Together", "Single", "Divorced", "Widowed"]


def sample_files(n: int = SAMPLE_SIZE, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    ids = [f"C{100000 + i}" for i in range(n)]
    income = np.clip(rng.normal(55_000, 20_000, n), 8_000, 160_000).round(-2)
    affluence = (income - 55_000) / 20_000
    kids = rng.choice([0, 1, 2], n, p=[0.55, 0.38, 0.07])
    teens = rng.choice([0, 1, 2], n, p=[0.5, 0.45, 0.05])
    base_spend = np.exp(rng.normal(5.6 + 0.9 * affluence - 0.4 * kids, 0.8))
    mix = rng.dirichlet([5, 1, 3, 1, 1, 1.5], n)
    spend = (base_spend[:, None] * mix * 1.6).round()
    level = np.clip(np.log1p(base_spend) - 3.5, 0.3, None)  # purchases grow with spend, more slowly
    web = 1 + rng.poisson(1.4 * level)
    catalog = rng.poisson(0.9 * level * (1 + np.clip(affluence, 0, None)))
    store = 2 + rng.poisson(1.9 * level)
    deals = np.minimum(rng.poisson(1 + kids * 1.2), (web + catalog + store) // 2)
    signup = pd.Timestamp("2023-08-01") + pd.to_timedelta(rng.integers(0, 680, n), unit="D")
    recency = rng.integers(0, 100, n)
    as_of = pd.Timestamp("2025-07-01")
    last_purchase = as_of - pd.to_timedelta(recency, unit="D")
    visits = np.clip(rng.poisson(np.clip(5 - 1.2 * affluence + kids, 1, None)), 1, 10)

    customers = pd.DataFrame(
        {
            "customer_id": ids,
            "birth_year": rng.integers(1957, 2001, n),
            "education": rng.choice(EDUCATION, n),
            "marital_status": rng.choice(MARITAL, n),
            "annual_income": income,
            "kids_at_home": kids,
            "teens_at_home": teens,
            "signup_date": signup.strftime("%Y-%m-%d"),
            "last_purchase_date": last_purchase.strftime("%Y-%m-%d"),
            "wine_spend": spend[:, 0],
            "fruit_spend": spend[:, 1],
            "meat_spend": spend[:, 2],
            "fish_spend": spend[:, 3],
            "sweets_spend": spend[:, 4],
            "gold_spend": spend[:, 5],
            "web_purchases": web,
            "catalog_purchases": catalog,
            "store_purchases": store,
            "discount_purchases": deals,
            "website_visits_last_month": visits,
            "complained": rng.choice(["no", "yes"], n, p=[0.99, 0.01]),
        }
    ).astype(object)

    # Campaign history and a simulated outcome for the latest campaign
    propensity = -3.4 + 0.9 * affluence - 0.02 * recency + 0.6 * (spend[:, 0] / (spend.sum(axis=1) + 1))
    history = {"customer_id": ids}
    accepted = np.zeros(n)
    for i in range(1, 6):
        took = rng.random(n) < 1 / (1 + np.exp(-(propensity + rng.normal(0, 0.5, n))))
        accepted += took
        history[f"campaign_{i}"] = np.where(took, "yes", "no")
    respond = rng.random(n) < 1 / (1 + np.exp(-(propensity + 1.3 * accepted + 1.2)))
    history["responded_last_campaign"] = np.where(respond, "yes", "no")
    history = pd.DataFrame(history).astype(object)

    # A few realistic data problems, so the validation report has something to show
    customers.loc[3, "annual_income"] = ""
    customers.loc[11, "meat_spend"] = -40
    customers.loc[25, "customer_id"] = customers.loc[24, "customer_id"]
    customers.loc[40, "signup_date"] = "not recorded"
    customers.loc[57, "birth_year"] = 1890
    return customers.astype(str).replace({"nan": ""}), history.astype(str)


def template() -> pd.DataFrame:
    """Column headers with three example rows, as a starting point for preparing a file."""
    customers, history = sample_files(n=60)
    merged = customers.merge(history, on="customer_id").head(3)
    return merged

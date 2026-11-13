"""
Scores one new customer with the trained bundle: segment, response probability and SHAP reasons.
Input fields mirror the raw dataset (already grouped education and marital status).
"""

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from customer_segmentation.artifacts.store import Bundle
from customer_segmentation.data.schema import PRIOR_CAMPAIGNS
from customer_segmentation.explainability.shap_values import Contribution, explain_row
from customer_segmentation.features.engineering import RESPONSE_FEATURES, build_features


@dataclass
class CustomerRecord:
    year_birth: int
    education: str  # Undergraduate | Graduate | Postgraduate
    marital_status: str  # Partnered | Single
    income: float
    kids: int
    teens: int
    customer_since: date
    recency: int
    spend: dict[str, float]  # wine, fruit, meat, fish, sweet, gold
    purchases: dict[str, int]  # web, catalog, store, deals
    web_visits: int
    accepted_campaigns: list[int] = field(default_factory=list)  # 1..5
    complain: bool = False


@dataclass
class ScoreResult:
    segment_id: int
    segment_name: str
    probability: float
    base_rate: float
    reasons: list[Contribution]
    bias: float


def to_raw_frame(c: CustomerRecord) -> pd.DataFrame:
    row = {
        "Year_Birth": c.year_birth,
        "Education": c.education,
        "Marital_Status": c.marital_status,
        "Income": c.income,
        "Kidhome": c.kids,
        "Teenhome": c.teens,
        "Dt_Customer": pd.Timestamp(c.customer_since),
        "Recency": c.recency,
        "MntWines": c.spend.get("wine", 0),
        "MntFruits": c.spend.get("fruit", 0),
        "MntMeatProducts": c.spend.get("meat", 0),
        "MntFishProducts": c.spend.get("fish", 0),
        "MntSweetProducts": c.spend.get("sweet", 0),
        "MntGoldProds": c.spend.get("gold", 0),
        "NumWebPurchases": c.purchases.get("web", 0),
        "NumCatalogPurchases": c.purchases.get("catalog", 0),
        "NumStorePurchases": c.purchases.get("store", 0),
        "NumDealsPurchases": c.purchases.get("deals", 0),
        "NumWebVisitsMonth": c.web_visits,
        "Complain": int(c.complain),
    }
    for i, col in enumerate(PRIOR_CAMPAIGNS, start=1):
        row[col] = int(i in c.accepted_campaigns)
    return pd.DataFrame([row])


def score_customer(bundle: Bundle, customer: CustomerRecord, top_reasons: int = 6) -> ScoreResult:
    ref_date = pd.Timestamp(bundle.report["meta"]["reference_date"])
    features = build_features(to_raw_frame(customer), ref_date)
    segment_id = int(bundle.segmenter.predict(features)[0])
    X = features[RESPONSE_FEATURES]
    probability = float(bundle.response_model.predict_proba(X)[0, 1])
    reasons, bias = explain_row(bundle.response_model, X, top_reasons)
    names = {s["segment_id"]: s["name"] for s in bundle.report["segmentation"]["segments"]}
    return ScoreResult(
        segment_id=segment_id,
        segment_name=names.get(segment_id, f"Segment {segment_id + 1}"),
        probability=probability,
        base_rate=float(bundle.report["data"]["response_rate"]),
        reasons=reasons,
        bias=bias,
    )

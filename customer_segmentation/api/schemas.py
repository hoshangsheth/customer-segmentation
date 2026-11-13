"""Typed request and response bodies for the HTTP API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------- shared ----------


class Health(BaseModel):
    status: Literal["ok"]
    model_version: str
    ai_available: bool
    ai_provider: str | None


class SegmentCard(BaseModel):
    segment_id: int
    name: str
    tagline: str
    size: int
    share: float
    response_rate: float
    avg_spend: float
    avg_income: float


class SegmentProfile(BaseModel):
    segment_id: int
    name: str
    tagline: str
    size: int
    share: float
    response_rate: float
    prior_accept_rate: float
    means: dict[str, float]
    spend_mix: dict[str, float]
    channel_mix: dict[str, float]
    traits: list[str]


class KScore(BaseModel):
    k: int
    inertia: float
    silhouette: float
    davies_bouldin: float


class KSelection(BaseModel):
    scores: list[KScore]
    chosen_k: int
    elbow_k: int
    rule: str


class SegmentsOverview(BaseModel):
    segments: list[SegmentProfile]
    population: dict[str, float]
    k_selection: KSelection


class ProjectionPoint(BaseModel):
    id: int
    x: float
    y: float
    segment: int


class Projection(BaseModel):
    explained_variance: list[float]
    points: list[ProjectionPoint]


class Overview(BaseModel):
    model_version: str
    trained_at: str
    customers: int
    response_rate: float
    n_segments: int
    roc_auc: float
    pr_auc: float
    top_decile_lift: float
    top_segment_lift: float
    top_segment_name: str
    best_profit_share: float
    best_profit: float
    segments: list[SegmentCard]


# ---------- model metrics and lift ----------


class CVScores(BaseModel):
    folds: int
    roc_auc_mean: float
    roc_auc_std: float
    pr_auc_mean: float
    pr_auc_std: float


class CalibrationBin(BaseModel):
    mean_predicted: float
    observed_rate: float
    count: int


class Holdout(BaseModel):
    n: int
    positives: int
    base_rate: float
    roc_auc: float
    pr_auc: float
    brier: float
    expected_calibration_error: float
    calibration: list[CalibrationBin]


class Importance(BaseModel):
    feature: str
    label: str
    mean_abs_shap: float


class ModelMetrics(BaseModel):
    train_size: int
    test_size: int
    cv_xgboost: CVScores
    cv_baseline: CVScores
    holdout: Holdout
    baseline_holdout_roc_auc: float
    baseline_holdout_pr_auc: float
    global_importance: list[Importance]
    cleaning: dict[str, float]


class DecileRow(BaseModel):
    decile: int
    customers: int
    responders: int
    response_rate: float
    lift: float
    cumulative_capture: float


class CurvePoint(BaseModel):
    share_targeted: float
    customers: int
    responders: int
    response_rate: float
    lift: float
    capture: float
    profit: float


class SegmentTargetingRow(BaseModel):
    segments: list[int]
    names: list[str]
    customers: int
    share_targeted: float
    response_rate: float
    lift: float
    capture: float


class SegmentTargeting(BaseModel):
    method: str
    test_base_rate: float
    rows: list[SegmentTargetingRow]


class Lift(BaseModel):
    method: str
    base_rate: float
    cost_per_contact: float
    revenue_per_response: float
    deciles: list[DecileRow]
    curve: list[CurvePoint]
    best_profit_point: CurvePoint
    segment_targeting: SegmentTargeting


# ---------- scoring ----------


class CustomerIn(BaseModel):
    year_birth: int = Field(ge=1920, le=2010)
    education: Literal["Undergraduate", "Graduate", "Postgraduate"]
    marital_status: Literal["Partnered", "Single"]
    income: float = Field(ge=0, le=200_000)
    kids: int = Field(ge=0, le=5)
    teens: int = Field(ge=0, le=5)
    customer_since: date
    recency: int = Field(ge=0, le=365, description="days since last purchase")
    spend: dict[Literal["wine", "fruit", "meat", "fish", "sweet", "gold"], float]
    purchases: dict[Literal["web", "catalog", "store", "deals"], int]
    web_visits: int = Field(ge=0, le=60)
    accepted_campaigns: list[int] = Field(default_factory=list, description="numbers 1 to 5")
    complain: bool = False

    @field_validator("spend", "purchases")
    @classmethod
    def non_negative(cls, v: dict) -> dict:
        if any(x < 0 for x in v.values()):
            raise ValueError("values must be zero or more")
        return v

    @field_validator("accepted_campaigns")
    @classmethod
    def campaigns_in_range(cls, v: list[int]) -> list[int]:
        if any(c not in range(1, 6) for c in v):
            raise ValueError("campaign numbers must be between 1 and 5")
        return sorted(set(v))


class Reason(BaseModel):
    feature: str
    label: str
    value: float
    shap: float


class ScoreOut(BaseModel):
    segment_id: int
    segment_name: str
    probability: float
    base_rate: float
    lift_vs_average: float
    reasons: list[Reason]


# ---------- AI insights ----------


class Campaign(BaseModel):
    title: str
    channel: str
    offer: str
    rationale: str


class Persona(BaseModel):
    segment_id: int
    segment_name: str
    persona: str
    motivations: list[str]
    campaigns: list[Campaign]
    watch_outs: list[str]
    source: Literal["llm", "rule-based"]
    model: str


class Explanation(BaseModel):
    score: ScoreOut
    summary: str
    next_best_action: str
    source: Literal["llm", "rule-based"]
    model: str

"""Request and response models for batch analysis of uploaded customer files."""

from typing import Literal

from pydantic import BaseModel, Field

FileRole = Literal["customers", "history"]


class FieldSpec(BaseModel):
    key: str
    label: str
    group: str
    kind: str
    description: str
    aliases: list[str]
    required: bool
    default: float | str | None
    file: FileRole
    history: bool


class RequiredGroupOut(BaseModel):
    keys: list[str]
    message: str


class FieldsOut(BaseModel):
    fields: list[FieldSpec]
    required_groups: list[RequiredGroupOut]
    max_mb: int
    max_rows: int


class ColumnRefIO(BaseModel):
    file: FileRole
    column: str


class FileInfo(BaseModel):
    role: FileRole
    filename: str
    rows: int
    columns: list[str]
    preview: list[dict[str, str]]


class Suggestion(BaseModel):
    mapping: dict[str, ColumnRefIO]
    history_id_column: str | None


class UploadOut(BaseModel):
    job_id: str
    sample: bool
    files: list[FileInfo]
    suggestion: Suggestion


class AnalyzeIn(BaseModel):
    mapping: dict[str, ColumnRefIO]
    history_id_column: str | None = None
    date_order: Literal["auto", "dmy", "mdy", "ymd"] = "auto"


class ModelInfo(BaseModel):
    kind: Literal["full", "behaviour"]
    name: str
    reference_roc_auc: float
    reference_pr_auc: float
    reference_top_decile_lift: float


class SegmentSummary(BaseModel):
    segment_id: int
    name: str
    tagline: str
    customers: int
    share: float
    mean_probability: float
    expected_responders: float
    reference_response_rate: float
    avg_spend: float
    avg_income: float
    observed_response_rate: float | None = None


class HistogramBin(BaseModel):
    from_: float = Field(alias="from")
    to: float
    customers: int

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class CurvePoint(BaseModel):
    share: float
    customers: int
    expected_responders: float


class Driver(BaseModel):
    feature: str
    label: str
    mean_abs_shap: float


class DataFitFlag(BaseModel):
    feature: str
    label: str
    share_outside: float
    training_range: list[float]


class DataFit(BaseModel):
    checked: bool
    flagged: list[DataFitFlag]
    threshold: float


class EvalDecile(BaseModel):
    decile: int
    customers: int
    response_rate: float
    lift: float


class Evaluation(BaseModel):
    available: bool
    known: int
    reason: str | None = None
    responders: int | None = None
    response_rate: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    top10_lift: float | None = None
    mean_predicted: float | None = None
    deciles: list[EvalDecile] = []


class RejectedExample(BaseModel):
    row: int
    customer_id: str
    reason: str


class Preparation(BaseModel):
    rows_in: int
    rows_ready: int
    rejected: dict[str, int]
    rejected_examples: list[RejectedExample]
    duplicate_ids: int
    defaults_used: dict[str, int]
    history_rows_matched: int | None
    history_rows_unmatched: int | None
    income_above_training_range: int
    date_order: str
    as_of: str
    uses_history: bool
    has_outcome: bool


class Economics(BaseModel):
    cost_per_contact: float
    revenue_per_response: float


class SummaryOut(BaseModel):
    job_id: str
    sample: bool
    filenames: dict[str, str]
    model: ModelInfo
    customers: int
    expected_responders: float
    mean_probability: float
    segments: list[SegmentSummary]
    histogram: list[HistogramBin]
    curve: list[CurvePoint]
    drivers: list[Driver]
    data_fit: DataFit
    evaluation: Evaluation | None
    preparation: Preparation
    defaults: Economics


class ReasonChip(BaseModel):
    label: str
    direction: Literal["up", "down"]


class CustomerRow(BaseModel):
    customer_id: str
    segment_id: int
    segment_name: str
    probability: float
    rank: int
    top_percent: float
    income: float
    age: float
    recency: float
    frequency: float
    monetary: float
    prior_accepts: float
    reasons: list[ReasonChip]
    outcome: int | None = None


class CustomerPage(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[CustomerRow]


class DetailReason(BaseModel):
    feature: str
    label: str
    value: float
    shap: float


class CustomerDetail(BaseModel):
    customer_id: str
    segment_id: int
    segment_name: str
    probability: float
    rank: int
    top_percent: float
    reasons: list[DetailReason]
    profile: dict[str, float]
    outcome: int | None = None


class BriefIn(BaseModel):
    top_share: float = Field(0.2, gt=0, le=1)
    cost_per_contact: float = Field(3.0, ge=0)
    revenue_per_response: float = Field(11.0, ge=0)


class BriefAction(BaseModel):
    segment: str
    audience: str
    channel: str
    message: str
    why: str


class BriefOut(BaseModel):
    headline: str
    summary: str
    actions: list[BriefAction]
    budget_note: str
    watch_outs: list[str]
    source: Literal["llm", "rule-based"]
    model: str

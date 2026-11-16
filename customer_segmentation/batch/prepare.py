"""
Turn uploaded files plus a column mapping into rows in the raw dataset format the models were
trained on, and report every change made along the way.

- Rows missing a required value, or with impossible values, are rejected with a reason.
- Optional fields that are not mapped, or blank in a row, get a stated default and are counted.
- A campaign-history file is joined on its own customer ID column.
- Dates accept day-first, month-first or ISO formats; `date_order="auto"` detects which.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from customer_segmentation.batch.fields import (
    CAMPAIGN_KEYS,
    FIELD_BY_KEY,
    HISTORY_KEYS,
    PURCHASE_KEYS,
    SPEND_KEYS,
    ColumnRef,
    missing_requirements,
)
from customer_segmentation.data.schema import DEALS, PRIOR_CAMPAIGNS, PURCHASE_CHANNELS, SPEND_COLUMNS, WEB_VISITS

MIN_AGE, MAX_AGE = 16, 100
TRAINING_MAX_INCOME = 200_000
TRUE = {"1", "yes", "y", "true", "t", "accepted", "responded", "converted"}
FALSE = {"0", "no", "n", "false", "f", "", "not accepted", "none"}


class PrepareError(ValueError):
    """The mapping cannot be used; `problems` are shown to the user."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class PrepareReport:
    rows_in: int
    rows_ready: int = 0
    rejected: dict[str, int] = field(default_factory=dict)
    rejected_examples: list[dict] = field(default_factory=list)
    duplicate_ids: int = 0
    defaults_used: dict[str, int] = field(default_factory=dict)
    history_rows_matched: int | None = None
    history_rows_unmatched: int | None = None
    income_above_training_range: int = 0
    date_order: str = "auto"
    as_of: str = ""
    uses_history: bool = False
    has_outcome: bool = False

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Prepared:
    raw: pd.DataFrame  # one row per customer in the raw dataset format, index 0..n-1
    ids: pd.Series  # customer IDs as strings, aligned with raw
    outcome: pd.Series | None  # 1/0 response to the latest campaign, if mapped
    as_of: pd.Timestamp
    report: PrepareReport


# ---------- value parsers ----------
def parse_number(s: pd.Series) -> pd.Series:
    cleaned = s.astype("string").str.strip().str.replace(r"[\s,$€£₹%]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("float64")


def parse_flag(s: pd.Series) -> pd.Series:
    text = s.astype("string").str.strip().str.lower().fillna("")
    num = pd.to_numeric(text, errors="coerce")
    out = pd.Series(np.nan, index=s.index)
    out[text.isin(TRUE)] = 1.0
    out[text.isin(FALSE)] = 0.0
    numeric = num.notna() & out.isna()
    out[numeric] = (num[numeric] > 0).astype(float)
    return out


def detect_date_order(s: pd.Series) -> str:
    text = s.dropna().astype(str).str.strip()
    if text.empty:
        return "ymd"
    iso = pd.to_datetime(text, format="ISO8601", errors="coerce")
    if iso.notna().mean() >= 0.95:
        return "ymd"
    parts = text.str.split(r"[^0-9]+", regex=True)
    first = pd.to_numeric(parts.str[0], errors="coerce")
    second = pd.to_numeric(parts.str[1], errors="coerce")
    if (second > 12).any() and not (first > 12).any():
        return "mdy"
    return "dmy"


def parse_date(s: pd.Series, order: str) -> pd.Series:
    text = s.astype("string").str.strip()
    if order == "ymd":
        return pd.to_datetime(text, format="mixed", yearfirst=True, errors="coerce")
    return pd.to_datetime(text, format="mixed", dayfirst=order == "dmy", errors="coerce")


def normalise_education(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.lower().fillna("")

    def one(v: str) -> str | None:
        if not v.strip():
            return None
        if re.search(r"phd|doctor|master|msc|mba|ma\b|postgrad|post-grad|graduate school|m\.s", v):
            return "Postgraduate"
        if re.search(r"basic|2n|high ?school|secondary|primary|undergrad|diploma|none|school|ged|associate", v):
            return "Undergraduate"
        return "Graduate"  # graduation, bachelor, degree, college...

    return pd.Series([one(v) for v in t], index=s.index, dtype=object)


def normalise_marital(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.lower().fillna("")

    def one(v: str) -> str | None:
        if not v.strip():
            return None
        if re.search(r"married|together|partner|couple|cohabit|union|engaged", v) and "unmarried" not in v:
            return "Partnered"
        return "Single"

    return pd.Series([one(v) for v in t], index=s.index, dtype=object)


# ---------- main ----------
def prepare(
    frames: dict[str, pd.DataFrame],
    mapping: dict[str, ColumnRef],
    history_id_column: str | None = None,
    date_order: str = "auto",
) -> Prepared:
    problems = missing_requirements(set(mapping))
    unknown = [k for k in mapping if k not in FIELD_BY_KEY]
    problems += [f"Unknown field {k}." for k in unknown]
    for key, ref in mapping.items():
        if ref.file not in frames:
            problems.append(f"{FIELD_BY_KEY.get(key, key)}: file {ref.file} was not uploaded.")
        elif ref.column not in frames[ref.file].columns:
            problems.append(f"Column {ref.column!r} is not in the {ref.file} file.")
    if "customer_id" in mapping and mapping["customer_id"].file != "customers":
        problems.append("Customer ID must come from the customers file.")
    uses_history_file = any(ref.file == "history" for ref in mapping.values())
    if uses_history_file and "history" in frames and not history_id_column:
        problems.append("Choose the customer ID column of the campaign history file.")
    if history_id_column and "history" in frames and history_id_column not in frames["history"].columns:
        problems.append(f"Column {history_id_column!r} is not in the history file.")
    if problems:
        raise PrepareError(problems)

    base = frames["customers"].copy()
    report = PrepareReport(rows_in=len(base))
    reasons = pd.Series("", index=base.index, dtype=object)

    def reject(mask: pd.Series, reason: str) -> None:
        new = mask & (reasons == "")
        reasons[new] = reason

    # IDs: required, unique
    ids = base[mapping["customer_id"].column].astype("string").str.strip()
    reject(ids.isna() | (ids == ""), "Missing customer ID")
    dup = ids.duplicated(keep="first") & ids.notna()
    report.duplicate_ids = int(dup.sum())
    reject(dup, "Duplicate customer ID")

    # Join the history file
    if uses_history_file and "history" in frames:
        hist = frames["history"].copy()
        hist["__id"] = hist[history_id_column].astype("string").str.strip()
        hist = hist.drop_duplicates("__id", keep="first").set_index("__id")
        matched = ids.isin(hist.index)
        report.history_rows_matched = int(matched.sum())
        report.history_rows_unmatched = int((~matched).sum())
        hist_aligned = hist.reindex(ids.to_numpy())
        hist_aligned.index = base.index
    else:
        hist_aligned = None

    def column(key: str) -> pd.Series | None:
        ref = mapping.get(key)
        if ref is None:
            return None
        src = base if ref.file == "customers" else hist_aligned
        return None if src is None else src[ref.column]

    # Dates decide the snapshot ("as of") date
    first_date = column("customer_since")
    order = date_order if date_order != "auto" else detect_date_order(first_date)
    report.date_order = order
    since = parse_date(first_date, order)
    reject(since.isna(), "Customer since: missing or not a date")
    last = parse_date(column("last_purchase_date"), order) if "last_purchase_date" in mapping else None
    candidates = [since.max()] + ([last.max()] if last is not None else [])
    as_of = (
        max(d for d in candidates if pd.notna(d)) + pd.Timedelta(days=1)
        if any(pd.notna(d) for d in candidates)
        else pd.Timestamp.today().normalize()
    )
    report.as_of = as_of.date().isoformat()

    def numeric(key: str, required: bool) -> pd.Series:
        fld = FIELD_BY_KEY[key]
        raw = column(key)
        if raw is None:
            return pd.Series(float(fld.default or 0), index=base.index)
        val = parse_number(raw) if fld.kind != "flag" else parse_flag(raw)
        if required:
            reject(val.isna(), f"{fld.label}: missing or not a number")
        elif val.isna().any():
            filled = int(val.isna().sum())
            report.defaults_used[fld.label] = report.defaults_used.get(fld.label, 0) + filled
            val = val.fillna(float(fld.default or 0))
        return val

    out = pd.DataFrame(index=base.index)

    # Household
    out["Income"] = numeric("income", required=True)
    reject(out["Income"] < 0, "Household income: negative")
    report.income_above_training_range = int((out["Income"] > TRAINING_MAX_INCOME).sum())
    if "year_birth" in mapping:
        out["Year_Birth"] = numeric("year_birth", required=True)
    else:
        out["Year_Birth"] = as_of.year - numeric("age", required=True)
    age = as_of.year - out["Year_Birth"]
    reject((age < MIN_AGE) | (age > MAX_AGE), f"Age outside {MIN_AGE} to {MAX_AGE}")

    for key, col, normaliser in (
        ("education", "Education", normalise_education),
        ("marital_status", "Marital_Status", normalise_marital),
    ):
        fld = FIELD_BY_KEY[key]
        raw = column(key)
        vals = normaliser(raw) if raw is not None else pd.Series(None, index=base.index, dtype=object)
        missing = vals.isna()
        if missing.any():
            report.defaults_used[fld.label] = int(missing.sum())
        out[col] = vals.fillna(fld.default)
    out["Kidhome"] = numeric("kids", required=False)
    out["Teenhome"] = numeric("teens", required=False)
    reject((out["Kidhome"] < 0) | (out["Teenhome"] < 0), "Children: negative")

    # Relationship
    out["Dt_Customer"] = since
    if "recency" in mapping:
        out["Recency"] = numeric("recency", required=True)
    else:
        out["Recency"] = (as_of - last).dt.days
        reject(out["Recency"].isna(), "Last purchase date: missing or not a date")
    reject(out["Recency"] < 0, "Days since last purchase: negative")
    out[WEB_VISITS] = numeric("web_visits", required=False)
    out["Complain"] = numeric("complain", required=False)

    # Spend and purchases: unmapped categories are zero, mapped blanks are zero and counted
    for key, col in zip(SPEND_KEYS, SPEND_COLUMNS.values(), strict=True):
        out[col] = numeric(key, required=False)
    for key, col in zip(PURCHASE_KEYS, [*PURCHASE_CHANNELS.values(), DEALS], strict=True):
        out[col] = numeric(key, required=False)
    money_cols = list(SPEND_COLUMNS.values()) + list(PURCHASE_CHANNELS.values()) + [DEALS, WEB_VISITS]
    reject((out[money_cols] < 0).any(axis=1), "Spend or purchases: negative")

    # Campaign history
    report.uses_history = any(k in mapping for k in HISTORY_KEYS)
    for key, col in zip(CAMPAIGN_KEYS, PRIOR_CAMPAIGNS, strict=True):
        out[col] = numeric(key, required=False) if key in mapping else 0.0
    if "offers_accepted" in mapping and not any(k in mapping for k in CAMPAIGN_KEYS):
        # Only a count is known: mark the most recent campaigns as accepted (campaign 5 is the latest).
        count = numeric("offers_accepted", required=False).clip(0, 5).round()
        for i, col in enumerate(reversed(PRIOR_CAMPAIGNS)):
            out[col] = (count > i).astype(float)
    if hist_aligned is not None and report.history_rows_unmatched:
        report.defaults_used["Campaign history (no matching row: treated as no acceptances)"] = (
            report.history_rows_unmatched
        )

    # Outcome
    outcome = None
    if "response" in mapping:
        outcome = parse_flag(column("response"))  # unknown outcomes stay missing, not "no"
        report.has_outcome = bool(outcome.notna().any())

    ok = reasons == ""
    counts = Counter(reasons[~ok])
    report.rejected = dict(counts.most_common())
    report.rejected_examples = [
        {
            "row": int(i) + 2,
            "customer_id": "" if pd.isna(ids[i]) else str(ids[i]),
            "reason": reasons[i],
        }  # +2: header + 1-based
        for i in reasons[~ok].index[:8]
    ]
    report.rows_ready = int(ok.sum())
    if report.rows_ready == 0:
        raise PrepareError(["No rows could be used. " + "; ".join(f"{r} ({n})" for r, n in counts.most_common(3))])

    out = out[ok].reset_index(drop=True)
    for c in out.columns:
        if c not in ("Education", "Marital_Status", "Dt_Customer"):
            out[c] = out[c].astype(float)
    return Prepared(
        raw=out,
        ids=ids[ok].reset_index(drop=True).astype(str),
        outcome=None if outcome is None else outcome[ok].reset_index(drop=True),
        as_of=as_of,
        report=report,
    )

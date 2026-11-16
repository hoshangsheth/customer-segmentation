import io
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from customer_segmentation.batch import ingest, sample
from customer_segmentation.batch.analyze import analyze, customer_detail
from customer_segmentation.batch.fields import ColumnRef, missing_requirements, suggest_mapping
from customer_segmentation.batch.jobs import JobNotFound, JobStore
from customer_segmentation.batch.prepare import (
    PrepareError,
    detect_date_order,
    normalise_education,
    normalise_marital,
    parse_flag,
    parse_number,
    prepare,
)
from customer_segmentation.llm.insights import InsightsService


@pytest.fixture(scope="module")
def files():
    customers, history = sample.sample_files(n=300)
    return {"customers": customers, "history": history}


@pytest.fixture(scope="module")
def suggestion(files):
    return suggest_mapping({k: list(v.columns) for k, v in files.items()})


def customers_only(suggestion):
    return {k: v for k, v in suggestion.mapping.items() if v.file == "customers"}


# ---------- fields and mapping ----------
def test_suggest_mapping_matches_sample_columns(suggestion):
    m = suggestion.mapping
    assert m["customer_id"] == ColumnRef("customers", "customer_id")
    assert m["income"].column == "annual_income"
    assert m["spend_sweet"].column == "sweets_spend"  # loose match
    assert m["purchases_deals"].column == "discount_purchases"
    assert m["accepted_cmp3"] == ColumnRef("history", "campaign_3")
    assert m["response"].column == "responded_last_campaign"
    assert suggestion.history_id_column == "customer_id"
    assert missing_requirements(set(m)) == []


def test_id_is_never_loosely_matched():
    sug = suggest_mapping({"customers": ["Dt_Customer", "Income"]})
    assert "customer_id" not in sug.mapping
    assert sug.mapping["customer_since"].column == "Dt_Customer"


def test_missing_requirements_lists_groups():
    problems = missing_requirements({"customer_id", "income", "customer_since"})
    assert any("birth year" in p for p in problems)
    assert any("spend" in p for p in problems)


# ---------- ingest ----------
def test_reads_csv_semicolon_and_excel():
    df = ingest.read_table(b"id;income\n1;100\n2;200\n", "x.csv")
    assert list(df.columns) == ["id", "income"] and len(df) == 2
    buf = io.BytesIO()
    pd.DataFrame({"id": [1, 2], "income": [3, 4]}).to_excel(buf, index=False)
    xl = ingest.read_table(buf.getvalue(), "x.xlsx")
    assert xl["income"].tolist() == ["3", "4"]
    assert ingest.preview(xl, 1) == [{"id": "1", "income": "3"}]


@pytest.mark.parametrize(
    "data,name,message",
    [
        (b"", "a.csv", "empty"),
        (b"a,b\n1,2\n", "a.pdf", "CSV"),
        (b"onlyone\n1\n", "a.csv", "no usable"),
        (b"a,a\n1,2\n", "a.csv", "duplicate"),
        (b"\x00\x01", "a.xlsx", "Excel"),
    ],
)
def test_ingest_rejects_bad_files(data, name, message):
    with pytest.raises(ingest.IngestError, match=message):
        ingest.read_table(data, name)


def test_ingest_limits(monkeypatch):
    monkeypatch.setattr(ingest, "MAX_BYTES", 5)
    with pytest.raises(ingest.IngestError, match="larger"):
        ingest.read_table(b"a,b\n1,2\n", "a.csv")
    monkeypatch.setattr(ingest, "MAX_BYTES", 10_000)
    monkeypatch.setattr(ingest, "MAX_ROWS", 1)
    with pytest.raises(ingest.IngestError, match="limit"):
        ingest.read_table(b"a,b\n1,2\n3,4\n", "a.csv")


def test_latin1_text_is_read():
    df = ingest.read_table("name,city\nJosé,Málaga\n".encode("latin-1"), "a.csv")
    assert df.iloc[0, 0] == "José"


# ---------- value parsing ----------
def test_parsers():
    assert parse_number(pd.Series(["$1,200", " 30 ", "x", "12%"])).tolist()[:2] == [1200.0, 30.0]
    assert np.isnan(parse_number(pd.Series(["x"]))[0])
    assert parse_flag(pd.Series(["Yes", "no", "1", "0", "2", "maybe", ""])).tolist()[:5] == [1, 0, 1, 0, 1]
    assert np.isnan(parse_flag(pd.Series(["maybe"]))[0])
    assert detect_date_order(pd.Series(["2024-01-31", "2023-12-01"])) == "ymd"
    assert detect_date_order(pd.Series(["31/01/2024", "01/02/2024"])) == "dmy"
    assert detect_date_order(pd.Series(["01/31/2024", "02/01/2024"])) == "mdy"
    assert detect_date_order(pd.Series([], dtype=str)) == "ymd"
    assert normalise_education(pd.Series(["PhD", "High school", "Bachelor", ""])).tolist() == [
        "Postgraduate",
        "Undergraduate",
        "Graduate",
        None,
    ]
    assert normalise_marital(pd.Series(["Married", "Unmarried", "divorced", ""])).tolist() == [
        "Partnered",
        "Single",
        "Single",
        None,
    ]


# ---------- prepare ----------
def test_prepare_reports_rejections(files, suggestion):
    p = prepare(files, suggestion.mapping, suggestion.history_id_column)
    r = p.report
    assert r.rows_in == 300 and r.rows_ready == 295
    assert r.duplicate_ids == 1
    assert set(r.rejected) == {
        "Household income: missing or not a number",
        "Spend or purchases: negative",
        "Duplicate customer ID",
        "Customer since: missing or not a date",
        "Age outside 16 to 100",
    }
    assert r.rejected_examples[0]["row"] >= 2
    assert r.uses_history and r.has_outcome and r.date_order == "ymd"
    assert r.history_rows_matched == 300
    assert p.raw["Recency"].between(0, 200).all()  # derived from last purchase date
    assert len(p.ids) == len(p.raw) == len(p.outcome)


def test_prepare_defaults_and_offer_count(files):
    c = files["customers"].head(20).copy()
    c.loc[0, "kids_at_home"] = ""
    hist = pd.DataFrame({"cid": c["customer_id"].head(15), "accepted": ["3"] * 15})
    mapping = {
        "customer_id": ColumnRef("customers", "customer_id"),
        "age": ColumnRef("customers", "birth_year"),  # treated as an age: 1957-2000 is outside 16..100
        "income": ColumnRef("customers", "annual_income"),
        "customer_since": ColumnRef("customers", "signup_date"),
        "last_purchase_date": ColumnRef("customers", "last_purchase_date"),
        "spend_wine": ColumnRef("customers", "wine_spend"),
        "purchases_store": ColumnRef("customers", "store_purchases"),
        "kids": ColumnRef("customers", "kids_at_home"),
        "offers_accepted": ColumnRef("history", "accepted"),
    }
    with pytest.raises(PrepareError, match="No rows"):
        prepare({"customers": c, "history": hist}, mapping, "cid")

    mapping["year_birth"] = mapping.pop("age")
    p = prepare({"customers": c, "history": hist}, mapping, "cid", date_order="ymd")
    assert p.report.defaults_used["Children at home"] == 1
    assert p.report.history_rows_unmatched == 5
    # three accepted offers -> the three most recent campaigns
    row = p.raw.iloc[0]
    assert [row[f"AcceptedCmp{i}"] for i in range(1, 6)] == [0, 0, 1, 1, 1]
    assert p.raw["MntFruits"].eq(0).all() and p.raw["Education"].eq("Graduate").all()


def test_prepare_validates_mapping(files, suggestion):
    with pytest.raises(PrepareError) as e:
        prepare(files, {"customer_id": ColumnRef("customers", "nope")})
    assert any("not in the customers file" in p for p in e.value.problems)

    m = dict(suggestion.mapping)
    with pytest.raises(PrepareError, match="ID column of the campaign history"):
        prepare(files, m, None)
    with pytest.raises(PrepareError, match="was not uploaded"):
        prepare({"customers": files["customers"]}, m, "customer_id")
    with pytest.raises(PrepareError, match="must come from the customers file"):
        prepare(files, {**m, "customer_id": ColumnRef("history", "customer_id")}, "customer_id")
    with pytest.raises(PrepareError, match="Unknown field"):
        prepare(files, {**m, "bogus": ColumnRef("customers", "customer_id")}, "customer_id")


def test_unknown_outcome_stays_missing(files, suggestion):
    h = files["history"].copy()
    h.loc[:9, "responded_last_campaign"] = "unknown"
    p = prepare({"customers": files["customers"], "history": h}, suggestion.mapping, "customer_id")
    unknown = set(h.loc[:9, "customer_id"])
    assert p.outcome.isna().sum() == p.ids.isin(unknown).sum() > 0


def test_recency_from_days_column(files, suggestion):
    c = files["customers"].copy()
    c["days_since"] = "10"
    m = {**customers_only(suggestion), "recency": ColumnRef("customers", "days_since")}
    del m["last_purchase_date"]
    p = prepare({"customers": c}, m)
    assert p.raw["Recency"].eq(10).all() and not p.report.uses_history


# ---------- analyze ----------
def test_analyze_full_and_behaviour_models(bundle, files, suggestion):
    full = analyze(bundle, prepare(files, suggestion.mapping, "customer_id"))
    assert full.summary["model"]["kind"] == "full"
    t = full.table
    assert t["rank"].tolist() == list(range(1, len(t) + 1))
    assert t["probability"].is_monotonic_decreasing
    assert len(t.iloc[0]["reasons"]) == 3
    curve = [c["expected_responders"] for c in full.summary["curve"]]
    assert curve == sorted(curve) and len(curve) == 100
    assert sum(b["customers"] for b in full.summary["histogram"]) == len(t)
    assert sum(s["customers"] for s in full.summary["segments"]) == len(t)
    assert full.summary["evaluation"]["available"]

    beh = analyze(bundle, prepare({"customers": files["customers"]}, customers_only(suggestion)))
    assert beh.summary["model"]["kind"] == "behaviour"
    assert beh.summary["evaluation"] is None
    assert "prior_accepts" not in beh.feature_names


def test_full_model_used_when_no_behaviour_model(bundle, files, suggestion):
    old = replace(bundle, response_model_no_history=None)
    a = analyze(old, prepare({"customers": files["customers"]}, customers_only(suggestion)))
    assert a.summary["model"]["kind"] == "full"


def test_evaluation_needs_both_classes(bundle, files, suggestion):
    h = files["history"].copy()
    h["responded_last_campaign"] = "no"
    a = analyze(bundle, prepare({"customers": files["customers"], "history": h}, suggestion.mapping, "customer_id"))
    assert a.summary["evaluation"]["available"] is False


def test_data_fit_flags_unusual_values(bundle, files, suggestion):
    c = files["customers"].copy()
    c["website_visits_last_month"] = "60"
    a = analyze(bundle, prepare({"customers": c}, customers_only(suggestion)))
    assert "web_visits" in [f["feature"] for f in a.summary["data_fit"]["flagged"]]


def test_customer_detail(bundle, files, suggestion):
    a = analyze(bundle, prepare(files, suggestion.mapping, "customer_id"))
    cid = a.table.iloc[0]["customer_id"]
    d = customer_detail(a, cid)
    assert d["rank"] == 1 and len(d["reasons"]) == 8 and "outcome" in d
    assert customer_detail(a, "missing") is None


# ---------- jobs ----------
def test_job_store_expiry_and_cap():
    store = JobStore(ttl_seconds=3600, max_jobs=2)
    a = store.create({}, {})
    store.create({}, {})
    store.create({}, {})
    assert len(store) == 2
    with pytest.raises(JobNotFound):
        store.get(a.id)
    expired = JobStore(ttl_seconds=-1)
    j = expired.create({}, {})
    with pytest.raises(JobNotFound):
        expired.get(j.id)


# ---------- brief ----------
def test_brief_fallback_mentions_model_and_data_fit():
    ctx = {
        "customers": 100,
        "expected_responders_all": 12.0,
        "model": {"name": "Behaviour-only", "uses_history": False},
        "target": {
            "share": 0.2,
            "contacts": 20,
            "expected_responders": 6.0,
            "cost_per_contact": 3,
            "revenue_per_response": 11,
            "cost": 60,
            "revenue": 66,
            "profit": 6,
        },
        "target_segments": [{"segment": "Unknown name", "customers": 20, "expected_responders": 6.0}],
        "data_fit_flags": ["Age"],
    }
    out = InsightsService(None, "v").campaign_brief(ctx)
    assert out["source"] == "rule-based" and "20%" in out["headline"]
    assert len(out["watch_outs"]) == 3 and "Age" in out["watch_outs"][1]
    assert out["actions"][0]["channel"] in {"web", "catalog", "store", "email"}

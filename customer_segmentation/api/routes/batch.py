"""
Batch analysis: upload a customer file (and optionally a campaign-history file), confirm the column
mapping, then browse, explain and export the scored customers. Uploads live in memory and expire.
"""

import io
import math

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from customer_segmentation.api import batch_schemas as s
from customer_segmentation.api.dependencies import get_analytics, get_insights
from customer_segmentation.api.service import AnalyticsService
from customer_segmentation.batch import ingest, sample
from customer_segmentation.batch.analyze import analyze, customer_detail
from customer_segmentation.batch.fields import FIELDS, REQUIRED_GROUPS, ColumnRef, suggest_mapping
from customer_segmentation.batch.jobs import Job, JobNotFound, JobStore
from customer_segmentation.batch.prepare import PrepareError, prepare
from customer_segmentation.llm.insights import InsightsService

router = APIRouter(prefix="/api/batch", tags=["batch"])

SORTABLE = {"rank", "customer_id", "segment_name", "monetary", "recency", "income", "frequency"}


def get_jobs(request: Request) -> JobStore:
    return request.app.state.jobs


def get_job(job_id: str, jobs: JobStore = Depends(get_jobs)) -> Job:
    try:
        return jobs.get(job_id)
    except JobNotFound:
        raise HTTPException(404, "This analysis has expired or does not exist. Upload the file again.") from None


def analysed(job: Job = Depends(get_job)) -> Job:
    if job.analysis is None:
        raise HTTPException(409, "Confirm the column mapping first.")
    return job


def _upload_out(job: Job) -> s.UploadOut:
    files = [
        s.FileInfo(
            role=role, filename=job.filenames[role], rows=len(df), columns=list(df.columns), preview=ingest.preview(df)
        )
        for role, df in job.frames.items()
    ]
    sug = suggest_mapping({role: list(df.columns) for role, df in job.frames.items()})
    return s.UploadOut(
        job_id=job.id,
        sample=job.sample,
        files=files,
        suggestion=s.Suggestion(
            mapping={k: s.ColumnRefIO(file=v.file, column=v.column) for k, v in sug.mapping.items()},
            history_id_column=sug.history_id_column,
        ),
    )


def _summary(job: Job) -> s.SummaryOut:
    return s.SummaryOut(job_id=job.id, sample=job.sample, filenames=job.filenames, **job.analysis.summary)


@router.get("/fields", response_model=s.FieldsOut)
def fields():
    """What an uploaded file can contain, with the column names each field is usually called."""
    return s.FieldsOut(
        fields=[s.FieldSpec(**f.to_dict()) for f in FIELDS],
        required_groups=[s.RequiredGroupOut(keys=list(g.keys), message=g.message) for g in REQUIRED_GROUPS],
        max_mb=ingest.MAX_BYTES // (1024 * 1024),
        max_rows=ingest.MAX_ROWS,
    )


@router.get("/template", response_class=Response)
def template():
    """A CSV with every supported column and three example rows."""
    buf = io.StringIO()
    sample.template().to_csv(buf, index=False)
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="customer_template.csv"'},
    )


@router.post("/sample", response_model=s.UploadOut)
def use_sample(jobs: JobStore = Depends(get_jobs)):
    """Start an analysis with generated demo files (synthetic customers, not real data)."""
    customers, history = sample.sample_files()
    job = jobs.create(
        {"customers": customers, "history": history},
        {"customers": "sample_customers.csv", "history": "sample_campaign_history.csv"},
        sample=True,
    )
    return _upload_out(job)


@router.post("/upload", response_model=s.UploadOut)
async def upload(
    customers: UploadFile = File(..., description="Customer file: CSV, TSV or Excel"),
    history: UploadFile | None = File(None, description="Optional campaign history file joined on customer ID"),
    jobs: JobStore = Depends(get_jobs),
):
    frames, names = {}, {}
    for role, f in (("customers", customers), ("history", history)):
        if f is None or not f.filename:
            continue
        data = await f.read(ingest.MAX_BYTES + 1)
        try:
            frames[role] = ingest.read_table(data, f.filename)
        except ingest.IngestError as e:
            raise HTTPException(422, str(e)) from None
        names[role] = f.filename
    return _upload_out(jobs.create(frames, names))


@router.post("/{job_id}/analyze", response_model=s.SummaryOut)
def run_analysis(body: s.AnalyzeIn, job: Job = Depends(get_job), svc: AnalyticsService = Depends(get_analytics)):
    mapping = {k: ColumnRef(v.file, v.column) for k, v in body.mapping.items()}
    try:
        prepared = prepare(job.frames, mapping, body.history_id_column, body.date_order)
    except PrepareError as e:
        raise HTTPException(422, {"problems": e.problems}) from None
    job.analysis = analyze(svc.bundle, prepared)
    return _summary(job)


@router.get("/{job_id}/summary", response_model=s.SummaryOut)
def summary(job: Job = Depends(analysed)):
    return _summary(job)


@router.get("/{job_id}/customers", response_model=s.CustomerPage)
def customers(
    job: Job = Depends(analysed),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    segment_id: int | None = None,
    q: str = "",
    sort: str = "rank",
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    t = job.analysis.table
    if segment_id is not None:
        t = t[t["segment_id"] == segment_id]
    if q.strip():
        t = t[t["customer_id"].str.contains(q.strip(), case=False, regex=False)]
    if sort not in SORTABLE:
        raise HTTPException(422, f"sort must be one of {sorted(SORTABLE)}")
    t = t.sort_values(sort, ascending=order == "asc", kind="stable")
    page = t.iloc[offset : offset + limit]
    rows = []
    for rec in page.to_dict(orient="records"):
        if "outcome" in rec:
            rec["outcome"] = None if pd.isna(rec["outcome"]) else int(rec["outcome"])
        rows.append(s.CustomerRow(**rec))
    return s.CustomerPage(total=len(t), offset=offset, limit=limit, rows=rows)


@router.get("/{job_id}/customers/{customer_id}", response_model=s.CustomerDetail)
def customer(customer_id: str, job: Job = Depends(analysed)):
    detail = customer_detail(job.analysis, customer_id)
    if detail is None:
        raise HTTPException(404, f"customer {customer_id} not found in this analysis")
    return s.CustomerDetail(**detail)


@router.get("/{job_id}/export", response_class=Response)
def export(job: Job = Depends(analysed), top_share: float = Query(1.0, gt=0, le=1)):
    """Every scored customer, best first, with a contact flag for the top share."""
    t = job.analysis.table
    k = math.ceil(len(t) * top_share)
    out = pd.DataFrame(
        {
            "customer_id": t["customer_id"],
            "rank": t["rank"],
            "top_percent": (t["top_percent"] * 100).round(2),
            "segment": t["segment_name"],
            "response_probability": t["probability"].round(4),
            "contact": ["yes" if r <= k else "no" for r in t["rank"]],
        }
    )
    for i in range(3):
        out[f"reason_{i + 1}"] = [
            f"{r[i]['label']} ({'raises' if r[i]['direction'] == 'up' else 'lowers'} chance)" if len(r) > i else ""
            for r in t["reasons"]
        ]
    if "outcome" in t.columns:
        out["actual_outcome"] = t["outcome"].map({1.0: "yes", 0.0: "no"}).fillna("")
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    name = f"target_list_top{round(top_share * 100)}pct.csv" if top_share < 1 else "scored_customers.csv"
    return Response(
        buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@router.post("/{job_id}/brief", response_model=s.BriefOut)
def brief(body: s.BriefIn, job: Job = Depends(analysed), insights: InsightsService = Depends(get_insights)):
    a = job.analysis
    summ, t = a.summary, a.table
    k = max(1, math.ceil(len(t) * body.top_share))
    top = t.iloc[:k]
    expected = float(top["probability"].sum())
    by_seg = (
        top.groupby("segment_name")
        .agg(customers=("customer_id", "size"), expected_responders=("probability", "sum"))
        .sort_values("expected_responders", ascending=False)
        .reset_index()
    )
    context = {
        "customers": int(len(t)),
        "expected_responders_all": float(summ["expected_responders"]),
        "model": {"name": summ["model"]["name"], "uses_history": summ["model"]["kind"] == "full"},
        "target": {
            "share": body.top_share,
            "contacts": k,
            "expected_responders": expected,
            "cost_per_contact": body.cost_per_contact,
            "revenue_per_response": body.revenue_per_response,
            "cost": k * body.cost_per_contact,
            "revenue": expected * body.revenue_per_response,
            "profit": expected * body.revenue_per_response - k * body.cost_per_contact,
        },
        "target_segments": [
            {
                "segment": r.segment_name,
                "customers": int(r.customers),
                "expected_responders": float(r.expected_responders),
            }
            for r in by_seg.itertuples()
        ],
        "segments_all": [
            {k2: seg[k2] for k2 in ("name", "tagline", "customers", "mean_probability", "avg_spend", "avg_income")}
            for seg in summ["segments"]
        ],
        "top_drivers": [d["label"] for d in summ["drivers"][:5]],
        "data_fit_flags": [f["label"] for f in summ["data_fit"]["flagged"]],
    }
    return s.BriefOut(**insights.campaign_brief(context))

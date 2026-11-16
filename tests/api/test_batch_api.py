import io

import pandas as pd
import pytest

from customer_segmentation.batch import sample


@pytest.fixture
def sample_job(client):
    up = client.post("/api/batch/sample").json()
    return up


def analyze(client, up):
    return client.post(
        f"/api/batch/{up['job_id']}/analyze",
        json={"mapping": up["suggestion"]["mapping"], "history_id_column": up["suggestion"]["history_id_column"]},
    )


def test_fields_and_template(client):
    f = client.get("/api/batch/fields").json()
    assert any(x["key"] == "customer_id" and x["required"] for x in f["fields"])
    assert f["max_rows"] > 0 and f["required_groups"]
    t = client.get("/api/batch/template")
    assert t.status_code == 200 and "attachment" in t.headers["content-disposition"]
    assert t.text.startswith("customer_id,")


def test_sample_flow_end_to_end(client, sample_job):
    assert sample_job["sample"] and {f["role"] for f in sample_job["files"]} == {"customers", "history"}
    jid = sample_job["job_id"]
    assert client.get(f"/api/batch/{jid}/summary").status_code == 409  # not analysed yet

    r = analyze(client, sample_job)
    assert r.status_code == 200
    s = r.json()
    assert s["model"]["kind"] == "full" and s["customers"] == 1495
    assert s["preparation"]["rows_in"] == 1500 and s["evaluation"]["available"]
    assert s["histogram"][0]["from"] == 0
    assert client.get(f"/api/batch/{jid}/summary").json()["customers"] == 1495

    page = client.get(f"/api/batch/{jid}/customers", params={"limit": 5}).json()
    assert page["total"] == 1495 and [r["rank"] for r in page["rows"]] == [1, 2, 3, 4, 5]
    seg = s["segments"][0]["segment_id"]
    filtered = client.get(
        f"/api/batch/{jid}/customers", params={"segment_id": seg, "sort": "monetary", "order": "desc"}
    ).json()
    assert all(r["segment_id"] == seg for r in filtered["rows"])
    first = page["rows"][0]["customer_id"]
    found = client.get(f"/api/batch/{jid}/customers", params={"q": first}).json()
    assert found["rows"][0]["customer_id"] == first
    assert client.get(f"/api/batch/{jid}/customers", params={"sort": "bogus"}).status_code == 422

    detail = client.get(f"/api/batch/{jid}/customers/{first}").json()
    assert detail["rank"] == 1 and detail["reasons"]
    assert client.get(f"/api/batch/{jid}/customers/nobody").status_code == 404

    export = client.get(f"/api/batch/{jid}/export", params={"top_share": 0.1})
    df = pd.read_csv(io.StringIO(export.text))
    assert (df["contact"] == "yes").sum() == 150 and "top10pct" in export.headers["content-disposition"]
    assert set(df["actual_outcome"].dropna()) <= {"yes", "no"}
    full = client.get(f"/api/batch/{jid}/export")
    assert "scored_customers.csv" in full.headers["content-disposition"]


def test_brief_uses_llm_or_rules(client, client_no_ai, sample_job):
    analyze(client, sample_job)
    llm = client.post(f"/api/batch/{sample_job['job_id']}/brief", json={"top_share": 0.2}).json()
    assert llm["source"] == "llm" and llm["headline"] == "Fake headline."

    up = client_no_ai.post("/api/batch/sample").json()
    analyze(client_no_ai, up)
    rules = client_no_ai.post(f"/api/batch/{up['job_id']}/brief", json={"top_share": 0.3, "cost_per_contact": 2}).json()
    assert rules["source"] == "rule-based" and "30%" in rules["headline"]


def test_upload_csv_and_excel(client):
    customers, history = sample.sample_files(n=120)
    xl = io.BytesIO()
    history.to_excel(xl, index=False)
    r = client.post(
        "/api/batch/upload",
        files={
            "customers": ("c.csv", customers.to_csv(index=False).encode(), "text/csv"),
            "history": ("h.xlsx", xl.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        },
    )
    assert r.status_code == 200
    up = r.json()
    assert not up["sample"] and up["files"][1]["filename"] == "h.xlsx"
    assert analyze(client, up).status_code == 200


def test_upload_and_mapping_errors(client):
    bad = client.post("/api/batch/upload", files={"customers": ("c.pdf", b"x", "application/pdf")})
    assert bad.status_code == 422 and "CSV" in bad.json()["detail"]
    up = client.post("/api/batch/upload", files={"customers": ("c.csv", b"id,x\n1,2\n", "text/csv")}).json()
    r = client.post(
        f"/api/batch/{up['job_id']}/analyze", json={"mapping": {"customer_id": {"file": "customers", "column": "id"}}}
    )
    assert r.status_code == 422 and r.json()["detail"]["problems"]
    assert client.get("/api/batch/unknown/summary").status_code == 404

from fastapi.testclient import TestClient

from customer_segmentation.api.app import create_app
from customer_segmentation.config import Settings


def test_health(client, client_no_ai, bundle):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "model_version": bundle.version, "ai_available": True, "ai_provider": "fake"}
    assert client_no_ai.get("/api/health").json()["ai_available"] is False


def test_overview(client, bundle):
    body = client.get("/api/overview").json()
    assert body["customers"] == 398
    assert len(body["segments"]) == len(bundle.report["segmentation"]["segments"])
    assert body["top_decile_lift"] == bundle.report["lift"]["deciles"][0]["lift"]


def test_segments_and_detail(client):
    body = client.get("/api/segments").json()
    assert body["k_selection"]["chosen_k"] == len(body["segments"])
    assert "monetary" in body["population"]
    first = body["segments"][0]
    assert client.get(f"/api/segments/{first['segment_id']}").json()["name"] == first["name"]
    assert client.get("/api/segments/99").status_code == 404


def test_projection_metrics_lift(client):
    assert len(client.get("/api/projection").json()["points"]) == 398
    metrics = client.get("/api/metrics").json()
    assert metrics["holdout"]["calibration"] and metrics["global_importance"]
    lift = client.get("/api/lift").json()
    assert lift["deciles"][0]["decile"] == 1 and lift["cost_per_contact"] == 3


def test_score_round_trip(client):
    customer = client.get("/api/score/defaults").json()
    body = client.post("/api/score", json=customer).json()
    assert 0 <= body["probability"] <= 1 and body["reasons"]
    assert body["lift_vs_average"] == body["probability"] / body["base_rate"]


def test_score_validation(client):
    customer = client.get("/api/score/defaults").json()
    assert client.post("/api/score", json={**customer, "income": -5}).status_code == 422
    assert client.post("/api/score", json={**customer, "accepted_campaigns": [7]}).status_code == 422
    bad_spend = {**customer, "spend": {**customer["spend"], "wine": -1}}
    assert client.post("/api/score", json=bad_spend).status_code == 422


def test_insights_with_llm(client, fake_llm):
    persona = client.get("/api/insights/segments/0").json()
    assert persona["source"] == "llm" and persona["persona"] == "Fake persona."
    customer = client.get("/api/score/defaults").json()
    explanation = client.post("/api/insights/explain", json=customer).json()
    assert explanation["source"] == "llm" and explanation["score"]["reasons"]
    assert len(fake_llm.calls) == 2


def test_insights_without_llm(client_no_ai):
    persona = client_no_ai.get("/api/insights/segments/0").json()
    assert persona["source"] == "rule-based" and persona["campaigns"]
    customer = client_no_ai.get("/api/score/defaults").json()
    assert client_no_ai.post("/api/insights/explain", json=customer).json()["source"] == "rule-based"
    assert client_no_ai.get("/api/insights/segments/99").status_code == 404


def test_app_without_artifacts_reports_503(tmp_path):
    settings = Settings(_env_file=None, artifacts_dir=tmp_path, gemini_api_key="")
    client = TestClient(create_app(settings))
    assert client.get("/api/health").json()["model_version"] == ""
    assert client.get("/api/overview").status_code == 503
    assert client.get("/api/insights/segments/0").status_code == 503

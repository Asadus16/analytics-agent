import os

os.environ.setdefault("SERVICE_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}


def test_health_open():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["metrics"] == 9


def test_query_requires_key():
    assert client.post("/query", json={"metric": "total_mrr", "params": {"as_of": "2026-06"}}).status_code == 401


def test_query_total_mrr():
    r = client.post("/query", json={"metric": "total_mrr", "params": {"as_of": "2026-06"}}, headers=HEADERS)
    body = r.json()
    assert body["value"] == 750.0 and body["audit_id"]


def test_query_undefined_metric_404():
    r = client.post("/query", json={"metric": "valuation", "params": {}}, headers=HEADERS)
    assert r.status_code == 404


def test_golden_endpoint_all_pass():
    r = client.post("/golden/run", headers=HEADERS)
    assert r.json()["failed"] == 0 and r.json()["passed"] >= 10


def test_metrics_catalog():
    assert len(client.get("/metrics", headers=HEADERS).json()) == 9


def test_ask_refuses_without_cassette():
    # In replay mode with no cassette, the planner fails closed -> refusal,
    # never a fabricated answer.
    r = client.post("/ask", json={"question": "what is total mrr in June 2026"}, headers=HEADERS)
    assert r.json()["refused"] is True


def test_audit_roundtrip():
    r = client.post("/query", json={"metric": "revenue", "params": {"month": "2026-03"}}, headers=HEADERS)
    audit_id = r.json()["audit_id"]
    a = client.get(f"/audit/{audit_id}", headers=HEADERS)
    assert a.status_code == 200 and a.json()["metric"] == "revenue"

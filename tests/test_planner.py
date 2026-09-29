from app.llm import gemini, planner
from app.metrics.layer import load_registry

REGISTRY = load_registry()


def _patch(monkeypatch, response: str):
    monkeypatch.setattr(gemini, "generate", lambda prompt: response)


def test_valid_plan(monkeypatch):
    _patch(monkeypatch, '{"metric": "total_mrr", "params": {"as_of": "2026-06"}}')
    p = planner.plan("total mrr in June 2026", REGISTRY)
    assert not p.refused and p.metric == "total_mrr" and p.params == {"as_of": "2026-06"}


def test_null_metric_refused(monkeypatch):
    _patch(monkeypatch, '{"metric": null, "params": {}}')
    assert planner.plan("what is our valuation", REGISTRY).refused


def test_undefined_metric_refused(monkeypatch):
    _patch(monkeypatch, '{"metric": "customer_lifetime_value", "params": {}}')
    assert planner.plan("ltv please", REGISTRY).refused


def test_missing_params_refused(monkeypatch):
    _patch(monkeypatch, '{"metric": "revenue", "params": {}}')
    assert planner.plan("revenue", REGISTRY).refused


def test_bad_json_refused(monkeypatch):
    _patch(monkeypatch, "not json at all")
    assert planner.plan("anything", REGISTRY).refused

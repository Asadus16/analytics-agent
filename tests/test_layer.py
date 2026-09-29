import pytest

from app.golden import run_all
from app.metrics.layer import MetricLayer, MetricNotDefined, MissingParams
from app.seed import DB_PATH
from app.sql.executor import Executor


def test_golden_all_pass():
    bad = [r for r in run_all() if not r.passed]
    assert not bad, [(r.question, r.detail) for r in bad]


def test_undefined_metric_refused():
    layer = MetricLayer(str(DB_PATH))
    with pytest.raises(MetricNotDefined):
        layer.answer("customer_lifetime_value", {})


def test_missing_params_raise():
    layer = MetricLayer(str(DB_PATH))
    with pytest.raises(MissingParams):
        layer.answer("total_mrr", {})


def test_answer_carries_sql_and_rowcount():
    layer = MetricLayer(str(DB_PATH))
    ans = layer.answer("revenue", {"month": "2026-03"})
    assert ans.value == 750.0
    assert "monthly_revenue" in ans.source
    assert ans.params == {"month": "2026-03"}


def test_read_only_blocks_writes():
    ex = Executor(str(DB_PATH))
    with pytest.raises(Exception):
        # bypass the guard to prove the connection itself is read-only
        with ex._connect() as con:
            con.execute("DELETE FROM subscriptions")

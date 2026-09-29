from app.llm.narrate import allowed_numbers, find_violations
from app.metrics.layer import Answer


def _answer():
    return Answer(metric="total_mrr", unit="currency", description="Total MRR",
                  value=750.0, params={"as_of": "2026-06"}, source="SELECT ...",
                  row_count=1)


def test_engine_number_allowed():
    a = _answer()
    assert 750.0 in allowed_numbers(a)
    assert find_violations("Total MRR as of 2026-06 is 750.", a) == []


def test_invented_number_flagged():
    a = _answer()
    assert 900.0 in find_violations("MRR is actually 900.", a)

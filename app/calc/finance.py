"""Deterministic financial calculators.

Computed metrics (churn, cohort retention, MRR growth) that need more than one
query are done here in Python, from guarded read-only queries. The arithmetic
never touches the LLM. Each function returns a plain float.
"""

from __future__ import annotations

from app.sql.executor import Executor

_ACTIVE_AS_OF = (
    "SELECT ROUND(SUM(mrr), 2) AS value FROM subscriptions "
    "WHERE start_month <= :a AND (cancel_month IS NULL OR :a < cancel_month)"
)
_ACTIVE_COUNT_AS_OF = (
    "SELECT COUNT(DISTINCT customer_id) AS value FROM subscriptions "
    "WHERE start_month <= :a AND (cancel_month IS NULL OR :a < cancel_month)"
)


def add_months(month: str, n: int) -> str:
    year, mon = (int(x) for x in month.split("-"))
    idx = (year * 12 + (mon - 1)) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def prev_month(month: str) -> str:
    return add_months(month, -1)


def churn_rate_pct(ex: Executor, month: str) -> float:
    start = prev_month(month)
    active_at_start = ex.scalar(_ACTIVE_COUNT_AS_OF, {"a": start}) or 0
    churned = ex.scalar(
        "SELECT COUNT(*) AS value FROM subscriptions WHERE cancel_month = :m", {"m": month}
    ) or 0
    if not active_at_start:
        return 0.0
    return round(100.0 * churned / active_at_start, 2)


def cohort_retention_pct(ex: Executor, cohort_month: str, offset_months) -> float:
    target = add_months(cohort_month, int(offset_months))
    cohort = ex.scalar(
        "SELECT COUNT(*) AS value FROM customers WHERE signup_month = :c", {"c": cohort_month}
    ) or 0
    if not cohort:
        return 0.0
    retained = ex.scalar(
        "SELECT COUNT(DISTINCT s.customer_id) AS value "
        "FROM subscriptions s JOIN customers c ON c.customer_id = s.customer_id "
        "WHERE c.signup_month = :c AND s.start_month <= :t "
        "AND (s.cancel_month IS NULL OR :t < s.cancel_month)",
        {"c": cohort_month, "t": target},
    ) or 0
    return round(100.0 * retained / cohort, 2)


def mrr_growth_pct(ex: Executor, from_month: str, to_month: str) -> float:
    start = ex.scalar(_ACTIVE_AS_OF, {"a": from_month}) or 0.0
    end = ex.scalar(_ACTIVE_AS_OF, {"a": to_month}) or 0.0
    if not start:
        return 0.0
    return round(100.0 * (end - start) / start, 2)


CALCULATORS = {
    "churn_rate_pct": churn_rate_pct,
    "cohort_retention_pct": cohort_retention_pct,
    "mrr_growth_pct": mrr_growth_pct,
}

import pytest

from app.sql.guard import GuardError, check


def test_allows_plain_select():
    check("SELECT SUM(mrr) AS value FROM subscriptions WHERE start_month <= :a")


def test_rejects_delete():
    with pytest.raises(GuardError):
        check("DELETE FROM subscriptions")


def test_rejects_drop():
    with pytest.raises(GuardError):
        check("DROP TABLE customers")


def test_rejects_multiple_statements():
    with pytest.raises(GuardError):
        check("SELECT 1 FROM customers; SELECT 1 FROM customers")


def test_rejects_unknown_table():
    with pytest.raises(GuardError):
        check("SELECT * FROM secrets")

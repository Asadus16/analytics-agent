"""Build a small, fully deterministic synthetic SaaS dataset.

The data is intentionally tiny and hand-verifiable so the golden answers in
data/golden/questions.json are an independent oracle, not a copy of what the
code computes. Months are 'YYYY-MM' strings; a subscription is active in a month
when start_month <= month and (cancel_month is null or month < cancel_month).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.db"

MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

# customer_id, region, signup_month
CUSTOMERS = [
    ("c1", "US", "2026-01"),
    ("c2", "US", "2026-01"),
    ("c3", "EU", "2026-02"),
    ("c4", "EU", "2026-03"),
    ("c5", "US", "2026-01"),
    ("c6", "EU", "2026-05"),
]

# customer_id, plan, mrr, start_month, cancel_month (None = still active)
SUBSCRIPTIONS = [
    ("c1", "Pro", 100.0, "2026-01", None),
    ("c2", "Pro", 100.0, "2026-01", "2026-04"),
    ("c3", "Basic", 50.0, "2026-02", None),
    ("c4", "Enterprise", 500.0, "2026-03", None),
    ("c5", "Basic", 50.0, "2026-01", "2026-03"),
    ("c6", "Pro", 100.0, "2026-05", None),
]

COGS_RATE = 0.20  # 20% cost of revenue -> 80% gross margin


def _active(month: str, start: str, cancel: str | None) -> bool:
    return start <= month and (cancel is None or month < cancel)


def build(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE regions (region TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE plans (plan TEXT PRIMARY KEY, tier TEXT, monthly_price REAL);
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            region TEXT REFERENCES regions(region),
            signup_month TEXT
        );
        CREATE TABLE subscriptions (
            customer_id TEXT REFERENCES customers(customer_id),
            plan TEXT REFERENCES plans(plan),
            mrr REAL, start_month TEXT, cancel_month TEXT
        );
        CREATE TABLE monthly_revenue (
            customer_id TEXT REFERENCES customers(customer_id),
            month TEXT, revenue REAL, cogs REAL
        );
        """
    )
    con.executemany("INSERT INTO regions VALUES (?,?)",
                    [("US", "United States"), ("EU", "Europe")])
    con.executemany("INSERT INTO plans VALUES (?,?,?)",
                    [("Basic", "standard", 50.0), ("Pro", "standard", 100.0),
                     ("Enterprise", "premium", 500.0)])
    con.executemany("INSERT INTO customers VALUES (?,?,?)", CUSTOMERS)
    con.executemany("INSERT INTO subscriptions VALUES (?,?,?,?,?)", SUBSCRIPTIONS)

    rows = []
    for cid, _plan, mrr, start, cancel in SUBSCRIPTIONS:
        for m in MONTHS:
            if _active(m, start, cancel):
                rows.append((cid, m, mrr, round(mrr * COGS_RATE, 2)))
    con.executemany("INSERT INTO monthly_revenue VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    print("built", build())

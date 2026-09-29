"""SQL guardrail: only a single read-only SELECT over allow-listed tables runs.

Even though the metric layer builds SQL from vetted templates with bound
parameters (so there is no user SQL and no injection surface), every statement
still passes through this guard before execution. It is the control a client
asks about: "what stops it from running something destructive or reading a table
it shouldn't?"
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"customers", "subscriptions", "monthly_revenue"}


class GuardError(ValueError):
    pass


def check(sql: str) -> str:
    statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    if len(statements) != 1:
        raise GuardError("exactly one statement is allowed")

    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Subquery, exp.Union)):
        raise GuardError(f"only SELECT is allowed, got {type(stmt).__name__}")

    # No DML/DDL anywhere in the tree.
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                 exp.Alter, exp.Command)
    for node in stmt.walk():
        if isinstance(node, forbidden):
            raise GuardError(f"forbidden operation: {type(node).__name__}")

    referenced = {t.name for t in stmt.find_all(exp.Table)}
    unknown = referenced - ALLOWED_TABLES
    if unknown:
        raise GuardError(f"table(s) not allow-listed: {sorted(unknown)}")

    return sql

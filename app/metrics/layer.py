"""The governed metric layer.

Resolves a (metric, params) request to a value using only vetted definitions.
The LLM selects the metric and fills declared params; it never authors SQL. An
undefined metric is refused. Every answer carries the exact SQL (or calculator),
the bound params, the row count and the metric definition, so any number can be
traced back to how it was produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.calc.finance import CALCULATORS
from app.sql.executor import Executor

METRICS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "metrics.yaml"


class MetricNotDefined(KeyError):
    pass


class MissingParams(ValueError):
    pass


@dataclass
class Answer:
    metric: str
    unit: str
    description: str
    value: float | int | None
    params: dict
    source: str                       # the SQL text or "computed:<fn>"
    row_count: int
    grouped_rows: list[dict] = field(default_factory=list)


def load_registry(path: Path = METRICS_PATH) -> dict:
    return yaml.safe_load(path.read_text())["metrics"]


class MetricLayer:
    def __init__(self, db_path: str, metrics_path: Path = METRICS_PATH) -> None:
        self.registry = load_registry(metrics_path)
        self.ex = Executor(db_path)

    def list_metrics(self) -> list[dict]:
        return [
            {"metric": name, "unit": d.get("unit"), "type": d["type"],
             "params": d.get("params", []), "description": d.get("description", "")}
            for name, d in self.registry.items()
        ]

    def _require_params(self, name: str, defn: dict, params: dict) -> dict:
        declared = defn.get("params", [])
        missing = [p for p in declared if p not in params]
        if missing:
            raise MissingParams(f"metric '{name}' requires params {missing}")
        return {p: params[p] for p in declared}

    def answer(self, metric: str, params: dict | None = None) -> Answer:
        params = params or {}
        if metric not in self.registry:
            raise MetricNotDefined(metric)
        defn = self.registry[metric]
        bound = self._require_params(metric, defn, params)

        if defn["type"] == "sql":
            sql = " ".join(defn["sql"].split())
            rows, n = self.ex.run(sql, bound)
            if defn.get("grouped"):
                return Answer(metric, defn.get("unit"), defn.get("description", ""),
                              None, bound, sql, n, grouped_rows=rows)
            value = rows[0]["value"] if rows else None
            return Answer(metric, defn.get("unit"), defn.get("description", ""),
                          value, bound, sql, n)

        # computed metric
        fn = CALCULATORS[defn["compute"]]
        value = fn(self.ex, **bound)
        return Answer(metric, defn.get("unit"), defn.get("description", ""),
                      value, bound, f"computed:{defn['compute']}", row_count=0)

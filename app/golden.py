"""Golden regression runner for the analytics layer.

Each golden question has a hand-verified expected number (see app/seed.py for the
tiny, deterministic dataset). The runner asks the metric layer and compares. A
refusal case checks that an undefined metric is refused, not fabricated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.metrics.layer import MetricLayer, MetricNotDefined
from app.seed import DB_PATH

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "data" / "golden" / "questions.json"


@dataclass
class CaseResult:
    question: str
    passed: bool
    detail: str


def _close(a, b, tol: float = 0.01) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def load_cases(path: Path = GOLDEN_PATH) -> list[dict]:
    return json.loads(path.read_text())


def check_case(case: dict, layer: MetricLayer) -> CaseResult:
    q = case.get("question", case.get("metric", "?"))

    if case.get("expect_refusal"):
        try:
            layer.answer(case["metric"], case.get("params", {}))
            return CaseResult(q, False, "expected a refusal but got an answer")
        except MetricNotDefined:
            return CaseResult(q, True, "refused as expected")

    ans = layer.answer(case["metric"], case.get("params", {}))

    if "expect_rows" in case:
        got = [{"region": r["region"], "value": r["value"]} for r in ans.grouped_rows]
        ok = len(got) == len(case["expect_rows"]) and all(
            g["region"] == e["region"] and _close(g["value"], e["value"])
            for g, e in zip(got, case["expect_rows"])
        )
        return CaseResult(q, ok, "" if ok else f"got {got}, expected {case['expect_rows']}")

    ok = _close(ans.value, case["expect"])
    return CaseResult(q, ok, "" if ok else f"got {ans.value}, expected {case['expect']}")


def run_all(path: Path = GOLDEN_PATH) -> list[CaseResult]:
    layer = MetricLayer(str(DB_PATH))
    return [check_case(c, layer) for c in load_cases(path)]

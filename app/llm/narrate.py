"""Narrate an answer, guarding that the model cannot introduce a number the
metric layer did not produce (numbers from code, not the model)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from app.llm import gemini
from app.metrics.layer import Answer

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _numbers_in(text: str) -> set[float]:
    out: set[float] = set()
    for tok in _NUMBER_RE.findall(text):
        tok = tok.rstrip(".").replace(",", "")
        if tok in ("", "-"):
            continue
        try:
            out.add(round(float(tok), 2))
        except ValueError:
            continue
    return out


def allowed_numbers(answer: Answer) -> set[float]:
    return _numbers_in(json.dumps(asdict(answer)))


def find_violations(narrative: str, answer: Answer) -> list[float]:
    allowed = allowed_numbers(answer)
    return [n for n in _numbers_in(narrative)
            if not any(abs(n - a) < 0.01 for a in allowed)]


def _template(answer: Answer) -> str:
    if answer.grouped_rows:
        parts = ", ".join(f"{r['region']}: {r['value']}" for r in answer.grouped_rows)
        return f"{answer.metric} ({answer.unit}): {parts}."
    return f"{answer.metric} ({answer.unit}) = {answer.value}."


def narrate(answer: Answer, max_retries: int = 1) -> tuple[str, bool]:
    prompt_tpl = (PROMPT_DIR / "narrate_v1.md").read_text()
    prompt = prompt_tpl.replace("{answer_json}", json.dumps(asdict(answer), indent=2))
    for _ in range(max_retries + 1):
        try:
            text = gemini.generate(prompt)
        except Exception:
            break
        if not find_violations(text, answer):
            return text.strip(), True
    return _template(answer), False

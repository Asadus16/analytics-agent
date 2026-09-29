"""Plan a question into a governed metric selection.

The LLM's entire job: pick a metric from the catalog and fill its params. If it
picks nothing valid, we refuse rather than guess. This is what keeps the model
away from authoring SQL or inventing figures.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings
from app.llm import gemini

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class Plan:
    metric: str | None
    params: dict = field(default_factory=dict)
    refused: bool = False
    reason: str = ""


def _catalog_text(metrics: list[dict]) -> str:
    lines = []
    for m in metrics:
        params = ", ".join(m["params"]) or "none"
        lines.append(f"- {m['metric']} (params: {params}) — {m['description']}")
    return "\n".join(lines)


def _loads_lenient(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def plan(question: str, registry: dict) -> Plan:
    version = get_settings().prompt_version
    catalog = [
        {"metric": n, "params": d.get("params", []), "description": d.get("description", "")}
        for n, d in registry.items()
    ]
    prompt = (PROMPT_DIR / f"plan_{version}.md").read_text()
    prompt = prompt.replace("{catalog}", _catalog_text(catalog)).replace("{question}", question)

    try:
        data = _loads_lenient(gemini.generate(prompt))
    except Exception as exc:  # bad JSON or LLM error -> refuse, never guess
        return Plan(None, refused=True, reason=f"could not plan the question ({exc})")

    metric = data.get("metric")
    params = data.get("params") or {}
    if not metric or metric not in registry:
        return Plan(None, params=params, refused=True,
                    reason="No defined metric matches this question.")

    declared = registry[metric].get("params", [])
    missing = [p for p in declared if p not in params]
    if missing:
        return Plan(metric, params=params, refused=True,
                    reason=f"Missing parameters for '{metric}': {missing}")
    return Plan(metric, params={p: params[p] for p in declared})

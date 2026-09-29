"""FastAPI service: deterministic financial analytics behind the n8n workflow.

/ask   - natural-language question -> LLM selects a governed metric -> layer
         computes the number in code -> guarded narration. Undefined -> refused.
/query - deterministic metric call (no LLM), the same engine the golden set uses.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException

from app.audit import QueryLog
from app.config import get_settings
from app.golden import run_all
from app.llm.narrate import narrate
from app.llm.planner import plan
from app.metrics.layer import MetricLayer, MetricNotDefined, MissingParams
from app.schemas import AskRequest, QueryRequest
from app.security import verify_api_key

app = FastAPI(title="Deterministic Analytics Agent", version="1.0.0")
_settings = get_settings()
_layer = MetricLayer(_settings.db_path)
_log = QueryLog(_settings.query_log_db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_mode": _settings.llm_mode,
            "metrics": len(_layer.registry)}


@app.get("/metrics", dependencies=[Depends(verify_api_key)])
def metrics() -> list[dict]:
    return _layer.list_metrics()


@app.post("/query", dependencies=[Depends(verify_api_key)])
def query(req: QueryRequest) -> dict:
    try:
        ans = _layer.answer(req.metric, req.params or {})
    except MetricNotDefined:
        raise HTTPException(status_code=404, detail=f"metric '{req.metric}' is not defined")
    except MissingParams as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    result = asdict(ans)
    result["audit_id"] = _log.record(ans, question="(direct query)", narrative="")
    return result


@app.post("/plan", dependencies=[Depends(verify_api_key)])
def plan_endpoint(req: AskRequest) -> dict:
    """LLM-only planning step: pick a governed metric, or refuse. No computation."""
    p = plan(req.question, _layer.registry)
    return {"metric": p.metric, "params": p.params,
            "refused": p.refused, "reason": p.reason}


@app.post("/ask", dependencies=[Depends(verify_api_key)])
def ask(req: AskRequest) -> dict:
    p = plan(req.question, _layer.registry)
    if p.refused:
        return {"refused": True, "reason": p.reason, "question": req.question}
    ans = _layer.answer(p.metric, p.params)
    narrative, used_llm = narrate(ans) if req.narrate else ("", False)
    audit_id = _log.record(ans, req.question, narrative)
    result = asdict(ans)
    result.update({
        "refused": False,
        "narrative": narrative,
        "narrative_from_llm": used_llm,
        "audit_id": audit_id,
    })
    return result


@app.get("/audit/{audit_id}", dependencies=[Depends(verify_api_key)])
def get_audit(audit_id: str) -> dict:
    record = _log.get(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail="audit id not found")
    return record


@app.post("/golden/run", dependencies=[Depends(verify_api_key)])
def golden_run() -> dict:
    results = run_all()
    passed = [r for r in results if r.passed]
    return {
        "total": len(results),
        "passed": len(passed),
        "failed": len(results) - len(passed),
        "failures": [{"question": r.question, "detail": r.detail}
                     for r in results if not r.passed],
    }

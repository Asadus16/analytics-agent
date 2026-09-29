# Deterministic Financial Analytics Agent

Ask business questions in plain English — *"what was our churn in April?"*,
*"MRR by region as of June?"* — and get an answer where **every number is
computed by code, never by the model.** Built as a hybrid: **n8n** orchestrates,
a **FastAPI** service holds a governed metric layer, a SQL guardrail, and
deterministic calculators.

It answers the one question every client asks about an analytics bot: *can the AI
make up numbers?* Here it structurally cannot.

## What makes it different

Most "talk to your database" demos let the LLM write SQL and run it. That works
on a toy schema and invents tables on a real one, with no governance and no way
to trust a figure. This one is built the way a company would actually adopt:

- **Governed metric layer** (`data/metrics.yaml`): every metric — MRR, revenue,
  gross margin, churn, cohort retention, MRR growth — is defined once, in code,
  versioned in git. "Revenue" has exactly one definition. No metric drift.
- **The LLM never writes SQL and never computes.** It only selects a metric from
  the catalog and fills its declared parameters. If nothing fits, the request is
  **refused**, not guessed (`customer_lifetime_value` → refusal, not a made-up
  number).
- **SQL guardrail** (`app/sql/guard.py`, sqlglot): only a single read-only SELECT
  over allow-listed tables can run; the DB connection itself is opened read-only.
- **Deterministic calculators** (`app/calc/finance.py`) for multi-step metrics
  (churn, cohort retention, MRR growth) — the arithmetic is Python, not the model.
- **Show your work**: every answer returns the exact SQL, the bound parameters,
  the row count and the metric definition. Click any number, see how it was made.
- **Narration guardrail**: after the LLM explains an answer, every number in its
  text is checked against the engine's output; a stray number is rejected.
- **Golden regression suite** (`data/golden/questions.json`) with hand-verified
  answers over a tiny deterministic dataset — a true oracle, not a copy of the
  code. `POST /golden/run` and CI fail the build if any number changes.

## Architecture

```
Question (n8n webhook)
  -> FastAPI /ask
       - planner (LLM) : question -> {metric, params}   (refuse if none fits)
       - metric layer  : vetted definition -> SQL / calculator
       - SQL guard     : single read-only SELECT, allow-listed tables
       - read-only DB  : execute with bound params
       - narrate       : explain, guardrail blocks invented numbers
  -> n8n IF refused? -> refusal message | answer (value + SQL + audit id)
```

`/query` is the deterministic path (no LLM) — the same engine the golden set and
CI exercise. `/ask` adds the natural-language planning on top.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set SERVICE_API_KEY; GEMINI_API_KEY optional
python -m app.seed            # build the deterministic demo database
pytest                        # 25 tests incl. the golden gate and SQL guard
uvicorn app.main:app --reload
```

Expose to n8n Cloud with `ngrok http 8000`, import
`n8n/analytics.workflow.json`, set the tunnel URL and `SERVICE_API_KEY`.

The `/ask` endpoint needs Gemini: run once with `LLM_MODE=record` and a
`GEMINI_API_KEY` to capture responses into `data/cassettes/`, then commit them so
the demo stays deterministic. `/query` and the whole test suite need no key.

## Honest limits

- The dataset is deliberately tiny and synthetic so the golden answers are
  hand-verifiable. On a real warehouse the metric layer would point at real
  tables (or a dbt/Cube semantic layer) — the governance pattern is the same.
- The metric catalog here is a starting set; real deployments add metrics and
  their golden cases together.
- Text-to-SQL accuracy on open schemas is an active research area; this design
  sidesteps it by not letting the LLM author SQL at all.

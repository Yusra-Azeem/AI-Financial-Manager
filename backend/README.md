# Backend — Database, Services & Tool-Calling Bridge

This is the backend half of the AI Financial Relationship Manager. It owns the
database, business logic (EMI/budget/prediction/policy), the LLM wrapper, and
`agent/tools.py` — the bridge the LangGraph agent (`agent/graph.py`,
`nodes.py`, `router.py`, `prompts.py`) calls into.

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- For a real Supabase Postgres DB, paste the connection string from
  Supabase → Project Settings → Database → Connection String (URI).
- For fast local testing without waiting on Supabase setup, just use:
  `DATABASE_URL=sqlite:///./local_dev.db`
- Add your Gemini or OpenAI key and set `LLM_PROVIDER`.

## Run

```bash
python seed_data.py     # creates tables + one demo customer with realistic data
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger docs (great for
Yusra to test the API without needing the frontend running).

## What's here

| File | Purpose |
|---|---|
| `config.py` | Loads `.env` into a typed `settings` object |
| `database.py` | SQLAlchemy engine/session, `get_db()` dependency |
| `models.py` | ORM tables: Customer, Transaction, Loan, Goal, LifeEvent |
| `schemas.py` | Pydantic request/response shapes for the API |
| `routes.py` | REST endpoints (`/customer/{id}`, `/agent/state/{id}`, `/agent/loan-offer`, `/agent/negotiate`) |
| `main.py` | FastAPI app + CORS + startup table creation |
| `seed_data.py` | Demo data — a customer whose transactions trigger a business-loan life event |
| `services/finance.py` | EMI, budget, savings math |
| `services/prediction.py` | Spend forecasting, cashflow, goal completion |
| `services/policy.py` | Loan eligibility, interest rates, negotiation/counter-offer logic |
| `services/llm.py` | `ask_llm()` — swaps between Gemini/OpenAI via `.env` |
| `agent/tools.py` | **The bridge.** LangGraph nodes import functions from here only. |

## For Yusra (agent/frontend side)

Your `nodes.py` should do:

```python
from agent.tools import (
    load_customer_bundle, analyze_behavior, predict_spending,
    detect_life_event, detect_opportunity, check_policy,
    negotiate_counter_offer, ask_llm,
)
```

Every function takes/returns plain dicts — no ORM objects leak past
`agent/tools.py`, so your LangGraph `AgentState` can just store these dicts
directly. `load_customer_bundle(db, customer_id)` gives you everything to
seed the initial state in one call (matches the "Build LangGraph State" step
in the architecture diagram).

If you'd rather call the backend over HTTP instead of importing directly
(e.g. if the agent runs as a separate process), use:
- `GET /agent/state/{customer_id}` → initial state bundle
- `POST /agent/loan-offer` → first policy offer
- `POST /agent/negotiate` → counter-offer for negotiation rounds 2+

## Verified working

I ran the full pipeline locally against the seed data: behavior analysis →
spending prediction → life-event detection (correctly flagged a business
startup from the seeded transactions) → opportunity detection → loan policy
check → negotiation round. All endpoints respond correctly via `curl`/Swagger.

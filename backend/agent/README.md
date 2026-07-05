# agent/ — LangGraph pipeline (Yusra's part)

Files in this folder:

| File | Purpose |
|---|---|
| `state.py` | `AgentState` TypedDict — the shared, JSON-serializable state passed between every node. |
| `prompts.py` | All LLM prompt templates, kept separate from node logic so tone is easy to tune. |
| `nodes.py` | One function per graph node. Only imports from `agent.tools` + `database.SessionLocal` — never touches ORM models directly. |
| `router.py` | Conditional-edge functions: decide what happens next based on state. |
| `graph.py` | Wires nodes + routers into a compiled `StateGraph`, exposes `run_proactive_cycle()` and `send_customer_message()`. |

## Wiring into routes.py

```python
from agent.graph import run_proactive_cycle, send_customer_message

@app.get("/agent/state/{customer_id}")
def agent_state(customer_id: str):
    return run_proactive_cycle(customer_id)

@app.post("/agent/negotiate")
def negotiate(payload: NegotiatePayload):
    return send_customer_message(payload.customer_id, payload.message, payload.customer_id)
```

`run_proactive_cycle` returns the full `AgentState` dict — that's exactly
the JSON shape `frontend/src/api.js` -> `getAgentState()` expects
(`customer_bundle`, `behavior_analysis`, `spending_prediction`,
`life_event`, `opportunity`, `recommendation_card`, `notifications`,
`messages`, `negotiation_history`, `negotiation_status`).

## Assumed signatures on `agent/tools.py`

These match the README's public bridge functions. If Roshni's actual
signatures differ slightly, only `nodes.py` needs to change — `state.py`,
`router.py` and `graph.py` don't care about tool internals:

```python
load_customer_bundle(db, customer_id) -> dict
analyze_behavior(bundle: dict) -> dict
predict_spending(bundle: dict) -> dict
detect_life_event(bundle: dict) -> dict | None
detect_opportunity(bundle: dict) -> dict | None
check_policy(bundle: dict, opportunity: dict | None) -> dict           # loan offer
negotiate_counter_offer(customer_bundle, current_offer, customer_message, round_number) -> dict
    # -> {"accepted": bool, "counter_offer": dict, "final": bool}
ask_llm(prompt: str) -> str
```

## Install

Add to `requirements.txt`:

```
langgraph>=0.2.0
langgraph-checkpoint>=1.0.0
```

## Negotiation cap

`MAX_NEGOTIATION_ROUNDS` in `nodes.py` is set to 3 — change it there if
policy wants more/fewer rounds before `negotiation_limit_node` kicks in.

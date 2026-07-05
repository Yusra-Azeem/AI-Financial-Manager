"""
graph.py
--------
Builds and compiles the LangGraph state machine for the AI Financial
Relationship Manager agent.

Two entry paths, both sharing one checkpointed thread per customer session:

1. Proactive cycle (no customer message yet):
     load_state -> analyze_behavior -> predict_spending -> detect_life_event
     -> detect_opportunity -> [check_policy if loan_product] -> END

2. Reactive cycle (customer sent a message):
     classify_intent -> negotiate | policy_question | chat -> END

--- Checkpointer (production note) -----------------------------------------
MemorySaver is fine for a single dev process but loses all sessions on
restart and does not work once you run more than one uvicorn/gunicorn
worker (each worker gets its own memory). In any real deployment, back the
checkpointer with Postgres (same DB as everything else) or, at minimum,
SQLite on a shared volume:

    CHECKPOINT_BACKEND=postgres   -> uses DATABASE_URL via PostgresSaver
    CHECKPOINT_BACKEND=sqlite     -> uses CHECKPOINT_SQLITE_PATH via SqliteSaver
    CHECKPOINT_BACKEND=memory     -> MemorySaver (dev/testing only)

Falls back to memory with a loud warning if the requested backend's
dependency isn't installed, so local dev never hard-fails.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from agent.state import AgentState, initial_state
from agent import nodes
from agent import router
from config import settings

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # --- register nodes -----------------------------------------------------
    graph.add_node("load_state", nodes.load_state_node)
    graph.add_node("analyze_behavior", nodes.analyze_behavior_node)
    graph.add_node("predict_spending", nodes.predict_spending_node)
    graph.add_node("detect_life_event", nodes.detect_life_event_node)
    graph.add_node("detect_opportunity", nodes.detect_opportunity_node)
    graph.add_node("check_policy", nodes.check_policy_node)
    graph.add_node("classify_intent", nodes.classify_intent_node)
    graph.add_node("negotiate", nodes.negotiate_node)
    graph.add_node("policy_question", nodes.policy_question_node)
    graph.add_node("chat", nodes.chat_node)

    # --- entry point ---------------------------------------------------------
    graph.set_conditional_entry_point(
        router.route_entry,
        {"load_state": "load_state", "classify_intent": "classify_intent"},
    )

    # --- proactive pipeline ---------------------------------------------------
    graph.add_edge("load_state", "analyze_behavior")
    graph.add_edge("analyze_behavior", "predict_spending")
    graph.add_edge("predict_spending", "detect_life_event")

    graph.add_conditional_edges(
        "detect_life_event",
        router.route_after_life_event,
        {"detect_opportunity": "detect_opportunity"},
    )
    graph.add_conditional_edges(
        "detect_opportunity",
        router.route_after_opportunity,
        {"check_policy": "check_policy", "end": END},
    )
    graph.add_edge("check_policy", END)

    # --- reactive pipeline (single-turn: each customer message is its own
    # invoke(), with prior state restored from the checkpointer by thread_id) --
    graph.add_conditional_edges(
        "classify_intent",
        router.route_after_intent,
        {"negotiate": "negotiate", "policy_question": "policy_question", "chat": "chat"},
    )
    graph.add_edge("negotiate", END)
    graph.add_edge("policy_question", END)
    graph.add_edge("chat", END)

    return graph


def _build_checkpointer():
    backend = getattr(settings, "CHECKPOINT_BACKEND", "sqlite")

    if backend == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            conn_string = settings.DATABASE_URL
            saver_cm = PostgresSaver.from_conn_string(conn_string)
            saver = saver_cm.__enter__()  # kept open for app lifetime
            saver.setup()
            logger.info("LangGraph checkpointer: Postgres (%s)", _redact(conn_string))
            return saver
        except Exception:  # noqa: BLE001 - deliberate broad fallback for dev ergonomics
            logger.exception("Failed to initialize Postgres checkpointer, falling back to SQLite")
            backend = "sqlite"

    if backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            path = getattr(settings, "CHECKPOINT_SQLITE_PATH", "./agent_checkpoints.sqlite")
            saver_cm = SqliteSaver.from_conn_string(path)
            saver = saver_cm.__enter__()
            logger.info("LangGraph checkpointer: SQLite (%s)", path)
            return saver
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize SQLite checkpointer, falling back to in-memory")

    from langgraph.checkpoint.memory import MemorySaver

    logger.warning(
        "LangGraph checkpointer: in-memory only — sessions will NOT survive a "
        "restart and will NOT be shared across multiple workers. Do not use "
        "this in production."
    )
    return MemorySaver()


def _redact(conn_string: str) -> str:
    """Don't log DB credentials."""
    if "@" in conn_string:
        return conn_string.split("@", 1)[-1]
    return conn_string


_checkpointer = _build_checkpointer()
agent_graph = build_graph().compile(checkpointer=_checkpointer)


def run_proactive_cycle(customer_id: int, session_id: str | None = None) -> dict:
    """Kick off (or resume) the proactive analysis pipeline for a customer."""
    config = {"configurable": {"thread_id": str(session_id or customer_id)}}
    state = initial_state(customer_id, session_id)
    return agent_graph.invoke(state, config=config)


def send_customer_message(customer_id: int, message: str, session_id: str | None = None) -> dict:
    """Feed a customer's chat/negotiation/policy-question message back into
    their existing session (thread_id), so history and offer state carry over."""
    config = {"configurable": {"thread_id": str(session_id or customer_id)}}
    return agent_graph.invoke({"pending_user_message": message}, config=config)

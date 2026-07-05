"""
state.py
--------
Shared state passed between every LangGraph node. Field names deliberately
mirror the dict shapes returned by agent/tools.py exactly, so nodes.py can
pass state pieces straight into tool calls without any reshaping.

Reference shapes (from tools.py):
  load_customer_bundle()  -> {"customer": {...}, "transactions": [...],
                               "loans": [...], "goals": [...]}
  analyze_behavior()      -> {"budget": {...}, "savings": {...}}
  predict_spending()      -> {**spend_forecast, **cashflow}
  detect_life_event()     -> {"detected": bool, "event_type": str|None,
                               "confidence": float, "evidence": [...]}
  detect_opportunity()    -> {"has_opportunity": bool, "opportunity_type":
                               "loan_product"|"spending_warning"|None,
                               "loan_type": str|None, "reason": str}
  check_policy()           -> policy decision dict (see services/policy.py;
                               treated as opaque here, forwarded as-is)
  negotiate_counter_offer()-> counter-offer dict (same treatment)
  explain_policy()         -> {"answer": str, "sources": [...]}
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentState(TypedDict, total=False):
    # --- identity / session -------------------------------------------------
    customer_id: int
    session_id: Optional[str]

    # --- raw bundle from load_customer_bundle() -----------------------------
    customer: dict[str, Any]
    transactions: list[dict[str, Any]]
    loans: list[dict[str, Any]]
    goals: list[dict[str, Any]]

    # --- analysis pipeline outputs -------------------------------------------
    behavior: dict[str, Any]              # {"budget": {...}, "savings": {...}}
    spending_forecast: dict[str, Any]      # predict_spending() output
    life_event: dict[str, Any]             # detect_life_event() output
    opportunity: dict[str, Any]            # detect_opportunity() output

    # --- policy / negotiation ------------------------------------------------
    # requested_amount / requested_tenure_months are whatever we asked
    # check_policy for — kept in state so negotiate_counter_offer's later
    # rounds have the original loan_type/terms to compare against.
    loan_type: Optional[str]
    requested_amount: Optional[float]
    requested_tenure_months: Optional[int]
    policy_offer: Optional[dict[str, Any]]     # last check_policy()/negotiate_counter_offer() result

    negotiation_round: int
    negotiation_history: list[dict[str, Any]]
    negotiation_status: Literal[
        "not_started", "in_progress", "accepted", "rejected", "max_rounds_reached"
    ]

    # --- intent routing for incoming customer messages -----------------------
    user_intent: Optional[Literal["negotiate", "policy_question", "chat"]]
    policy_question: Optional[str]
    policy_answer: Optional[dict[str, Any]]     # explain_policy() output

    # --- conversation ---------------------------------------------------------
    messages: list[ChatMessage]
    pending_user_message: Optional[str]

    # --- control flow -----------------------------------------------------
    current_step: str
    error: Optional[str]

    # --- output surfaces for the frontend -------------------------------------
    recommendation_card: Optional[dict[str, Any]]
    notifications: list[dict[str, Any]]


def initial_state(customer_id: int, session_id: str | None = None) -> AgentState:
    return AgentState(
        customer_id=customer_id,
        session_id=session_id,
        customer={},
        transactions=[],
        loans=[],
        goals=[],
        behavior={},
        spending_forecast={},
        life_event={},
        opportunity={},
        loan_type=None,
        requested_amount=None,
        requested_tenure_months=None,
        policy_offer=None,
        negotiation_round=0,
        negotiation_history=[],
        negotiation_status="not_started",
        user_intent=None,
        policy_question=None,
        policy_answer=None,
        messages=[],
        pending_user_message=None,
        current_step="start",
        error=None,
        recommendation_card=None,
        notifications=[],
    )

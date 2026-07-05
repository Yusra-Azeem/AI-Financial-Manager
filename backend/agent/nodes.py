"""
nodes.py
--------
One function per LangGraph node. Every node calls into agent/tools.py only
— never touches models.py / ORM objects directly, and never opens a DB
session except where a tool explicitly requires one (load_customer_bundle,
explain_policy).

Matches the real tools.py signatures:
    load_customer_bundle(db, customer_id) -> {"customer","transactions","loans","goals"}
    analyze_behavior(customer, transactions) -> {"budget","savings"}
    predict_spending(customer, transactions) -> {**spend_forecast, **cashflow}
    detect_life_event(customer, transactions) -> {"detected","event_type","confidence","evidence"}
    detect_opportunity(customer, behavior, spending_forecast, life_event)
        -> {"has_opportunity","opportunity_type","loan_type","reason"}
    check_policy(loan_type, customer, requested_amount, requested_tenure_months) -> dict
    negotiate_counter_offer(loan_type, customer, proposed_principal, proposed_rate,
                             proposed_tenure, round_number) -> dict
    ask_llm(prompt, system="") -> str
    explain_policy(db, question) -> {"answer","sources"}
"""

from __future__ import annotations
import json
from typing import Any

from agent.state import AgentState
from agent import prompts
from agent.tools import (
    load_customer_bundle,
    analyze_behavior,
    predict_spending,
    detect_life_event,
    detect_opportunity,
    check_policy,
    negotiate_counter_offer,
    ask_llm,
    explain_policy,
)
from database import SessionLocal


MAX_NEGOTIATION_ROUNDS = 3

# ASSUMPTION: tools.check_policy() needs an explicit requested_amount /
# requested_tenure_months, but nothing upstream (detect_opportunity) produces
# those numbers. Until product gives us a real "how much do you want to
# borrow" input (e.g. a frontend field), we default to a conservative
# request derived from income so the pipeline can still produce a first
# offer automatically. Replace this the moment there's a real UI input.
DEFAULT_TENURE_MONTHS = 36


def _default_requested_amount(customer: dict[str, Any]) -> float:
    income = customer.get("monthly_income") or 0
    return round(income * 6, 2)


def _append_messages(state: AgentState, new_messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return list(state.get("messages", [])) + new_messages


def _append_notifications(state: AgentState, new_notifications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(state.get("notifications", [])) + new_notifications


def _append_history(state: AgentState, entry: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("negotiation_history", [])) + [entry]


# ---------------------------------------------------------------------------
# 1. Load / seed state
# ---------------------------------------------------------------------------
def load_state_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        bundle = load_customer_bundle(db, state["customer_id"])
    finally:
        db.close()

    if not bundle:
        return {"error": f"No customer found for id {state['customer_id']}", "current_step": "load_state"}

    return {
        "customer": bundle["customer"],
        "transactions": bundle["transactions"],
        "loans": bundle["loans"],
        "goals": bundle["goals"],
        "current_step": "load_state",
    }


# ---------------------------------------------------------------------------
# 2. Behavior analysis
# ---------------------------------------------------------------------------
def analyze_behavior_node(state: AgentState) -> dict:
    behavior = analyze_behavior(state["customer"], state["transactions"])
    return {"behavior": behavior, "current_step": "analyze_behavior"}


# ---------------------------------------------------------------------------
# 3. Spending prediction
# ---------------------------------------------------------------------------
def predict_spending_node(state: AgentState) -> dict:
    forecast = predict_spending(state["customer"], state["transactions"])
    return {"spending_forecast": forecast, "current_step": "predict_spending"}


# ---------------------------------------------------------------------------
# 4. Life-event detection
# ---------------------------------------------------------------------------
def detect_life_event_node(state: AgentState) -> dict:
    event = detect_life_event(state["customer"], state["transactions"])
    new_state: dict[str, Any] = {"life_event": event, "current_step": "detect_life_event"}

    if event.get("detected"):
        system, user = prompts.life_event_narration_prompt(state["customer"], event)
        narration = ask_llm(user, system)
        new_state["messages"] = _append_messages(state, [{"role": "assistant", "content": narration}])
        new_state["notifications"] = _append_notifications(
            state,
            [{"type": "life_event", "title": f"New life event: {event.get('event_type')}", "body": narration, "read": False}],
        )

    return new_state


# ---------------------------------------------------------------------------
# 5. Opportunity detection
# ---------------------------------------------------------------------------
def detect_opportunity_node(state: AgentState) -> dict:
    opportunity = detect_opportunity(
        state["customer"], state["behavior"], state["spending_forecast"], state["life_event"]
    )
    new_state: dict[str, Any] = {"opportunity": opportunity, "current_step": "detect_opportunity"}

    if not opportunity.get("has_opportunity"):
        return new_state

    if opportunity["opportunity_type"] == "loan_product":
        system, user = prompts.opportunity_pitch_prompt(state["customer"], state["life_event"], opportunity)
        pitch = ask_llm(user, system)
        new_state["messages"] = _append_messages(state, [{"role": "assistant", "content": pitch}])
        new_state["recommendation_card"] = {
            "type": "loan_product",
            "loan_type": opportunity.get("loan_type"),
            "pitch": pitch,
        }
        new_state["loan_type"] = opportunity.get("loan_type")

    elif opportunity["opportunity_type"] == "spending_warning":
        system, user = prompts.spending_warning_prompt(state["customer"], state["behavior"])
        warning = ask_llm(user, system)
        new_state["messages"] = _append_messages(state, [{"role": "assistant", "content": warning}])
        new_state["notifications"] = _append_notifications(
            state, [{"type": "spending_warning", "title": "Savings goal at risk", "body": warning, "read": False}]
        )

    return new_state


# ---------------------------------------------------------------------------
# 6. Policy check -> first loan offer
# ---------------------------------------------------------------------------
def check_policy_node(state: AgentState) -> dict:
    loan_type = state["opportunity"].get("loan_type")
    requested_amount = state.get("requested_amount") or _default_requested_amount(state["customer"])
    requested_tenure = state.get("requested_tenure_months") or DEFAULT_TENURE_MONTHS

    offer = check_policy(loan_type, state["customer"], requested_amount, requested_tenure)

    system, user = prompts.policy_offer_explanation_prompt(state["customer"], offer, loan_type)
    explanation = ask_llm(user, system)

    card = dict(state.get("recommendation_card") or {})
    card.update({"offer": offer, "explanation": explanation})

    return {
        "loan_type": loan_type,
        "requested_amount": requested_amount,
        "requested_tenure_months": requested_tenure,
        "policy_offer": offer,
        "recommendation_card": card,
        "negotiation_status": "not_started",
        "messages": _append_messages(state, [{"role": "assistant", "content": explanation}]),
        "current_step": "check_policy",
    }


# ---------------------------------------------------------------------------
# 7. Intent classification for an incoming customer message
# ---------------------------------------------------------------------------
def classify_intent_node(state: AgentState) -> dict:
    message = state.get("pending_user_message") or ""
    has_active_offer = bool(state.get("policy_offer")) and state.get("negotiation_status") != "accepted"

    system, user = prompts.classify_intent_prompt(message, has_active_offer)
    raw = ask_llm(user, system).strip().lower()

    intent = raw if raw in ("negotiate", "policy_question", "chat") else "chat"
    return {"user_intent": intent, "current_step": "classify_intent"}


# ---------------------------------------------------------------------------
# 8. Negotiation round
# ---------------------------------------------------------------------------
def negotiate_node(state: AgentState) -> dict:
    user_message = state.get("pending_user_message") or ""
    current_offer = state["policy_offer"]
    loan_type = state["loan_type"]
    round_number = state.get("negotiation_round", 0) + 1

    # Ask the LLM to extract structured terms from free text, since
    # negotiate_counter_offer() needs explicit numeric proposed_principal /
    # proposed_rate / proposed_tenure — never invented here, only parsed
    # from what the customer actually said (falling back to current terms).
    system, user = prompts.parse_negotiation_terms_prompt(user_message, current_offer)
    raw_terms = ask_llm(user, system)
    proposed = _safe_parse_terms(raw_terms, current_offer)

    counter = negotiate_counter_offer(
        loan_type=loan_type,
        customer=state["customer"],
        proposed_principal=proposed["principal"],
        proposed_rate=proposed["rate"],
        proposed_tenure=proposed["tenure_months"],
        round_number=round_number,
    )

    accepted = bool(counter.get("accepted"))
    is_final = round_number >= MAX_NEGOTIATION_ROUNDS and not accepted

    system, user = prompts.negotiation_response_prompt(
        state["customer"], current_offer, counter, user_message, accepted, is_final
    )
    reply = ask_llm(user, system)

    if accepted:
        status = "accepted"
    elif is_final:
        status = "max_rounds_reached"
    else:
        status = "in_progress"

    return {
        "policy_offer": counter,
        "negotiation_round": round_number,
        "negotiation_status": status,
        "negotiation_history": _append_history(
            state, {"round": round_number, "user_message": user_message, "offer": counter, "accepted": accepted}
        ),
        "messages": _append_messages(
            state, [{"role": "user", "content": user_message}, {"role": "assistant", "content": reply}]
        ),
        "pending_user_message": None,
        "current_step": "negotiate",
    }


def _safe_parse_terms(raw: str, current_offer: dict[str, Any]) -> dict[str, Any]:
    """Best-effort JSON parse of the LLM's extracted terms; falls back to
    the current offer's numbers if parsing fails or fields are missing."""
    fallback = {
        "principal": current_offer.get("principal") or current_offer.get("amount"),
        "rate": current_offer.get("interest_rate") or current_offer.get("rate"),
        "tenure_months": current_offer.get("tenure_months"),
    }
    cleaned = raw.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
        return {
            "principal": parsed.get("principal", fallback["principal"]),
            "rate": parsed.get("rate", fallback["rate"]),
            "tenure_months": parsed.get("tenure_months", fallback["tenure_months"]),
        }
    except (json.JSONDecodeError, AttributeError):
        return fallback


# ---------------------------------------------------------------------------
# 9. Policy Q&A (RAG)
# ---------------------------------------------------------------------------
def policy_question_node(state: AgentState) -> dict:
    question = state.get("pending_user_message") or ""
    db = SessionLocal()
    try:
        result = explain_policy(db, question)
    finally:
        db.close()

    return {
        "policy_question": question,
        "policy_answer": result,
        "messages": _append_messages(
            state, [{"role": "user", "content": question}, {"role": "assistant", "content": result["answer"]}]
        ),
        "pending_user_message": None,
        "current_step": "policy_question",
    }


# ---------------------------------------------------------------------------
# 10. Free-form chat (fallback)
# ---------------------------------------------------------------------------
def chat_node(state: AgentState) -> dict:
    user_message = state.get("pending_user_message") or ""
    context_summary = {
        "life_event": state.get("life_event"),
        "opportunity": state.get("opportunity"),
        "policy_offer": state.get("policy_offer"),
        "negotiation_status": state.get("negotiation_status"),
    }
    system, user = prompts.general_chat_prompt(state["customer"], context_summary, user_message)
    reply = ask_llm(user, system)

    return {
        "messages": _append_messages(
            state, [{"role": "user", "content": user_message}, {"role": "assistant", "content": reply}]
        ),
        "pending_user_message": None,
        "current_step": "chat",
    }

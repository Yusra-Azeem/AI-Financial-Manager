"""
router.py
---------
Conditional-edge functions for graph.py. Each returns the name of the next
node — a key that must exist in the `path_map` passed to
add_conditional_edges() in graph.py.
"""

from __future__ import annotations
from agent.state import AgentState


def route_entry(state: AgentState) -> str:
    """Top-level router: decides where an invocation joins the graph."""
    if not state.get("customer"):
        return "load_state"

    if state.get("pending_user_message"):
        return "classify_intent"

    return "load_state"


def route_after_life_event(state: AgentState) -> str:
    """Always continue to opportunity detection — it can surface
    opportunities independent of any detected life event."""
    return "detect_opportunity"


def route_after_opportunity(state: AgentState) -> str:
    """Only loan-product opportunities need a priced offer; spending
    warnings stop here since there's nothing to negotiate."""
    opportunity = state.get("opportunity") or {}
    if opportunity.get("has_opportunity") and opportunity.get("opportunity_type") == "loan_product":
        return "check_policy"
    return "end"


def route_after_intent(state: AgentState) -> str:
    """Send the incoming message to the right handler based on
    classify_intent_node's output."""
    intent = state.get("user_intent")
    has_active_offer = bool(state.get("policy_offer")) and state.get("negotiation_status") != "accepted"

    if intent == "negotiate" and has_active_offer:
        return "negotiate"
    if intent == "policy_question":
        return "policy_question"
    return "chat"

"""
prompts.py
----------
Prompt builders for every LLM call the agent makes. tools.ask_llm has the
signature `ask_llm(prompt: str, system: str = "")` — so every function here
returns a (system, user) tuple. Call sites do:

    system, user = prompts.something(...)
    reply = ask_llm(user, system)

Kept dependency-free (plain f-strings) and separate from node logic so tone
is easy to tune without touching graph wiring.
"""

from __future__ import annotations
from typing import Any

SYSTEM_PERSONA = (
    "You are Sahayak, an AI financial relationship manager for a retail bank. "
    "You speak directly to the customer in a warm, plain-spoken, trustworthy way — "
    "never salesy, never robotic. You explain money matters the way a good "
    "relationship manager would: in the customer's own terms, with concrete "
    "numbers, and always with their interests first. Keep responses concise "
    "(3-5 sentences unless asked for detail). Never invent numbers that were "
    "not given to you in the data below."
)


def life_event_narration_prompt(customer: dict[str, Any], life_event: dict[str, Any]) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    system = SYSTEM_PERSONA
    user = f"""Customer: {name}
Detected life event: {life_event.get("event_type", "unknown")}
Evidence: {life_event.get("evidence", [])}
Confidence: {life_event.get("confidence", "n/a")}

Write a short, warm message to {name} noticing this change in their life
(e.g. a new business, a move, a new dependent) based only on the evidence
above. Do not mention that this came from transaction analysis explicitly —
speak the way a relationship manager who "just noticed" would. End with one
open question inviting them to share more."""
    return system, user


def opportunity_pitch_prompt(
    customer: dict[str, Any],
    life_event: dict[str, Any],
    opportunity: dict[str, Any],
) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    event_line = (
        f"Related life event: {life_event.get('event_type')}"
        if life_event.get("detected")
        else "No specific life event tied to this."
    )
    system = SYSTEM_PERSONA
    user = f"""Customer: {name}
{event_line}
Opportunity type: {opportunity.get("opportunity_type")}
Suggested loan type: {opportunity.get("loan_type")}
Reason: {opportunity.get("reason")}

Pitch this opportunity to {name} in 3-4 sentences. Be specific about why it
fits their situation right now. Do not state numeric terms (rate, tenure,
EMI) here — those come in a separate offer card. Close by inviting them to
see the offer."""
    return system, user


def spending_warning_prompt(customer: dict[str, Any], behavior: dict[str, Any]) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    system = SYSTEM_PERSONA
    user = f"""Customer: {name}
Savings analysis: {behavior.get("savings")}

{name} is projected to fall short of their savings goal. Write a brief,
supportive (not alarming) message flagging this, using only the numbers
given above, and suggest they review their budget together with you.
2-3 sentences."""
    return system, user


def policy_offer_explanation_prompt(customer: dict[str, Any], offer: dict[str, Any], loan_type: str) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    system = SYSTEM_PERSONA
    user = f"""Customer: {name}
Loan type: {loan_type}
Offer details: {offer}

Explain this loan offer to {name} in plain language, using the exact
numbers/fields given above (whatever is present — amount, rate, EMI,
tenure, approval status). Keep it to 3-4 sentences. If the offer was not
approved, say so plainly and explain what's stated as the reason. End by
asking whether the terms work for them or if they'd like to negotiate."""
    return system, user


def classify_intent_prompt(user_message: str, has_active_offer: bool) -> tuple[str, str]:
    system = (
        "You are an intent classifier for a banking assistant. Reply with "
        "exactly one word, lowercase, no punctuation: negotiate, policy_question, "
        "or chat. Choose 'negotiate' only if there is an active loan offer AND "
        "the customer is proposing or reacting to specific terms (amount, rate, "
        "tenure, EMI). Choose 'policy_question' if they're asking why a decision "
        "was made or how policy works. Otherwise choose 'chat'."
    )
    context = "There IS an active loan offer on the table." if has_active_offer else "There is NO active loan offer."
    user = f'{context}\nCustomer message: "{user_message}"'
    return system, user


def parse_negotiation_terms_prompt(customer_message: str, current_offer: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You extract loan negotiation terms from a customer's message and "
        "reply with ONLY a JSON object, no prose, no markdown fences, in the "
        "exact shape: "
        '{"principal": <number>, "rate": <number>, "tenure_months": <integer>}. '
        "If the customer does not mention a term, reuse its value from the "
        "current offer given below. If the customer only wants a lower EMI "
        "without stating amount/rate/tenure, keep principal and rate the same "
        "and lengthen tenure_months as a reasonable guess."
    )
    user = f"""Current offer: {current_offer}
Customer message: "{customer_message}"

Return only the JSON object."""
    return system, user


def negotiation_response_prompt(
    customer: dict[str, Any],
    current_offer: dict[str, Any],
    counter_offer: dict[str, Any],
    customer_message: str,
    accepted: bool,
    is_final: bool,
) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    system = SYSTEM_PERSONA
    if accepted:
        user = f"""Customer: {name}
Customer said: "{customer_message}"
Final agreed offer: {counter_offer}

Confirm the final agreed terms warmly and clearly, using the exact numbers
in "Final agreed offer". Tell them the next step is e-signing the
agreement. Keep it to 2-3 sentences."""
        return system, user

    final_note = (
        "\n\nThis is the final round — let them know kindly that this is the "
        "best the bank can currently do, without sounding final in a cold way."
        if is_final
        else ""
    )
    user = f"""Customer: {name}
Customer said: "{customer_message}"
Previous offer: {current_offer}
New counter-offer: {counter_offer}

Respond to the customer's request. Explain, in plain language, what changed
between the previous offer and the new counter-offer (use the exact numbers
given) and why this is the best the bank can currently do right now.
Keep a collaborative, non-defensive tone. 3-4 sentences.{final_note}"""
    return system, user


def general_chat_prompt(customer: dict[str, Any], context_summary: dict[str, Any], user_message: str) -> tuple[str, str]:
    name = customer.get("name", "the customer")
    system = SYSTEM_PERSONA
    user = f"""Customer: {name}
Known context so far: {context_summary}
Customer's message: "{user_message}"

Reply to the customer directly, using the known context where relevant.
If the question is outside what the context supports, say so honestly
rather than guessing at numbers. If this sounds like a policy/"why" question
you can't answer from context alone, say you'll look into the specific
policy for them."""
    return system, user

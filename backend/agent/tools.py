"""
agent/tools.py
THE BRIDGE. Yusra's LangGraph nodes (nodes.py) import and call these functions
directly — they should never touch the DB or services/ folder themselves.
Each function here takes plain Python data in, returns plain dict/JSON-safe
data out, so it's trivial to drop into any LangGraph node's state update.

Functions expected by nodes.py, per the architecture doc:
    analyze_behavior()
    predict_spending()
    detect_life_event()
    detect_opportunity()
    check_policy()
    ask_llm()
"""
from sqlalchemy.orm import Session

from services import finance, prediction, policy, llm
from services.llm import ask_llm as _ask_llm  # re-exported below

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _customer_to_dict(customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "monthly_income": customer.monthly_income,
        "monthly_savings_goal": customer.monthly_savings_goal,
        "credit_score": customer.credit_score,
    }


def _transactions_to_dicts(transactions) -> list[dict]:
    return [
        {
            "id": t.id,
            "date": t.date,
            "category": t.category,
            "description": t.description,
            "amount": t.amount,
            "type": t.type,
        }
        for t in transactions
    ]


def load_customer_bundle(db: Session, customer_id: int) -> dict:
    """
    Fetches everything LangGraph's initial state needs in one call:
    customer profile + transactions + loans + goals.
    """
    import models

    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        return {}

    return {
        "customer": _customer_to_dict(customer),
        "transactions": _transactions_to_dicts(customer.transactions),
        "loans": [
            {
                "id": l.id, "loan_type": l.loan_type, "principal": l.principal,
                "interest_rate": l.interest_rate, "tenure_months": l.tenure_months,
                "status": l.status, "emi": l.emi,
            }
            for l in customer.loans
        ],
        "goals": [
            {
                "id": g.id, "goal_name": g.goal_name, "target_amount": g.target_amount,
                "current_amount": g.current_amount, "target_date": g.target_date,
            }
            for g in customer.goals
        ],
    }


# ---------------------------------------------------------------------------
# Tool functions called by LangGraph nodes
# ---------------------------------------------------------------------------

def analyze_behavior(customer: dict, transactions: list[dict]) -> dict:
    """Used by the Behavior Agent node."""
    budget = finance.calculate_budget(customer["monthly_income"], transactions)
    savings = finance.calculate_savings(
        customer["monthly_income"], budget["total_spend"], customer["monthly_savings_goal"]
    )
    return {"budget": budget, "savings": savings}


def predict_spending(customer: dict, transactions: list[dict]) -> dict:
    """Used by the Spending Analysis Agent node."""
    spend_forecast = prediction.predict_monthly_spending(transactions)
    cashflow = prediction.predict_cashflow(
        customer["monthly_income"], spend_forecast["predicted_next_month_spend"]
    )
    return {**spend_forecast, **cashflow}


def detect_life_event(customer: dict, transactions: list[dict]) -> dict:
    """
    Used by the Financial Life Event Agent node.
    Simple heuristic: look for keyword hits in recent transaction categories/descriptions.
    Swap this for an LLM call (ask_llm) if you want smarter detection with more time.
    """
    keyword_map = {
        "education": ["tuition", "university", "college", "course", "exam fee"],
        "business_startup": ["business registration", "vendor payment", "equipment purchase", "office rent"],
        "medical": ["hospital", "surgery", "medical", "clinic", "pharmacy"],
        "home_purchase": ["down payment", "property", "real estate", "home loan"],
        "vehicle_purchase": ["car dealership", "vehicle", "auto loan", "showroom"],
    }

    hits: dict[str, list[str]] = {}
    for t in transactions:
        text = f"{t.get('category','')} {t.get('description','')}".lower()
        for event, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text:
                    hits.setdefault(event, []).append(t.get("description") or t.get("category"))

    if not hits:
        return {"detected": False, "event_type": None, "confidence": 0.0, "evidence": []}

    # pick the event with the most matching transactions
    best_event = max(hits, key=lambda k: len(hits[k]))
    confidence = min(1.0, 0.3 + 0.2 * len(hits[best_event]))

    return {
        "detected": True,
        "event_type": best_event,
        "confidence": round(confidence, 2),
        "evidence": hits[best_event][:5],
    }


def detect_opportunity(customer: dict, behavior: dict, spending_forecast: dict, life_event: dict) -> dict:
    """
    Used by the Opportunity Detection Agent node. Combines the outputs of the
    previous three agents into a single recommendation decision.
    """
    # Life event -> suggest matching loan product
    event_to_loan = {
        "education": "education",
        "business_startup": "business",
        "medical": "medical",
        "home_purchase": "home",
        "vehicle_purchase": "vehicle",
    }

    if life_event.get("detected") and life_event["confidence"] >= 0.5:
        loan_type = event_to_loan.get(life_event["event_type"])
        return {
            "has_opportunity": True,
            "opportunity_type": "loan_product",
            "loan_type": loan_type,
            "reason": f"Detected a likely {life_event['event_type'].replace('_',' ')} event.",
        }

    # No life event, but savings are falling behind -> spending warning instead of a product
    if not behavior["savings"]["on_track"]:
        return {
            "has_opportunity": True,
            "opportunity_type": "spending_warning",
            "loan_type": None,
            "reason": f"Projected savings shortfall of {behavior['savings']['shortfall']}.",
        }

    return {"has_opportunity": False, "opportunity_type": None, "loan_type": None, "reason": "No action needed."}


def check_policy(loan_type: str, customer: dict, requested_amount: float, requested_tenure_months: int) -> dict:
    """Used by the Bank Policy Agent node during the negotiation loop."""
    return policy.check_policy(
        loan_type=loan_type,
        credit_score=customer["credit_score"],
        monthly_income=customer["monthly_income"],
        requested_amount=requested_amount,
        requested_tenure_months=requested_tenure_months,
    )


def negotiate_counter_offer(loan_type: str, customer: dict, proposed_principal: float,
                             proposed_rate: float, proposed_tenure: int, round_number: int) -> dict:
    """Used by the Bank Policy Agent node on rounds 2+ of negotiation."""
    return policy.counter_offer(
        loan_type=loan_type,
        credit_score=customer["credit_score"],
        monthly_income=customer["monthly_income"],
        customer_proposed_principal=proposed_principal,
        customer_proposed_rate=proposed_rate,
        customer_proposed_tenure=proposed_tenure,
        round_number=round_number,
    )


def ask_llm(prompt: str, system: str = "") -> str:
    """Re-exported so nodes.py only ever needs `from agent.tools import ask_llm, ...`"""
    return _ask_llm(prompt, system)


def explain_policy(db: Session, question: str) -> dict:
    """
    RAG entry point. Used when a customer asks "why" about a decision
    (e.g. "why is my loan capped?", "why this interest rate?"). Retrieves the
    most relevant chunks of the loan policy document and asks the LLM to
    answer using only that retrieved text, with citations back to the
    section(s) used — so the answer is grounded in real policy, not invented.
    """
    from services import rag

    chunks = rag.retrieve(db, question, top_k=3)

    if not chunks:
        return {
            "answer": "I don't have the policy document indexed yet, so I can't answer that with certainty. Please contact support.",
            "sources": [],
        }

    context = "\n\n".join(f"[{c['section']}]\n{c['content']}" for c in chunks)

    system_prompt = (
        "You are a bank assistant explaining lending policy to a customer. "
        "Answer ONLY using the policy excerpts provided below. If the excerpts "
        "don't fully answer the question, say what you can and note what's unclear. "
        "Keep the answer to 2-4 sentences, plain language, no jargon. "
        "Mention which policy section(s) you're drawing from.\n\n"
        f"POLICY EXCERPTS:\n{context}"
    )

    answer = _ask_llm(prompt=question, system=system_prompt)

    return {
        "answer": answer,
        "sources": [{"section": c["section"], "relevance": c["score"]} for c in chunks],
    }

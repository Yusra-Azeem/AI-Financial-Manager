"""
services/policy.py
Bank policy / eligibility rules engine. Deliberately simple, transparent rules
so results are explainable — a judge or teammate can read this and understand
exactly why an offer was made. Tune the numbers to fit your demo data.
"""
from services.finance import calculate_emi

# Base policy table per loan type: (min_credit_score, max_multiple_of_income, base_rate)
POLICY_TABLE = {
    "education": {"min_credit_score": 650, "max_amount_multiple": 3.0, "base_rate": 8.5, "max_tenure": 84},
    "business":  {"min_credit_score": 700, "max_amount_multiple": 4.0, "base_rate": 11.0, "max_tenure": 60},
    "home":      {"min_credit_score": 700, "max_amount_multiple": 6.0, "base_rate": 8.0, "max_tenure": 240},
    "vehicle":   {"min_credit_score": 650, "max_amount_multiple": 2.0, "base_rate": 9.5, "max_tenure": 84},
    "medical":   {"min_credit_score": 600, "max_amount_multiple": 1.5, "base_rate": 10.0, "max_tenure": 48},
}


def _annual_income(monthly_income: float) -> float:
    return monthly_income * 12


def check_eligibility(loan_type: str, credit_score: int, monthly_income: float, requested_amount: float) -> dict:
    policy = POLICY_TABLE.get(loan_type)
    if not policy:
        return {"eligible": False, "reason": f"Unknown loan type '{loan_type}'."}

    max_amount = _annual_income(monthly_income) * policy["max_amount_multiple"]

    if credit_score < policy["min_credit_score"]:
        return {
            "eligible": False,
            "reason": f"Credit score {credit_score} is below the minimum {policy['min_credit_score']} for {loan_type} loans.",
            "max_amount": round(max_amount, 2),
        }

    if requested_amount > max_amount:
        return {
            "eligible": True,
            "capped": True,
            "reason": f"Requested amount exceeds cap; offering max eligible amount instead.",
            "max_amount": round(max_amount, 2),
        }

    return {"eligible": True, "capped": False, "max_amount": round(max_amount, 2)}


def calculate_interest_rate(loan_type: str, credit_score: int) -> float:
    """Better credit score => small discount off the base rate."""
    policy = POLICY_TABLE.get(loan_type)
    if not policy:
        return 12.0
    base = policy["base_rate"]
    if credit_score >= 800:
        return round(base - 1.0, 2)
    if credit_score >= 750:
        return round(base - 0.5, 2)
    if credit_score >= 700:
        return base
    return round(base + 1.0, 2)


def check_policy(loan_type: str, credit_score: int, monthly_income: float,
                  requested_amount: float, requested_tenure_months: int) -> dict:
    """
    Main entry point used by tools.py. Returns a full offer decision.
    """
    policy = POLICY_TABLE.get(loan_type)
    if not policy:
        return {"approved": False, "reasoning": f"Loan type '{loan_type}' is not offered."}

    elig = check_eligibility(loan_type, credit_score, monthly_income, requested_amount)
    if not elig.get("eligible"):
        return {"approved": False, "reasoning": elig.get("reason", "Not eligible.")}

    principal = min(requested_amount, elig["max_amount"])
    tenure = min(requested_tenure_months, policy["max_tenure"])
    rate = calculate_interest_rate(loan_type, credit_score)
    emi = calculate_emi(principal, rate, tenure)

    reasoning_parts = [f"Approved based on credit score {credit_score} and policy for {loan_type} loans."]
    if elig.get("capped"):
        reasoning_parts.append(f"Amount capped to {round(elig['max_amount'],2)} based on income.")
    if tenure != requested_tenure_months:
        reasoning_parts.append(f"Tenure capped to {policy['max_tenure']} months per policy.")

    return {
        "approved": True,
        "loan_type": loan_type,
        "principal": round(principal, 2),
        "interest_rate": rate,
        "tenure_months": tenure,
        "emi": emi,
        "reasoning": " ".join(reasoning_parts),
    }


def counter_offer(loan_type: str, credit_score: int, monthly_income: float,
                   customer_proposed_principal: float, customer_proposed_rate: float,
                   customer_proposed_tenure: int, round_number: int = 1) -> dict:
    """
    Called during negotiation when the customer agent proposes terms that don't
    match the bank's default policy offer. The bank agent nudges terms toward
    policy limits rather than flat-out rejecting, up to 3 rounds.
    """
    base_offer = check_policy(loan_type, credit_score, monthly_income,
                               customer_proposed_principal, customer_proposed_tenure)
    if not base_offer.get("approved"):
        return base_offer

    policy_rate = base_offer["interest_rate"]

    # Bank concedes a small amount each round if the customer's ask is close to policy rate
    rate_gap = customer_proposed_rate - policy_rate
    if abs(rate_gap) <= 0.25:
        final_rate = customer_proposed_rate
        agreement = True
    elif round_number >= 3:
        final_rate = policy_rate  # bank holds firm after 3 rounds
        agreement = False
    else:
        # meet in the middle, biased toward policy rate
        concession = rate_gap * 0.3
        final_rate = round(policy_rate + concession, 2)
        agreement = False

    emi = calculate_emi(base_offer["principal"], final_rate, base_offer["tenure_months"])

    return {
        "approved": True,
        "agreement": agreement,
        "loan_type": loan_type,
        "principal": base_offer["principal"],
        "interest_rate": final_rate,
        "tenure_months": base_offer["tenure_months"],
        "emi": emi,
        "round_number": round_number,
        "reasoning": (
            f"Round {round_number}: bank {'accepted' if agreement else 'countered'} at {final_rate}% "
            f"(policy baseline was {policy_rate}%)."
        ),
    }

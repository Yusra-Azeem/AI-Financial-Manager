"""
services/finance.py
Pure-math helper functions. No DB access here — just calculations so they're
easy to unit test and reuse from policy.py / tools.py.
"""


def calculate_emi(principal: float, annual_interest_rate: float, tenure_months: int) -> float:
    """
    Standard reducing-balance EMI formula.
    annual_interest_rate is a percentage, e.g. 9.5 for 9.5%.
    """
    if tenure_months <= 0:
        return 0.0
    monthly_rate = (annual_interest_rate / 100) / 12
    if monthly_rate == 0:
        return round(principal / tenure_months, 2)
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months
    emi /= (1 + monthly_rate) ** tenure_months - 1
    return round(emi, 2)


def calculate_budget(monthly_income: float, transactions: list[dict]) -> dict:
    """
    transactions: list of dicts with at least {"amount": float, "category": str}
    Negative amount = spend, positive = income/credit.
    Returns a category-wise spend breakdown plus totals.
    """
    spend_by_category: dict[str, float] = {}
    total_spend = 0.0

    for t in transactions:
        amt = t.get("amount", 0.0)
        if amt < 0:
            cat = t.get("category", "other")
            spend_by_category[cat] = spend_by_category.get(cat, 0.0) + abs(amt)
            total_spend += abs(amt)

    return {
        "monthly_income": monthly_income,
        "total_spend": round(total_spend, 2),
        "spend_by_category": {k: round(v, 2) for k, v in spend_by_category.items()},
        "remaining": round(monthly_income - total_spend, 2),
    }


def calculate_savings(monthly_income: float, total_spend: float, savings_goal: float) -> dict:
    actual_savings = monthly_income - total_spend
    shortfall = max(0.0, savings_goal - actual_savings)
    return {
        "actual_savings": round(actual_savings, 2),
        "savings_goal": savings_goal,
        "on_track": actual_savings >= savings_goal,
        "shortfall": round(shortfall, 2),
    }

"""
services/prediction.py
Lightweight statistical predictions — no ML training needed for a 2-day hackathon.
Uses simple trend/average calculations over transaction history via pandas.
"""
from datetime import date
import pandas as pd


def predict_monthly_spending(transactions: list[dict]) -> dict:
    """
    Groups spend transactions by month and extrapolates next month's spend
    using a simple linear trend (or the average if there isn't enough history).
    """
    spends = [t for t in transactions if t.get("amount", 0) < 0]
    if not spends:
        return {"predicted_next_month_spend": 0.0, "trend": "flat", "confidence": "low"}

    df = pd.DataFrame(spends)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].abs()
    monthly = df.groupby(df["date"].dt.to_period("M"))["amount"].sum().sort_index()

    if len(monthly) < 2:
        predicted = float(monthly.iloc[-1])
        trend = "flat"
        confidence = "low"
    else:
        # simple trend: average month-over-month change
        diffs = monthly.diff().dropna()
        avg_change = diffs.mean()
        predicted = float(monthly.iloc[-1] + avg_change)
        trend = "increasing" if avg_change > 0 else "decreasing" if avg_change < 0 else "flat"
        confidence = "medium" if len(monthly) < 4 else "high"

    return {
        "predicted_next_month_spend": round(max(0.0, predicted), 2),
        "trend": trend,
        "confidence": confidence,
        "monthly_history": {str(k): round(v, 2) for k, v in monthly.items()},
    }


def predict_cashflow(monthly_income: float, predicted_spend: float) -> dict:
    predicted_net = monthly_income - predicted_spend
    return {
        "predicted_net_cashflow": round(predicted_net, 2),
        "status": "healthy" if predicted_net > 0 else "at_risk",
    }


def predict_goal_completion(goal: dict, monthly_contribution: float) -> dict:
    """
    goal: {"target_amount": float, "current_amount": float, "target_date": "YYYY-MM-DD" or None}
    """
    remaining = max(0.0, goal["target_amount"] - goal["current_amount"])
    if monthly_contribution <= 0:
        return {"months_to_complete": None, "on_track": False, "remaining": round(remaining, 2)}

    months_needed = remaining / monthly_contribution
    on_track = True

    if goal.get("target_date"):
        target = goal["target_date"]
        if isinstance(target, str):
            target = date.fromisoformat(target)
        months_available = (target.year - date.today().year) * 12 + (target.month - date.today().month)
        on_track = months_needed <= max(months_available, 0)

    return {
        "months_to_complete": round(months_needed, 1),
        "on_track": on_track,
        "remaining": round(remaining, 2),
    }

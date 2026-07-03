"""
schemas.py
Pydantic models for API request/response bodies. Keeps ORM objects from leaking
directly into JSON responses.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    category: str
    description: str
    amount: float
    type: str


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    loan_type: str
    principal: float
    interest_rate: float
    tenure_months: int
    status: str
    emi: float


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_name: str
    target_amount: float
    current_amount: float
    target_date: Optional[date] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    monthly_income: float
    monthly_savings_goal: float
    credit_score: int
    transactions: list[TransactionOut] = []
    loans: list[LoanOut] = []
    goals: list[GoalOut] = []


# ---- Agent / negotiation payloads ----

class LoanOfferRequest(BaseModel):
    customer_id: int
    loan_type: str
    requested_amount: float
    requested_tenure_months: int


class LoanOfferResponse(BaseModel):
    approved: bool
    loan_type: str
    principal: float
    interest_rate: float
    tenure_months: int
    emi: float
    reasoning: str


class NegotiationRound(BaseModel):
    customer_id: int
    loan_type: str
    proposed_principal: float
    proposed_interest_rate: float
    proposed_tenure_months: int
    round_number: int = 1

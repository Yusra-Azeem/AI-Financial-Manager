"""
routes.py
HTTP endpoints. Two groups:
  1. Plain CRUD-ish reads for the React dashboard (customer/transactions/loans).
  2. Agent-facing endpoints Yusra's LangGraph graph.py can call over HTTP
     if she runs the agent from the frontend/a separate process — OR, if the
     agent runs inside this same FastAPI app, graph.py can just import
     agent.tools directly instead of hitting these routes.
"""
from fastapi import APIRouter, Depends, HTTPException  # type: ignore[import]
from sqlalchemy.orm import Session  # type: ignore[import]

import models
import schemas
from database import get_db
from agent import tools as agent_tools

router = APIRouter()


# ---- Dashboard data ----

@router.get("/customer/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/customer/{customer_id}/transactions", response_model=list[schemas.TransactionOut])
def get_transactions(customer_id: int, db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(models.Transaction.customer_id == customer_id).all()


@router.get("/customer/{customer_id}/loans", response_model=list[schemas.LoanOut])
def get_loans(customer_id: int, db: Session = Depends(get_db)):
    return db.query(models.Loan).filter(models.Loan.customer_id == customer_id).all()


# ---- Agent-facing endpoints ----

@router.get("/agent/state/{customer_id}")
def get_agent_initial_state(customer_id: int, db: Session = Depends(get_db)):
    """Everything LangGraph needs to build its initial AgentState in one call."""
    bundle = agent_tools.load_customer_bundle(db, customer_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Customer not found")
    return bundle


@router.post("/agent/loan-offer", response_model=schemas.LoanOfferResponse)
def get_loan_offer(payload: schemas.LoanOfferRequest, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = agent_tools.check_policy(
        loan_type=payload.loan_type,
        customer=agent_tools._customer_to_dict(customer),
        requested_amount=payload.requested_amount,
        requested_tenure_months=payload.requested_tenure_months,
    )
    if not result.get("approved"):
        raise HTTPException(status_code=400, detail=result.get("reasoning", "Not approved"))
    return result


@router.post("/agent/negotiate")
def negotiate(payload: schemas.NegotiationRound, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return agent_tools.negotiate_counter_offer(
        loan_type=payload.loan_type,
        customer=agent_tools._customer_to_dict(customer),
        proposed_principal=payload.proposed_principal,
        proposed_rate=payload.proposed_interest_rate,
        proposed_tenure=payload.proposed_tenure_months,
        round_number=payload.round_number,
    )

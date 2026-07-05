"""
models.py
SQLAlchemy ORM models mirroring the Supabase tables:
customers, transactions, loans, goals, life_events
"""
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship

from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    monthly_income = Column(Float, default=0.0)
    monthly_savings_goal = Column(Float, default=0.0)
    credit_score = Column(Integer, default=700)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="customer", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="customer", cascade="all, delete-orphan")
    life_events = relationship("LifeEvent", back_populates="customer", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    date = Column(Date, default=date.today)
    category = Column(String, nullable=False)   # e.g. "groceries", "rent", "entertainment"
    description = Column(String, default="")
    amount = Column(Float, nullable=False)       # negative = spend, positive = income/credit
    type = Column(String, default="debit")        # "debit" or "credit"

    customer = relationship("Customer", back_populates="transactions")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    loan_type = Column(String, nullable=False)   # "education", "business", "home", "vehicle", "medical"
    principal = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    status = Column(String, default="active")     # "active", "closed", "proposed"
    emi = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="loans")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    goal_name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(Date, nullable=True)

    customer = relationship("Customer", back_populates="goals")


class LifeEvent(Base):
    """Optional table if you want to persist detected life events instead of
    only inferring them on the fly from transactions."""
    __tablename__ = "life_events"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    event_type = Column(String, nullable=False)   # "education", "business_startup", "home_purchase", etc.
    confidence = Column(Float, default=0.0)
    detected_at = Column(DateTime, default=datetime.utcnow)
    evidence = Column(Text, default="")            # short text explaining why it was detected

    customer = relationship("Customer", back_populates="life_events")


class PolicyChunk(Base):
    """
    RAG storage for the loan policy document. Each row is one chunk of
    policy text plus its embedding vector, stored as a JSON string so this
    works on both sqlite (local dev) and Postgres/Supabase without requiring
    the pgvector extension. Similarity search happens in Python
    (services/rag.py) via cosine similarity.

    To upgrade to native pgvector on Supabase for larger-scale search, swap
    `embedding` for a `sqlalchemy.dialects.postgresql.ARRAY(Float)` or the
    `pgvector.sqlalchemy.Vector` column type, enable the pgvector extension
    (`create extension vector;`), and do the similarity search in SQL instead.
    """
    __tablename__ = "policy_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, default="loan_policy.md")
    section = Column(String, default="")     # e.g. "Education Loans" - helps citations
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON-encoded list[float]

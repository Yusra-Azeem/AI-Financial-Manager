"""
seed_data.py
Populates the DB with one demo customer whose transaction history is designed
to trigger a "business_startup" life-event detection and a savings shortfall —
so the full agent pipeline has something interesting to react to during the demo.

Run with:  python seed_data.py
"""
from datetime import date, timedelta

from database import SessionLocal, init_db
import models


def run():
    init_db()
    db = SessionLocal()

    # wipe existing demo data (fine for a hackathon)
    db.query(models.Transaction).delete()
    db.query(models.Loan).delete()
    db.query(models.Goal).delete()
    db.query(models.Customer).delete()
    db.commit()

    customer = models.Customer(
        name="Aditi Sharma",
        email="aditi.sharma@example.com",
        monthly_income=90000,
        monthly_savings_goal=15000,
        credit_score=735,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    today = date.today()

    transactions = [
        # regular monthly spend, last 3 months
        {"days_ago": 85, "category": "rent", "description": "Monthly rent", "amount": -25000, "type": "debit"},
        {"days_ago": 84, "category": "groceries", "description": "Grocery run", "amount": -6000, "type": "debit"},
        {"days_ago": 55, "category": "rent", "description": "Monthly rent", "amount": -25000, "type": "debit"},
        {"days_ago": 54, "category": "groceries", "description": "Grocery run", "amount": -6500, "type": "debit"},
        {"days_ago": 40, "category": "entertainment", "description": "Movies & dining", "amount": -3000, "type": "debit"},
        # business-startup signal in the last month
        {"days_ago": 20, "category": "business", "description": "Business registration fee", "amount": -8000, "type": "debit"},
        {"days_ago": 15, "category": "business", "description": "Equipment purchase for new shop", "amount": -45000, "type": "debit"},
        {"days_ago": 10, "category": "business", "description": "Vendor payment - initial inventory", "amount": -20000, "type": "debit"},
        {"days_ago": 5, "category": "rent", "description": "Office rent - new business", "amount": -12000, "type": "debit"},
        {"days_ago": 1, "category": "salary", "description": "Monthly salary credit", "amount": 90000, "type": "credit"},
    ]

    for t in transactions:
        db.add(models.Transaction(
            customer_id=customer.id,
            date=today - timedelta(days=t["days_ago"]),
            category=t["category"],
            description=t["description"],
            amount=t["amount"],
            type=t["type"],
        ))

    db.add(models.Goal(
        customer_id=customer.id,
        goal_name="Emergency Fund",
        target_amount=300000,
        current_amount=90000,
        target_date=today + timedelta(days=365),
    ))

    db.add(models.Loan(
        customer_id=customer.id,
        loan_type="vehicle",
        principal=400000,
        interest_rate=9.5,
        tenure_months=48,
        status="active",
        emi=10014.23,
    ))

    db.commit()
    print(f"Seeded customer id={customer.id} ({customer.name}) with transactions, a goal, and a loan.")
    db.close()


if __name__ == "__main__":
    run()

"""Generate ~2 years of synthetic transactions for demo users (Postgres/MySQL/SQLite)."""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app import create_app, db  # noqa: E402
from app.models import Category, Transaction, User  # noqa: E402


def generate_for_user(user_id: int, days: int = 730, seed: int = 42) -> None:
    rng = random.Random(seed)
    cats = {c.name: c for c in Category.query.filter_by(user_id=user_id).all()}
    if not cats:
        raise RuntimeError("Run seed_sample.py first to create categories")

    end = date.today()
    start = end - timedelta(days=days)

    # Clear existing txs for idempotent re-run on same range (optional)
    Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start,
    ).delete()
    db.session.commit()

    d = start
    while d <= end:
        # Weekly income (sales)
        if d.weekday() < 5 and rng.random() < 0.45:
            amt = rng.uniform(2500, 9000)
            c = cats.get("Sales")
            db.session.add(
                Transaction(
                    user_id=user_id,
                    date=d,
                    amount=round(amt, 2),
                    type="income",
                    category_id=c.id if c else None,
                    merchant=rng.choice(["Acme", "Beta LLC", "Gamma Inc", ""]),
                )
            )
        # Rent monthly
        if d.day == 1:
            c = cats.get("Rent")
            db.session.add(
                Transaction(
                    user_id=user_id,
                    date=d,
                    amount=12000,
                    type="expense",
                    category_id=c.id if c else None,
                    merchant="Landlord",
                )
            )
        # Payroll biweekly
        if d.day in (5, 20):
            c = cats.get("Payroll")
            db.session.add(
                Transaction(
                    user_id=user_id,
                    date=d,
                    amount=rng.uniform(18000, 24000),
                    type="expense",
                    category_id=c.id if c else None,
                    merchant="Payroll",
                )
            )
        # Random expenses
        if rng.random() < 0.35:
            cname = rng.choice(["Utilities", "Supplies", "Marketing"])
            c = cats.get(cname)
            db.session.add(
                Transaction(
                    user_id=user_id,
                    date=d,
                    amount=rng.uniform(150, 2500),
                    type="expense",
                    category_id=c.id if c else None,
                    merchant="Vendor",
                )
            )
        # Noise / outliers
        if rng.random() < 0.02:
            db.session.add(
                Transaction(
                    user_id=user_id,
                    date=d,
                    amount=rng.uniform(5000, 15000),
                    type="expense",
                    category_id=cats.get("Supplies").id if cats.get("Supplies") else None,
                    merchant="One-off",
                )
            )
        d += timedelta(days=1)

    db.session.commit()
    print(f"Inserted synthetic transactions from {start} to {end} for user_id={user_id}")


def main() -> None:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email="demo@example.com").first()
        if not user:
            print("Create demo user first: python scripts/seed_sample.py")
            sys.exit(1)
        generate_for_user(user.id, days=730, seed=42)


if __name__ == "__main__":
    main()

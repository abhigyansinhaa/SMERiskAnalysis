"""Seed sample data for demo. Run after init_db.sql and with app context."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from app import create_app, db
from app.models import User, Category, Transaction, Alert


def seed():
    app = create_app()
    with app.app_context():
        # Create demo user
        user = User.query.filter_by(email="demo@example.com").first()
        if not user:
            user = User(email="demo@example.com")
            user.set_password("demo123")
            db.session.add(user)
            db.session.commit()
            print("Created demo user: demo@example.com / demo123")

        # Default categories
        cats = Category.query.filter_by(user_id=user.id).all()
        if not cats:
            for name, t in [
                ("Sales", "income"),
                ("Other Income", "income"),
                ("Rent", "expense"),
                ("Utilities", "expense"),
                ("Supplies", "expense"),
                ("Payroll", "expense"),
                ("Marketing", "expense"),
            ]:
                c = Category(user_id=user.id, name=name, type=t)
                db.session.add(c)
            db.session.commit()
            print("Created default categories")

        # Sample transactions (last 60 days)
        tx_count = Transaction.query.filter_by(user_id=user.id).count()
        if tx_count < 10:
            cats = {c.name: c for c in Category.query.filter_by(user_id=user.id).all()}
            today = date.today()
            samples = [
                (today - timedelta(days=5), 5000, "income", "Sales", "Acme Corp"),
                (today - timedelta(days=8), 1200, "expense", "Rent", "Landlord"),
                (today - timedelta(days=10), 3500, "income", "Sales", "Beta Inc"),
                (today - timedelta(days=12), 200, "expense", "Utilities", "Electric Co"),
                (today - timedelta(days=15), 800, "expense", "Supplies", "Office Depot"),
                (today - timedelta(days=18), 4200, "income", "Sales", "Gamma LLC"),
                (today - timedelta(days=22), 1200, "expense", "Rent", "Landlord"),
                (today - timedelta(days=25), 150, "expense", "Utilities", "Water"),
                (today - timedelta(days=30), 2800, "income", "Sales", "Delta Co"),
                (today - timedelta(days=35), 2500, "expense", "Payroll", "Staff"),
            ]
            for d, amt, typ, cat_name, merchant in samples:
                cat = cats.get(cat_name)
                t = Transaction(
                    user_id=user.id,
                    date=d,
                    amount=amt,
                    type=typ,
                    category_id=cat.id if cat else None,
                    merchant=merchant,
                )
                db.session.add(t)
            db.session.commit()
            print(f"Created {len(samples)} sample transactions")

        # Sample alert
        if Alert.query.filter_by(user_id=user.id).count() == 0:
            a = Alert(
                user_id=user.id,
                kind="runway",
                severity="info",
                message="Run forecast to see runway estimate.",
            )
            db.session.add(a)
            db.session.commit()
            print("Created sample alert")

        print("Seed complete.")


if __name__ == "__main__":
    seed()

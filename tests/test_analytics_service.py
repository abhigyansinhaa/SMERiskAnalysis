"""Analytics service unit tests (SQLite)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from app import db
from app.models import Category, Transaction, User
from app.services.analytics import (
    compute_runway,
    get_burn_rate,
    get_current_balance,
    get_dashboard_month,
    get_monthly_totals,
)


@pytest.fixture
def user_id(app):
    with app.app_context():
        u = User.query.filter_by(email="test@example.com").first()
        assert u is not None
        for name, t in [("Sales", "income"), ("Rent", "expense")]:
            db.session.add(Category(user_id=u.id, name=name, type=t))
        db.session.commit()
        return u.id


def test_get_monthly_totals_empty(app, user_id):
    with app.app_context():
        y, m, _ = get_dashboard_month(user_id)
        t = get_monthly_totals(user_id, y, m)
        assert t["income"] == 0.0
        assert t["expense"] == 0.0


def test_balance_and_burn(app, user_id):
    with app.app_context():
        cats = {c.name: c for c in Category.query.filter_by(user_id=user_id).all()}
        today = date.today()
        db.session.add(
            Transaction(
                user_id=user_id,
                date=today,
                amount=5000,
                type="income",
                category_id=cats["Sales"].id,
            )
        )
        db.session.add(
            Transaction(
                user_id=user_id,
                date=today - timedelta(days=1),
                amount=1000,
                type="expense",
                category_id=cats["Rent"].id,
            )
        )
        db.session.commit()
        bal = get_current_balance(user_id)
        assert bal == 4000.0
        burn = get_burn_rate(user_id, 30)
        assert burn > 0
        rw = compute_runway(user_id, bal, burn)
        assert rw is not None and rw > 0

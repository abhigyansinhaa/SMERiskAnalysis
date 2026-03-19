"""Analytics service: aggregates, risk metrics, alerts."""
from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import func
from app import db
from app.models import Transaction, Alert, Category


def get_monthly_totals(user_id: int, year: int, month: int) -> dict:
    """Income, expense, net for a given month."""
    start = date(year, month, 1)
    _, last = __import__("calendar").monthrange(year, month)
    end = date(year, month, last)

    income = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "income",
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .scalar()
        or 0
    )
    expense = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .scalar()
        or 0
    )
    return {"income": float(income), "expense": float(expense), "net": float(income - expense)}


def get_category_breakdown(user_id: int, year: int, month: int) -> list[dict]:
    """Category-wise totals for the month."""
    start = date(year, month, 1)
    _, last = __import__("calendar").monthrange(year, month)
    end = date(year, month, last)

    rows = (
        db.session.query(Category.name, Transaction.type, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(Category.name, Transaction.type)
        .all()
    )
    by_cat = defaultdict(lambda: {"income": 0, "expense": 0})
    for name, typ, total in rows:
        by_cat[name][typ] = float(total)
    return [{"name": k, **v} for k, v in sorted(by_cat.items())]


def get_top_vendors(user_id: int, year: int, month: int, limit: int = 10) -> list[dict]:
    """Top merchants by expense amount."""
    start = date(year, month, 1)
    _, last = __import__("calendar").monthrange(year, month)
    end = date(year, month, last)

    rows = (
        db.session.query(Transaction.merchant, func.sum(Transaction.amount).label("total"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.merchant.isnot(None),
            Transaction.merchant != "",
        )
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )
    return [{"merchant": m or "Unknown", "total": float(t)} for m, t in rows]


def get_burn_rate(user_id: int, days: int = 30) -> float:
    """Average daily expense over last N days."""
    end = date.today()
    start = end - timedelta(days=days)
    total = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .scalar()
        or 0
    )
    return float(total) / days if days > 0 else 0


def get_current_balance(user_id: int) -> float:
    """Net sum of all transactions (simplified balance)."""
    income = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.type == "income")
        .scalar()
        or 0
    )
    expense = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.user_id == user_id, Transaction.type == "expense")
        .scalar()
        or 0
    )
    return float(income - expense)


def compute_runway(user_id: int, balance: float | None = None, burn_rate: float | None = None) -> float | None:
    """Days until balance < 0. Returns None if burn_rate <= 0 or balance >= 0 with no burn."""
    if balance is None:
        balance = get_current_balance(user_id)
    if burn_rate is None:
        burn_rate = get_burn_rate(user_id, 30)
    if balance <= 0:
        return 0
    if burn_rate <= 0:
        return None  # infinite
    return balance / burn_rate


def check_and_create_alerts(user_id: int) -> None:
    """Evaluate risk metrics and create/update alerts."""
    balance = get_current_balance(user_id)
    burn = get_burn_rate(user_id, 30)
    runway = compute_runway(user_id, balance, burn)

    # Runway alert
    if runway is not None and runway < 30:
        severity = "critical" if runway < 7 else "warning"
        Alert.query.filter_by(user_id=user_id, kind="runway").delete()
        db.session.add(
            Alert(
                user_id=user_id,
                kind="runway",
                severity=severity,
                message=f"Runway: {runway:.0f} days until cash runs out at current burn rate.",
            )
        )
    elif runway is not None and runway >= 30:
        Alert.query.filter_by(user_id=user_id, kind="runway").delete()
        db.session.add(
            Alert(
                user_id=user_id,
                kind="runway",
                severity="info",
                message=f"Runway: ~{runway:.0f} days at current burn rate.",
            )
        )

    db.session.commit()


def get_alerts(user_id: int, unread_only: bool = False) -> list:
    """Fetch user alerts."""
    q = Alert.query.filter_by(user_id=user_id).order_by(Alert.created_at.desc())
    if unread_only:
        q = q.filter_by(is_read=False)
    return q.limit(20).all()

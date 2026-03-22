"""Analytics service: aggregates, risk metrics, alerts."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func

from app import db
from app.models import Alert, Category, Transaction


def get_dashboard_month(user_id: int) -> tuple[int, int, str]:
    """
    Calendar month for dashboard KPIs.

    Uses *today's* month if it has any income or expense; otherwise uses the
    month of the latest transaction (so imported historical CSVs still show
    meaningful monthly numbers when your PC date is past that data).
    """
    today = date.today()
    cur = get_monthly_totals(user_id, today.year, today.month)
    if cur["income"] > 0 or cur["expense"] > 0:
        return today.year, today.month, ""

    latest = (
        db.session.query(func.max(Transaction.date)).filter(Transaction.user_id == user_id).scalar()
    )
    if latest:
        cal = __import__("calendar")
        label = cal.month_abbr[latest.month] + f" {latest.year} (latest activity; not {cal.month_abbr[today.month]} {today.year})"
        return latest.year, latest.month, label
    return today.year, today.month, ""


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
    """Average daily expense over last N days (calendar window ending today)."""
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
    if total > 0:
        return float(total) / days if days > 0 else 0

    # Demo/historical data: no expenses in the last N calendar days from *today*,
    # but older rows exist — use trailing N days ending on the latest expense date.
    latest_exp = (
        db.session.query(func.max(Transaction.date))
        .filter(Transaction.user_id == user_id, Transaction.type == "expense")
        .scalar()
    )
    if not latest_exp:
        return 0.0
    start2 = latest_exp - timedelta(days=days)
    total2 = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date >= start2,
            Transaction.date <= latest_exp,
        )
        .scalar()
        or 0
    )
    return float(total2) / days if days > 0 and total2 else 0.0


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

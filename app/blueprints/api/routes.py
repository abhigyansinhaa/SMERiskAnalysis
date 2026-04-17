"""
REST-style JSON endpoints under /api/v1.

Auth: Flask-Login session cookie. Returns 401 JSON if not authenticated.
OpenAPI: /api/v1/swagger (Swagger UI), /api/v1/openapi.json
"""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from functools import wraps

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.blueprints.api import api_v1_bp
from app.models import Category, Transaction
from app.openapi import spec
from app.schemas.api_v1 import ForecastRunIn, TransactionCreateIn, WhatIfIn
from app.services.advisor import generate_summary
from app.services.analytics import (
    check_and_create_alerts,
    compute_runway,
    get_alerts,
    get_burn_rate,
    get_category_breakdown,
    get_current_balance,
    get_dashboard_month,
    get_monthly_totals,
    get_top_vendors,
)
from app.services.forecast import run_forecast, run_whatif
from app.utils.formatting import parse_amount


def api_login_required(f):
    """Return 401 JSON instead of redirecting to the login page."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return wrapped


def _transaction_to_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "date": t.date.isoformat() if t.date else None,
        "amount": float(t.amount),
        "type": t.type,
        "category_id": t.category_id,
        "merchant": t.merchant,
        "notes": t.notes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _alert_to_dict(a) -> dict:
    return {
        "id": a.id,
        "kind": a.kind,
        "severity": a.severity,
        "message": a.message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "is_read": a.is_read,
    }


def _get_or_create_categories(user_id: int) -> None:
    """Ensure default categories exist (same as transactions blueprint)."""
    cats = Category.query.filter_by(user_id=user_id).all()
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
            db.session.add(Category(user_id=user_id, name=name, type=t))
        db.session.commit()


@api_v1_bp.route("/me", methods=["GET"])
@api_login_required
def me():
    return jsonify({"id": current_user.id, "email": current_user.email})


@api_v1_bp.route("/dashboard", methods=["GET"])
@api_login_required
def dashboard():
    uid = current_user.id
    y, m, period_note = get_dashboard_month(uid)
    check_and_create_alerts(uid)
    totals = get_monthly_totals(uid, y, m)
    categories = get_category_breakdown(uid, y, m)
    vendors = get_top_vendors(uid, y, m)
    balance = get_current_balance(uid)
    burn = get_burn_rate(uid, 30)
    runway = compute_runway(uid, balance, burn)
    alerts = get_alerts(uid)

    return jsonify(
        {
            "dashboard_year": y,
            "dashboard_month": m,
            "period_note": period_note or None,
            "totals": totals,
            "balance": balance,
            "burn_rate": burn,
            "runway_days": runway,
            "categories": categories,
            "vendors": vendors,
            "alerts": [_alert_to_dict(a) for a in alerts],
        }
    )


@api_v1_bp.route("/transactions", methods=["GET"])
@api_login_required
def list_transactions():
    uid = current_user.id
    q = Transaction.query.filter_by(user_id=uid).order_by(Transaction.date.desc())
    type_filter = request.args.get("type")
    if type_filter in ("income", "expense"):
        q = q.filter_by(type=type_filter)
    month = request.args.get("month")
    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d").date()
            _, last = monthrange(start.year, start.month)
            end = start.replace(day=last)
            q = q.filter(Transaction.date >= start, Transaction.date <= end)
        except ValueError:
            pass
    transactions = q.limit(200).all()
    return jsonify({"transactions": [_transaction_to_dict(t) for t in transactions]})


@api_v1_bp.route("/transactions", methods=["POST"])
@api_login_required
@spec.validate(json=TransactionCreateIn, tags=["transactions"])
def create_transaction():
    uid = current_user.id
    _get_or_create_categories(uid)
    data: TransactionCreateIn = request.context.json  # type: ignore[attr-defined]

    try:
        amount = parse_amount(data.amount)
        tx_type = data.type
        category_id = data.category_id
        merchant = (data.merchant or "").strip() or None
        notes = (data.notes or "").strip() or None
        date_str = data.date

        if not date_str:
            return jsonify({"error": "date is required (YYYY-MM-DD)"}), 422

        tx_date = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        if category_id is not None:
            cat = Category.query.filter_by(id=category_id, user_id=uid).first()
            if not cat:
                return jsonify({"error": "Invalid category_id"}), 400

        if tx_type == "income":
            amount = abs(amount)
        else:
            amount = abs(amount)

        t = Transaction(
            user_id=uid,
            date=tx_date,
            amount=amount,
            type=tx_type,
            category_id=category_id if category_id else None,
            merchant=merchant,
            notes=notes,
        )
        db.session.add(t)
        db.session.commit()
        return jsonify(_transaction_to_dict(t)), 201
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/forecast/run", methods=["POST"])
@api_login_required
@spec.validate(json=ForecastRunIn, tags=["forecast"])
def forecast_run():
    try:
        body: ForecastRunIn = request.context.json  # type: ignore[attr-defined]
        horizon = body.horizon_days
        result = run_forecast(current_user.id, horizon_days=horizon)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/forecast/whatif", methods=["POST"])
@api_login_required
@spec.validate(json=WhatIfIn, tags=["forecast"])
def forecast_whatif():
    try:
        data: WhatIfIn = request.context.json  # type: ignore[attr-defined]
        sales_pct = float(data.sales_pct_change)
        rent_change = parse_amount(data.rent_change)
        one_time = parse_amount(data.one_time_expense)
        result = run_whatif(
            current_user.id,
            sales_pct_change=sales_pct,
            rent_change=rent_change,
            one_time_expense=one_time,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route("/advisor/summary", methods=["POST"])
@api_login_required
def advisor_summary():
    try:
        summary_text, actions = generate_summary(current_user.id)
        return jsonify({"summary": summary_text, "actions": actions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

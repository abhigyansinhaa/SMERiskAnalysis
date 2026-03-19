"""Dashboard and analytics routes."""
from datetime import date

from flask import render_template
from flask_login import login_required, current_user

from app.blueprints.analytics import analytics_bp
from app.services.analytics import (
    get_monthly_totals,
    get_category_breakdown,
    get_top_vendors,
    get_burn_rate,
    get_current_balance,
    compute_runway,
    check_and_create_alerts,
    get_alerts,
)


@analytics_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard with KPIs, charts, and alerts."""
    today = date.today()
    totals = get_monthly_totals(current_user.id, today.year, today.month)
    categories = get_category_breakdown(current_user.id, today.year, today.month)
    vendors = get_top_vendors(current_user.id, today.year, today.month)
    balance = get_current_balance(current_user.id)
    burn = get_burn_rate(current_user.id, 30)
    runway = compute_runway(current_user.id, balance, burn)
    check_and_create_alerts(current_user.id)
    alerts = get_alerts(current_user.id)

    return render_template(
        "analytics/dashboard.html",
        totals=totals,
        categories=categories,
        vendors=vendors,
        balance=balance,
        burn_rate=burn,
        runway=runway,
        alerts=alerts,
    )



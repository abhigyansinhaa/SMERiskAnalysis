"""Dashboard and analytics routes."""
from flask import render_template
from flask_login import current_user, login_required

from app.blueprints.analytics import analytics_bp
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


@analytics_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard with KPIs, charts, and alerts."""
    y, m, period_note = get_dashboard_month(current_user.id)
    totals = get_monthly_totals(current_user.id, y, m)
    categories = get_category_breakdown(current_user.id, y, m)
    vendors = get_top_vendors(current_user.id, y, m)
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
        dashboard_year=y,
        dashboard_month=m,
        period_note=period_note,
    )



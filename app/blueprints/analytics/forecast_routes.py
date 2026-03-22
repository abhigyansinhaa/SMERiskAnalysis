"""Forecast and what-if routes."""
from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.blueprints.analytics import analytics_bp
from app.services.forecast import run_forecast, run_whatif


@analytics_bp.route("/forecast")
@login_required
def forecast():
    """Forecast and what-if simulation page."""
    return render_template("analytics/forecast.html")


@analytics_bp.route("/forecast/run", methods=["POST"])
@login_required
def run_forecast_api():
    """Run baseline forecast."""
    try:
        horizon = int(request.json.get("horizon_days", 30))
        result = run_forecast(current_user.id, horizon_days=horizon)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@analytics_bp.route("/forecast/whatif", methods=["POST"])
@login_required
def whatif_api():
    """Run what-if scenario."""
    try:
        data = request.json or {}
        sales_pct = float(data.get("sales_pct_change", 0))
        rent_change = float(data.get("rent_change", 0))
        one_time = float(data.get("one_time_expense", 0))
        result = run_whatif(
            current_user.id,
            sales_pct_change=sales_pct,
            rent_change=rent_change,
            one_time_expense=one_time,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

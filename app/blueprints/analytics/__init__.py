"""Analytics / Dashboard blueprint."""
from flask import Blueprint

analytics_bp = Blueprint("analytics", __name__)

from app.blueprints.analytics import routes  # noqa: E402, F401
from app.blueprints.analytics import forecast_routes  # noqa: E402, F401

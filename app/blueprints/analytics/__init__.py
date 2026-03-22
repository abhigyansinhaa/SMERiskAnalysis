"""Analytics / Dashboard blueprint."""
from flask import Blueprint

analytics_bp = Blueprint("analytics", __name__)

from app.blueprints.analytics import (  # noqa: E402
    forecast_routes,  # noqa: F401
    routes,  # noqa: F401
)

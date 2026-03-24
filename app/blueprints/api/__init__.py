"""Versioned JSON API (`/api/v1`). Session cookie auth (Flask-Login), same as the web UI."""
from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

from app.blueprints.api import routes  # noqa: E402, F401

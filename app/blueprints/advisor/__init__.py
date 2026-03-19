"""Advisor (LLM) blueprint."""
from flask import Blueprint

advisor_bp = Blueprint("advisor", __name__)

from app.blueprints.advisor import routes  # noqa: E402, F401

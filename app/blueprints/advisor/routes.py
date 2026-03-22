"""LLM Advisor routes - grounded summary and recommendations."""
from flask import jsonify, render_template
from flask_login import current_user, login_required

from app.blueprints.advisor import advisor_bp
from app.services.advisor import generate_summary


@advisor_bp.route("/")
@login_required
def index():
    """Advisor page with summary and actions."""
    return render_template("advisor/index.html")


@advisor_bp.route("/summary", methods=["POST"])
@login_required
def summary():
    """Generate LLM summary from user's computed metrics."""
    try:
        summary_text, actions = generate_summary(current_user.id)
        return jsonify({"summary": summary_text, "actions": actions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

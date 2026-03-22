"""Cashflow Risk Advisor - Flask application factory."""
from config import config_by_name
from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    config_name = config_name or "default"
    app = Flask(__name__)
    cfg = config_by_name[config_name]
    app.config.from_object(cfg)
    # SQLALCHEMY_DATABASE_URI is a property - evaluate via instance
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg().SQLALCHEMY_DATABASE_URI

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.blueprints.advisor import advisor_bp
    from app.blueprints.analytics import analytics_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.transactions import transactions_bp

    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(analytics_bp)
    app.register_blueprint(advisor_bp, url_prefix="/advisor")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("analytics.dashboard"))
        return render_template("home.html")

    return app

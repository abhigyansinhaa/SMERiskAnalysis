"""Forecast service with SQLite + minimal bundle."""
from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from app import db
from app.models import Category, Transaction, User
from app.services.forecast import reset_forecast_model_cache, run_forecast
from app.services.forecast_features import FEATURE_COLUMNS
from joblib import dump
from lightgbm import LGBMRegressor


@pytest.fixture(autouse=True)
def _reset():
    reset_forecast_model_cache()
    yield
    reset_forecast_model_cache()


def _make_bundle(path: Path) -> None:
    rng = np.random.default_rng(1)
    X = rng.standard_normal((120, len(FEATURE_COLUMNS)))
    y = rng.standard_normal(120)
    models = {}
    for alpha, key in [(0.1, "q010"), (0.5, "q050"), (0.9, "q090")]:
        m = LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            n_estimators=30,
            verbosity=-1,
            random_state=1,
        )
        m.fit(X, y)
        models[key] = m
    dump(
        {"version": 2, "models": models, "feature_columns": FEATURE_COLUMNS, "country": "IN"},
        path,
    )


def test_run_forecast_empty_history_still_returns_shape(app):
    """No transactions: daily series is flat zeros; forecast may still run over long lookback."""
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        p = tmp.name
    try:
        _make_bundle(Path(p))
        app.config["FORECAST_MODEL_PATH"] = p
        with app.app_context():
            u = User.query.first()
            uid = u.id
            out = run_forecast(uid, horizon_days=7, as_of_date=date.today())
            assert "metrics" in out
            assert "predicted_balance" in out
            assert isinstance(out.get("daily_forecast"), list)
    finally:
        Path(p).unlink(missing_ok=True)


def test_run_forecast_with_history(app):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        p = tmp.name
    try:
        _make_bundle(Path(p))
        app.config["FORECAST_MODEL_PATH"] = p
        with app.app_context():
            u = User.query.first()
            uid = u.id
            c = Category(user_id=uid, name="Sales", type="income")
            db.session.add(c)
            db.session.commit()
            start = date.today() - timedelta(days=120)
            for i in range(120):
                db.session.add(
                    Transaction(
                        user_id=uid,
                        date=start + timedelta(days=i),
                        amount=100.0 + (i % 7) * 10,
                        type="income" if i % 2 == 0 else "expense",
                        category_id=c.id,
                    )
                )
            db.session.commit()
            out = run_forecast(uid, horizon_days=5, as_of_date=date.today())
            assert len(out["daily_forecast"]) == 5
            assert "net_low" in out["daily_forecast"][0]
    finally:
        Path(p).unlink(missing_ok=True)

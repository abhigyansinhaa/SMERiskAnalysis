"""Regression-based cashflow forecasting."""
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import load
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import func

from app import db
from app.models import Forecast, Transaction
from app.services.forecast_features import FEATURE_COLUMNS, engineer_features

_forecast_model: Any = None
_loaded_model_path: str | None = None


def reset_forecast_model_cache() -> None:
    """Clear cached Ridge model (for tests or after swapping artifact)."""
    global _forecast_model, _loaded_model_path
    _forecast_model = None
    _loaded_model_path = None


def _resolve_forecast_model_path() -> str:
    try:
        from flask import current_app

        return str(current_app.config["FORECAST_MODEL_PATH"])
    except RuntimeError:
        from config import Config

        return Config.FORECAST_MODEL_PATH


def get_forecast_model() -> Any:
    """Load pre-trained Ridge once per path (joblib)."""
    global _forecast_model, _loaded_model_path
    path = _resolve_forecast_model_path()
    if _forecast_model is not None and _loaded_model_path == path:
        return _forecast_model
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"Forecast model not found at {p.resolve()}. Run: python scripts/train_forecast_model.py"
        )
    _forecast_model = load(p)
    _loaded_model_path = path
    return _forecast_model


def _build_daily_series(user_id: int, start: date, end: date) -> pd.DataFrame:
    """Build daily income, expense, net from transactions."""
    rows = (
        Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .all()
    )
    by_date = {}
    for r in rows:
        d = r.date
        if d not in by_date:
            by_date[d] = {"income": 0, "expense": 0}
        if r.type == "income":
            by_date[d]["income"] += r.amount
        else:
            by_date[d]["expense"] += r.amount

    dates = pd.date_range(start=start, end=end, freq="D")
    data = []
    for d in dates:
        day = d.date()
        rec = by_date.get(day, {"income": 0, "expense": 0})
        net = rec["income"] - rec["expense"]
        data.append({"date": day, "income": rec["income"], "expense": rec["expense"], "net": net})
    return pd.DataFrame(data)


def run_forecast(
    user_id: int,
    horizon_days: int = 30,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Run Ridge regression forecast using a pre-trained model. Returns predicted net, balance, and metrics.
    """
    as_of_date = as_of_date or date.today()
    lookback = 90
    start = as_of_date - timedelta(days=lookback)
    df = _build_daily_series(user_id, start, as_of_date)

    if len(df) < 14:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data"},
        }

    df = engineer_features(df)
    df = df.dropna(subset=["lag1", "lag7", "lag14", "roll7", "roll14"])

    if len(df) < 7:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data after feature engineering"},
        }

    try:
        model = get_forecast_model()
    except FileNotFoundError as e:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": str(e)},
        }

    X = df[FEATURE_COLUMNS]
    y = df["net"]

    # Time-based train/test: last 14 days for test (metrics for global model on user holdout)
    split = max(7, len(df) - 14)
    X_test = X.iloc[split:]
    y_test = y.iloc[split:]

    if len(X_test) == 0:
        mae = rmse = None
    else:
        y_pred_test = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))

    # Roll forward: predict next horizon_days
    current_balance = _get_balance_at(user_id, as_of_date)
    daily_forecast = []
    last_row = df.iloc[-1]
    lag1, lag7, lag14 = last_row["net"], df["net"].iloc[-7] if len(df) >= 7 else 0, df["net"].iloc[-14] if len(df) >= 14 else 0
    roll7 = df["net"].tail(7).mean()
    roll14 = df["net"].tail(14).mean()

    cumulative_net = 0
    for i in range(horizon_days):
        d = as_of_date + timedelta(days=i + 1)
        dow = d.weekday()
        dom = d.day
        X_next = np.array([[lag1, lag7, lag14, roll7, roll14, dow, dom]])
        pred_net = float(model.predict(X_next)[0])
        cumulative_net += pred_net
        daily_forecast.append({"date": d.isoformat(), "net": pred_net})
        # Update lags for next iteration (simplified)
        lag1, lag7, lag14 = pred_net, lag1, lag7
        roll7 = (roll7 * 6 + pred_net) / 7
        roll14 = (roll14 * 13 + pred_net) / 14

    predicted_balance = current_balance + cumulative_net

    metrics_payload = {"mae": mae, "rmse": rmse}
    # Store forecast
    f = Forecast(
        user_id=user_id,
        horizon_days=horizon_days,
        as_of_date=as_of_date,
        predicted_net=cumulative_net,
        predicted_balance=predicted_balance,
        model_name="ridge",
        metrics_json=json.dumps(metrics_payload),
    )
    db.session.add(f)
    db.session.commit()

    return {
        "predicted_net": cumulative_net,
        "predicted_balance": predicted_balance,
        "opening_balance": current_balance,
        "daily_forecast": daily_forecast,
        "metrics": metrics_payload,
    }


def _get_balance_at(user_id: int, end_date: date) -> float:
    """Net balance up to end_date."""
    income = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "income",
            Transaction.date <= end_date,
        )
        .scalar()
        or 0
    )
    expense = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.date <= end_date,
        )
        .scalar()
        or 0
    )
    return float(income - expense)


def run_whatif(
    user_id: int,
    sales_pct_change: float = 0,
    rent_change: float = 0,
    one_time_expense: float = 0,
) -> dict[str, Any]:
    """
    Apply scenario adjustments to baseline forecast.
    sales_pct_change: e.g. -0.2 for -20% sales
    rent_change: absolute change in rent (e.g. +500)
    one_time_expense: one-time expense to add
    """
    baseline = run_forecast(user_id, horizon_days=30)

    # Simplified: adjust predicted_net by scenario
    adj_net = baseline["predicted_net"]
    # Approximate: assume some fraction of predicted net is income
    # For demo: apply sales_pct to a rough income share
    income_share = 0.7  # rough
    adj_net += baseline["predicted_net"] * income_share * sales_pct_change
    adj_net -= rent_change
    adj_net -= one_time_expense

    balance = _get_balance_at(user_id, date.today())
    adj_balance = balance + adj_net

    daily = baseline.get("daily_forecast") or []
    baseline_net = float(baseline.get("predicted_net") or 0)
    epsilon = 1e-6
    if not daily:
        adjusted_daily_forecast: list[dict[str, Any]] = []
    elif abs(baseline_net) > epsilon:
        factor = adj_net / baseline_net
        adjusted_daily_forecast = [{"date": row["date"], "net": float(row["net"]) * factor} for row in daily]
    else:
        n = len(daily)
        uniform = (adj_net / n) if n else 0.0
        adjusted_daily_forecast = [{"date": row["date"], "net": uniform} for row in daily]

    return {
        "baseline": baseline,
        "scenario": {
            "sales_pct_change": sales_pct_change,
            "rent_change": rent_change,
            "one_time_expense": one_time_expense,
        },
        "adjusted_net": adj_net,
        "adjusted_balance": adj_balance,
        "adjusted_daily_forecast": adjusted_daily_forecast,
    }

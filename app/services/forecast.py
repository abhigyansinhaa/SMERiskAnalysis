"""Regression-based cashflow forecasting."""
import json
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from sqlalchemy import func

from app import db
from app.models import Transaction, Forecast


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


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag, rolling, and time features."""
    df = df.copy()
    df["lag1"] = df["net"].shift(1)
    df["lag7"] = df["net"].shift(7)
    df["lag14"] = df["net"].shift(14)
    df["roll7"] = df["net"].rolling(7, min_periods=1).mean().shift(1)
    df["roll14"] = df["net"].rolling(14, min_periods=1).mean().shift(1)
    df["dow"] = pd.to_datetime(df["date"]).dt.dayofweek
    df["dom"] = pd.to_datetime(df["date"]).dt.day
    return df


def run_forecast(
    user_id: int,
    horizon_days: int = 30,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Run Ridge regression forecast. Returns predicted net, balance, and metrics.
    """
    as_of_date = as_of_date or date.today()
    lookback = 90
    start = as_of_date - timedelta(days=lookback)
    df = _build_daily_series(user_id, start, as_of_date)

    if len(df) < 14:
        return {
            "predicted_net": 0,
            "predicted_balance": 0,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data"},
        }

    df = _engineer_features(df)
    df = df.dropna(subset=["lag1", "lag7", "lag14", "roll7", "roll14"])

    if len(df) < 7:
        return {
            "predicted_net": 0,
            "predicted_balance": 0,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data after feature engineering"},
        }

    features = ["lag1", "lag7", "lag14", "roll7", "roll14", "dow", "dom"]
    X = df[features]
    y = df["net"]

    # Time-based train/test: last 14 days for test
    split = max(7, len(df) - 14)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = Ridge(alpha=1.0, random_state=42)
    model.fit(X_train, y_train)

    y_pred_test = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

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

    # Store forecast
    f = Forecast(
        user_id=user_id,
        horizon_days=horizon_days,
        as_of_date=as_of_date,
        predicted_net=cumulative_net,
        predicted_balance=predicted_balance,
        model_name="ridge",
        metrics_json=json.dumps({"mae": mae, "rmse": rmse}),
    )
    db.session.add(f)
    db.session.commit()

    return {
        "predicted_net": cumulative_net,
        "predicted_balance": predicted_balance,
        "daily_forecast": daily_forecast,
        "metrics": {"mae": mae, "rmse": rmse},
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

    return {
        "baseline": baseline,
        "scenario": {
            "sales_pct_change": sales_pct_change,
            "rent_change": rent_change,
            "one_time_expense": one_time_expense,
        },
        "adjusted_net": adj_net,
        "adjusted_balance": adj_balance,
    }

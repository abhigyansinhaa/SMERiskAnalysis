"""Cashflow forecasting: LightGBM quantile bundle (preferred) with sliding-window multi-step."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import load
from sqlalchemy import func

from app import db
from app.models import Forecast, Transaction
from app.services.forecast_features import (
    FEATURE_COLUMNS,
    engineer_features,
    feature_vector_for_date,
)

_forecast_bundle: Any = None
_loaded_bundle_path: str | None = None


def reset_forecast_model_cache() -> None:
    """Clear cached model bundle (tests or after swapping artifact)."""
    global _forecast_bundle, _loaded_bundle_path
    _forecast_bundle = None
    _loaded_bundle_path = None


def _resolve_forecast_model_path() -> str:
    try:
        from flask import current_app

        return str(current_app.config["FORECAST_MODEL_PATH"])
    except RuntimeError:
        from config import Config

        return Config.FORECAST_MODEL_PATH


def get_forecast_bundle() -> dict[str, Any]:
    """Load joblib bundle once per path."""
    global _forecast_bundle, _loaded_bundle_path
    path = _resolve_forecast_model_path()
    if _forecast_bundle is not None and _loaded_bundle_path == path:
        return _forecast_bundle
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"Forecast bundle not found at {p.resolve()}. Run: python scripts/train_forecast_model.py"
        )
    _forecast_bundle = load(p)
    _loaded_bundle_path = path
    return _forecast_bundle


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
    by_date: dict[date, dict[str, float]] = {}
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


def _country_from_config() -> str:
    try:
        from flask import current_app

        return str(current_app.config.get("HOLIDAY_COUNTRY", "IN"))
    except RuntimeError:
        from config import Config

        return Config.HOLIDAY_COUNTRY


def run_forecast(
    user_id: int,
    horizon_days: int = 30,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Quantile LightGBM forecast with sliding-window multi-step rollout.
    Returns predicted net (median path), balance, daily series with low/high bands.
    """
    as_of_date = as_of_date or date.today()
    lookback = 400
    start = as_of_date - timedelta(days=lookback)
    df = _build_daily_series(user_id, start, as_of_date)
    country = _country_from_config()

    if len(df) < 40:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0.0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data"},
        }

    df = engineer_features(df, country=country)
    req = ["lag1", "lag7", "lag14", "lag28", "roll7_mean"]
    df = df.dropna(subset=req)

    if len(df) < 35:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0.0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Insufficient data after feature engineering"},
        }

    try:
        bundle = get_forecast_bundle()
    except FileNotFoundError as e:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0.0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": str(e)},
        }

    models: dict[str, Any] = bundle.get("models") or {}
    feats = bundle.get("feature_columns") or FEATURE_COLUMNS
    if not models or "q050" not in models:
        opening = _get_balance_at(user_id, as_of_date)
        return {
            "predicted_net": 0.0,
            "predicted_balance": opening,
            "opening_balance": opening,
            "daily_forecast": [],
            "metrics": {"mae": None, "rmse": None, "note": "Invalid forecast bundle (missing q050)"},
        }

    X_all = df[feats].to_numpy(dtype=float)
    y_all = df["net"].to_numpy(dtype=float)
    split = max(20, len(df) - 14)
    X_test = X_all[split:]
    y_test = y_all[split:]
    mae_v = rmse_v = None
    if len(X_test) > 0 and "q050" in models:
        y_pred = models["q050"].predict(X_test)
        mae_v = float(np.mean(np.abs(y_test - y_pred)))
        rmse_v = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))

    history = [float(x) for x in df["net"].tolist()]
    current_balance = _get_balance_at(user_id, as_of_date)
    cumulative_net = 0.0
    daily_forecast: list[dict[str, Any]] = []

    for i in range(horizon_days):
        d = as_of_date + timedelta(days=i + 1)
        x_vec = feature_vector_for_date(history, d, country=country)
        x_map = dict(zip(FEATURE_COLUMNS, x_vec, strict=True))
        x_ordered = np.array([x_map[c] for c in feats], dtype=np.float64).reshape(1, -1)
        q10 = float(models.get("q010").predict(x_ordered)[0]) if models.get("q010") else 0.0
        q50 = float(models["q050"].predict(x_ordered)[0])
        q90 = float(models.get("q090").predict(x_ordered)[0]) if models.get("q090") else q50
        cumulative_net += q50
        daily_forecast.append(
            {
                "date": d.isoformat(),
                "net": q50,
                "net_low": q10,
                "net_high": q90,
            }
        )
        history.append(q50)
        if len(history) > 400:
            history = history[-400:]

    predicted_balance = current_balance + cumulative_net
    metrics_payload = {"mae": mae_v, "rmse": rmse_v}

    f = Forecast(
        user_id=user_id,
        horizon_days=horizon_days,
        as_of_date=as_of_date,
        predicted_net=cumulative_net,
        predicted_balance=predicted_balance,
        model_name="lgbm_quantile",
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
    """Apply scenario adjustments to baseline forecast."""
    baseline = run_forecast(user_id, horizon_days=30)

    adj_net = float(baseline.get("predicted_net") or 0)
    income_share = 0.7
    adj_net += float(baseline.get("predicted_net") or 0) * income_share * sales_pct_change
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
        adjusted_daily_forecast = [
            {
                "date": row["date"],
                "net": float(row["net"]) * factor,
                "net_low": float(row.get("net_low", row["net"])) * factor,
                "net_high": float(row.get("net_high", row["net"])) * factor,
            }
            for row in daily
        ]
    else:
        n = len(daily)
        uniform = (adj_net / n) if n else 0.0
        adjusted_daily_forecast = [
            {"date": row["date"], "net": uniform, "net_low": uniform, "net_high": uniform}
            for row in daily
        ]

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

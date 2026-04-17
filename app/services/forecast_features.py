"""Feature engineering for cashflow forecasting (train + serve)."""
from __future__ import annotations

import calendar
from datetime import date

import holidays as holidays_lib
import numpy as np
import pandas as pd

# Order must match training script and inference.
FEATURE_COLUMNS = [
    "lag1",
    "lag7",
    "lag14",
    "lag28",
    "roll7_mean",
    "roll14_mean",
    "roll28_mean",
    "roll7_std",
    "roll14_std",
    "dow",
    "dom",
    "month",
    "is_holiday",
    "is_payday",
]


def _payday_flag(d: date) -> int:
    """Simple SME-style payday: 1st, 15th, or last calendar day."""
    last = calendar.monthrange(d.year, d.month)[1]
    return int(d.day in (1, 15) or d.day == last)


def engineer_features(df: pd.DataFrame, *, country: str = "IN") -> pd.DataFrame:
    """Add lag, rolling, calendar, and holiday features to a daily net series."""
    df = df.copy()
    years = sorted({pd.Timestamp(x).year for x in df["date"]})
    cal = holidays_lib.country_holidays(country, years=years) if years else {}

    hol = []
    for x in df["date"]:
        dd = x if isinstance(x, date) else pd.Timestamp(x).date()
        hol.append(1 if dd in cal else 0)
    df["is_holiday"] = hol

    pay = []
    for x in df["date"]:
        dd = x if isinstance(x, date) else pd.Timestamp(x).date()
        pay.append(_payday_flag(dd))
    df["is_payday"] = pay

    df["lag1"] = df["net"].shift(1)
    df["lag7"] = df["net"].shift(7)
    df["lag14"] = df["net"].shift(14)
    df["lag28"] = df["net"].shift(28)

    df["roll7_mean"] = df["net"].rolling(7, min_periods=1).mean().shift(1)
    df["roll14_mean"] = df["net"].rolling(14, min_periods=1).mean().shift(1)
    df["roll28_mean"] = df["net"].rolling(28, min_periods=1).mean().shift(1)
    df["roll7_std"] = df["net"].rolling(7, min_periods=1).std().shift(1).fillna(0.0)
    df["roll14_std"] = df["net"].rolling(14, min_periods=1).std().shift(1).fillna(0.0)

    dt = pd.to_datetime(df["date"])
    df["dow"] = dt.dt.dayofweek
    df["dom"] = dt.dt.day
    df["month"] = dt.dt.month

    return df


def feature_vector_for_date(
    history_net: list[float],
    target: date,
    *,
    country: str = "IN",
) -> np.ndarray:
    """
    Build a single feature row from trailing daily net values (oldest first)
    for predicting target date. history_net must include known nets up to day before target.
    """
    if len(history_net) < 28:
        raise ValueError("history_net must have at least 28 values")
    lag1 = float(history_net[-1])
    lag7 = float(history_net[-7])
    lag14 = float(history_net[-14])
    lag28 = float(history_net[-28])
    tail7 = np.array(history_net[-7:])
    tail14 = np.array(history_net[-14:])
    tail28 = np.array(history_net[-28:])
    roll7_mean = float(tail7.mean())
    roll14_mean = float(tail14.mean())
    roll28_mean = float(tail28.mean())
    roll7_std = float(tail7.std(ddof=0)) if len(tail7) > 1 else 0.0
    roll14_std = float(tail14.std(ddof=0)) if len(tail14) > 1 else 0.0

    cal = holidays_lib.country_holidays(country, years=[target.year])
    is_holiday = 1 if target in cal else 0
    is_payday = _payday_flag(target)

    dow = target.weekday()
    dom = target.day
    month = target.month

    row = np.array(
        [
            lag1,
            lag7,
            lag14,
            lag28,
            roll7_mean,
            roll14_mean,
            roll28_mean,
            roll7_std,
            roll14_std,
            float(dow),
            float(dom),
            float(month),
            float(is_holiday),
            float(is_payday),
        ],
        dtype=np.float64,
    )
    return row

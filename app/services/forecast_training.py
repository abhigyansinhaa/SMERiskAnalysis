"""Walk-forward backtests, baselines, and LightGBM quantile training (used by scripts)."""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

try:
    from prophet import Prophet
except ImportError:
    Prophet = None  # type: ignore[misc, assignment]


def seasonal_naive_predict(full_y: np.ndarray, test_idx: np.ndarray) -> np.ndarray:
    """Per test index, predict value from 7 days earlier in the full series."""
    out = np.zeros(len(test_idx), dtype=float)
    for i, idx in enumerate(test_idx):
        j = int(idx) - 7
        out[i] = float(full_y[j]) if j >= 0 else float(full_y[0])
    return out


def prophet_predict_train_test(
    df_daily: pd.DataFrame,
    train_end_idx: int,
    test_len: int,
) -> np.ndarray | None:
    """Fit Prophet on df_daily[:train_end_idx] and forecast test_len days."""
    if Prophet is None or test_len <= 0 or train_end_idx < 14:
        return None
    train = df_daily.iloc[:train_end_idx].copy()
    train["ds"] = pd.to_datetime(train["date"])
    train["y"] = train["net"].astype(float)
    m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(train[["ds", "y"]])
    future = m.make_future_dataframe(periods=test_len, freq="D", include_history=False)
    fc = m.predict(future)
    return fc["yhat"].values.astype(float)


def walk_forward_splits(n_samples: int, n_splits: int = 5, test_size: int = 30) -> list[tuple[np.ndarray, np.ndarray]]:
    """Expanding-window splits: train [0:test_start), test [test_start:test_end)."""
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for k in range(n_splits):
        test_end = n_samples - k * test_size
        test_start = test_end - test_size
        if test_start < 50:
            continue
        train_idx = np.arange(0, test_start)
        test_idx = np.arange(test_start, test_end)
        out.append((train_idx, test_idx))
    out.reverse()
    return out


def train_quantile_models(
    X: np.ndarray,
    y: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    """Train three LightGBM quantile regressors; keys q010, q050, q090."""
    models: dict[str, LGBMRegressor] = {}
    for alpha in (0.1, 0.5, 0.9):
        key = f"q{int(alpha * 100):03d}"
        m = LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            random_state=seed,
            verbosity=-1,
        )
        m.fit(X, y)
        models[key] = m
    return models


def dataset_hash(df: pd.DataFrame) -> str:
    raw = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    return hashlib.sha256(raw).hexdigest()[:16]

"""Forecast bundle loading and feature engineering."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from app import create_app
from app.services.forecast import get_forecast_bundle, reset_forecast_model_cache
from app.services.forecast_features import FEATURE_COLUMNS, engineer_features
from joblib import dump
from lightgbm import LGBMRegressor


@pytest.fixture(autouse=True)
def _reset_bundle_cache():
    reset_forecast_model_cache()
    yield
    reset_forecast_model_cache()


def test_engineer_features_columns() -> None:
    df = engineer_features(
        pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=40, freq="D"),
                "net": np.arange(40, dtype=float),
            }
        ),
        country="IN",
    )
    for col in FEATURE_COLUMNS:
        assert col in df.columns


def test_joblib_bundle_load_predict() -> None:
    rng = np.random.default_rng(0)
    X = rng.standard_normal((80, len(FEATURE_COLUMNS)))
    y = rng.standard_normal(80)
    models = {}
    for alpha, key in [(0.1, "q010"), (0.5, "q050"), (0.9, "q090")]:
        m = LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            n_estimators=20,
            verbosity=-1,
            random_state=42,
        )
        m.fit(X, y)
        models[key] = m
    bundle = {"version": 2, "models": models, "feature_columns": FEATURE_COLUMNS, "country": "IN"}

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        path = tmp.name
    try:
        dump(bundle, path)
        app = create_app("testing")
        with app.app_context():
            app.config["FORECAST_MODEL_PATH"] = path
            loaded = get_forecast_bundle()
        out = loaded["models"]["q050"].predict(np.ones((1, len(FEATURE_COLUMNS))))
        assert out.shape == (1,)
    finally:
        Path(path).unlink(missing_ok=True)

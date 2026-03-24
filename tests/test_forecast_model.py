"""Tests for pre-trained Ridge forecast artifact loading."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from app import create_app
from app.services.forecast import get_forecast_model, reset_forecast_model_cache
from app.services.forecast_features import FEATURE_COLUMNS, engineer_features
from joblib import dump
from sklearn.linear_model import Ridge


class TestForecastModel(unittest.TestCase):
    def tearDown(self) -> None:
        reset_forecast_model_cache()

    def test_joblib_load_predict_matches_feature_count(self) -> None:
        rng = np.random.default_rng(0)
        X = rng.standard_normal((30, len(FEATURE_COLUMNS)))
        y = rng.standard_normal(30)
        model = Ridge(alpha=1.0, random_state=42)
        model.fit(X, y)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
            path = tmp.name
        try:
            dump(model, path)
            app = create_app()
            with app.app_context():
                app.config["FORECAST_MODEL_PATH"] = path
                loaded = get_forecast_model()
            out = loaded.predict(np.ones((1, len(FEATURE_COLUMNS))))
            self.assertEqual(out.shape, (1,))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_engineer_features_columns(self) -> None:
        df = engineer_features(
            pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=20, freq="D"),
                    "net": np.arange(20, dtype=float),
                }
            )
        )
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)


if __name__ == "__main__":
    unittest.main()

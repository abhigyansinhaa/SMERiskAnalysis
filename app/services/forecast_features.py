"""Shared feature engineering for cashflow Ridge forecasting (train + serve)."""
import pandas as pd

# Must match train script and run_forecast inference order.
FEATURE_COLUMNS = ["lag1", "lag7", "lag14", "roll7", "roll14", "dow", "dom"]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag, rolling, and calendar features to a daily net series."""
    df = df.copy()
    df["lag1"] = df["net"].shift(1)
    df["lag7"] = df["net"].shift(7)
    df["lag14"] = df["net"].shift(14)
    df["roll7"] = df["net"].rolling(7, min_periods=1).mean().shift(1)
    df["roll14"] = df["net"].rolling(14, min_periods=1).mean().shift(1)
    df["dow"] = pd.to_datetime(df["date"]).dt.dayofweek
    df["dom"] = pd.to_datetime(df["date"]).dt.day
    return df

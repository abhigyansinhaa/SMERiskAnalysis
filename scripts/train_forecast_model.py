"""Train Ridge on synthetic daily net series and save joblib artifact for run_forecast."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.linear_model import Ridge

# Project root on path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app.services.forecast_features import FEATURE_COLUMNS, engineer_features  # noqa: E402


def _one_series(n_days: int, base_seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(base_seed)
    end = pd.Timestamp.today().normalize()
    dates = pd.date_range(end=end, periods=n_days, freq="D")
    t = np.arange(n_days, dtype=float)
    scale = 0.5 + (base_seed % 7) * 0.15
    weekly = scale * 350 * np.sin(2 * np.pi * t / 7)
    trend = ((-1) ** (base_seed % 3)) * 0.12 * t
    noise = rng.normal(0, 280 + 40 * (base_seed % 5), n_days)
    spikes = np.zeros(n_days)
    spike_idx = rng.choice(n_days, size=max(2, n_days // 35), replace=False)
    spikes[spike_idx] = rng.normal(0, 1800, len(spike_idx))
    net = weekly + trend + noise + spikes
    return pd.DataFrame({"date": dates.date, "net": net})


def build_training_arrays(seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    chunks: list[pd.DataFrame] = []
    for k in range(12):
        n = int(rng.integers(320, 520))
        chunks.append(_one_series(n, seed + k * 97))
    raw = pd.concat(chunks, ignore_index=True)
    df = engineer_features(raw)
    df = df.dropna(subset=["lag1", "lag7", "lag14", "roll7", "roll14"])
    X = df[FEATURE_COLUMNS].to_numpy()
    y = df["net"].to_numpy()
    return X, y


def main() -> None:
    p = argparse.ArgumentParser(description="Train Ridge forecast model and save joblib artifact.")
    p.add_argument(
        "--output",
        type=Path,
        default=_ROOT / "models" / "ridge_forecast.pkl",
        help="Output path for joblib file (default: models/ridge_forecast.pkl)",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed for synthetic data and Ridge")
    args = p.parse_args()

    X, y = build_training_arrays(args.seed)
    model = Ridge(alpha=1.0, random_state=args.seed)
    model.fit(X, y)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump(model, args.output)
    print(f"Saved Ridge model ({len(X)} rows) to {args.output.resolve()}")


if __name__ == "__main__":
    main()

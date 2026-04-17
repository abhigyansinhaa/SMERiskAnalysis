"""Train LightGBM quantile models on synthetic or DB daily series; log MLflow; save joblib bundle."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import dump  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app.services.forecast_features import FEATURE_COLUMNS, engineer_features  # noqa: E402
from app.services.forecast_training import (  # noqa: E402
    dataset_hash,
    prophet_predict_train_test,
    seasonal_naive_predict,
    train_quantile_models,
    walk_forward_splits,
)
from app.services.ml_metrics import mae, mape, pinball_loss, rmse, smape  # noqa: E402


def _synthetic_daily_series(n_days: int, seed: int, country: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    dates = pd.date_range(end=end, periods=n_days, freq="D")
    t = np.arange(n_days, dtype=float)
    weekly = 400 * np.sin(2 * np.pi * t / 7)
    monthly = 120 * np.sin(2 * np.pi * t / 30.5)
    noise = rng.normal(0, 350, n_days)
    spikes = np.zeros(n_days)
    idx = rng.choice(n_days, size=max(3, n_days // 40), replace=False)
    spikes[idx] = rng.normal(0, 2000, len(idx))
    net = weekly + monthly + noise + spikes
    return pd.DataFrame({"date": [d.date() for d in dates], "net": net})


def main() -> None:
    p = argparse.ArgumentParser(description="Train LightGBM quantile forecast bundle + MLflow logging.")
    p.add_argument("--output", type=Path, default=_ROOT / "models" / "forecast_bundle.pkl")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--days", type=int, default=730, help="Synthetic history length (days)")
    p.add_argument("--fast", action="store_true", help="Shorter run for CI (120 days, 2 folds)")
    p.add_argument("--country", type=str, default="IN")
    args = p.parse_args()

    n_days = 120 if args.fast else args.days
    df = _synthetic_daily_series(n_days, args.seed, args.country)
    df = engineer_features(df, country=args.country)
    req = ["lag1", "lag7", "lag14", "lag28", "roll7_mean"]
    df = df.dropna(subset=req)
    y = df["net"].to_numpy()
    X = df[FEATURE_COLUMNS].to_numpy()

    mlflow.set_experiment("cashflow_forecast")
    with mlflow.start_run():
        mlflow.log_params(
            {
                "feature_columns": ",".join(FEATURE_COLUMNS),
                "country": args.country,
                "n_days": n_days,
                "seed": args.seed,
            }
        )
        h = dataset_hash(df)
        mlflow.log_param("dataset_hash", h)

        test_size = 30 if not args.fast else 14
        n_splits = 2 if args.fast else 5
        splits = walk_forward_splits(len(df), n_splits=n_splits, test_size=test_size)
        if not splits:
            splits = [(np.arange(0, max(30, len(df) - test_size)), np.arange(len(df) - test_size, len(df)))]

        fold_rows = []
        for fold_i, (tr_idx, te_idx) in enumerate(splits):
            X_tr, X_te = X[tr_idx], X[te_idx]
            y_tr, y_te = y[tr_idx], y[te_idx]
            if len(X_tr) < 40 or len(X_te) < 5:
                continue
            models = train_quantile_models(X_tr, y_tr, args.seed + fold_i)
            pred = models["q050"].predict(X_te)
            fold_rows.append(
                {
                    "fold": fold_i,
                    "mae": mae(y_te, pred),
                    "rmse": rmse(y_te, pred),
                    "mape": mape(y_te, pred),
                    "smape": smape(y_te, pred),
                    "pinball_q010": pinball_loss(y_te, models["q010"].predict(X_te), 0.1),
                    "pinball_q050": pinball_loss(y_te, pred, 0.5),
                    "pinball_q090": pinball_loss(y_te, models["q090"].predict(X_te), 0.9),
                }
            )
            mlflow.log_metrics({f"fold_{fold_i}_mae": fold_rows[-1]["mae"], f"fold_{fold_i}_mape": fold_rows[-1]["mape"]})

        # Baselines on last split
        if splits:
            tr_idx, te_idx = splits[-1]
            y_te = y[te_idx]
            naive = seasonal_naive_predict(y, te_idx)
            mlflow.log_metric("mape_seasonal_naive_last_fold", mape(y_te, naive))

            ph = prophet_predict_train_test(df[["date", "net"]], int(tr_idx[-1]) + 1, len(te_idx))
            if ph is not None and len(ph) == len(y_te):
                mlflow.log_metric("mape_prophet_last_fold", mape(y_te, ph))

        # Train final models on full data
        final_models = train_quantile_models(X, y, args.seed)
        bundle = {
            "version": 2,
            "models": final_models,
            "feature_columns": FEATURE_COLUMNS,
            "country": args.country,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        dump(bundle, args.output)
        mlflow.log_artifact(str(args.output))

        # Plot last 90 days actual vs q050 on holdout
        split = max(40, len(X) - 60)
        y_pred_plot = final_models["q050"].predict(X[split:])
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(y[split:], label="actual")
        ax.plot(y_pred_plot, label="q050")
        ax.legend()
        fig.tight_layout()
        plot_path = _ROOT / "artifacts" / "train_plot.png"
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(plot_path)
        plt.close(fig)
        mlflow.log_artifact(str(plot_path))

        print(f"Saved bundle to {args.output.resolve()}")
        if fold_rows:
            fr = _ROOT / "artifacts" / f"backtest_{pd.Timestamp.now(tz='UTC').strftime('%Y%m%d_%H%M%S')}.csv"
            fr.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(fold_rows).to_csv(fr, index=False)
            mlflow.log_artifact(str(fr))
            print("Fold MAPE:", [round(r["mape"], 1) for r in fold_rows])


if __name__ == "__main__":
    main()

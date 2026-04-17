# Model card: cashflow net forecast

## Overview

- **Model:** LightGBM quantile regression (`objective=quantile`, α ∈ {0.1, 0.5, 0.9}).
- **Target:** Daily net cashflow (income − expense) per calendar day.
- **Output:** Point forecast uses the median (q50); q10 and q90 form an approximate 80% band.
- **Serving:** Multi-step horizon via **sliding-window rollout**: each day’s q50 is appended to history; features are recomputed from the buffer (no incorrect single-step lag rotation).

## Data

- **Training default:** Synthetic daily series generated in `scripts/train_forecast_model.py` (configurable length, default 730 days).
- **Production:** Retrain on your own DB-derived daily series when you have enough history (≥ ~90 days recommended).

## Features

See `app/services/forecast_features.py`: lags (1, 7, 14, 28), rolling means/std (7, 14, 28), day-of-week, day-of-month, month, country holiday flag, payday heuristic.

## Metrics (offline)

Walk-forward folds with MAE, RMSE, MAPE, sMAPE, pinball loss; seasonal-naive and Prophet baselines logged in MLflow for comparison.

## Limitations

- Not financial advice; uncertainty bands are model-based, not calibrated guarantees.
- Sparse transaction history produces weak signal; synthetic demos are for engineering demos, not real SME forecasting without domain validation.

## Intended use

Internal dashboards and portfolio demos; validate on real data before any operational use.

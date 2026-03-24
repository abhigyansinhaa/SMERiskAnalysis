# SME Cashflow & Risk Advisor

Flask + MySQL web app for SMEs to track income/expenses, forecast cashflow with regression, run what-if scenarios, and get grounded LLM explanations and action suggestions.

## Features

- **Auth**: Login/Register
- **Transactions**: CRUD, categories, CSV import
- **Dashboard**: Monthly totals, burn rate, runway, category breakdown, top vendors, alerts
- **Forecast**: Pre-trained Ridge (joblib) over time-series features; 7/14/30 day predictions (train once with `scripts/train_forecast_model.py`)
- **What-If**: Sales ±%, rent change, one-time expense
- **Advisor**: LLM summary + actions (or template fallback)

## Setup

1. Create MySQL database and user (see `scripts/init_db.sql`)
2. Copy `.env.example` to `.env` and configure
3. Install: `pip install -r requirements.txt`
4. Create tables: `python scripts/create_tables.py`
5. Seed: `python scripts/seed_sample.py`
6. Train the forecast Ridge artifact (required for `/forecast` and advisor): `python scripts/train_forecast_model.py`  
   - Writes `models/ridge_forecast.pkl` by default. Override path with `--output` or set `FORECAST_MODEL_PATH` in `.env` if you store the file elsewhere.
7. Run: `python run.py` or `flask run`

## Demo

- Login: `demo@example.com` / `demo123`
- Run `python sample_data/build_harborline_dataset.py` then import **`sample_data/harborline_supply_transactions.csv`** (dates align with today; recommended) or `sample_data/sample_transactions.csv` (minimal)
- See `DEMO_SCRIPT.md` for full demo flow

## Linting

```bash
pip install -r requirements-dev.txt
ruff check .
```

Config: `pyproject.toml` (Ruff: E, F, I, UP, B).

## JSON API (`/api/v1`)

Versioned JSON endpoints for scripts or SPAs. **Authentication** uses the same **Flask-Login session cookie** as the web UI (log in via the browser, or `POST /login` with a client that stores cookies). Unauthenticated requests return `401` with `{"error":"Unauthorized"}` (no HTML redirect).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/me` | Current user `id` and `email` |
| GET | `/api/v1/dashboard` | KPIs, balance, burn, runway, categories, vendors, alerts |
| GET | `/api/v1/transactions` | List transactions (`?type=`, `?month=YYYY-MM`) |
| POST | `/api/v1/transactions` | Create transaction (JSON: `date`, `amount`, `type`, optional `category_id`, `merchant`, `notes`) |
| POST | `/api/v1/forecast/run` | Body: `{"horizon_days": 30}` |
| POST | `/api/v1/forecast/whatif` | Body: `sales_pct_change`, `rent_change`, `one_time_expense` |
| POST | `/api/v1/advisor/summary` | LLM summary + actions |

Legacy JSON routes (`/forecast/run`, `/advisor/summary`, etc.) remain for the existing HTML pages.

```bash
python -m unittest tests.test_api_v1 -v
```

## Tech Stack

- Flask, SQLAlchemy, Flask-Login
- MySQL (PyMySQL)
- scikit-learn (Ridge regression)
- OpenRouter API (optional, for LLM advisor; set `OPENROUTER_API_KEY` in `.env`, and optionally `OPENROUTER_MODEL`, e.g. `openai/gpt-4o-mini`)
- UI: Outfit + Fraunces (Google Fonts), responsive layout

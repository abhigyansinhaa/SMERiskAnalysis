# SME Cashflow & Risk Advisor

Flask + MySQL web app for SMEs to track income/expenses, forecast cashflow with regression, run what-if scenarios, and get grounded LLM explanations and action suggestions.

## Features

- **Auth**: Login/Register
- **Transactions**: CRUD, categories, CSV import
- **Dashboard**: Monthly totals, burn rate, runway, category breakdown, top vendors, alerts
- **Forecast**: Ridge regression over time-series features; 7/14/30 day predictions
- **What-If**: Sales ±%, rent change, one-time expense
- **Advisor**: LLM summary + actions (or template fallback)

## Setup

1. Create MySQL database and user (see `scripts/init_db.sql`)
2. Copy `.env.example` to `.env` and configure
3. Install: `pip install -r requirements.txt`
4. Create tables: `python scripts/create_tables.py`
5. Seed: `python scripts/seed_sample.py`
6. Run: `python run.py` or `flask run`

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

## Tech Stack

- Flask, SQLAlchemy, Flask-Login
- MySQL (PyMySQL)
- scikit-learn (Ridge regression)
- OpenAI API (optional, for LLM advisor)
- UI: Outfit + Fraunces (Google Fonts), responsive layout

---
name: Cashflow Risk Advisor
overview: Build a Flask + MySQL web app for SMEs to track income/expenses, forecast cashflow with regression, run what-if scenarios, and generate grounded LLM explanations and action suggestions.
todos:
  - id: scaffold
    content: Scaffold Flask project structure, config, env handling, and dependency setup.
    status: pending
  - id: db_schema
    content: Implement MySQL schema + migrations/init script + seed sample data.
    status: pending
  - id: auth
    content: Add authentication and user scoping for all queries.
    status: pending
  - id: transactions
    content: Build transactions CRUD UI + CSV import pipeline.
    status: pending
  - id: analytics
    content: Compute dashboard aggregates and risk metrics; persist alerts.
    status: pending
  - id: forecast
    content: Implement regression forecasting + store results + baseline vs scenario what-if.
    status: pending
  - id: advisor
    content: Implement LLM advisor with grounded prompt; add non-LLM fallback narrative.
    status: pending
  - id: polish_demo
    content: Polish UI, add sample CSV, and produce a tight demo script/report checklist.
    status: pending
isProject: false
---

# SME Cashflow & Risk Advisor (Flask + MySQL + HTML/CSS + Regression + LLM)

## Goal

Deliver a web app where a user records or imports transactions, sees cashflow dashboards, gets a short-term forecast and risk alerts, can run what-if scenarios, and receives an LLM-generated explanation that is grounded strictly in their stored data.

## Core features (mark-scoring)

- **Auth + roles**: simple login (single-tenant acceptable if time is tight).
- **Transactions**: add/edit/delete income & expense entries; categories; recurring items.
- **Import**: CSV upload (bank export) to auto-create transactions.
- **Dashboards**: monthly totals, burn rate, net cashflow, category breakdown, top vendors.
- **Forecast (regression)**: predict next 7/14/30 days net cashflow and end-of-month balance.
- **Risk metrics**: runway (days until balance < 0), anomaly flags (spike detection), budget threshold alerts.
- **What-if simulation**: sliders/inputs (sales ±%, rent change, one-time expense) applied to forecast.
- **LLM advisor**: generate an “Executive summary” + “Recommended actions” using only the user’s computed metrics + recent aggregates.

## Architecture

- **Backend**: Flask app with blueprints (`auth`, `transactions`, `analytics`, `advisor`).
- **DB**: MySQL with normalized tables and indexed transaction dates.
- **ML**: lightweight `scikit-learn` regression (Ridge/Lasso) over engineered time-series features; store forecast outputs.
- **LLM**:
  - Primary: API-based (config via environment variables).
  - Fallback: local template-based narrative if no API key.

## Data model (MySQL)

- `users(id, email, password_hash, created_at)`
- `categories(id, user_id, name, type[income|expense])`
- `transactions(id, user_id, date, amount, type, category_id, merchant, notes, created_at)`
- `budgets(id, user_id, category_id, month, amount)`
- `forecasts(id, user_id, horizon_days, as_of_date, predicted_net, predicted_balance, model_name, metrics_json)`
- `alerts(id, user_id, kind, severity, message, created_at, is_read)`

## Key pages (HTML/CSS)

- **Login/Register**
- **Transactions** (table + filters + add form + CSV import)
- **Dashboard** (charts + KPIs + alerts)
- **Forecast & What-if** (baseline vs scenario plot + inputs)
- **Advisor** (LLM summary + links to supporting numbers)

## Endpoints (high-level)

- `GET/POST /login`, `POST /logout`
- `GET/POST /transactions`, `POST /transactions/import`
- `GET /dashboard`
- `GET /forecast`, `POST /forecast/whatif`
- `POST /advisor/summary`

## Regression approach (CPU-friendly)

- Build daily series from transactions: daily_income, daily_expense, daily_net.
- Feature engineering: lag features (1, 7, 14), rolling means, day-of-week, month-to-date totals.
- Model: Ridge regression (stable, fast) to predict next-day net; roll forward to create multi-day forecast.
- Report metrics for viva: train/test split by time, MAE/RMSE on last N days.

## Demo flow (what you show in exam)

1. Import a prepared CSV (or add 10 sample transactions).
2. Dashboard updates (KPIs + category chart + alerts).
3. Run forecast and show runway.
4. Apply what-if (sales -20%, new one-time expense) and compare.
5. Generate Advisor summary (LLM) that cites the computed metrics.

## Deliverables

- Clean UI + working CRUD + forecast + advisor + seeded sample dataset.
- Short report: schema, endpoints, model choice, metrics, screenshots.


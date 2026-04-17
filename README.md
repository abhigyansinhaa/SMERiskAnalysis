# SME Cashflow & Risk Advisor

[![CI](https://img.shields.io/github/actions/workflow/status/abhigyansinhaa/SMERiskAnalysis/ci.yml?branch=main&label=CI)](https://github.com/abhigyansinhaa/SMERiskAnalysis/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Flask + Postgres/MySQL app for SMEs to track income/expenses, forecast cashflow with **LightGBM quantile** models (10th–90th percentile band), run what-if scenarios, and get LLM-backed advice (optional).

## Architecture

```mermaid
flowchart TB
  subgraph clients [Clients]
    Browser[Browser UI]
    APIClient[API clients]
  end
  subgraph app [Flask app]
    Web[Blueprints: auth, transactions, analytics, advisor]
    API["/api/v1 JSON + OpenAPI"]
    ForecastSvc[forecast.py + LightGBM bundle]
  end
  subgraph data [Data]
    DB[(Postgres / MySQL)]
    Models[models/forecast_bundle.pkl]
  end
  Browser --> Web
  APIClient --> API
  Web --> DB
  API --> DB
  ForecastSvc --> Models
  ForecastSvc --> DB
```

## Features

- **Auth:** Register / login (passwords hashed with **Argon2**; legacy Werkzeug hashes upgraded on login).
- **Transactions:** CRUD, categories, CSV import.
- **Dashboard:** Monthly totals, burn rate, runway, categories, vendors, alerts.
- **Forecast:** LightGBM quantile models; sliding-window multi-step rollout; optional Prophet + seasonal-naive baselines in training (`scripts/train_forecast_model.py`).
- **What-if:** Sales ±%, rent change, one-time expense.
- **Advisor:** OpenRouter LLM (optional) or template fallback.
- **API:** `/api/v1` with **Pydantic** request bodies and **Spectree** OpenAPI — Swagger UI at **`/api/v1/docs`** (redirects to `/api/v1/swagger`).

### Why Spectree + Pydantic (not flask-pydantic-spec)

We use **Spectree** with **Pydantic v2** schemas: stable OpenAPI 3 generation, first-class Flask integration, and `@spec.validate(json=Model)` on POST routes without pulling in a second schema library. Functionally equivalent to the “flask-pydantic-spec” route for validation + docs.

## Quick start (Docker)

```bash
cp .env.example .env
# edit SECRET_KEY if needed
make up
# DB is migrated on container start; then:
docker compose exec api python scripts/seed_sample.py
docker compose exec api python scripts/train_forecast_model.py --fast
```

App: `http://localhost:5000` — demo: `demo@example.com` / `demo123` (after `seed_sample`).

### Local (without Docker)

1. Python **3.11+**, Postgres or MySQL (or SQLite for quick dev only).
2. `cp .env.example .env` — set `DATABASE_URL` e.g.  
   `postgresql+psycopg://user:pass@localhost:5432/cashflow_risk`
3. `pip install -r requirements-dev.txt`
4. `alembic upgrade head`
5. `python scripts/seed_sample.py`
6. `python scripts/train_forecast_model.py` (or `--fast` for a quick bundle)
7. `python run.py`

**Synthetic history (~2 years)** for ML demos:

```bash
python scripts/generate_synthetic_data.py
```

## API documentation

- **Swagger UI:** `GET /api/v1/docs` → redirect to Spectree UI.
- **OpenAPI JSON:** served under `/api/v1/` by Spectree (see UI for exact path).

Authentication: **Flask-Login session cookie** (same as the HTML UI). Unauthenticated JSON requests return `401` with `{"error":"Unauthorized"}`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/me` | Current user `id`, `email` |
| GET | `/api/v1/dashboard` | KPIs, balance, burn, runway, … |
| GET | `/api/v1/transactions` | List (`?type=`, `?month=YYYY-MM`) |
| POST | `/api/v1/transactions` | Create transaction (JSON) |
| POST | `/api/v1/forecast/run` | `{"horizon_days": 30}` |
| POST | `/api/v1/forecast/whatif` | Scenario fields |
| POST | `/api/v1/advisor/summary` | LLM summary + actions |

## ML training & MLflow

```bash
python scripts/train_forecast_model.py --days 730
# Artifacts: models/forecast_bundle.pkl, local MLflow under ./mlruns/
```

`--fast` shortens data and folds for CI. See [MODEL_CARD.md](MODEL_CARD.md) for model scope and limitations.

### Baseline metrics (example)

After training, compare **MAPE** in MLflow: `mape_seasonal_naive_last_fold`, `mape_prophet_last_fold`, and per-fold LGBM metrics. Fill your own numbers in the table below when you run locally.

| Model | Fold MAPE (typ.) |
|-------|------------------|
| Seasonal naive (7d) | _run_ |
| Prophet | _run_ |
| LightGBM q50 | _run_ |

## Nightly retrain (optional)

- `scripts/retrain_job.py` — trains a candidate bundle and promotes to `models/forecast_bundle.pkl`.
- Set `ENABLE_SCHEDULER=1` to run APScheduler inside the Flask process (see `app/scheduler.py`).

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest tests/ -v
# Targeted coverage (forecast + analytics services):
python -m pytest tests/ --cov=app/services/forecast --cov=app/services/analytics --cov-report=term-missing
```

See [PERFORMANCE.md](PERFORMANCE.md) for the transaction list N+1 / `joinedload` notes.

## Tech stack

- Flask, SQLAlchemy, Flask-Login, Alembic  
- Postgres (`psycopg`) or MySQL (`PyMySQL`) via `DATABASE_URL`  
- LightGBM, scikit-learn, Prophet, MLflow, holidays  
- Spectree + Pydantic v2, Argon2  

## CV talking points

- Containerized **Flask + Postgres** with **Docker Compose**, **Alembic** migrations, **GitHub Actions** (Ruff + pytest + fast training step).
- **REST API** documented with **OpenAPI/Swagger**, **Pydantic** validation on JSON bodies.
- **LightGBM quantile** forecasting with **walk-forward** evaluation, **Prophet** / **seasonal-naive** baselines, **MLflow** experiment tracking, optional **scheduled retrain**.
- **Performance:** Documented SQL query comparison for eager-loaded categories vs lazy.

## Legacy

- `scripts/init_db.sql` — reference only; prefer **Alembic**.
- `scripts/create_tables.py` — prints deprecation; use `alembic upgrade head`.

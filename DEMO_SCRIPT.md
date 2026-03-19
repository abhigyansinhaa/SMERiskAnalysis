# Cashflow Risk Advisor – Demo Script

## Prerequisites

1. **MySQL** running with database `cashflow_risk` created
2. **Python 3.10+** with dependencies: `pip install -r requirements.txt`
3. **Environment**: Copy `.env.example` to `.env` and set `MYSQL_*` and optionally `OPENAI_API_KEY`

## Setup

```bash
# Create tables (from project root)
python scripts/create_tables.py

# Seed sample data
python scripts/seed_sample.py
```

## Demo Flow (5–7 minutes)

### 1. Login / Register
- Open http://localhost:5000
- Login: `demo@example.com` / `demo123` (or register a new user)

### 2. Import CSV
- Go to **Transactions** → **Import CSV**
- Upload `sample_data/sample_transactions.csv`
- Confirm import count

### 3. Dashboard
- Go to **Dashboard**
- Show KPIs: Monthly Income, Expense, Net, Balance, Burn Rate, Runway
- Show category breakdown and top vendors
- Show alerts (runway, budget, etc.)

### 4. Forecast
- Go to **Forecast**
- Click **Run Forecast (30 days)**
- Show predicted net and balance, MAE/RMSE

### 5. What-If
- Set Sales change: `-20` (for -20%)
- Set One-time expense: `5000`
- Click **Apply What-If**
- Compare baseline vs adjusted net and balance

### 6. Advisor
- Go to **Advisor**
- Click **Generate Summary**
- Show executive summary and recommended actions (LLM or fallback)

## Report Checklist

- [ ] Schema diagram / ER
- [ ] Endpoint list with methods
- [ ] Model choice (Ridge regression) and rationale
- [ ] Train/test split, MAE/RMSE metrics
- [ ] Screenshots: Dashboard, Forecast, What-If, Advisor

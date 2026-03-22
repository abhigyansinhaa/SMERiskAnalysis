# Cashflow Risk Advisor – Demo Script

## Setup

```bash
# Create tables (from project root)
python scripts/create_tables.py

# Seed sample data
python scripts/seed_sample.py
```

## Demo Flow (5–7 minutes)

### 1. Home & login
- Open http://localhost:5000 — **landing page** with product overview; use **Get started** / **Sign in**
- Login: `demo@example.com` / `demo123` (or register a new user)

### 2. Import CSV
- Regenerate dates from **today** (recommended): `python sample_data/build_harborline_dataset.py`
- Go to **Transactions** → **Import CSV**
- Upload **`sample_data/harborline_supply_transactions.csv`** (realistic SME — tests all features) or `sample_data/sample_transactions.csv` (short smoke test)
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

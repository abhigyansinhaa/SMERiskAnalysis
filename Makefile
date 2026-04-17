.PHONY: up down migrate seed test lint train train-fast ci

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	python scripts/seed_sample.py

synthetic:
	python scripts/generate_synthetic_data.py

test:
	python -m pytest tests/ -v

lint:
	ruff check .

train:
	python scripts/train_forecast_model.py

train-fast:
	python scripts/train_forecast_model.py --fast

ci: lint test

"""Deprecated: use Alembic migrations instead.

    alembic upgrade head

Legacy helper (creates tables from models without migration history):
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db  # noqa: E402

if __name__ == "__main__":
    print("Prefer: alembic upgrade head")
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tables created (no Alembic version row). Prefer Alembic for production.")

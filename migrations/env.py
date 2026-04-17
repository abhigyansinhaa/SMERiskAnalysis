"""Alembic environment: uses DATABASE_URL / Flask config."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Ensure .env is loaded before reading DATABASE_URL / MYSQL_* (same as config.py)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app import create_app  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _metadata():
    """Import models (registers tables on metadata). Requires project dependencies."""
    import app.models  # noqa: F401
    from app import db

    return db.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    from config import Config

    return Config().SQLALCHEMY_DATABASE_URI


def run_migrations_offline() -> None:
    target_metadata = _metadata()
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _ = create_app(os.environ.get("FLASK_ENV", "development"))
    target_metadata = _metadata()
    url = get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

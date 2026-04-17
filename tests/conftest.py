"""Pytest fixtures: in-memory SQLite app + tables."""
from __future__ import annotations

import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        u = User(email="test@example.com")
        u.set_password("secret")
        db.session.add(u)
        db.session.commit()
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()

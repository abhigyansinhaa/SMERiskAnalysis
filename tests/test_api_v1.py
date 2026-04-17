"""API v1 smoke tests."""
from __future__ import annotations


def test_me_returns_401_without_session(client):
    rv = client.get("/api/v1/me")
    assert rv.status_code == 401
    assert b"Unauthorized" in rv.data


def test_routes_registered(client):
    rules = {r.rule for r in client.application.url_map.iter_rules()}
    assert "/api/v1/me" in rules
    assert "/api/v1/dashboard" in rules
    assert "/api/v1/transactions" in rules
    assert "/api/v1/forecast/run" in rules
    assert "/api/v1/forecast/whatif" in rules
    assert "/api/v1/advisor/summary" in rules


def test_docs_redirect(client):
    rv = client.get("/api/v1/docs", follow_redirects=False)
    assert rv.status_code in (301, 302, 308)

"""Smoke tests for /api/v1 JSON API (no DB required for unauthenticated checks)."""
import unittest

from app import create_app


class TestApiV1Unauthorized(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_me_returns_401_without_session(self):
        rv = self.client.get("/api/v1/me")
        self.assertEqual(rv.status_code, 401)
        self.assertIn(b"Unauthorized", rv.data)

    def test_dashboard_returns_401_without_session(self):
        rv = self.client.get("/api/v1/dashboard")
        self.assertEqual(rv.status_code, 401)

    def test_routes_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn("/api/v1/me", rules)
        self.assertIn("/api/v1/dashboard", rules)
        self.assertIn("/api/v1/transactions", rules)
        self.assertIn("/api/v1/forecast/run", rules)
        self.assertIn("/api/v1/forecast/whatif", rules)
        self.assertIn("/api/v1/advisor/summary", rules)


if __name__ == "__main__":
    unittest.main()

"""OpenAPI 3 + Swagger UI via Spectree (registered in app factory)."""
from spectree import SpecTree

spec = SpecTree(
    "flask",
    title="SME Cashflow & Risk API",
    version="1.0.0",
    path="/api/v1",
)

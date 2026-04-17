"""Request/response models for /api/v1 (Pydantic v2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ForecastRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horizon_days: int = Field(default=30, ge=1, le=365)


class WhatIfIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales_pct_change: float = 0.0
    rent_change: str | float = 0
    one_time_expense: str | float = 0


class TransactionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str = Field(..., description="YYYY-MM-DD")
    amount: str | float | int = 0
    type: Literal["income", "expense"] = "expense"
    category_id: int | None = None
    merchant: str | None = None
    notes: str | None = None


class MeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    email: str


class ErrorOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    error: str
    detail: Any | None = None

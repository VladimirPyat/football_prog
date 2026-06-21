"""Pydantic schemas for public rounds."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RoundOut(BaseModel):
    id: int
    contest_id: int
    number: int
    deadline: datetime
    status: str
    matches_count: int

    model_config = {"from_attributes": True}

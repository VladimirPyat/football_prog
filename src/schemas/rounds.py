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
    kind: str = "REGULAR"
    supplementary_index: int | None = None
    source_round_numbers: list[int] = []

    model_config = {"from_attributes": True}

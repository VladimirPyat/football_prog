"""Pydantic schemas for contest lifecycle and settings."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContestSettingsOut(BaseModel):
    id: int
    is_locked: bool
    status: str
    paused_at: datetime | None = None
    finished_at: datetime | None = None
    total_teams: int
    matches_per_round: int
    total_rounds: int
    is_round_robin: bool
    rules_json: dict

    model_config = {"from_attributes": True}


class ContestSettingsPatchRequest(BaseModel):
    total_teams: int | None = None
    matches_per_round: int | None = None
    total_rounds: int | None = None
    is_round_robin: bool | None = None
    rules_json: dict | None = None


class ContestLifecycleOut(BaseModel):
    status: str
    paused_at: datetime | None = None
    finished_at: datetime | None = None
    deletable_at: datetime | None = None
    seconds_until_deletable: int | None = None


class ContestDeleteConfirmRequest(BaseModel):
    confirm: Literal["DELETE"]


class ContestDeleteResponse(BaseModel):
    deleted: bool = True
    status: str = "DRAFT"


class ExceptionalTiebreakRequest(BaseModel):
    points: int = Field(ge=0)


class ExceptionalTiebreakResponse(BaseModel):
    user_id: int
    exceptional_tiebreak_points: int

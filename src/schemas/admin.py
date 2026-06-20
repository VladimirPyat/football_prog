"""Pydantic schemas for admin operations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MatchCreateItem(BaseModel):
    team1_id: int
    team2_id: int
    date_time: datetime


class CreateRoundRequest(BaseModel):
    number: int
    deadline: datetime
    matches: list[MatchCreateItem]


class MatchUpdateItem(BaseModel):
    match_id: int | None = None
    team1_id: int | None = None
    team2_id: int | None = None
    date_time: datetime | None = None
    status: str | None = None


class UpdateRoundRequest(BaseModel):
    deadline: datetime | None = None
    matches: list[MatchUpdateItem] | None = None


class MatchResultRequest(BaseModel):
    score1: int = Field(ge=0)
    score2: int = Field(ge=0)
    status: str = "FINISHED"


class MatchStatusPatch(BaseModel):
    status: str


class RoundActionResponse(BaseModel):
    round_id: int | None = None
    status: str | None = None
    users_scored: int | None = None


class MatchResultResponse(BaseModel):
    success: bool = True
    round_id: int


class MatchStatusResponse(BaseModel):
    success: bool = True
    recalculation_triggered: bool = False


class RecalculateResponse(BaseModel):
    recalculated_rounds: int

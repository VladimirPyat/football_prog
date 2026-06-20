"""Pydantic schemas for predictions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    match_id: int
    score1: int = Field(ge=0)
    score2: int = Field(ge=0)


class PredictionBatchRequest(BaseModel):
    predictions: list[PredictionItem]


class PredictionBatchResponse(BaseModel):
    success: bool = True
    saved_count: int


class MatchPredictionOut(BaseModel):
    match_id: int
    score1: int | None = None
    score2: int | None = None


class PredictionEntryOut(BaseModel):
    user_id: int
    user_name: str | None = None
    submitted: bool
    predictions: list[MatchPredictionOut] | None = None


class RoundPredictionsView(BaseModel):
    round_id: int
    deadline_passed: bool
    matches: list[dict]
    entries: list[PredictionEntryOut]

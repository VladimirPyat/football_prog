"""Pydantic schemas for contest lifecycle and settings."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContestOut(BaseModel):
    id: int
    name: str
    slug: str | None = None
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


class CreateContestRequest(BaseModel):
    name: str
    slug: str | None = None
    rules_json: dict | None = None
    total_teams: int | None = None
    matches_per_round: int | None = None
    total_rounds: int | None = None
    is_round_robin: bool | None = None


class ContestPatchRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    total_teams: int | None = None
    matches_per_round: int | None = None
    total_rounds: int | None = None
    is_round_robin: bool | None = None
    rules_json: dict | None = None


# Legacy alias for 1.3 shims
ContestSettingsOut = ContestOut
ContestSettingsPatchRequest = ContestPatchRequest


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
    status: str = "DELETED"


class DeletedContestOut(BaseModel):
    id: int
    name: str
    deleted_at: datetime
    restore_available: bool


class ExceptionalTiebreakRequest(BaseModel):
    points: int = Field(ge=0)


class ExceptionalTiebreakResponse(BaseModel):
    contest_id: int | None = None
    user_id: int
    exceptional_tiebreak_points: int


class LogoUploadResponse(BaseModel):
    logo_url: str


class TeamOut(BaseModel):
    id: int
    contest_id: int
    name: str
    short_name: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class TeamCreateRequest(BaseModel):
    name: str
    short_name: str
    logo_url: str | None = None


class TeamPatchRequest(BaseModel):
    name: str | None = None
    short_name: str | None = None
    logo_url: str | None = None


class ParticipantOut(BaseModel):
    user_id: int
    login: str
    first_name: str
    last_name: str
    email: str | None = None
    status: str
    exceptional_tiebreak_points: int


class ParticipantCreateRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    login: str | None = None


class ParticipantInviteOut(BaseModel):
    user_id: int
    login: str
    temp_password: str
    status: str
    setup_url: str


class ContestRestoreResponse(BaseModel):
    restored: bool = True


class FreeTourMatchItem(BaseModel):
    match_id: int
    new_date_time: datetime


class FreeTourRequest(BaseModel):
    deadline: datetime
    matches: list[FreeTourMatchItem]


class UserContestOut(BaseModel):
    id: int
    name: str
    status: str
    participant_status: str
    role: str
    slug: str | None = None


class PublicContestOut(BaseModel):
    id: int
    name: str
    status: str
    slug: str | None = None

    model_config = {"from_attributes": True}

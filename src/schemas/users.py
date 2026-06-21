"""Pydantic schemas for admin user management."""

from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.auth import UserOut


class CreateSupervisorRequest(BaseModel):
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    is_temp_password: bool = False


class CreateSupervisorResponse(BaseModel):
    user: UserOut

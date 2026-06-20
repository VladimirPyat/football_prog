"""Pydantic schemas for authentication."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_temp_password: bool


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: int
    login: str
    role: str
    first_name: str
    last_name: str
    is_temp_password: bool

    model_config = {"from_attributes": True}

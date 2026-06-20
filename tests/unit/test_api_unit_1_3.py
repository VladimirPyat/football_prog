"""Unit tests for Stage 1.3: security, JWT, schemas, RBAC."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.deps import RoleChecker
from core.security import create_access_token, decode_access_token, hash_password, verify_password
from database.models import User, UserRole
from schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
from schemas.contest import ContestDeleteConfirmRequest, ExceptionalTiebreakRequest
from schemas.predictions import PredictionBatchRequest, PredictionItem


class TestSecurity:
    def test_hash_and_verify_password(self) -> None:
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_roundtrip(self) -> None:
        token = create_access_token({"sub": "42", "role": "USER"}, expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "USER"

    def test_jwt_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            decode_access_token("not.a.valid.token")


class TestSchemas:
    def test_login_request_valid(self) -> None:
        req = LoginRequest(login="user1", password="pass")
        assert req.login == "user1"

    def test_token_response(self) -> None:
        resp = TokenResponse(access_token="abc", is_temp_password=False)
        assert resp.token_type == "bearer"

    def test_change_password_request(self) -> None:
        req = ChangePasswordRequest(old_password="old", new_password="new")
        assert req.new_password == "new"

    def test_user_out_from_attributes(self) -> None:
        user = User(
            id=1,
            login="u",
            password_hash="h",
            role=UserRole.USER,
            first_name="A",
            last_name="B",
            is_temp_password=False,
        )
        out = UserOut.model_validate(user)
        assert out.role == "USER"

    def test_prediction_batch_requires_scores(self) -> None:
        with pytest.raises(ValidationError):
            PredictionBatchRequest(predictions=[PredictionItem(match_id=1, score1=-1, score2=0)])

    def test_exceptional_tiebreak_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExceptionalTiebreakRequest(points=-1)

    def test_delete_confirm_must_be_delete(self) -> None:
        req = ContestDeleteConfirmRequest(confirm="DELETE")
        assert req.confirm == "DELETE"


class TestRoleChecker:
    @pytest.mark.asyncio
    async def test_allowed_role_passes(self) -> None:
        checker = RoleChecker(UserRole.ADMIN)
        user = User(
            id=1,
            login="admin",
            password_hash="h",
            role=UserRole.ADMIN,
            first_name="A",
            last_name="B",
            is_temp_password=False,
        )
        result = await checker(user)
        assert result.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_forbidden_role_raises_403(self) -> None:
        checker = RoleChecker(UserRole.ADMIN)
        user = User(
            id=2,
            login="user",
            password_hash="h",
            role=UserRole.USER,
            first_name="U",
            last_name="S",
            is_temp_password=False,
        )
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403

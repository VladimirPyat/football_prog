"""Stage 1.5: AppError → HTTP mapping and notify_admin stub."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest_plugins = ["tests.api.conftest"]

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.exceptions import (  # noqa: E402
    ContestLockedError,
    ContestRuleError,
    GracePeriodError,
    IllegalTransitionError,
    NotFoundError,
    ScoreOutOfRangeError,
    ValidationError,
)
from tests.api.conftest import api_login, auth_header, contest_url  # noqa: E402


async def _app_error_response(exc: Exception):
    from api.error_handlers import app_error_handler  # noqa: PLC0415
    from starlette.requests import Request  # noqa: PLC0415

    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    return await app_error_handler(request, exc)


def test_exc_classes_metadata():
    """[EXC-META] Exception HTTP status and codes."""
    assert NotFoundError("x").http_status == 404
    assert ScoreOutOfRangeError("x").http_status == 422
    assert IllegalTransitionError("x").http_status == 409
    assert GracePeriodError("x").http_status == 400
    assert ContestLockedError("x").code == "CONTEST_LOCKED"
    assert ValidationError("x").code == "VALIDATION_ERROR"
    err = ContestRuleError("дедлайн", code="DEADLINE_PASSED")
    assert err.code == "DEADLINE_PASSED"
    assert err.http_status == 403


@pytest.mark.asyncio
async def test_exc_app_error_handler_json():
    """[EXC-HANDLER] AppError returns detail + code JSON."""
    response = await _app_error_response(NotFoundError("Конкурс не найден"))
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["code"] == "NOT_FOUND"
    assert "не найден" in body["detail"].lower()


@pytest.mark.asyncio
async def test_exc_404_not_found():
    """[EXC-404] NotFoundError → 404 NOT_FOUND with Russian detail."""
    response = await _app_error_response(NotFoundError("Конкурс 99999 не найден"))
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["code"] == "NOT_FOUND"
    assert "не найден" in body["detail"].lower()


@pytest.mark.asyncio
async def test_exc_403_rule_deadline():
    """[EXC-403-RULE] ContestRuleError / deadline → 403 with code."""
    exc = ContestRuleError(
        "Дедлайн тура истёк — прогнозы больше не принимаются",
        code="DEADLINE_PASSED",
    )
    response = await _app_error_response(exc)
    assert response.status_code == 403
    body = json.loads(response.body)
    assert body["code"] == "DEADLINE_PASSED"
    assert "дедлайн" in body["detail"].lower()


@pytest.mark.asyncio
async def test_exc_422_score_out_of_range():
    """[EXC-422-SCORE] ScoreOutOfRangeError → 422 SCORE_OUT_OF_RANGE."""
    response = await _app_error_response(
        ScoreOutOfRangeError("Счёт 99 вне диапазона [0, 20] (score1)")
    )
    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["code"] == "SCORE_OUT_OF_RANGE"


@pytest.mark.asyncio
async def test_exc_409_illegal_transition():
    """[EXC-409-TRANS] IllegalTransitionError → 409 ILLEGAL_TRANSITION."""
    response = await _app_error_response(
        IllegalTransitionError("Недопустимый переход статуса: DRAFT → PAUSED")
    )
    assert response.status_code == 409
    body = json.loads(response.body)
    assert body["code"] == "ILLEGAL_TRANSITION"
    assert "недопустимый" in body["detail"].lower()


@pytest.mark.asyncio
async def test_exc_400_grace_period():
    """[EXC-400-GRACE] GracePeriodError → 400 GRACE_PERIOD_ACTIVE."""
    response = await _app_error_response(
        GracePeriodError("Период ожидания удаления ещё не истёк")
    )
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["code"] == "GRACE_PERIOD_ACTIVE"


@pytest.mark.asyncio
async def test_exc_403_contest_locked():
    """[EXC-403-LOCK] ContestLockedError → 403 CONTEST_LOCKED."""
    response = await _app_error_response(
        ContestLockedError("Конкурс заблокирован — изменение структуры запрещено")
    )
    assert response.status_code == 403
    body = json.loads(response.body)
    assert body["code"] == "CONTEST_LOCKED"
    assert "заблокирован" in body["detail"].lower()


@pytest.mark.asyncio
async def test_exc_400_validation():
    """[EXC-400-VAL] ValidationError → 400 VALIDATION_ERROR."""
    response = await _app_error_response(
        ValidationError("Неполный пакет прогнозов — заполните все матчи тура")
    )
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_exc_500_unhandled_notify_admin(caplog):
    """[EXC-500-UNHANDLED] Unhandled exception → 500 + notify_admin + ERROR log."""
    import logging
    from unittest.mock import AsyncMock, patch

    from starlette.requests import Request

    from api.error_handlers import unhandled_exception_handler

    caplog.set_level(logging.ERROR, logger="api.error_handlers")

    scope = {"type": "http", "method": "GET", "path": "/probe", "headers": []}
    request = Request(scope)

    with patch("api.error_handlers.notify_admin", new_callable=AsyncMock) as mock_notify:
        response = await unhandled_exception_handler(request, RuntimeError("probe failure"))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["code"] == "INTERNAL_ERROR"
    assert "Внутренняя ошибка" in body["detail"]
    mock_notify.assert_awaited_once()
    assert any(r.levelname == "ERROR" for r in caplog.records)


@pytest.mark.asyncio
async def test_exc_get_contest_404_not_500(loaded_contest_api):
    """[EXC-GET-CONTEST-404] GET missing contest as SUPERVISOR → 404 not 500."""
    client, _, _ = loaded_contest_api
    sup = await api_login(client, "supervisor_api")
    resp = await client.get(contest_url(99999, ""), headers=auth_header(sup))
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body.get("code") == "NOT_FOUND"
    assert "detail" in body

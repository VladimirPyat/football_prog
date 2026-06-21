"""Centralized FastAPI exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions import AppError, CriticalError
from services.notification_service import notify_admin

logger = logging.getLogger(__name__)

_GENERIC_500_DETAIL = "Внутренняя ошибка сервера"


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.http_status >= 500:
        logger.error(
            "AppError %s path=%s detail=%s",
            exc.code,
            request.url.path,
            exc.message,
        )
        if isinstance(exc, CriticalError):
            await notify_admin(
                "critical_error",
                detail=exc.message,
                context={"path": request.url.path, "code": exc.code},
            )
    else:
        logger.warning(
            "AppError %s path=%s status=%s detail=%s",
            exc.code,
            request.url.path,
            exc.http_status,
            exc.message,
        )
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": exc.message, "code": exc.code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        detail = exc.detail
        if not isinstance(detail, str):
            detail = str(detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    if isinstance(exc, RequestValidationError):
        raise exc
    logger.exception("Unhandled exception path=%s", request.url.path)
    await notify_admin(
        "unhandled_exception",
        detail=str(exc),
        context={"path": request.url.path, "type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": _GENERIC_500_DETAIL, "code": "INTERNAL_ERROR"},
    )

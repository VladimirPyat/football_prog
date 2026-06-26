"""Domain exception hierarchy for HTTP mapping and internal error policy."""

from __future__ import annotations


class AppError(Exception):
    """Domain error mapped to HTTP by error_handlers."""

    http_status: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"


class ValidationError(AppError):
    http_status = 400
    code = "VALIDATION_ERROR"


class ScoreOutOfRangeError(AppError):
    http_status = 422
    code = "SCORE_OUT_OF_RANGE"


class ContestRuleError(AppError):
    """Contest business rule violation (403).

    Known codes include PARTICIPANT_NOT_ENROLLED and PARTICIPANT_NOT_ACCEPTED
    (prediction submit when user is not an accepted participant).
    """

    http_status = 403
    code = "CONTEST_RULE_VIOLATION"


class ContestLockedError(AppError):
    http_status = 403
    code = "CONTEST_LOCKED"


class GracePeriodError(AppError):
    http_status = 400
    code = "GRACE_PERIOD_ACTIVE"


class ContestNotPausedError(AppError):
    http_status = 403
    code = "CONTEST_NOT_PAUSED"


class ContestDeleteDisabledError(AppError):
    http_status = 403
    code = "CONTEST_DELETE_DISABLED"


class IllegalTransitionError(AppError):
    http_status = 409
    code = "ILLEGAL_TRANSITION"


class ConflictError(AppError):
    http_status = 409
    code = "CONFLICT"


class PasswordSetupRequiredError(AppError):
    http_status = 403
    code = "PASSWORD_SETUP_REQUIRED"


class SnapshotNotFoundError(AppError):
    http_status = 404
    code = "SNAPSHOT_NOT_FOUND"


class SnapshotExpiredError(AppError):
    http_status = 410
    code = "SNAPSHOT_EXPIRED"


class CriticalError(AppError):
    http_status = 500
    code = "INTERNAL_ERROR"


class RecoverableError(Exception):
    """Non-fatal data issue; caller applies fallback. Never mapped to HTTP directly."""

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(message)

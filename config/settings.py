"""Application configuration.

**Source of truth for defaults:** this module (committed to git, no secrets).

**``.env``** (gitignored; template: ``.env.example``) — secrets and deployment-specific
values only: database URL, JWT signing key, bootstrap passwords, ``APP_MODE``.

``APP_MODE`` selects a preset bundle (URLs, CORS, database driver defaults) so the
server ``.env`` survives ``git pull`` without being overwritten by repo defaults.

See ``manuals/CONFIG.md`` for the full reference.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self, TypedDict

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTEST_DEFAULTS_PATH = PROJECT_ROOT / "config" / "contest_defaults.json"

AppMode = Literal["local", "web_dev", "web_prod"]


class ModePreset(TypedDict):
    database_url: str
    frontend_base_url: str
    cors_origins: list[str]
    enforce_password_setup: bool
    contest_allow_instant_delete: bool
    log_to_file: bool


def resolve_app_mode_preset(
    app_mode: AppMode,
    *,
    public_frontend_url: str | None = None,
    postgres_password: str | None = None,
) -> ModePreset:
    """Return explicit settings for the given ``APP_MODE``.

    Each branch lists every mode-controlled field in one place.
    ``DATABASE_URL`` in the process environment always overrides ``database_url``.
    """
    if app_mode == "local":
        preset: ModePreset = {
            "database_url": "sqlite+aiosqlite:///./football.db",
            "frontend_base_url": "http://127.0.0.1:3000",
            "cors_origins": ["*"],
            "enforce_password_setup": True,
            "contest_allow_instant_delete": False,
            "log_to_file": True,
        }

    elif app_mode == "web_dev":
        frontend_base_url = (public_frontend_url or "http://localhost:3000").strip().rstrip("/")
        preset = {
            "database_url": "sqlite+aiosqlite:///./data/football.db",
            "frontend_base_url": frontend_base_url,
            "cors_origins": [frontend_base_url],
            "enforce_password_setup": True,
            "contest_allow_instant_delete": False,
            "log_to_file": True,
        }

    elif app_mode == "web_prod":
        if not public_frontend_url or not public_frontend_url.strip():
            msg = "PUBLIC_FRONTEND_URL is required when APP_MODE=web_prod"
            raise ValueError(msg)
        frontend_base_url = public_frontend_url.strip().rstrip("/")
        db_password = postgres_password or "football"
        preset = {
            "database_url": (
                f"postgresql+asyncpg://football:{db_password}@db:5432/football"
            ),
            "frontend_base_url": frontend_base_url,
            "cors_origins": [frontend_base_url],
            "enforce_password_setup": True,
            "contest_allow_instant_delete": False,
            "log_to_file": True,
        }

    else:
        msg = f"Unknown APP_MODE: {app_mode!r}"
        raise ValueError(msg)

    if "DATABASE_URL" in os.environ:
        preset["database_url"] = os.environ["DATABASE_URL"]

    return preset


def _env_bool(name: str) -> bool | None:
    if name not in os.environ:
        return None
    return os.environ[name].strip().lower() in {"true", "1", "yes"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Deployment mode (override via .env on each host) ─────────────────────
    app_mode: AppMode = "local"
    public_frontend_url: str | None = None
    public_api_url: str | None = None
    postgres_password: str | None = None

    # ── Secrets & deployment (override via .env) ───────────────────────────
    database_url: str = "sqlite+aiosqlite:///./football.db"
    jwt_secret_key: str = "dev-secret-change-in-production"

    seed_support_password: str | None = None
    seed_support_password_hash: str | None = None
    seed_supervisor_password: str | None = None
    seed_supervisor_password_hash: str | None = None

    # ── Bootstrap identities (non-secret; override rarely) ───────────────────
    seed_support_login: str = "support"
    seed_support_first_name: str = "Support"
    seed_support_last_name: str = "User"
    seed_supervisor_login: str = "supervisor"
    seed_supervisor_first_name: str = "Supervisor"
    seed_supervisor_last_name: str = "User"

    # ── JWT (non-secret parameters) ──────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # ── HTTP / CORS ─────────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    # ── Auth & invite links ───────────────────────────────────────────────────
    frontend_base_url: str = "http://127.0.0.1:3000"
    setup_token_expire_hours: int = 72
    enforce_password_setup: bool = True

    # ── Contest lifecycle ────────────────────────────────────────────────────
    contest_delete_grace_seconds: int = 10
    contest_delete_enabled: bool = True
    contest_allow_instant_delete: bool = False
    supervisor_training_mode: bool = False
    contest_restore_window_seconds: int = 86400
    # Hard-delete soft-deleted contests after this many seconds (default 30 days).
    contest_purge_retention_seconds: int = 2_592_000

    # ── HTTP caching (public leaderboard/results) ────────────────────────────
    cache_max_age_seconds: int = 300
    cache_stale_while_revalidate_seconds: int = 60

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file: Path = PROJECT_ROOT / "logs" / "app.log"
    log_archive_dir: Path = PROJECT_ROOT / "logs" / "archive"
    log_archive_max_bytes: int = 5_242_880  # 5 MiB
    log_archive_interval_days: int = 7
    auth_log_file: Path = PROJECT_ROOT / "logs" / "auth.log"

    # ── Datetime (API / DB) ───────────────────────────────────────────────────
    # All TIMESTAMPTZ values are stored and compared in this zone (UTC only today).
    api_timestamp_timezone: str = "UTC"

    # ── Paths & seed data ────────────────────────────────────────────────────
    contest_defaults_path: Path = DEFAULT_CONTEST_DEFAULTS_PATH
    upload_dir: Path = PROJECT_ROOT / "uploads"
    static_assets_dir: Path = PROJECT_ROOT / "static" / "assets"
    static_url_prefix: str = "/static"

    # ── Team logos ───────────────────────────────────────────────────────────
    max_logo_bytes: int = 2_097_152  # 2 MiB
    team_logo_target_px: int = 64
    default_team_logo_url: str = "/static/assets/default-team-logo.jpg"

    @model_validator(mode="after")
    def apply_app_mode_preset(self) -> Self:
        preset = resolve_app_mode_preset(
            self.app_mode,
            public_frontend_url=self.public_frontend_url,
            postgres_password=self.postgres_password,
        )
        for field, value in preset.items():
            object.__setattr__(self, field, value)

        # Explicit .env overrides win over mode presets (same rule as DATABASE_URL).
        enforce = _env_bool("ENFORCE_PASSWORD_SETUP")
        if enforce is not None:
            object.__setattr__(self, "enforce_password_setup", enforce)
        instant_delete = _env_bool("CONTEST_ALLOW_INSTANT_DELETE")
        if instant_delete is not None:
            object.__setattr__(self, "contest_allow_instant_delete", instant_delete)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application configuration.

**Source of truth for defaults:** this module (committed to git, no secrets).

**``.env``** (gitignored; template: ``.env.example``) — secrets and deployment-specific
values only: database URL, JWT signing key, bootstrap passwords.

Any field *can* be overridden via environment variable (pydantic-settings maps
``log_level`` → ``LOG_LEVEL``). Optional tuning (logging, CORS, cache, paths) uses
defaults here — do not duplicate them in ``.env.example``.

See ``manuals/CONFIG.md`` for the full reference.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTEST_DEFAULTS_PATH = PROJECT_ROOT / "docs" / "test_data" / "config" / "contest_defaults.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Secrets & deployment (override via .env) ───────────────────────────
    database_url: str = "sqlite+aiosqlite:///./football.db"
    jwt_secret_key: str = "dev-secret-change-in-production"

    seed_admin_password: str | None = None
    seed_admin_password_hash: str | None = None
    seed_supervisor_password: str | None = None
    seed_supervisor_password_hash: str | None = None
    seed_demo_user_password: str | None = "user"

    # ── Bootstrap identities (non-secret; override rarely) ───────────────────
    seed_admin_login: str = "admin"
    seed_admin_first_name: str = "Admin"
    seed_admin_last_name: str = "User"
    seed_supervisor_login: str = "supervisor"
    seed_supervisor_first_name: str = "Supervisor"
    seed_supervisor_last_name: str = "User"
    seed_demo_user_login: str = "user"
    seed_demo_user_first_name: str = "Demo"
    seed_demo_user_last_name: str = "User"

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
    log_file: Path = PROJECT_ROOT / "app.log"
    log_archive_dir: Path = PROJECT_ROOT / "logs" / "archive"
    log_archive_max_bytes: int = 5_242_880  # 5 MiB
    log_archive_interval_days: int = 7

    # ── Paths & seed data ────────────────────────────────────────────────────
    contest_defaults_path: Path = DEFAULT_CONTEST_DEFAULTS_PATH
    upload_dir: Path = PROJECT_ROOT / "uploads"
    static_assets_dir: Path = PROJECT_ROOT / "static" / "assets"
    static_url_prefix: str = "/static"

    # ── Team logos ───────────────────────────────────────────────────────────
    max_logo_bytes: int = 2_097_152  # 2 MiB
    team_logo_target_px: int = 64
    default_team_logo_url: str = "/static/assets/default-team-logo.jpg"


@lru_cache
def get_settings() -> Settings:
    return Settings()

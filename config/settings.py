from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTEST_DEFAULTS_PATH = PROJECT_ROOT / "docs" / "test_data" / "config" / "contest_defaults.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./football.db"
    contest_defaults_path: Path = DEFAULT_CONTEST_DEFAULTS_PATH
    seed_admin_login: str = "admin"
    seed_admin_password: str | None = None
    seed_admin_password_hash: str | None = None
    seed_admin_first_name: str = "Admin"
    seed_admin_last_name: str = "User"

    seed_supervisor_login: str | None = None
    seed_supervisor_password: str | None = None
    seed_supervisor_password_hash: str | None = None
    seed_supervisor_first_name: str = "Supervisor"
    seed_supervisor_last_name: str = "User"

    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["*"]

    contest_delete_grace_seconds: int = 10
    contest_delete_enabled: bool = True
    contest_allow_instant_delete: bool = False

    cache_max_age_seconds: int = 300
    cache_stale_while_revalidate_seconds: int = 60

    log_level: str = "INFO"

    # Team logos — target 64×64 px square after upload (center-crop)
    upload_dir: Path = PROJECT_ROOT / "uploads"
    static_assets_dir: Path = PROJECT_ROOT / "static" / "assets"
    static_url_prefix: str = "/static"
    max_logo_bytes: int = 2_097_152  # 2 MiB
    team_logo_target_px: int = 64
    default_team_logo_url: str = "/static/assets/default-team-logo.jpg"


@lru_cache
def get_settings() -> Settings:
    return Settings()

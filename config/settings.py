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
    seed_admin_password_hash: str = "dev-only-placeholder-hash"
    seed_admin_first_name: str = "Admin"
    seed_admin_last_name: str = "User"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()

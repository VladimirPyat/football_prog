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


@lru_cache
def get_settings() -> Settings:
    return Settings()

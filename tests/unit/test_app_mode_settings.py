"""Unit tests for APP_MODE configuration presets."""

from __future__ import annotations

import pytest
from config.settings import Settings, get_settings, resolve_app_mode_preset
from pydantic import ValidationError


class TestResolveAppModePreset:
    def test_local_preset(self) -> None:
        preset = resolve_app_mode_preset("local")
        assert preset["database_url"] == "sqlite+aiosqlite:///./football.db"
        assert preset["cors_origins"] == ["*"]
        assert preset["frontend_base_url"] == "http://127.0.0.1:3000"

    def test_web_dev_preset_uses_sqlite(self) -> None:
        preset = resolve_app_mode_preset("web_dev")
        assert preset["database_url"] == "sqlite+aiosqlite:///./data/football.db"
        assert preset["frontend_base_url"] == "http://localhost:3000"
        assert preset["cors_origins"] == ["http://localhost:3000"]

    def test_web_prod_preset_requires_frontend_url(self) -> None:
        with pytest.raises(ValueError, match="PUBLIC_FRONTEND_URL"):
            resolve_app_mode_preset("web_prod")

    def test_web_prod_preset_builds_postgres_url(self) -> None:
        preset = resolve_app_mode_preset(
            "web_prod",
            public_frontend_url="https://app.example.com",
            postgres_password="secret",
        )
        assert preset["database_url"] == "postgresql+asyncpg://football:secret@db:5432/football"
        assert preset["cors_origins"] == ["https://app.example.com"]


class TestAppModeSettings:
    def test_local_mode_keeps_sqlite_and_wildcard_cors(self) -> None:
        settings = Settings(app_mode="local")
        assert settings.database_url == "sqlite+aiosqlite:///./football.db"
        assert settings.cors_origins == ["*"]
        assert settings.frontend_base_url == "http://127.0.0.1:3000"

    def test_web_dev_uses_sqlite_in_data_dir(self) -> None:
        settings = Settings(app_mode="web_dev")
        assert settings.database_url == "sqlite+aiosqlite:///./data/football.db"
        assert settings.frontend_base_url == "http://localhost:3000"
        assert settings.cors_origins == ["http://localhost:3000"]

    def test_web_dev_honors_public_urls(self) -> None:
        settings = Settings(
            app_mode="web_dev",
            public_frontend_url="https://dev.example.com/",
            public_api_url="https://api-dev.example.com",
        )
        assert settings.frontend_base_url == "https://dev.example.com"
        assert settings.cors_origins == ["https://dev.example.com"]

    def test_web_prod_requires_public_frontend_url(self) -> None:
        with pytest.raises(ValidationError, match="PUBLIC_FRONTEND_URL"):
            Settings(app_mode="web_prod")

    def test_web_prod_applies_postgres(self) -> None:
        settings = Settings(
            app_mode="web_prod",
            public_frontend_url="https://app.example.com",
            postgres_password="secret",
        )
        assert settings.database_url == "postgresql+asyncpg://football:secret@db:5432/football"
        assert settings.enforce_password_setup is True
        assert settings.contest_allow_instant_delete is False

    def test_database_url_env_overrides_mode_preset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        custom = "postgresql+asyncpg://user:pass@db.example.com:5432/football"
        monkeypatch.setenv("DATABASE_URL", custom)
        settings = Settings(
            app_mode="web_prod",
            public_frontend_url="https://app.example.com",
        )
        assert settings.database_url == custom

    def test_get_settings_cache_can_be_cleared(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.app_mode in ("local", "web_dev", "web_prod")

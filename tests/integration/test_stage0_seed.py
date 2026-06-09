"""Stage 0 integration tests for seed script and contest_settings population."""

import json
import pytest
import pytest_asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.base import Base
from database.models import ContestSettings
from scripts.seed import build_rules_json, load_contest_defaults, run_seed

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = PROJECT_ROOT / "docs" / "test_data" / "config" / "contest_defaults.json"


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    db_path = tmp_path / "seed_test.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    await run_seed(database_url=database_url, defaults_path=DEFAULTS_PATH)
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory, engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_contest_settings_matches_defaults(seeded_db):
    """[STAGE0-SEED-01] rules_json and structural columns match contest_defaults.json."""
    session_factory, _ = seeded_db
    defaults = load_contest_defaults(DEFAULTS_PATH)
    expected_rules = build_rules_json(defaults)
    structure = defaults["contest_structure"]

    async with session_factory() as session:
        settings = await session.scalar(select(ContestSettings).limit(1))
        assert settings is not None
        assert settings.total_teams == structure["total_teams"]
        assert settings.matches_per_round == structure["matches_per_round"]
        assert settings.total_rounds == structure["total_rounds"]
        assert settings.is_round_robin == structure["is_round_robin"]
        assert settings.rules_json == expected_rules


@pytest.mark.asyncio
async def test_seed_rules_json_excludes_meta_only_fields(seeded_db):
    """[STAGE0-SEED-02] rules_json stores contest payload, not _meta from defaults file."""
    session_factory, _ = seeded_db
    defaults = load_contest_defaults(DEFAULTS_PATH)

    async with session_factory() as session:
        settings = await session.scalar(select(ContestSettings).limit(1))
        assert settings is not None
        assert "_meta" not in settings.rules_json
        assert settings.rules_json["scoring_rules"] == defaults["scoring_rules"]
        assert settings.rules_json["tiebreakers"] == defaults["tiebreakers"]
        assert settings.rules_json["constraints"] == defaults["constraints"]
        assert settings.rules_json["contest_structure"] == defaults["contest_structure"]

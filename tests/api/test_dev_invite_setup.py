"""Stage 1.12 — dev_invite_setup.py CLI helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.api.conftest import API_PREFIX
from tests.api.stage_112_helpers import (
    NEW_SECURE_PASSWORD,
    create_draft_contest,
    invite_participant,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "dev_invite_setup.py"


def _run_dev_script(db_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "ENFORCE_PASSWORD_SETUP": "true",
        "SUPERVISOR_TRAINING_MODE": "true",
        "CONTEST_DELETE_GRACE_SECONDS": "0",
        "CONTEST_RESTORE_WINDOW_SECONDS": "3600",
        "FRONTEND_BASE_URL": "http://127.0.0.1:3000",
    }
    return subprocess.run(
        [sys.executable, str(DEV_SCRIPT), *args],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.asyncio
async def test_dev_list_pending(stage_112_api):
    """[DEV-LIST-PENDING] list-pending shows contest id and pending count."""
    client, _, db_url = stage_112_api
    cid, h = await create_draft_contest(client)
    await invite_participant(client, cid, h, email="list1@example.com", login="list1_user")
    await invite_participant(client, cid, h, email="list2@example.com", login="list2_user")

    proc = _run_dev_script(db_url, "list-pending")
    assert proc.returncode == 0, proc.stderr
    assert f"{cid}\t2\t" in proc.stdout


@pytest.mark.asyncio
async def test_dev_get_unconfirmed(stage_112_api, tmp_path):
    """[DEV-GET-UNCONFIRMED] TSV export with header and PENDING rows."""
    client, _, db_url = stage_112_api
    cid, h = await create_draft_contest(client)
    await invite_participant(client, cid, h, email="dev1@example.com", login="dev1_user")
    await invite_participant(client, cid, h, email="dev2@example.com", login="dev2_user")

    out = tmp_path / "dev_unconfirmed.tsv"
    tokens = tmp_path / ".tokens"
    proc = _run_dev_script(
        db_url,
        "get-unconfirmed",
        "--contest-id",
        str(cid),
        "--out",
        str(out),
        "--links-out",
        str(tokens),
    )
    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert text.startswith("user_id\tcontest_id\temail\tlogin\n")
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("user_id")]
    assert len(lines) == 2
    assert tokens.exists()


@pytest.mark.asyncio
async def test_dev_confirm_list(stage_112_api, tmp_path):
    """[DEV-CONFIRM-LIST] confirm-list accepts uncommented TSV rows only."""
    client, _, db_url = stage_112_api
    cid, h = await create_draft_contest(client)
    a = await invite_participant(client, cid, h, email="lista@example.com", login="lista_user")
    b = await invite_participant(client, cid, h, email="listb@example.com", login="listb_user")

    out = tmp_path / "dev_unconfirmed.tsv"
    out.write_text(
        "user_id\tcontest_id\temail\tlogin\n"
        f"{a['user_id']}\t{cid}\tlista@example.com\tlista_user\n"
        f"# {b['user_id']}\t{cid}\tlistb@example.com\tlistb_user\n",
        encoding="utf-8",
    )
    proc = _run_dev_script(
        db_url,
        "confirm-list",
        "--file",
        str(out),
        "--password",
        NEW_SECURE_PASSWORD,
    )
    assert proc.returncode == 0, proc.stderr

    parts = await client.get(f"{API_PREFIX}/contests/{cid}/participants", headers=h)
    statuses = {p["user_id"]: p["status"] for p in parts.json()}
    assert statuses[a["user_id"]] == "ACCEPTED"
    assert statuses[b["user_id"]] == "PENDING"

    again = _run_dev_script(
        db_url,
        "confirm-list",
        "--file",
        str(out),
        "--password",
        NEW_SECURE_PASSWORD,
    )
    assert again.returncode == 0, again.stderr


@pytest.mark.asyncio
async def test_dev_confirm_all(stage_112_api):
    """[DEV-CONFIRM-ALL] confirm-all accepts all PENDING temp users."""
    client, _, db_url = stage_112_api
    cid, h = await create_draft_contest(client)
    await invite_participant(client, cid, h, email="all1@example.com", login="all1_user")
    await invite_participant(client, cid, h, email="all2@example.com", login="all2_user")

    proc = _run_dev_script(
        db_url,
        "confirm-all",
        "--contest-id",
        str(cid),
        "--password",
        NEW_SECURE_PASSWORD,
    )
    assert proc.returncode == 0, proc.stderr

    parts = await client.get(f"{API_PREFIX}/contests/{cid}/participants", headers=h)
    assert all(p["status"] == "ACCEPTED" for p in parts.json())


@pytest.mark.asyncio
async def test_dev_confirm_all_seed_password(stage_112_api, monkeypatch):
    """[DEV-CONFIRM-ALL-ENV] confirm-all uses SEED_SUPERVISOR_PASSWORD when --password omitted."""
    monkeypatch.setenv("SEED_SUPERVISOR_PASSWORD", NEW_SECURE_PASSWORD)
    from config.settings import get_settings

    get_settings.cache_clear()

    client, _, db_url = stage_112_api
    cid, h = await create_draft_contest(client)
    await invite_participant(client, cid, h, email="env1@example.com", login="env1_user")

    proc = _run_dev_script(db_url, "confirm-all", "--contest-id", str(cid))
    assert proc.returncode == 0, proc.stderr

    parts = await client.get(f"{API_PREFIX}/contests/{cid}/participants", headers=h)
    assert parts.json()[0]["status"] == "ACCEPTED"

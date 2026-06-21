"""Stage 1.9 — team logo upload, static serving, and default asset."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.api.conftest import API_PREFIX, api_login, auth_header, contest_url


def _jpeg_bytes(width: int = 128, height: int = 96, color: tuple[int, int, int] = (200, 50, 50)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _oversized_file_bytes() -> bytes:
    header = _jpeg_bytes(10, 10)
    return header + b"\x00" * (2_097_153 - len(header))


@pytest.fixture
def logo_settings(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from config.settings import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.mark.asyncio
async def test_logo_default(empty_api, logo_settings):
    """[LOGO-DEFAULT] New team without upload returns configured default logo URL."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Default", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team A", "short_name": "TA"},
    )
    assert team.status_code == 200
    assert team.json()["logo_url"] == logo_settings.default_team_logo_url

    listed = await client.get(contest_url(cid, "/teams"), headers=h)
    assert listed.json()[0]["logo_url"] == logo_settings.default_team_logo_url


@pytest.mark.asyncio
async def test_logo_static_default(empty_api, logo_settings):
    """[LOGO-STATIC-DEFAULT] Bundled default asset is served."""
    client, _, _ = empty_api
    resp = await client.get(logo_settings.default_team_logo_url)
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("image/jpeg")


@pytest.mark.asyncio
async def test_logo_upload_ok(empty_api, logo_settings):
    """[LOGO-UPLOAD-OK] Valid JPEG upload persists file and returns public URL."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Upload", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team B", "short_name": "TB"},
    )
    tid = team.json()["id"]

    files = {"file": ("logo.jpg", _jpeg_bytes(), "image/jpeg")}
    upload = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files=files,
    )
    assert upload.status_code == 200, upload.text
    expected_url = f"{logo_settings.static_url_prefix}/teams/{cid}/{tid}.jpg"
    assert upload.json()["logo_url"] == expected_url

    got = await client.get(contest_url(cid, "/teams"), headers=h)
    assert got.json()[0]["logo_url"] == expected_url

    disk_path = logo_settings.upload_dir / "teams" / str(cid) / f"{tid}.jpg"
    assert disk_path.is_file()

    static = await client.get(expected_url)
    assert static.status_code == 200


@pytest.mark.asyncio
async def test_logo_upload_reupload(empty_api, logo_settings):
    """[LOGO-UPLOAD-REUPLOAD] Second upload replaces file; URL stays stable."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Reupload", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team R", "short_name": "TR"},
    )
    tid = team.json()["id"]
    expected_url = f"{logo_settings.static_url_prefix}/teams/{cid}/{tid}.jpg"
    disk_path = logo_settings.upload_dir / "teams" / str(cid) / f"{tid}.jpg"

    first_bytes = _jpeg_bytes(color=(200, 50, 50))
    first = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files={"file": ("logo.jpg", first_bytes, "image/jpeg")},
    )
    assert first.status_code == 200
    assert first.json()["logo_url"] == expected_url
    assert disk_path.is_file()
    first_saved = disk_path.read_bytes()

    second_bytes = _jpeg_bytes(color=(50, 200, 50))
    second = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files={"file": ("logo.jpg", second_bytes, "image/jpeg")},
    )
    assert second.status_code == 200
    assert second.json()["logo_url"] == expected_url

    listed = await client.get(contest_url(cid, "/teams"), headers=h)
    assert listed.json()[0]["logo_url"] == expected_url
    second_saved = disk_path.read_bytes()
    assert second_saved != first_saved
    with Image.open(io.BytesIO(second_saved)) as img:
        assert img.size == (logo_settings.team_logo_target_px, logo_settings.team_logo_target_px)


@pytest.mark.asyncio
async def test_logo_upload_type(empty_api, logo_settings):
    """[LOGO-UPLOAD-TYPE] Non-image content type → 400 VALIDATION_ERROR."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Type", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team C", "short_name": "TC"},
    )
    tid = team.json()["id"]

    files = {"file": ("notes.txt", b"not an image", "text/plain")}
    resp = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files=files,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_logo_upload_size(empty_api, logo_settings):
    """[LOGO-UPLOAD-SIZE] File over max_logo_bytes → 400."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Size", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team D", "short_name": "TD"},
    )
    tid = team.json()["id"]

    files = {"file": ("big.jpg", _oversized_file_bytes(), "image/jpeg")}
    resp = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files=files,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_logo_locked(empty_api, logo_settings):
    """[LOGO-LOCKED] Upload after contest activation → 403."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Locked", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team E", "short_name": "TE"},
    )
    tid = team.json()["id"]

    from datetime import datetime, timedelta, timezone

    from tests.api.conftest import _load_teams_csv

    teams = _load_teams_csv()[:16]
    tids = [tid]
    for row in teams[1:16]:
        t = await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
        tids.append(t.json()["id"])

    now = datetime.now(timezone.utc)
    matches = []
    for i in range(8):
        matches.append(
            {
                "team1_id": tids[i * 2],
                "team2_id": tids[i * 2 + 1],
                "date_time": (now + timedelta(days=30 + i)).isoformat(),
            }
        )
    earliest = now + timedelta(days=30)
    deadline = (earliest - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(cid, "/admin/rounds"),
        headers=h,
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    activate = await client.post(
        contest_url(cid, f"/admin/rounds/{rid}/activate"),
        headers=h,
    )
    assert activate.status_code == 200

    files = {"file": ("logo.jpg", _jpeg_bytes(), "image/jpeg")}
    resp = await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files=files,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_logo_clear(empty_api, logo_settings):
    """[LOGO-CLEAR] PATCH logo_url null restores default in GET response."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Clear", "total_teams": 16},
    )
    cid = created.json()["id"]
    team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team F", "short_name": "TF"},
    )
    tid = team.json()["id"]

    files = {"file": ("logo.jpg", _jpeg_bytes(), "image/jpeg")}
    await client.post(
        contest_url(cid, f"/teams/{tid}/logo"),
        headers=h,
        files=files,
    )

    cleared = await client.patch(
        contest_url(cid, f"/teams/{tid}"),
        headers=h,
        json={"logo_url": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["logo_url"] == logo_settings.default_team_logo_url

    disk_path = logo_settings.upload_dir / "teams" / str(cid) / f"{tid}.jpg"
    assert not disk_path.is_file()


@pytest.mark.asyncio
async def test_logo_reg_crud(empty_api, logo_settings):
    """[LOGO-REG] Team CRUD without upload remains unchanged."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Logo Reg", "total_teams": 16},
    )
    cid = created.json()["id"]
    created_team = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Team G", "short_name": "TG"},
    )
    assert created_team.status_code == 200
    tid = created_team.json()["id"]

    patched = await client.patch(
        contest_url(cid, f"/teams/{tid}"),
        headers=h,
        json={"short_name": "TGX"},
    )
    assert patched.status_code == 200
    assert patched.json()["short_name"] == "TGX"
    assert patched.json()["logo_url"] == logo_settings.default_team_logo_url

    deleted = await client.delete(contest_url(cid, f"/teams/{tid}"), headers=h)
    assert deleted.status_code == 200

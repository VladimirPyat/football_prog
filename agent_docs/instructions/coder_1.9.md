# Coder Instructions — Stage 1.9: Team Logo Upload & Default Asset

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.6 at `TEST_PASS` (1.7/1.8 independent).
> Plan: `agent_docs/plans/draft_1.7_frontend_prerequisites.md` §5.6, §6.3.
> **Default asset:** `static/assets/default-team-logo.jpg` (copied from `docs/screens/screen_team_default.jpg` by Planner).
> **Language policy:** code comments English; HTTP `detail` Russian; handler docstrings Russian; manuals English.

## 1. Objective

Close blocker **B5** — team logo file upload for supervisor teams admin (Stage 2.3).

| Deliverable | Description |
|-------------|-------------|
| `POST /contests/{id}/teams/{team_id}/logo` | Multipart upload, validate, resize, persist |
| Static file serving | Bundled default + uploaded logos |
| Default logo | Configurable URL; API returns default when `teams.logo_url` is NULL |
| Config | Env vars documented in `CONFIG.md`, `.env.example` |

**Non-goals:** Multipart on team PATCH; S3/CDN; SVG/WebP; frontend implementation.

## 2. Default logo asset layout

### 2.1 Canonical paths (repo)

| Path | Role | Git |
|------|------|-----|
| `static/assets/default-team-logo.jpg` | Bundled placeholder (source: `docs/screens/screen_team_default.jpg`) | **Committed** |
| `uploads/teams/{contest_id}/{team_id}.{ext}` | Supervisor-uploaded logos | **Gitignored** |

**Do not** store defaults under `docs/` — that directory is immutable spec/screens only.

### 2.2 Frontend (Stage 2 — document in handoff)

When `frontend/` is scaffolded, **copy the same file** to:

```
frontend/public/assets/default-team-logo.jpg
```

Next.js serves `public/` at site root → browser URL `/assets/default-team-logo.jpg`.

| Env (frontend) | Purpose |
|----------------|---------|
| `NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL=/assets/default-team-logo.jpg` | Local Next.js static (recommended for SSR/offline) |
| Or `${NEXT_PUBLIC_API_BASE}/static/assets/default-team-logo.jpg` | Single source via backend (no duplicate file) |

**Recommendation:** duplicate into `frontend/public/assets/` for faster page load; keep backend copy as API fallback when `TeamOut.logo_url` is null.

### 2.3 Display size

| Setting | Default | Notes |
|---------|---------|-------|
| `TEAM_LOGO_TARGET_PX` | `64` | Backend normalizes uploads to **64×64** square (center-crop, LANCZOS) |
| Frontend CSS | 64×64 or 48×48 box | `object-fit: contain`; comment in frontend instructions |

Document target size in `config/settings.py` field comment and `manuals/CONFIG.md`.

## 3. Scope — files you may create/modify

```
static/assets/default-team-logo.jpg     # EXISTS — verify present
uploads/.gitkeep                        # optional — ensure dir exists at runtime
.gitignore                              # add uploads/ if missing
config/settings.py                      # upload + default logo settings
src/services/team_logo_service.py       # NEW — validate, resize, save
src/services/team_out.py                # NEW optional — resolve logo_url helper
src/api/v1/contest_teams.py             # POST .../logo; TeamOut with default
src/schemas/contest.py                  # LogoUploadResponse if needed
main.py                                 # StaticFiles mounts
agent_docs/contracts/api_v1.yaml        # bump to **1.2.0**; new path
manuals/API_GUIDE.md                    # upload + static URLs
manuals/CONFIG.md                       # new env vars
.env.example                            # upload block
tests/api/test_team_logo_upload.py      # NEW
agent_docs/progress/stage_1.md          # append
```

**Dependency:** `uv add pillow` — **requires user approval** before install; pin in `pyproject.toml`.

**Do NOT modify:** `docs/`, `src/scoring/*`.

## 4. Settings (`config/settings.py`)

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Team logos — target 64×64 px square after upload (center-crop)
upload_dir: Path = PROJECT_ROOT / "uploads"
static_assets_dir: Path = PROJECT_ROOT / "static" / "assets"
static_url_prefix: str = "/static"
max_logo_bytes: int = 2_097_152  # 2 MiB
team_logo_target_px: int = 64
default_team_logo_url: str = "/static/assets/default-team-logo.jpg"
```

Env overrides: `UPLOAD_DIR`, `STATIC_URL_PREFIX`, `MAX_LOGO_BYTES`, `TEAM_LOGO_TARGET_PX`, `DEFAULT_TEAM_LOGO_URL`.

Ensure `upload_dir` and `static_assets_dir` directories created at startup or on first upload (`mkdir(parents=True, exist_ok=True)`).

## 5. Static file mounts (`main.py`)

Mount **after** API routers (FastAPI order):

```python
from fastapi.staticfiles import StaticFiles

# Bundled defaults (read-only repo assets)
app.mount(
    f"{settings.static_url_prefix}/assets",
    StaticFiles(directory=settings.static_assets_dir),
    name="static_assets",
)
# Uploaded team logos (writable)
teams_upload_root = settings.upload_dir / "teams"
teams_upload_root.mkdir(parents=True, exist_ok=True)
app.mount(
    f"{settings.static_url_prefix}/teams",
    StaticFiles(directory=teams_upload_root),
    name="static_teams",
)
```

Uploaded file URL pattern: `{static_url_prefix}/teams/{contest_id}/{team_id}.jpg`

## 6. Service — `team_logo_service.py`

```python
ALLOWED_MIME = {"image/png", "image/jpeg", "image/gif"}
EXT_BY_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif"}


async def save_team_logo(
    session: AsyncSession,
    *,
    contest_id: int,
    team_id: int,
    file_bytes: bytes,
    content_type: str,
    settings: Settings,
) -> str:
    """Validate, resize to team_logo_target_px², write file, update team.logo_url. Returns public URL."""
```

Rules:

1. `require_unlocked(session, contest_id)` — same as team PATCH.
2. Team must exist and belong to contest.
3. Reject if `len(file_bytes) > max_logo_bytes` → `ValidationError`.
4. Reject if `content_type` not in `ALLOWED_MIME` → `ValidationError`.
5. Pillow: open image, convert RGBA→RGB if needed, **center-crop to square**, resize to `(target_px, target_px)`, save as JPEG quality ~85 (or preserve PNG/GIF for PNG/GIF uploads — **prefer normalize all to JPEG** for consistency).
6. Path: `upload_dir / "teams" / str(contest_id) / f"{team_id}.jpg"`.
7. Set `team.logo_url = f"{static_url_prefix}/teams/{contest_id}/{team_id}.jpg"`.
8. Return `team.logo_url`.

**Clear custom logo:** existing `PATCH` with `logo_url: null` — delete file if under `/teams/` path, set DB NULL; GET returns default via resolver.

### 6.1 `resolve_team_logo_url(logo_url: str | None, settings) -> str`

Used in all `TeamOut` responses:

```python
return logo_url if logo_url else settings.default_team_logo_url
```

Apply in router via helper or Pydantic `@model_validator` wrapper — do **not** persist default URL in DB.

## 7. API — `POST /contests/{contest_id}/teams/{team_id}/logo`

| Item | Value |
|------|-------|
| Auth | SUPERVISOR+ (`RoleChecker`) |
| Body | `file: UploadFile = File(...)` |
| Response | `200` `{ "logo_url": "..." }` or `TeamOut` with resolved logo |

Docstring (RU): «Загрузить логотип команды (PNG/JPG/GIF, до 2 МБ). Доступно только в фазе SETUP.»

Register on existing `contest_teams` router.

Also update `GET/POST/PATCH` team handlers to return **resolved** `logo_url` (default when NULL).

## 8. Contract (`api_v1.yaml`)

- Bump `info.version` to **`1.2.0`** (final frontend prerequisite bundle).
- Add path `POST /api/v1/contests/{contest_id}/teams/{team_id}/logo`.
- Document `multipart/form-data`, field `file`.
- Note on `TeamOut.logo_url`: never null in responses — default URL when unset in DB.

## 9. `.gitignore`

Add:

```
uploads/
!uploads/.gitkeep
```

## 10. `.env.example`

```bash
# ─── Team logos (Stage 1.9) ─────────────────────────────────────────────────
# UPLOAD_DIR=./uploads
# STATIC_URL_PREFIX=/static
# MAX_LOGO_BYTES=2097152
# TEAM_LOGO_TARGET_PX=64
# DEFAULT_TEAM_LOGO_URL=/static/assets/default-team-logo.jpg
```

## 11. Tests — `test_team_logo_upload.py`

Use `empty_api`; create minimal PNG/JPEG bytes in test (Pillow or tiny fixture file in `tests/fixtures/`).

| ID | Scenario |
|----|----------|
| `[LOGO-DEFAULT]` | New team without upload → GET teams → `logo_url == settings.default_team_logo_url` |
| `[LOGO-STATIC-DEFAULT]` | `GET /static/assets/default-team-logo.jpg` → 200, `image/jpeg` |
| `[LOGO-UPLOAD-OK]` | POST valid JPEG ≤2MB → 200; GET team shows `/static/teams/...`; file on disk |
| `[LOGO-UPLOAD-TYPE]` | POST `text/plain` → 400 `VALIDATION_ERROR` |
| `[LOGO-UPLOAD-SIZE]` | POST file > 2MB → 400 |
| `[LOGO-LOCKED]` | Activate contest → POST logo → 403 |
| `[LOGO-CLEAR]` | PATCH `logo_url: null` → GET returns default URL |
| `[LOGO-REG]` | Team CRUD without upload unchanged |

## 12. Acceptance criteria

- [ ] Default asset served at `/static/assets/default-team-logo.jpg`
- [ ] `DEFAULT_TEAM_LOGO_URL` in settings; documented in CONFIG.md
- [ ] Upload resizes to 64×64; stored under `uploads/teams/`
- [ ] `TeamOut.logo_url` never null in API responses
- [ ] `api_v1.yaml` v1.2.0
- [ ] `pillow` pinned in pyproject.toml
- [ ] `pytest tests/ --ignore=tests/manual` green

## 13. OUT OF SCOPE

- Image CDN, virus scan, async processing
- Logo on team create (two-step: create → upload)
- Frontend file picker (Stage 2.3)

## 14. Implementation order

1. User approval → `uv add pillow`
2. Settings + `.gitignore` + `.env.example`
3. `team_logo_service.py` + logo URL resolver
4. `main.py` static mounts
5. `contest_teams.py` POST logo + TeamOut resolution
6. Tests
7. `api_v1.yaml` v1.2.0 + manuals
8. Progress handoff

## 15. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.9 team logo upload)
- STATUS: READY_FOR_TEST
- Blocker: B5
- Asset: static/assets/default-team-logo.jpg
- Contract: api_v1.yaml v1.2.0
- Frontend note: copy to frontend/public/assets/default-team-logo.jpg
- Next: agent_docs/instructions/tester_1.9.md
```

After 1.7+1.8+1.9 TEST_PASS: update `agent_docs/reports/BLOCKED.md` — mark B1–B6 RESOLVED.

## 16. Frontend integration (Stage 2.3)

| Concern | Approach |
|---------|----------|
| Show default | If `logo_url` points to default path OR use `NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL` |
| Upload UI | `FormData` with `file` → `POST .../teams/{id}/logo` |
| Display | `<img className="h-16 w-16 object-contain" />` — 64px box |
| Fallback before 1.9 | Text input for `logo_url` (remove when B5 live) |

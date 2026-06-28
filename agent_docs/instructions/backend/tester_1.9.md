# Tester Instructions — Stage 1.9: Team Logo Upload & Default Asset

> Status gate: @Coder `READY_FOR_TEST` for 1.9. **Prerequisite:** Stage 1.6 at `TEST_PASS`.
> Reference: `instructions/coder_1.9.md`, `plans/draft_1.7_frontend_prerequisites.md` §7.3.
> **Default asset:** `static/assets/default-team-logo.jpg` must exist in repo.

## 1. Objective

Verify Stage 1.9 closes blocker **B5**:

1. Default logo served from static mount; API returns default URL when team has no custom logo.
2. Multipart upload validates type/size, resizes, persists, updates `logo_url`.
3. Upload blocked when contest locked.
4. Contract v1.2.0, CONFIG/API docs, `.env.example`.
5. Full regression green.

**Non-goals:** Frontend Playwright, image pixel-perfect comparison, B1–B4/B6 tests.

## 2. Scope — files you may create

```
tests/api/test_team_logo_upload.py      # extend if gaps
tests/fixtures/minimal_logo.jpg         # optional tiny test image
agent_docs/reports/test_1.9.md          # NEW — Russian report
```

**Do NOT modify** `src/` unless Coder blocker.

## 3. Default logo & static serving

### 3.1 `[LOGO-ASSET-EXISTS]`

File present: `static/assets/default-team-logo.jpg` (committed; ~26 KB JPEG from spec screenshot).

### 3.2 `[LOGO-STATIC-DEFAULT]`

With app running (ASGI client):

```http
GET /static/assets/default-team-logo.jpg
```

Assert: **200**, `Content-Type` contains `image/jpeg`, body length > 0.

### 3.3 `[LOGO-DEFAULT-API]`

`empty_api`: create team without logo → `GET /contests/{cid}/teams` → item `logo_url == "/static/assets/default-team-logo.jpg"` (or configured `DEFAULT_TEAM_LOGO_URL`).

## 4. Upload flow

Use `empty_api`; supervisor creates contest + one team.

### 4.1 `[LOGO-UPLOAD-OK]`

```http
POST /api/v1/contests/{cid}/teams/{tid}/logo
Content-Type: multipart/form-data
file: <valid JPEG or PNG, < 2MB>
```

Assert:

- HTTP 200
- `body.logo_url` matches `/static/teams/{cid}/{tid}.jpg` (or `.png` if Coder preserves ext)
- `GET .../teams` → same custom URL
- `GET {logo_url}` → 200 image

Optional: verify file dimensions ≈ 64×64 via Pillow in test.

### 4.2 `[LOGO-UPLOAD-REUPLOAD]`

Second upload replaces first; URL stable; old file overwritten.

### 4.3 `[LOGO-UPLOAD-TYPE]`

Upload non-image (e.g. tiny `.txt` as `file`) → **400**, `code == "VALIDATION_ERROR"`.

### 4.4 `[LOGO-UPLOAD-SIZE]`

File > 2_097_152 bytes → **400**.

### 4.5 `[LOGO-LOCKED]`

Create round + activate (contest locked) → POST logo → **403** (`CONTEST_LOCKED` or setup guard).

### 4.6 `[LOGO-CLEAR]`

After upload, `PATCH` team `{ "logo_url": null }` → GET returns **default** URL (not custom path).

## 5. Regression

| ID | Check |
|----|-------|
| `[LOGO-REG-TEAMS]` | `[SETUP-TEAMS]` CRUD still passes |
| Full suite | `uv run pytest tests/ --ignore=tests/manual -q` |

## 6. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-CONTRACT]` | `api_v1.yaml` version **1.2.0**; POST logo path documented |
| `[DOC-CONFIG]` | `CONFIG.md` lists upload settings + default URL; `.env.example` secrets only |
| `[DOC-API-GUIDE]` | Logo upload + default behaviour documented |
| `[DOC-FRONTEND-HINT]` | Handoff mentions `frontend/public/assets/default-team-logo.jpg` |

## 7. Report (`agent_docs/reports/test_1.9.md`)

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[LOGO-ASSET-EXISTS]` | PASS/FAIL | |
| `[LOGO-STATIC-DEFAULT]` | PASS/FAIL | |
| `[LOGO-DEFAULT-API]` | PASS/FAIL | |
| `[LOGO-UPLOAD-OK]` | PASS/FAIL | |
| `[LOGO-UPLOAD-TYPE]` | PASS/FAIL | |
| `[LOGO-UPLOAD-SIZE]` | PASS/FAIL | |
| `[LOGO-LOCKED]` | PASS/FAIL | |
| `[LOGO-CLEAR]` | PASS/FAIL | |
| `[LOGO-REG-TEAMS]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Regression | PASS/FAIL | N passed |

Verdict: **TEST_PASS** / **TEST_FAIL**.

On **TEST_PASS** with 1.7+1.8 also passed: recommend updating `BLOCKED.md` B1–B6 → RESOLVED.

## 8. Progress update

```
## YYYY-MM-DD — Tester (1.9)
- STATUS: TEST_PASS
- Blocker verified: B5
- Report: agent_docs/reports/test_1.9.md
- Contract: api_v1.yaml v1.2.0
```

## 9. OUT OF SCOPE

- Visual match to `docs/screens/supervisor_settings3.jpg`
- Performance/load test on large images
- CORS test from separate frontend origin (Stage 2)

## 10. Frontend checklist (informational — for Stage 2.3 coder)

Pass to frontend team after TEST_PASS:

- [ ] Copy `static/assets/default-team-logo.jpg` → `frontend/public/assets/default-team-logo.jpg`
- [ ] Set `NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL=/assets/default-team-logo.jpg`
- [ ] Team row `<img>` 64×64, `object-fit: contain`
- [ ] Upload via `POST .../logo` with `FormData`

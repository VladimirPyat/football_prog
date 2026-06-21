# Отчёт тестирования — Stage 1.9: Team Logo Upload & Default Asset

**Дата:** 2026-06-22  
**Вердикт:** **TEST_PASS**

## Краткое резюме

Проверен блокер B5: default logo asset, static mount, multipart upload (type/size/lock/clear/reupload), контракт v1.2.0 и конфигурация. Полный регрессионный прогон зелёный.

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[LOGO-ASSET-EXISTS]` | PASS | `static/assets/default-team-logo.jpg` — 26 125 bytes, committed |
| `[LOGO-STATIC-DEFAULT]` | PASS | `GET /static/assets/default-team-logo.jpg` → 200, `image/jpeg` |
| `[LOGO-DEFAULT-API]` | PASS | `test_logo_default`: `logo_url == DEFAULT_TEAM_LOGO_URL` |
| `[LOGO-UPLOAD-OK]` | PASS | Upload → custom URL, disk file, static GET 200 |
| `[LOGO-UPLOAD-REUPLOAD]` | PASS | `test_logo_upload_reupload`: URL stable, file overwritten (64×64) |
| `[LOGO-UPLOAD-TYPE]` | PASS | `.txt` → 400 `VALIDATION_ERROR` |
| `[LOGO-UPLOAD-SIZE]` | PASS | > 2 MiB → 400 `VALIDATION_ERROR` |
| `[LOGO-LOCKED]` | PASS | After activate → 403 |
| `[LOGO-CLEAR]` | PASS | `PATCH logo_url: null` → default URL, file removed |
| `[LOGO-REG-TEAMS]` | PASS | `test_setup_teams_crud_and_duplicate` → 1 passed |
| `[DOC-CONTRACT]` | PASS | `api_v1.yaml` v1.2.0; `POST .../teams/{team_id}/logo` documented |
| `[DOC-CONFIG]` | PASS | `CONFIG.md` + `.env.example`: `UPLOAD_DIR`, `MAX_LOGO_BYTES`, `TEAM_LOGO_TARGET_PX`, `DEFAULT_TEAM_LOGO_URL`, `STATIC_URL_PREFIX` |
| `[DOC-API-GUIDE]` | PASS | Logo upload, default behaviour, static paths |
| `[DOC-FRONTEND-HINT]` | PASS | `stage_1.md` Coder (1.9): copy → `frontend/public/assets/default-team-logo.jpg` |
| Regression | PASS | 302 passed, 2 skipped |

## Выполненные команды

```bash
uv run pytest tests/api/test_team_logo_upload.py -v
# → 9 passed

uv run pytest tests/api/test_setup_phase_1_4.py::test_setup_teams_crud_and_duplicate -q
# → 1 passed

uv run pytest tests/ --ignore=tests/manual -q
# → 302 passed, 2 skipped
```

## Созданные/изменённые тесты

| Файл | Назначение |
|------|------------|
| `tests/api/test_team_logo_upload.py` | [LOGO-*] + новый `test_logo_upload_reupload` |

## Блокеры

- **B5** — закрыт: multipart upload, default asset, static serving.

## Frontend checklist (Stage 2.3)

- [ ] Copy `static/assets/default-team-logo.jpg` → `frontend/public/assets/default-team-logo.jpg`
- [ ] Set `NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL=/assets/default-team-logo.jpg`
- [ ] Team row `<img>` 64×64, `object-fit: contain`
- [ ] Upload via `POST .../logo` with `FormData`

## Следующий шаг

Stage 1.9 sign-off. Рекомендуется обновить `BLOCKED.md` B4–B6 → RESOLVED (bundle 1.7–1.9 complete).

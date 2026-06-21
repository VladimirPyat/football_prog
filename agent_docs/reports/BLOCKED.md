# BLOCKED — Stage 2 Frontend: Backend Prerequisites

> **Created:** 2026-06-21  
> **Updated:** 2026-06-22 — B1–B6 **RESOLVED** (Stages 1.7–1.9, `test_1.7.md` / `test_1.8.md` / `test_1.9.md` TEST_PASS). **Stage 2.1–2.4 backend prerequisites complete.**  
> **Context:** `agent_docs/plans/draft_2.md`, `agent_docs/contracts/api_v1.yaml` v1.2.0.  
> **Rule:** Frontend integrates the real backend (no mocks). Where an endpoint is missing, use documented fallbacks — never mock data.

---

## Status summary

| # | Item | Stage 2.1 | Stage 2.3 | Stage 2.4 | Status |
|---|------|-----------|-----------|-----------|--------|
| **B1** | `GET /api/v1/me/contests` | ✅ required | — | — | **RESOLVED** (1.8) |
| **B2** | `GET /api/v1/contests/public` | ✅ required | — | optional | **RESOLVED** (1.8) |
| **B3** | `GET/PATCH /api/v1/auth/me/contacts` | ✅ required | — | — | **RESOLVED** (1.8) |
| **B4** | `count_*` in `ScoreDetail` | — | — | ✅ required | **RESOLVED** (1.7) |
| **B5** | Team logo upload | — | ✅ required | — | **RESOLVED** (1.9) |
| **B6** | Invite-accept flow confirmation | — | optional | — | **RESOLVED** (1.7) |

**Verdict:** Sub-stages **2.1–2.4** backend prerequisites complete. Frontend may integrate all B1–B6 endpoints without fallbacks (fallbacks remain for legacy/dev resilience).

---

## RESOLVED — B1: `GET /api/v1/me/contests` (Stage 1.8)

- **Delivered:** `src/api/v1/me.py`; tests `tests/api/test_me_contests.py`.
- **Contract:** Bearer → enrolled contests only; fields include `participant_status`, global `role`.
- **Frontend:** User «Конкурсы» picker → primary path.
- **Fallback (if endpoint fails / empty in dev):** use `NEXT_PUBLIC_DEFAULT_CONTEST_ID` from frontend config (see § Frontend fallbacks).

---

## RESOLVED — B2: `GET /api/v1/contests/public` (Stage 1.8)

- **Delivered:** `GET /api/v1/contests/public` in `contests.py` (registered before `/{contest_id}`); tests `tests/api/test_contests_public.py`.
- **Contract:** No auth; **RUNNING contests only** (DRAFT/PAUSED/FINISHED excluded).
- **Frontend:** Visitor home discovery → primary path.
- **Fallback:** redirect to contest from `NEXT_PUBLIC_DEFAULT_CONTEST_ID`.

---

## RESOLVED — B3: `GET/PATCH /api/v1/auth/me/contacts` (Stage 1.8)

- **Delivered:** `src/api/v1/auth.py`; tests `tests/api/test_contacts.py`.
- **Contract:** GET defaults when row missing; PATCH upsert; allowed during `is_temp_password`.
- **Frontend:** Profile contacts form → primary path (editable).
- **Fallback (if GET fails e.g. 404/501 on old backend):** show contact fields **readonly** with empty values; hide Save button; log warning.

---

## RESOLVED — B4: Leaderboard count columns (Stage 1.7)

- **Delivered:** `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` in round/global leaderboard; tests `tests/api/test_leaderboard_counts.py`.
- **Contract:** `ScoreDetail` in `api_v1.yaml`; documented in `manuals/API_GUIDE.md`.
- **Frontend:** Sub-stage **2.4** — four count columns in user leaderboard.
- **Fallback (legacy):** hide columns if API omits keys.

---

## RESOLVED — B5: Team logo upload (Stage 1.9)

- **Delivered:** `POST /api/v1/contests/{id}/teams/{team_id}/logo` (multipart); default asset `static/assets/default-team-logo.jpg`; tests `tests/api/test_team_logo_upload.py`.
- **Contract:** `api_v1.yaml` v1.2.0; upload settings in `CONFIG.md` / `.env.example`.
- **Frontend:** Sub-stage **2.3** — file picker + 64×64 preview; copy default asset to `frontend/public/assets/`.
- **Fallback (legacy):** plain `logo_url` text input.

---

## RESOLVED — B6: Invite-accept flow (Stage 1.7)

- **Delivered:** `POST /auth/change-password` flips `contest_participants.status` PENDING → ACCEPTED; prediction guard `PARTICIPANT_NOT_ACCEPTED`; tests `tests/api/test_participant_accept.py`.
- **Frontend:** Sub-stage **2.3** — accurate `participant_status` badge; `/me/contests` shows ACCEPTED after password change.
- **Fallback:** display status from `GET /participants`.

---

## Frontend fallbacks (config-driven, no mocks)

Documented in `agent_docs/contracts/frontend_api_integration.md` §6.

| Blocker | Primary API | Fallback |
|---------|-------------|----------|
| **B1** | `GET /me/contests` | If empty or request fails → open contest `NEXT_PUBLIC_DEFAULT_CONTEST_ID` from `frontend/.env.local` |
| **B2** | `GET /contests/public` | If empty or request fails → redirect to `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| **B3** | `GET/PATCH /auth/me/contacts` | If GET unavailable → fields **readonly**, no Save; if PATCH fails → keep readonly + toast |

**Config (`frontend/.env.local.example`):**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1   # fallback contest when B1/B2 lists are empty or unavailable
```

Implement a single helper e.g. `resolveDefaultContestId()` used by Visitor home and User «Конкурсы» when list endpoints return `[]` or error.

---

## Stage 2.1 readiness checklist

Criteria for marking sub-stage **2.1 done** (manual + E2E smoke):

- [ ] **`user/user` login → `/profile`** — `POST /auth/login`, redirect to profile hub; header shows login instead of «Вход».
- [ ] **Supervisor sees contest switcher** — `ContestPicker` populated from `GET /contests` (SUPERVISOR+); selection updates active contest context.
- [ ] **401 on any request → auto logout** — API client clears `fp_access_token`, resets auth context, Visitor state; login modal available.
- [ ] **Temp password → forced change** — `is_temp_password=true` after login redirects to `/change-password`; other routes blocked until `POST /auth/change-password` succeeds.
- [ ] **CORS `:3000` ↔ `:8000`** — Next.js dev on 3000 calls FastAPI on 8000 without browser CORS errors (`cors_origins` includes `http://localhost:3000` or `*` in dev).

**Also expected in 2.1 (from plan, not in smoke list above):**

- [ ] Visitor: `GET /contests/public` → contest list (or fallback to default contest id).
- [ ] User: `GET /me/contests` → «Конкурсы» (or fallback).
- [ ] Profile: `GET/PATCH /auth/me/contacts` (or readonly fallback).

---

## References

| Doc | Content |
|-----|---------|
| `agent_docs/reports/test_1.7.md` | B4, B6 TEST_PASS |
| `agent_docs/reports/test_1.8.md` | B1–B3 TEST_PASS |
| `agent_docs/reports/test_1.9.md` | B5 TEST_PASS |
| `agent_docs/contracts/api_v1.yaml` | v1.2.0 |
| `manuals/API_GUIDE.md` | B1–B6 sections |
| `agent_docs/plans/draft_2.md` | § Sub-stages 2.1–2.4 |

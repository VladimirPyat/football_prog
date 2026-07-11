# Frontend ↔ API Integration Contract (Stage 2)

> **Living document** — see update log at the bottom.
> **Authoritative API spec:** `agent_docs/contracts/api_v1.yaml` (v1.1.0) + `manuals/dev/API_GUIDE.md`, `manuals/ERROR_LOGGING.md`.
> **Plan:** `agent_docs/plans/draft_2.md` (§7, §12, §13).
> **Rule:** No mocks. Frontend integrates the real backend. Where an endpoint is missing it is a Stage-2 prerequisite (B1–B6, §9), with a documented fallback.

---

## 1. Base configuration

| Item | Value |
|------|-------|
| API base URL | `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) |
| API prefix | `/api/v1` |
| Default contest (fallback) | `NEXT_PUBLIC_DEFAULT_CONTEST_ID` — used when B1/B2 lists empty or unavailable |
| CORS | Backend `cors_origins` default `["*"]` (`config/settings.py`); direct browser→FastAPI calls OK in dev |
| Timestamps | See [§1.1 Timestamps](#11-timestamps) |
| Content type | `application/json` (except team logo upload B5 → `multipart/form-data`) |

### 1.1 Timestamps

| Layer | Timezone | Config |
|-------|----------|--------|
| **DB / API storage** | UTC | Backend `TIMESTAMPTZ`; naive ISO from API → UTC (`config/settings.py` → `api_timestamp_timezone`) |
| **Wire format** | UTC ISO 8601 | Prefer `…Z`; naive `2026-06-28T17:00:00` is **UTC wall clock**, not local |
| **Parse on read** | UTC | `frontend/src/lib/datetime/parseApiUtc.ts` + `NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE=UTC` |
| **Supervisor input** | Display zone | `<input type="datetime-local">` — wall time in `NEXT_PUBLIC_DISPLAY_TIMEZONE` (default `Europe/Moscow`) |
| **Submit to API** | UTC | `fromDatetimeLocal()` → `toISOString()` |
| **Labels in UI** | Display zone | `formatDateTimeRu()` via `NEXT_PUBLIC_DISPLAY_TIMEZONE` + `NEXT_PUBLIC_DATETIME_LOCALE` |
| **Unset display zone** | Browser local | Omit `NEXT_PUBLIC_DISPLAY_TIMEZONE` — inputs/labels follow supervisor device |

Implementation hub: `frontend/src/lib/datetime/config.ts`, `formatApiDateTime.ts`.

**Do not** use bare `Date.parse(naiveIso)` on API fields — browsers treat naive ISO as local; backend treats it as UTC.

**Path builder convention:** all contest data is scoped: `${API}/api/v1/contests/${contestId}/…`. Never call legacy deprecated shims (`/api/v1/rounds`, `/api/v1/leaderboard`, `/api/v1/admin/contest-settings`, `/api/v1/admin/*` without contest) from new code.

---

## 2. Authentication

JWT bearer. Payload `{ sub: user_id, role, exp }`. Default expiry 24h (`jwt_expire_minutes`).

### 2.1 Flow

```
POST /api/v1/auth/login {login, password}
  → 200 {access_token, token_type:"bearer", is_temp_password}
  → 401 {detail:"Неверный логин или пароль"}   (no `code`)
  → 403 {detail, code:"PASSWORD_SETUP_REQUIRED"}  when enforce_password_setup=true and temp password

store token (localStorage: fp_access_token)

if is_temp_password === true && enforce_password_setup === false:
   force redirect /change-password
   POST /api/v1/auth/change-password {old_password, new_password} (Bearer)
     → 200  → is_temp_password cleared server-side

if PASSWORD_SETUP_REQUIRED on login:
   redirect user to /auth/setup (link from invite letter or request-password-reset)

GET /api/v1/auth/me (Bearer) → UserOut {id, login, role, first_name, last_name, is_temp_password}
```

### 2.1.1 Invite / password setup (Stage 1.12)

Signed link: `{FRONTEND_BASE_URL}/auth/setup?token=…`

```
GET /api/v1/auth/setup-preview?token=…
  → 200 {login, mode:"password_form"|"confirm_only", already_completed}

POST /api/v1/auth/complete-setup {token, new_password?}
  → 200 {success, accepted, already_completed}  (idempotent)
  → PENDING→ACCEPTED when contest_id in token

POST /api/v1/auth/request-password-reset {email}
  → 200 {message}  (always 200; re-issues temp password when email known)

POST /api/v1/contests/{id}/participants (SUPERVISOR+)
  → 200 ParticipantInviteOut {user_id, login, temp_password, status, setup_url}
```

UI `/auth/setup`: `password_form` → form + `new_password`; `confirm_only` → confirm button only. Success → redirect to login (no auto-JWT).

Config field names (`enforce_password_setup`, `frontend_base_url`, `supervisor_training_mode`, …) — defaults in `config/settings.py`; override via deployment env or shell prefix for tests. **Root `.env` = secrets only.** See `manuals/setup/CONFIG.md`.

### 2.2 Rules

- Attach `Authorization: Bearer <token>` to every authenticated request.
- While `is_temp_password=true`, backend allows only `/auth/change-password` and `/auth/me`; all mutations return `403`. UI must hard-gate to `/change-password`.
- Test credentials (seed/bootstrap, `manuals/setup/BOOTSTRAP_USERS.md`): `admin/…`, `supervisor/…`; demo participant `user/user` from `bootstrap_users.py` (2.1.1, **TEMPORARY** until 2.3 invite UI).
- Roles: `Support (ADMIN) ⊃ SUPERVISOR ⊃ USER`; Visitor = no token.

### 2.4 Post-login routing by role

After successful `POST /auth/login` and `GET /auth/me`, the frontend **must not** hardcode `/profile` for all roles. Use a single resolver: `resolvePostLoginPath(user)` in `frontend/src/lib/auth/resolvePostLoginPath.ts`.

| Condition | Redirect target |
|-----------|-----------------|
| `is_temp_password === true` | `/change-password` |
| `role === 'USER'` | `/profile` (participant hub) |
| `role === 'SUPERVISOR'` | `/admin/settings/parameters` (or `/admin` with redirect to settings stub) |
| `role === 'ADMIN'` (support) | `/admin` (dashboard stub until 2.3) |

**Same resolver** applies after `POST /auth/change-password` success (not hardcoded `/profile`).

**Route guards (2.1.1+):**

| Route | Allowed roles | Notes |
|-------|---------------|-------|
| `/profile` | USER only | SUPERVISOR+/Support → redirect `/admin` |
| `/admin/*` | SUPERVISOR+ | USER → redirect `/` or `/profile` |
| `/` (authenticated) | all | USER → participant flow (`/contests`); SUPERVISOR+/Support → `/admin` |
| `/staff/login` | Visitor (login form) | Same API as modal login; staff-oriented copy |

**Staff login:** optional dedicated page `/staff/login` — still `POST /auth/login`; no second auth mechanism.

**App shell nav:** USER sees «Личный кабинет» → `/profile`; SUPERVISOR+ sees «Управление» → `/admin`.

Introduced in **Stage 2.1.1** — fixes bug where all roles landed on `/profile` (`AuthProvider` hardcode).

### 2.3 Token storage decision

- `localStorage` key `fp_access_token` (per `docs/02_project_structure.md`).
- On app load: if token present → `GET /auth/me` to hydrate; on 401 → clear and treat as Visitor.

---

## 3. Error handling contract

Backend has two error shapes (`manuals/ERROR_LOGGING.md`):

| Source | Body | Has `code`? |
|--------|------|-------------|
| Domain `AppError` (services) | `{ "detail": "<RU>", "code": "<CODE>" }` | ✅ |
| Auth / RBAC (`deps.py`) | `{ "detail": "<RU>" }` | ❌ |
| Pydantic validation | FastAPI 422 `{ "detail": [ {loc, msg, type} ] }` | ❌ |

**Display:** `detail` is Russian, human-readable → show as-is. Use `code` (when present) for branching, never for user text.

### 3.1 HTTP → frontend action

| HTTP | Action |
|------|--------|
| 400 | Form/field error or toast (`VALIDATION_ERROR`, `GRACE_PERIOD_ACTIVE`) |
| 401 | Clear token → Visitor → open login modal |
| 403 | Toast; branch on `code` (see 3.2); if temp-password block → route to `/change-password` |
| 404 | Not-found state (`NOT_FOUND`) — contest/round/match missing |
| 409 | Conflict toast (`ILLEGAL_TRANSITION`) — illegal status transition |
| 422 | Map Pydantic field errors to form inputs; `SCORE_OUT_OF_RANGE` highlights score cell |
| 500 | Generic error toast («Внутренняя ошибка сервера») |

### 3.2 Known `code` values (branch on these)

| `code` | HTTP | Frontend meaning |
|--------|------|------------------|
| `NOT_FOUND` | 404 | Resource missing |
| `VALIDATION_ERROR` | 400 | Incomplete batch, duplicate team, early close |
| `SCORE_OUT_OF_RANGE` | 422 | Score outside `[0, max_score_value]` |
| `CONTEST_RULE_VIOLATION` | 403 | Generic rule break |
| `DEADLINE_PASSED` | 403 | Prediction after deadline → set form readonly |
| `CONTEST_NOT_RUNNING` | 403 | Contest PAUSED/FINISHED → disable mutations, banner |
| `CONTEST_LOCKED` | 403 | Structural change after lock → setup forms readonly |
| `GRACE_PERIOD_ACTIVE` | 400 | Delete blocked until grace elapses |
| `ILLEGAL_TRANSITION` | 409 | Round/match status step invalid |
| `CONTEST_NOT_PAUSED` | 403 | Delete needs PAUSED |
| `INTERNAL_ERROR` | 500 | Server error |

> RBAC 403 has **no** `code` — distinguish from temp-password (check `auth.user.is_temp_password`) and from `CONTEST_*` codes.

---

## 4. Caching / ETag

Public GET leaderboard & results return (`manuals/dev/API_GUIDE.md`):

```
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: <16-char sha256 of score state>
```

- ETag changes after calculate / VOID / recalculate.
- Client: store ETag per resource; send `If-None-Match` on refresh; on `304` reuse cached payload (optionally seed from `localStorage`).
- **Never cache:** `GET/POST predictions`, all admin routes, contest PATCH.

### 4.1 Public round visibility (frontend gate — 2.3.1)

Endpoints `GET …/leaderboard` and `GET …/results` are **public** (ETag), but backend returns **`403 RESULTS_NOT_AVAILABLE`** for rounds not yet **`PUBLISHED`**. Frontend **must** gate before fetch:

```ts
// frontend/src/lib/contest/roundPublicVisibility.ts
isRoundPubliclyVisible(status) === (status === 'PUBLISHED')
```

| Tab / feature | Gate | Stub copy |
|---------------|------|-----------|
| Public **Лидерборд** / **Результаты** | `PUBLISHED` only | `ROUND_NOT_PUBLISHED_COPY` |
| **Прогнозы** matrix | **`deadline_passed`** privacy — **not** publish-gated | visitor pre-deadline stub |

Global `GET …/leaderboard` aggregates **PUBLISHED** rounds only (server-side). Detail: [admin_ui_status_matrix.md](admin_ui_status_matrix.md) §10–11.

```ts
const res = await fetch(url, { headers: etag ? { 'If-None-Match': etag } : {} });
if (res.status === 304) return cached;
const next = await res.json(); saveEtag(url, res.headers.get('ETag')); return next;
```

---

## 5. Endpoint matrix (contest-scoped — use these)

### 5.1 Auth (global)
| Method | Path | Role |
|--------|------|------|
| POST | `/api/v1/auth/login` | none |
| POST | `/api/v1/auth/change-password` | Bearer |
| GET | `/api/v1/auth/me` | Bearer |

### 5.2 Contests
| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/contests` | SUPERVISOR+ |
| POST | `/api/v1/contests` | SUPERVISOR+ |
| GET | `/api/v1/contests/{id}` | SUPERVISOR+ |
| PATCH | `/api/v1/contests/{id}` | SUPERVISOR+ (403 when locked) |
| POST | `/api/v1/contests/{id}/pause\|resume\|finish` | Support (ADMIN) |
| DELETE | `/api/v1/contests/{id}` (body `{confirm:"DELETE"}`) | Support (ADMIN) |

### 5.3 Setup (SUPERVISOR+, SETUP phase)
| Method | Path |
|--------|------|
| GET/POST | `/api/v1/contests/{id}/teams` |
| PATCH/DELETE | `/api/v1/contests/{id}/teams/{team_id}` |
| GET/POST | `/api/v1/contests/{id}/participants` |
| DELETE | `/api/v1/contests/{id}/participants/{user_id}` |
| PUT | `/api/v1/contests/{id}/participants/{user_id}/exceptional-tiebreak` (Support (ADMIN), allowed when locked) |

### 5.4 Public / User (contest-scoped)
| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/contests/{id}/rounds` | public |
| GET | `/api/v1/contests/{id}/rounds/{rid}/predictions` | public post-deadline; USER+ pre-deadline (privacy) |
| POST | `/api/v1/contests/{id}/rounds/{rid}/predictions` | USER+ |
| GET | `/api/v1/contests/{id}/rounds/{rid}/leaderboard` | public (ETag); public contest tab uses `?scope=total` |
| GET | `/api/v1/contests/{id}/rounds/{rid}/results` | public (ETag) |
| GET | `/api/v1/contests/{id}/leaderboard` | public (ETag) |

### 5.5 Admin operational (SUPERVISOR+ unless noted)
| Method | Path |
|--------|------|
| POST | `/api/v1/contests/{id}/admin/rounds` |
| POST | `/api/v1/contests/{id}/admin/rounds/free-tour` |
| PATCH | `/api/v1/contests/{id}/admin/rounds/{rid}` |
| POST | `/api/v1/contests/{id}/admin/rounds/{rid}/activate\|close\|calculate\|publish` |
| PUT | `/api/v1/contests/{id}/admin/matches/{mid}/result` |
| PATCH | `/api/v1/contests/{id}/admin/matches/{mid}/status` |
| POST | `/api/v1/contests/{id}/admin/recalculate` (Support (ADMIN)) |
| POST | `/api/v1/admin/users/supervisor` (Support (ADMIN), global) |

---

## 6. Backend prerequisites (not in v1.1.0 — see `reports/BLOCKED.md`)

These endpoints/fields are **assumed by the frontend** and tracked as Stage-2 prerequisites. Contracts are pre-specified here so backend & frontend can proceed in parallel. Until delivered, use the listed fallback (never mock).

### Fallback implementation (Stage 2.1)

| # | Primary | Fallback |
|---|---------|----------|
| B1 | `GET /me/contests` | Empty/error → navigate using `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B2 | `GET /contests/public` | Empty/error → redirect to `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B3 | `GET/PATCH /auth/me/contacts` | GET fails → contacts fields **readonly**, hide Save; PATCH fails → toast, stay readonly |

Helper: `resolveDefaultContestId()` — reads env, validates number, used by Visitor home and User «Конкурсы».

**Status (2026-06-22):** B1–B3 **implemented** (Stage 1.8). Fallbacks remain for resilience and older backends.

| # | Proposed endpoint / change | Request | Response (proposed) | Fallback |
|---|----------------------------|---------|---------------------|----------|
| B1 | `GET /api/v1/me/contests` | Bearer | `[{ id, name, status, participant_status }]` | `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B2 | `GET /api/v1/contests/public` | none | `[{ id, name, status }]` (RUNNING only) | `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B3 | `GET/PATCH /api/v1/auth/me/contacts` | Bearer; PATCH partial | `{email, vk_id, tg_id, notify_enabled}` | **readonly** fields, no Save |
| B4 | Extend `ScoreDetail` | — | + `count_exact_high, count_exact, count_diff, count_outcome` | hide 4 columns |
| B5 | `POST /api/v1/contests/{id}/teams/{team_id}/logo` | `multipart` file | `{ logo_url }` | `logo_url` text input |
| B6 | Invite-accept confirmation | — | status `PENDING→ACCEPTED` on first login+pwd change | show status from `/participants` |

---

## 7. Key response shapes (from `api_v1.yaml`)

```ts
// UserOut
{ id:number; login:string; role:'SUPERVISOR'|'ADMIN'|'USER'; /* ADMIN = support */ first_name:string; last_name:string; is_temp_password:boolean }

// ContestOut
{ id:number; name:string; slug:string|null; is_locked:boolean;
  status:'DRAFT'|'RUNNING'|'PAUSED'|'FINISHED';
  total_teams:number; matches_per_round:number; total_rounds:number;
  is_round_robin:boolean; rules_json:object }

// RoundOut
{ id:number; contest_id:number; number:number; deadline:string;
  status:'DRAFT'|'ACTIVE'|'CLOSED'|'CALCULATED'|'PUBLISHED'; matches_count:number;
  kind?:'REGULAR'|'SUPPLEMENTARY'; supplementary_index?:number|null;
  source_round_numbers?:number[] }

// MatchOut
{ id:number; team1:string; team2:string; team1_short:string; team2_short:string; date_time:string;
  score1:number|null; score2:number|null;
  status:'SCHEDULED'|'POSTPONED'|'CANCELED'|'VOID'|'FINISHED' }

// RoundPredictionsView
{ round_id:number; deadline_passed:boolean; matches:MatchOut[]; entries:object[] }

// ScoreDetail (+ B4 count_* once delivered)
{ user_id:number; user_name:string; points_base:number;
  bonus1:number; bonus2:number; bonus3:number;
  total_without_bonus3:number; total_with_bonus3:number; correct_outcomes:number }

// Leaderboard
{ contest_id:number; round_id:number|null; round_number:number|null;
  leaderboard: (ScoreDetail & { rank:number; predictions_count:number;
    exceptional_tiebreak_points:number; tiebreaker_status:null|'manual_override' })[] }

// MatchPoints (Stage 1.17 — results matrix cell)
{ match_id:number; base_points:number|null }

// RoundResultRow (Stage 1.17)
{ user_id:number; user_name:string; points:MatchPoints[];
  bonus1:number; bonus2:number; bonus3:number|null;
  total_without_bonus3:number; total:number; correct_outcomes:number }

// RoundResults
{ round_id:number; matches:MatchOut[]; results:RoundResultRow[] }

// PredictionBatchRequest
{ predictions: { match_id:number; score1:number; score2:number }[] }   // all matches; 0 valid; NULL≠0
```

> `rules_json.constraints.score_validation_range[1]` = `max_score_value` for score inputs (do not hardcode 20). Confirm exact key path against a real `GET /contests/{id}` response during 2.0/2.1; adjust here if it differs.

---

## 8. Client module sketch

```
lib/api/
  client.ts        // fetch wrapper: base url, JWT header, JSON, error parse → AppError {status, detail, code?}
  endpoints.ts     // typed path builders (contestId injected); contestPublic for public LB/results GETs (2.4)
  errors.ts        // code constants + helpers (isTempPasswordBlock, isContestLocked, …)
  cache.ts         // ETag store + If-None-Match (stub — full LB/results ETag wiring deferred 2.4)
types/api.ts       // interfaces from §7
hooks/
  useLeaderboard.ts   // public round leaderboard (2.4)
  useRoundResults.ts  // public results matrix (2.4)
lib/leaderboard/mapLeaderboardRow.ts
lib/results/mapRoundResultsRow.ts
lib/results/roundResultsGuard.ts   // shouldFetchPublicResults(status)
```

`client.ts` responsibilities: inject base URL + Bearer; throw typed `AppError` on non-2xx (parse `detail`/`code`); 401 → emit logout event; expose `get/post/patch/put/del/upload` + `getCached` (ETag). **2.3:** `apiUpload()` for B5 team logo — skips `Content-Type` when body is `FormData`.

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-22 | B1–B3 RESOLVED (Stage 1.8); fallback table for B1/B2/B3; `NEXT_PUBLIC_DEFAULT_CONTEST_ID` naming. |
| 2026-06-23 | Stage 2.1: `fp:unauthorized` custom event (not generic `unauthorized`); Pydantic 422 array parsed in `parseErrorDetail()` (`frontend/src/lib/api/errors.ts`); `localStorage` key `fp_active_contest_id` for contest picker persistence. |
| 2026-06-24 | Stage 2.1.1: §2.4 Post-login routing by role (`resolvePostLoginPath`); `/profile` USER-only; `/admin/*` SUPERVISOR+; demo `user/user` from bootstrap (TEMPORARY until 2.3 invite UI). |
| 2026-06-24 | Stage 2.3: B5 logo multipart via `apiUpload`; extended `contestAdmin` path builders in `endpoints.ts`; admin hook matrix. |
| 2026-06-27 | Stage 1.12: §2.1.1 invite/setup flow (`setup-preview`, `complete-setup`, `request-password-reset`, `ParticipantInviteOut.setup_url`); `PASSWORD_SETUP_REQUIRED` login gate; training mode restore `POST /contests/{id}/restore`. |
| 2026-06-27 | Stage 2.1.2: `resolveAssetUrl()` for team logos; supervisor lifecycle CTAs on parameters page; login «Забыли пароль?» checkbox → `request-password-reset`. |
| 2026-06-28 | Stage 2.3.1 / 2.2 prep: §4.1 public LB/results `PUBLISHED` client gate; `RoundOut` supplementary fields; cross-ref `admin_ui_status_matrix.md`. |
| 2026-06-28 | Stage 2.2.1: GET predictions public post-deadline (no Bearer); visitor pre-deadline 403/stub; removed login prompt. |
| 2026-06-28 | Stage 2.2: predictions GET/POST wired; privacy matrix via `shouldShowScore`; 60s poll pre-deadline. |
| 2026-07-08 | Stage 1.17: `RoundResults` typed — `results[].points[]` with `{ match_id, base_points }` aligned to `matches[]`; `total_without_bonus3` on each row. |
| 2026-07-08 | Stage 2.4: public contest page wired — `contestPublic` paths, `useLeaderboard`/`useRoundResults`, mappers; ETag client wiring deferred. |

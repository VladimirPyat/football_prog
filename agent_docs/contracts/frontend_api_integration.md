# Frontend ↔ API Integration Contract (Stage 2)

> **Living document** — see update log at the bottom.
> **Authoritative API spec:** `agent_docs/contracts/api_v1.yaml` (v1.1.0) + `manuals/API_GUIDE.md`, `manuals/ERROR_LOGGING.md`.
> **Plan:** `agent_docs/plans/draft_2.md` (§7, §12, §13).
> **Rule:** No mocks. Frontend integrates the real backend. Where an endpoint is missing it is a Stage-2 prerequisite (B1–B6, §9), with a documented fallback.

---

## 1. Base configuration

| Item | Value |
|------|-------|
| API base URL | `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) |
| API prefix | `/api/v1` |
| Default contest (dev) | `NEXT_PUBLIC_DEFAULT_CONTEST_ID` (optional convenience) |
| CORS | Backend `cors_origins` default `["*"]` (`config/settings.py`); direct browser→FastAPI calls OK in dev |
| Timestamps | TIMESTAMPTZ, UTC, ISO 8601 — parse as UTC, render local |
| Content type | `application/json` (except team logo upload B5 → `multipart/form-data`) |

**Path builder convention:** all contest data is scoped: `${API}/api/v1/contests/${contestId}/…`. Never call legacy deprecated shims (`/api/v1/rounds`, `/api/v1/leaderboard`, `/api/v1/admin/contest-settings`, `/api/v1/admin/*` without contest) from new code.

---

## 2. Authentication

JWT bearer. Payload `{ sub: user_id, role, exp }`. Default expiry 24h (`jwt_expire_minutes`).

### 2.1 Flow

```
POST /api/v1/auth/login {login, password}
  → 200 {access_token, token_type:"bearer", is_temp_password}
  → 401 {detail:"Неверный логин или пароль"}   (no `code`)

store token (localStorage: fp_access_token)

if is_temp_password === true:
   force redirect /change-password
   POST /api/v1/auth/change-password {old_password, new_password} (Bearer)
     → 200  → is_temp_password cleared server-side

GET /api/v1/auth/me (Bearer) → UserOut {id, login, role, first_name, last_name, is_temp_password}
```

### 2.2 Rules

- Attach `Authorization: Bearer <token>` to every authenticated request.
- While `is_temp_password=true`, backend allows only `/auth/change-password` and `/auth/me`; all mutations return `403`. UI must hard-gate to `/change-password`.
- Test credentials (seed/bootstrap, `manuals/BOOTSTRAP_USERS.md`): `admin/…`, `supervisor/…`; scenarios reference `user/user`.
- Roles: `ADMIN ⊃ SUPERVISOR ⊃ USER`; Visitor = no token.

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

Public GET leaderboard & results return (`manuals/API_GUIDE.md`):

```
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: <16-char sha256 of score state>
```

- ETag changes after calculate / VOID / recalculate.
- Client: store ETag per resource; send `If-None-Match` on refresh; on `304` reuse cached payload (optionally seed from `localStorage`).
- **Never cache:** `GET/POST predictions`, all admin routes, contest PATCH.

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
| POST | `/api/v1/contests/{id}/pause\|resume\|finish` | ADMIN |
| DELETE | `/api/v1/contests/{id}` (body `{confirm:"DELETE"}`) | ADMIN |

### 5.3 Setup (SUPERVISOR+, SETUP phase)
| Method | Path |
|--------|------|
| GET/POST | `/api/v1/contests/{id}/teams` |
| PATCH/DELETE | `/api/v1/contests/{id}/teams/{team_id}` |
| GET/POST | `/api/v1/contests/{id}/participants` |
| DELETE | `/api/v1/contests/{id}/participants/{user_id}` |
| PUT | `/api/v1/contests/{id}/participants/{user_id}/exceptional-tiebreak` (ADMIN, allowed when locked) |

### 5.4 Public / User (contest-scoped)
| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/contests/{id}/rounds` | public |
| GET | `/api/v1/contests/{id}/rounds/{rid}/predictions` | USER+ (privacy) |
| POST | `/api/v1/contests/{id}/rounds/{rid}/predictions` | USER+ |
| GET | `/api/v1/contests/{id}/rounds/{rid}/leaderboard` | public (ETag) |
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
| POST | `/api/v1/contests/{id}/admin/recalculate` (ADMIN) |
| POST | `/api/v1/admin/users/supervisor` (ADMIN, global) |

---

## 6. Backend prerequisites (not in v1.1.0 — see `reports/BLOCKED.md`)

These endpoints/fields are **assumed by the frontend** and tracked as Stage-2 prerequisites. Contracts are pre-specified here so backend & frontend can proceed in parallel. Until delivered, use the listed fallback (never mock).

| # | Proposed endpoint / change | Request | Response (proposed) | Fallback |
|---|----------------------------|---------|---------------------|----------|
| B1 | `GET /api/v1/me/contests` | Bearer | `[{ id, name, status, participant_status }]` | `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B2 | `GET /api/v1/contests/public` | none | `[{ id, name, status }]` (RUNNING/visible) | default contest id |
| B3 | `GET/PATCH /api/v1/auth/me/contacts` | Bearer; PATCH `{email?, vk_id?, tg_id?, notify_enabled?}` | `{email, vk_id, tg_id, notify_enabled}` | read-only stub |
| B4 | Extend `ScoreDetail` | — | + `count_exact_high, count_exact, count_diff, count_outcome` | hide 4 columns |
| B5 | `POST /api/v1/contests/{id}/teams/{team_id}/logo` | `multipart` file | `{ logo_url }` | `logo_url` text input |
| B6 | Invite-accept confirmation | — | status `PENDING→ACCEPTED` on first login+pwd change | show status from `/participants` |

---

## 7. Key response shapes (from `api_v1.yaml`)

```ts
// UserOut
{ id:number; login:string; role:'SUPERVISOR'|'ADMIN'|'USER'; first_name:string; last_name:string; is_temp_password:boolean }

// ContestOut
{ id:number; name:string; slug:string|null; is_locked:boolean;
  status:'DRAFT'|'RUNNING'|'PAUSED'|'FINISHED';
  total_teams:number; matches_per_round:number; total_rounds:number;
  is_round_robin:boolean; rules_json:object }

// RoundOut
{ id:number; contest_id:number; number:number; deadline:string;
  status:'DRAFT'|'ACTIVE'|'CLOSED'|'CALCULATED'|'PUBLISHED'; matches_count:number }

// MatchOut
{ id:number; team1:string; team2:string; date_time:string;
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

// PredictionBatchRequest
{ predictions: { match_id:number; score1:number; score2:number }[] }   // all matches; 0 valid; NULL≠0
```

> `rules_json.constraints.score_validation_range[1]` = `max_score_value` for score inputs (do not hardcode 20). Confirm exact key path against a real `GET /contests/{id}` response during 2.0/2.1; adjust here if it differs.

---

## 8. Client module sketch

```
lib/api/
  client.ts        // fetch wrapper: base url, JWT header, JSON, error parse → AppError {status, detail, code?}
  endpoints.ts     // typed path builders (contestId injected)
  errors.ts        // code constants + helpers (isTempPasswordBlock, isContestLocked, …)
  cache.ts         // ETag store + If-None-Match
types/api.ts       // interfaces from §7
```

`client.ts` responsibilities: inject base URL + Bearer; throw typed `AppError` on non-2xx (parse `detail`/`code`); 401 → emit logout event; expose `get/post/patch/put/del` + `getCached` (ETag).

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-21 | Initial version: auth, errors, caching, endpoint matrix, prerequisites B1–B6, response shapes, client sketch (covers 2.1; 2.2–2.4 to be deepened). |

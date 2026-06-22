# Coder Instructions — Stage 1.8: Contest Discovery & User Contacts

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.6 at `TEST_PASS`.
> Plan: `agent_docs/plans/draft_1.7_frontend_prerequisites.md` §5.3–5.5, §6.2.
> **Language policy:** code comments English; HTTP `detail` Russian (1.5 policy);
> API handler docstrings Russian; manuals English.
> **Note:** User chose to implement **1.8 before 1.7/1.9** — this stage is independent of B4/B6/B5.

## 1. Objective

Close three Stage-2 frontend blockers from `agent_docs/reports/BLOCKED.md`:

| ID | Endpoint | Purpose |
|----|----------|---------|
| **B1** | `GET /api/v1/me/contests` | Authenticated user sees only contests they are enrolled in |
| **B2** | `GET /api/v1/contests/public` | Anonymous Visitor discovers **RUNNING** contests |
| **B3** | `GET/PATCH /api/v1/auth/me/contacts` | Profile contacts (email, VK, TG, notify toggle) |

**Non-goals:** B4 leaderboard counts, B6 invite accept, B5 logo upload (stages 1.7 / 1.9).
No DB migrations — tables `contests`, `contest_participants`, `contacts` already exist.

## 2. Background

- Frontend Stage 2.1 needs contest picker (User) and public home list (Visitor) per `draft_2.md` §13.
- `contest_setup_service.add_participant()` already creates `Contact` rows with invite email.
- `GET /api/v1/contests` remains SUPERVISOR+ only; do not widen its RBAC.

## 3. Scope — files you may create/modify

```
src/api/v1/me.py                         # NEW — GET /me/contests
src/api/v1/contests.py                   # GET /contests/public (route order!)
src/api/v1/auth.py                       # GET/PATCH /auth/me/contacts
src/services/contact_service.py          # NEW
src/services/contest_discovery_service.py  # NEW — list_user_contests, list_public_contests
src/schemas/contest.py                   # UserContestOut, PublicContestOut
src/schemas/auth.py                      # ContactOut, ContactPatchRequest
main.py                                  # register me router
agent_docs/contracts/api_v1.yaml         # bump info.version → 1.2.0-rc; new paths/schemas
manuals/API_GUIDE.md                     # new sections
tests/api/test_me_contests.py            # NEW
tests/api/test_contests_public.py        # NEW
tests/api/test_contacts.py               # NEW
agent_docs/progress/stage_1.md           # append handoff (append-only)
```

**Do NOT modify:** `docs/`, `src/scoring/*`, loader scripts, 1.4–1.6 behaviour unrelated to this scope.

## 4. Schemas

### 4.1 `src/schemas/contest.py`

```python
class UserContestOut(BaseModel):
    id: int
    name: str
    status: str
    participant_status: str  # PENDING | ACCEPTED
    role: str                # global users.role echo (USER | SUPERVISOR | ADMIN)
    slug: str | None = None


class PublicContestOut(BaseModel):
    id: int
    name: str
    status: str
    slug: str | None = None
```

### 4.2 `src/schemas/auth.py`

```python
from pydantic import BaseModel, EmailStr, Field


class ContactOut(BaseModel):
    email: str | None = None
    vk_id: str | None = None
    tg_id: str | None = None
    notify_enabled: bool = False

    model_config = {"from_attributes": True}


class ContactPatchRequest(BaseModel):
    email: EmailStr | None = None
    vk_id: str | None = Field(default=None, max_length=255)
    tg_id: str | None = Field(default=None, max_length=255)
    notify_enabled: bool | None = None
```

Use `model_dump(exclude_unset=True)` on PATCH — only sent fields are updated.

## 5. Service — `contest_discovery_service.py`

```python
async def list_user_contests(
    session: AsyncSession,
    *,
    user_id: int,
    role: str,
) -> list[UserContestOut]:
    """JOIN contests + contest_participants for user; order by contests.name."""


async def list_public_contests(session: AsyncSession) -> list[PublicContestOut]:
    """contests WHERE status = RUNNING, order by name."""
```

Implementation sketch:

```python
from sqlalchemy import select
from database.models import Contest, ContestLifecycleStatus, ContestParticipant

# list_user_contests
rows = await session.execute(
    select(Contest, ContestParticipant.status)
    .join(ContestParticipant, ContestParticipant.contest_id == Contest.id)
    .where(ContestParticipant.user_id == user_id)
    .order_by(Contest.name)
)
return [
    UserContestOut(
        id=c.id,
        name=c.name,
        status=c.status,
        participant_status=part_status,
        role=role,
        slug=c.slug,
    )
    for c, part_status in rows.all()
]

# list_public_contests
contests = await session.scalars(
    select(Contest)
    .where(Contest.status == ContestLifecycleStatus.RUNNING)
    .order_by(Contest.name)
)
return [PublicContestOut.model_validate(c) for c in contests]
```

## 6. Service — `contact_service.py`

```python
async def get_contacts(session: AsyncSession, user_id: int) -> ContactOut:
    """Return Contact row or empty defaults if no row."""


async def upsert_contacts(
    session: AsyncSession,
    user_id: int,
    patch: dict[str, object],
) -> ContactOut:
    """Create or update contacts row; partial patch only."""
```

Rules:

- GET missing row → `ContactOut(email=None, vk_id=None, tg_id=None, notify_enabled=False)`.
- PATCH: load or create `Contact(user_id=...)`, apply only keys present in `patch`.
- Empty string for `email` in JSON → treat as `null` (clear email) before validation.
- Invalid email → `ValidationError` with Russian message → HTTP 400 `VALIDATION_ERROR`.
- Do **not** require `require_not_temp_password` — contacts allowed under temp password (same as `/auth/me`).

## 7. API routes

### 7.1 `src/api/v1/me.py`

| Item | Value |
|------|-------|
| Router | `APIRouter(prefix="/me", tags=["user"])` |
| Route | `GET /contests` → full path `/api/v1/me/contests` |
| Auth | `CurrentUser` (any role) |
| Response | `list[UserContestOut]` |

Docstring (RU): «Список конкурсов, в которых текущий пользователь участвует.»

Register in `main.py` **after** `auth.router`, before or after `contests.router` (order vs `/contests/public` irrelevant).

### 7.2 `src/api/v1/contests.py` — `GET /contests/public`

**Critical:** declare `@router.get("/public", ...)` **before** `@router.get("/{contest_id}", ...)`.

| Item | Value |
|------|-------|
| Auth | None |
| Filter | `status == RUNNING` only |
| Response | `list[PublicContestOut]` |
| Headers | optional `Cache-Control: public, max-age=60` (reuse pattern from `cache_control_header()` or inline 60s) |

Docstring (RU): «Публичный список активных конкурсов для неавторизованных посетителей.»

No `RoleChecker`, no Bearer dependency.

### 7.3 `src/api/v1/auth.py` — contacts

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/auth/me/contacts` | `CurrentUser` | `ContactOut` |
| PATCH | `/auth/me/contacts` | `CurrentUser` | `ContactOut` |

Docstrings (RU):

- GET: «Контактные данные текущего пользователя.»
- PATCH: «Обновить контактные данные (частичное обновление).»

Handlers delegate to `contact_service`; `await session.commit()` in router after PATCH.

## 8. Contract sync (`api_v1.yaml`)

Update `info.version` to **`1.2.0-rc`**.

Add paths:

- `/api/v1/me/contests`
- `/api/v1/contests/public` (document route-order note in description)
- `/api/v1/auth/me/contacts` (get + patch)

Add schemas: `UserContestOut`, `PublicContestOut`, `ContactOut`, `ContactPatchRequest`.

Add tag `user` if missing.

## 9. Documentation — `manuals/API_GUIDE.md`

Add subsections under appropriate headings:

### User contest list (B1)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/me/contests` | Bearer | Enrolled contests with `participant_status` and global `role` |

### Public discovery (B2)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/contests/public` | None | RUNNING contests only |

### User contacts (B3)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auth/me/contacts` | Bearer | Profile contacts |
| PATCH | `/auth/me/contacts` | Bearer | Partial update / upsert |

Note: allowed while `is_temp_password=true`.

Update Implementation Status table with Stage 1.8 row.

## 10. Tests

Create three test modules using `empty_api` / `loaded_api` fixtures from `tests/api/conftest.py`.

### `test_me_contests.py`

| ID | Test |
|----|------|
| `[ME-CONTESTS-USER]` | Invite participant → login as that user → GET `/me/contests` → one item, correct `participant_status`, `role=="USER"` |
| `[ME-CONTESTS-EMPTY]` | New USER with no `contest_participants` → `[]` |
| `[ME-CONTESTS-RBAC]` | No Authorization → 401 |

### `test_contests_public.py`

| ID | Test |
|----|------|
| `[PUBLIC-LIST]` | Seed contests: DRAFT, RUNNING, PAUSED, FINISHED → public list contains **only** RUNNING |
| `[PUBLIC-NO-AUTH]` | No Bearer → 200 |

Use `empty_api` + supervisor creates contests + lifecycle transitions (`pause_contest`, `finish_contest` via API or direct DB) to set statuses.

### `test_contacts.py`

| ID | Test |
|----|------|
| `[CONTACTS-GET-DEFAULT]` | USER without contact row → all nulls, `notify_enabled=false` |
| `[CONTACTS-PATCH]` | PATCH `{vk_id, notify_enabled}` → GET reflects; email unchanged if omitted |
| `[CONTACTS-INVITE]` | POST participant invite → login as invitee → GET contacts → email from invite |
| `[CONTACTS-TEMP-PW]` | User with `is_temp_password=true` can GET/PATCH contacts (200) |

Optional: invalid email → 400 `VALIDATION_ERROR`.

## 11. Acceptance criteria

- [ ] `GET /api/v1/me/contests` returns enrolled contests only; includes `role` + `participant_status`
- [ ] `GET /api/v1/contests/public` returns RUNNING only; no auth; declared before `/{contest_id}`
- [ ] `GET/PATCH /api/v1/auth/me/contacts` upsert works; defaults when row missing
- [ ] Contacts endpoints work under temp password
- [ ] `api_v1.yaml` at 1.2.0-rc with new paths
- [ ] `manuals/API_GUIDE.md` updated
- [ ] All `[ME-*]`, `[PUBLIC-*]`, `[CONTACTS-*]` tests pass
- [ ] `pytest tests/ --ignore=tests/manual` green

## 12. Explicitly OUT OF SCOPE

- `GET /contests` RBAC change (still SUPERVISOR+)
- Per-contest `role_in_contest` column or field
- PAUSED/FINISHED in public list (locked decision: RUNNING only)
- Email send / notification dispatch on `notify_enabled`
- Stage 1.7 (counts, invite accept) and 1.9 (logo upload)

## 13. Implementation order

1. Schemas (`contest.py`, `auth.py`)
2. Services (`contest_discovery_service.py`, `contact_service.py`)
3. Routes (`me.py`, `contests.py` public, `auth.py` contacts)
4. `main.py` router registration
5. `api_v1.yaml`
6. Tests
7. `manuals/API_GUIDE.md`
8. Append progress handoff

## 14. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.8 discovery & contacts)
- STATUS: READY_FOR_TEST
- Blockers closed: B1, B2, B3
- Files: me.py, contest_discovery_service, contact_service, auth contacts, contests/public, ...
- Contract: api_v1.yaml v1.2.0-rc
- Verified: pytest tests/ -> N passed
- Next: agent_docs/instructions/tester_1.8.md
```

## 15. Frontend integration hints (for parallel Stage 2.1 work)

Document in handoff / API guide — frontend can wire immediately after TEST_PASS:

| UI surface | Endpoint | Notes |
|------------|----------|-------|
| Visitor home contest list | `GET /contests/public` | No JWT |
| User «Конкурсы» tab | `GET /me/contests` | Bearer required |
| Profile contacts form | `GET/PATCH /auth/me/contacts` | Partial PATCH |

Fallback until deploy: `NEXT_PUBLIC_DEFAULT_CONTEST_ID` (see `BLOCKED.md`) — frontend-only, not backend.

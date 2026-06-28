# Coder Instructions — Stage 1.16 Fix: Public Predictions After Deadline (Backend)

> **Status gate:** `INSTRUCTIONS_READY`
> **Distinct from:** `coder_1.16_fix_deadline.md` (per-round auto-close — already `IMPLEMENTED`)
> **Prerequisite:** Stage 1.3+ predictions API (`visible_predictions`, `build_round_predictions_view`); 1.16 deadline auto-close shipped
> **Frontend counterpart:** `agent_docs/instructions/coder_2.2.1.md`
> **Follow-up tester:** `agent_docs/instructions/tester_2.2.1.md`
> **Specs:** `docs/03_user_scenarios.md` §4, `agent_docs/contracts/contest_lifecycle_flow.md` §3.3, `agent_docs/contracts/api_v1.yaml`, `agent_docs/contracts/frontend_api_integration.md` §5.4
> **Language policy:** API `detail` Russian; code comments English

---

## 1. Objective

Align GET predictions with product spec: **after round deadline, anyone (including Visitor without JWT) sees the full predictions table**. Before deadline, anonymous callers must **not** receive prediction data.

| ID | Problem | Target |
|----|---------|--------|
| **P1** | `GET …/predictions` requires Bearer → 401 for Visitor | Optional auth; **200 full table** when `now >= deadline` |
| **P2** | `test_pred_visitor_unauthorized` asserts 401 always | Split: **403 pre-deadline**, **200 post-deadline** anonymous |
| **P3** | Contract says `USER+` only | Document **public GET post-deadline**; POST unchanged |
| **P4** | Legacy shim `GET /rounds/{id}/predictions` same 401 | Same rules as contest-scoped route |

**Non-goals:**

- Public GET **before** deadline (Visitor still sees UI stub only; API returns 403)
- Anonymous POST predictions
- ETag / public caching for predictions (keep **no cache** per `frontend_api_integration.md`)
- Changing privacy rules for **authenticated** USER pre-deadline (own scores only)

---

## 2. Spec alignment (LOCKED)

From `docs/03_user_scenarios.md` §4 (Сценарий 4):

| Phase | Visitor |
|-------|---------|
| Pre-deadline | Заглушка — no scores |
| Post-deadline | **Полная таблица** (same as authenticated users) |

Stage 2.2 intentionally deviated (401 → login prompt). **This fix restores spec + `contest_lifecycle_flow.md` §3.3** («Post-deadline — full table for everyone»).

---

## 3. P1 — Route auth: `OptionalUser` (LOCKED)

### 3.1 Contest-scoped route

File: `src/api/v1/contest_ops.py`

Change `get_predictions` dependency from `CurrentUser` to `OptionalUser` (already defined in `api/deps.py`).

```python
@router.get("/rounds/{round_id}/predictions", response_model=RoundPredictionsView)
async def get_predictions(
    contest_id: int,
    round_id: int,
    session: DbSession,
    user: OptionalUser,
    _contest: ContestContext,
) -> RoundPredictionsView:
```

`ContestContext` stays — batch auto-close on contest touch remains valid.

### 3.2 Legacy shim

File: `src/api/v1/predictions.py`

Same change: `user: OptionalUser` on GET handler.

POST handlers on both routers: **keep `CurrentUser`** (no change).

---

## 4. P1 — Handler + service logic (LOCKED)

### 4.1 `build_round_predictions_view`

File: `src/api/handlers/predictions.py`

Signature:

```python
async def build_round_predictions_view(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    user: User | None,
) -> RoundPredictionsView:
```

Flow (after `ensure_round_closed_if_expired`):

1. Compute `deadline_passed` (`now >= deadline` UTC) — same as today.
2. **If `user is None` and not `deadline_passed`:** raise `ContestRuleError` (or `HTTPException` 403) with:
   - `detail`: `"Прогнозы будут доступны после дедлайна"`
   - `code`: `"PREDICTIONS_NOT_PUBLIC"`
3. Call `visible_predictions` with nullable viewer:

```python
viewer_role = user.role if user is not None else None
viewer_id = user.id if user is not None else None
raw = await visible_predictions(session, contest_id, round_id, viewer_role, viewer_id)
```

### 4.2 `visible_predictions`

File: `src/services/prediction_service.py`

Update signature:

```python
async def visible_predictions(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    viewer_role: str | None,
    viewer_id: int | None,
) -> list[dict]:
```

Visibility rule (unchanged semantics, explicit null viewer):

```python
is_privileged = viewer_role == UserRole.ADMIN

for pred in predictions:
    if after_deadline or is_privileged or (viewer_id is not None and pred.user_id == viewer_id):
        # full score row
    else:
        # submitted-only mask
```

When `after_deadline` is true, **anonymous** callers get full scores (viewer_id ignored).

When `after_deadline` is false and `viewer_id is None`, handler must **not** reach this function (403 at §4.1). Do not return masked rows to anonymous pre-deadline — that would leak who submitted.

### 4.3 Admin/support

`ADMIN` with Bearer still sees all scores pre-deadline — unchanged.

---

## 5. Behaviour matrix (acceptance)

| Caller | `now < deadline` | `now >= deadline` |
|--------|------------------|-------------------|
| No token | **403** `PREDICTIONS_NOT_PUBLIC` | **200** full `entries` with scores |
| USER (participant) | **200** own scores; others masked | **200** full table |
| SUPERVISOR | **200** own scores; others masked | **200** full table |
| ADMIN | **200** all scores | **200** full table |
| POST (any) | Bearer required; existing 403 rules | Bearer required; 403 `DEADLINE_PASSED` |

Test round: **9** (`PUBLISHED`, deadline passed) for anonymous 200; **10** after `--e2e` restore (ACTIVE, future deadline) for anonymous 403.

---

## 6. Tests (pytest)

### 6.1 Update existing

File: `tests/api/test_predictions_flow_1_3.py`

| Old | New |
|-----|-----|
| `[API-PRED-VISITOR]` 401 always | **Remove** or replace with two cases below |

### 6.2 New cases

Add to `tests/api/test_predictions_flow_1_3.py` or new `tests/api/test_predictions_public_1_16.py`:

| ID | Case | Expected |
|----|------|----------|
| `[API-PRED-VISITOR-PRE]` | GET round **10** (ACTIVE, future deadline), no token | **403**, `code=PREDICTIONS_NOT_PUBLIC` |
| `[API-PRED-VISITOR-POST]` | GET round **9** (deadline passed), no token | **200**, `deadline_passed=true`, all submitted entries have `predictions` arrays |
| `[API-PRED-VISITOR-POST-SHIM]` | Legacy `GET /api/v1/rounds/{rid}/predictions` round 9, no token | **200** (same body shape) |
| `[API-PRED-USER-PRE]` | Existing privacy tests — no regression | USER sees own only pre-deadline |
| `[API-PRED-POST-AUTH]` | POST without token | **401** unchanged |

Use `loaded_api` fixture + `get_round_id(sf, 9|10)` pattern from existing file.

---

## 7. Contract & docs sync

| File | Change |
|------|--------|
| `agent_docs/contracts/api_v1.yaml` | GET predictions: `security: []` optional bearer; description: anonymous allowed **only** post-deadline; 403 pre-deadline |
| `agent_docs/contracts/frontend_api_integration.md` | §5.4: `GET …/predictions` → **public post-deadline**; remove «visitor 401 → login prompt» |
| `agent_docs/contracts/contest_lifecycle_flow.md` | §3.3: add bullet — anonymous GET **403** pre-deadline, **200** post-deadline |
| `manuals/API_GUIDE.md` | Short subsection under predictions GET |

**Do not** mark `coder_2.2.md` as outdated — behaviour change is documented in this patch + contracts only.

---

## 8. File checklist

| File | Change |
|------|--------|
| `src/api/v1/contest_ops.py` | `OptionalUser` on GET |
| `src/api/v1/predictions.py` | `OptionalUser` on GET |
| `src/api/handlers/predictions.py` | `User \| None`; 403 gate pre-deadline anonymous |
| `src/services/prediction_service.py` | Nullable `viewer_role` / `viewer_id` |
| `tests/api/test_predictions_flow_1_3.py` | Update visitor tests |
| `agent_docs/contracts/api_v1.yaml` | Security + description |
| `agent_docs/contracts/frontend_api_integration.md` | §5.4 matrix |
| `agent_docs/contracts/contest_lifecycle_flow.md` | §3.3 |

---

## 9. Acceptance criteria

- [ ] Anonymous GET round 9 → 200 full predictions
- [ ] Anonymous GET round 10 (ACTIVE, future deadline) → 403 `PREDICTIONS_NOT_PUBLIC`
- [ ] Authenticated pre-deadline privacy unchanged
- [ ] POST predictions still 401 without token
- [ ] `uv run pytest` relevant tests green
- [ ] `uv run ruff check` / `mypy` on touched `src/` files

---

## 10. Execution order

```text
1. backend/coder_1.16_fix_public_predictions.md (this) — API + tests + contracts
2. coder_2.2.1.md                         — frontend visitor matrix
3. tester_2.2.1.md                        — regression + new E2E
```

Mark `READY_FOR_TEST` in `agent_docs/progress/stage_2.md` when done (append-only).

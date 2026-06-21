# Tester Instructions — Stage 1.4.1: Scenario Gap Patch

> **Patch** to `tester_1.4.md`. Apply after or alongside 1.4 main suite.
> Prerequisite: Coder 1.4 `READY_FOR_TEST`; 1.3 `TEST_PASS`.
> Do NOT modify `src/`. Code/comments English; report Russian.

## 1. Why this patch exists

Audit of `tester_1.4.md` against:
- `docs/03_user_scenarios.md` (User / Visitor)
- `docs/04_supervisor_scenario.md` (Supervisor / Admin)
- `agent_docs/contracts/api_v1.yaml` (Stage 1.4 contract)

**Findings:**
- Core operational flow (setup → predict → close → result → calculate → 90/90) is covered.
- **Safe delete** lifecycle (`DELETE /contests/{id}`) exists in API but was **only** in 1.3 legacy tests — not contest-scoped in 1.4.
- Several supervisor/user behaviours rely on **1.3 regression** (`tests/api/`) or are **implicit** in E2E helpers — not explicit `[TEST-ID]` on contest-scoped paths.
- **Newsletters** (supervisor §4), **contacts/profile** (user §2), **Playwright E2E** — out of Stage 1 backend scope (documented below, not tested).

## 2. Scenario coverage matrix

Legend: ✅ explicit in 1.4 | 🔄 1.3 regression only | ➕ added in 1.4.1 | ⏭ out of scope

### User scenarios (`docs/03_user_scenarios.md`)

| Scenario / UC | API endpoints (contest-scoped) | 1.4 coverage | 1.4.1 |
|---------------|-------------------------------|--------------|-------|
| §1 Leaderboard (Visitor) | `GET .../leaderboard`, `GET .../rounds/{id}/leaderboard` | ✅ `[API-LB-GLOBAL]`, `[API-CACHE]` | — |
| §1 Round list / results nav | `GET .../rounds`, `GET .../rounds/{id}/results` | 🔄 E2E helper + 1.3 shim | ➕ `[OP-ROUNDS-LIST]` smoke |
| §2 Auth login / temp password | `POST /auth/login`, `POST /auth/change-password` | 🔄 `tests/api/` 1.3 | ➕ `[SETUP-PART-AUTH]` invite→login |
| §3 Batch predictions 8/8 | `POST .../rounds/{id}/predictions` | ✅ `[OP-PRED]`, `[OP-PRED-DEADLINE]` | — |
| §4 Privacy pre/post deadline | `GET .../rounds/{id}/predictions` | 🔄 1.3 `[API-PRED-PRIVACY]` | ➕ `[OP-PRED-PRIVACY]` contest-scoped |
| §4 Visitor predictions | same GET without token | 🔄 1.3 `[API-PRED-VISITOR]` | — (regression) |
| Profile / contacts | — | ⏭ no API in Stage 1 | — |
| Playwright E2E | — | ⏭ frontend stage | — |

### Supervisor scenarios (`docs/04_supervisor_scenario.md`)

| Scenario / UC | API endpoints | 1.4 coverage | 1.4.1 |
|---------------|---------------|--------------|-------|
| §1 Parameters readonly after start | `GET/PATCH .../contests/{id}` | ✅ `[SETUP-PATCH]`, `[OP-ACTIVATE]`, locks | — |
| §2 Participants CRUD + invite | `.../participants` | ✅ `[SETUP-PART]`, `[SETUP-PART-LOCK]` | ➕ `[SETUP-PART-AUTH]` |
| §3 Teams CRUD | `.../teams` | ✅ `[SETUP-TEAMS]`, `[SETUP-TEAMS-LOCK]` | — |
| §4 Newsletters | — | ⏭ Coder 1.4 OUT OF SCOPE | — |
| §5 Create round + activate | `POST .../admin/rounds`, `.../activate` | 🔄 E2E helper only | ➕ `[OP-ROUND-CREATE]` smoke |
| §6 Edit ACTIVE round (pre-deadline) | `PATCH .../admin/rounds/{id}` | ❌ missing | ➕ `[OP-ROUND-EDIT]` |
| §7 Free Tour | `POST .../admin/rounds/free-tour` | ✅ `[OP-FREE-TOUR]` | — |
| §8 Enter results after deadline | `PUT .../admin/matches/{id}/result` | ✅ `[OP-RESULT-GUARD]`, `[OP-RESULT-OK]` | — |
| §9 VOID match | `PATCH .../admin/matches/{id}/status` | ✅ `[OP-VOID]`, `[API-VOID]` | — |
| §10 24h deadline rule | `PATCH .../admin/rounds/{id}` | ❌ missing | ➕ `[OP-24H-RULE]` |
| Pause / resume | `POST .../pause`, `.../resume` | ✅ `[OP-PAUSE]` | — |
| Early finish | `POST .../finish` | ❌ missing | ➕ `[API-CONTEST-FINISH]` |
| Safe delete | `DELETE .../contests/{id}` | ❌ (1.3 legacy only) | ➕ `[API-CONTEST-DELETE-*]` |
| Admin recalculate | `POST .../admin/recalculate` | ❌ missing | ➕ `[OP-RECALC]` |
| Exceptional tie-break | `PUT .../participants/{id}/exceptional-tiebreak` | ✅ `[API-TB-*]` | — |
| Audit log | — | ⏭ not in Stage 1 API | — |

### API contract completeness (`api_v1.yaml`)

All Stage 1.4 **contest-scoped** endpoints are defined in `api_v1.yaml`. Legacy shims cover 1.3 regression paths.

**Gaps are in test coverage, not missing routes** — except contacts/newsletters (future stages).

## 3. Scope — files to create/extend

```
tests/api/conftest.py                          # EXTEND: delete_api_contest fixture (instant delete env)
tests/api/test_contest_lifecycle_1_4.py        # NEW — [API-CONTEST-DELETE-*], finish, contest-scoped
tests/api/test_operational_gaps_1_4.py        # NEW — privacy, 24h, round edit, recalc, rounds list
tests/api/test_canary_scoring_1_4.py           # NEW — [CANARY-PYTEST-*] automated oracle check
```

Update `tester_1.4.md` execution (§10): run full suite including 1.4.1 files.

## 4. Safe delete — contest-scoped (`[API-CONTEST-DELETE-*]`)

**File:** `tests/api/test_contest_lifecycle_1_4.py`

Use **contest-scoped** paths: `/api/v1/contests/{contest_id}/...`

Fixtures:
- `loaded_contest_api` — loader DB, `CONTEST_ALLOW_INSTANT_DELETE=false`, contest id=1
- `delete_contest_api` — isolated DB, `CONTEST_ALLOW_INSTANT_DELETE=true`

Reuse helpers from `tests/api/conftest.py` (`api_login`, `auth_header`, `ensure_contest_running`); extend for `contest_id` if needed.

| TEST-ID | Description | Expected |
|---------|-------------|----------|
| `[API-CONTEST-FINISH]` | POST `.../finish` from RUNNING → FINISHED; predictions → 403; public GET → 200 | 200 |
| `[API-CONTEST-FINISH-IDEM]` | second finish → 200 no-op | 200 |
| `[API-CONTEST-PAUSE-BLOCK]` | predictions while PAUSED → 403 (contest-scoped POST predictions) | 403 |
| `[API-CONTEST-DELETE-RBAC]` | DELETE as SUPERVISOR → 403 | 403 |
| `[API-CONTEST-DELETE-NOGRACE]` | DELETE immediately after pause (`instant=false`) → 400 | 400 |
| `[API-CONTEST-DELETE-BADCONFIRM]` | body `{confirm:"NOPE"}` → 422 or 400 | 422/400 |
| `[API-CONTEST-DELETE-OK]` | pause → DELETE `{confirm:"DELETE"}` with instant=true → 200; contest wiped / DRAFT | 200 |

**Note:** `[API-CONTEST-DELETE-NOGRACE]` validates production `_ensure_utc_aware()` — **no** conftest monkeypatch.

Also keep 1.3 legacy delete tests in `tests/api/test_contest_lifecycle_1_3.py` as regression (shim paths).

## 5. Operational gaps — contest-scoped (`[OP-*]` supplement)

**File:** `tests/api/test_operational_gaps_1_4.py`

| TEST-ID | Maps to | Description |
|---------|---------|-------------|
| `[OP-PRED-PRIVACY]` | User §4, UC-8/9 | Before deadline: others' scores hidden; after deadline: full table. Contest-scoped GET predictions. |
| `[OP-24H-RULE]` | Supervisor §10, UC-6 | PATCH round deadline violating 24h rule → 400 |
| `[OP-ROUND-EDIT]` | Supervisor §6 | PATCH ACTIVE round: change match datetime before deadline → 200 |
| `[OP-ROUND-CREATE]` | Supervisor §5, UC-5 | POST admin round DRAFT with 8 matches, unique teams → 200 |
| `[OP-ROUNDS-LIST]` | User §1 | GET `.../rounds` public → list includes round numbers |
| `[OP-RECALC]` | Admin override | POST `.../admin/recalculate` as ADMIN → 200; USER → 403 |
| `[SETUP-PART-AUTH]` | Supervisor §2, UC-3 | POST participant → temp password → login → change-password → predictions OK |

## 6. Canary — scoring not hardcoded (`[CANARY-*]`)

### Already in `tester_1.4.md` (do not skip)

| Artifact | Purpose |
|----------|---------|
| §8 Script 2 | `compare_db_vs_reference.py` — DB vs CSV; **CANARY:** edit CSV → must fail |
| §8a §5 | Step-by-step **manual CANARY** for project owner (Russian) |
| §8a §8 | Acceptance checklist includes CANARY fail → revert → pass |
| Deliverable | `manuals/MANUAL_SCORING_VERIFICATION.md` — full human guide |

**Owner manual flow (summary):**
1. Run Script 1 (`verify_via_api.py`) — builds contest via HTTP, no expected CSV values in script.
2. Run Script 2 (`compare_db_vs_reference.py`) — compares DB `scores` to `expected_scores.csv`, leaderboard to `leaderboard.csv` → **must PASS**.
3. **CANARY:** edit one cell in `expected_scores.csv` (or `predictions.csv` + re-submit) → Script 2 (or pytest) **must FAIL** with login/round mismatch → revert → **PASS**.

### New automated canary (1.4.1)

**File:** `tests/api/test_canary_scoring_1_4.py`

| TEST-ID | Description |
|---------|-------------|
| `[CANARY-PYTEST-ORACLE]` | After `[API-RESULTS]` fixture data loaded: copy `expected_scores.csv` to temp dir, corrupt one `expected_total`, run comparison helper → assert failure with row detail |
| `[CANARY-PYTEST-REVERT]` | Same temp oracle restored → assert pass |

Implementation: use `tmp_path` + `shutil.copy` — **never** modify files under `docs/test_data/contracted/`.

Optional: `[CANARY-PYTEST-PRED]` — corrupt prediction input in test DB (not CSV) → `[API-RESULTS]` fails for that row.

Report CANARY results in `test_1.4.md` § «Canary verification».

## 7. Explicitly out of scope (document in report, do not test)

| Item | Source | Reason |
|------|--------|--------|
| Newsletters / scheduled email | Supervisor §4 | Coder 1.4 §9 OUT OF SCOPE |
| Contacts CRUD | User §2 | No API in `api_v1.yaml` Stage 1 |
| Personal statistics | User §2 | UI stub only |
| Playwright browser E2E | Both docs | Stage 1 = backend HTTP + manual scripts |
| Audit log endpoint | Supervisor §9 | Not in Stage 1 API |

## 8. Execution

```bash
# Full Stage 1.4 + 1.4.1
uv run pytest tests/api/ -v

# 1.4.1 patch only
uv run pytest tests/api/test_contest_lifecycle_1_4.py \
  tests/api/test_operational_gaps_1_4.py \
  tests/api/test_canary_scoring_1_4.py -v

# Manual canary (owner)
uv run python tests/manual/compare_db_vs_reference.py --contest-id 1
# edit expected_scores.csv (local copy or canary branch) → re-run → must fail
```

Append to `agent_docs/reports/test_1.4.md` table all new `[TEST-ID]` rows.

## 9. Verdict addition (Russian, for user)

Патч 1.4.1 закрывает пробелы: **safe delete** на contest-scoped API, finish contest, privacy/24h/round-edit/recalc на primary paths, **CANARY** (ручной + pytest). Сценарии рассылок и профиля — вне Stage 1. Legacy 1.3 тесты остаются регрессией.

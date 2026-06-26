# Tester Instructions — Stage 2.1.2 Fix: Supervisor UI QA Fixes

> **Status gate:** @Coder `READY_FOR_TEST` for 2.1.2 fix.
> **Coder spec:** `agent_docs/instructions/coder_2.1.2_fix_supervisor.md`
> **Prerequisite:** `tester_1.12_fix.md` **TEST_PASS** (B11/B12 API); Stage 2.3 admin shell exists.
> **Report:** `agent_docs/reports/test_2.1.2_fix_supervisor.md`
> **Reference screens:** `docs/screens/supervisor_*.jpg` (descriptive; routes may be `/admin/*` until 1.13 rename)
> **Strategy:** Vitest unit + manual supervisor walkthrough + selective Playwright; **do not modify** `src/` unless test-only.

---

## 1. Objective

Verify supervisor UI fixes from manual QA (`coder_2.1.2_fix_supervisor.md`):

| # | Area | Tags |
|---|------|------|
| 1 | Parameters — scoring rules + lifecycle buttons | `[UI-PARAM-RULES]`, `[UI-PARAM-LIFE]` |
| 2 | Teams — default + uploaded logos | `[UI-TEAMS-LOGO]` |
| 3 | Rounds — create tour + status sidebar + close | `[UI-ROUNDS-CREATE]`, `[UI-ROUNDS-SIDEBAR]`, `[UI-ROUNDS-CLOSE]` |
| 4 | Results — save workflow + Russian labels | `[UI-RESULTS-SAVE]`, `[UI-RESULTS-LABELS]` |
| 5 | Participants — invite modal content | `[UI-PART-INVITE]` |
| 6 | Login — password recovery checkbox | `[UI-LOGIN-RESET]` |

**Non-goals:**

- Backend B11/B12 implementation → `tester_1.12_fix.md`
- Route rename → `tester_1.13_supervisor_rename.md`
- Full newsletter UI
- Full E2E suite rewrite (spot-check + unit only unless gaps found)

---

## 2. Test environment

### 2.1 Backend + bootstrap

```bash
cd /work/football_prog
uv run python src/scripts/dev_setup.py
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

For **invite** tests use **DRAFT unlocked** contest (create via API or env `NEXT_PUBLIC_DEFAULT_CONTEST_ID` pointing to fresh contest). Contest `id=1` after dev_setup is **RUNNING + locked** → invite returns `403 CONTEST_LOCKED`.

Recommended: helper `createDraftContest()` from E2E fixtures or manual API before participants test.

### 2.2 Frontend

```bash
cd frontend
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

For lifecycle buttons (pause/resume): `SUPERVISOR_TRAINING_MODE=true` in backend `.env` if testing finish/delete UI from 1.12.

For login reset checkbox: `request-password-reset` API must exist (1.12).

### 2.3 Credentials

| Role | Login | Password |
|------|-------|----------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` |
| USER | `user` | `user` |

---

## 3. Scope — files you may create/modify

```
agent_docs/reports/test_2.1.2_fix_supervisor.md
frontend/e2e/supervisor_ui_fix_smoke.spec.ts   # optional NEW — minimal smoke
```

**Do NOT modify** `src/` components (Coder scope). Test/fixtures only.

---

## 4. Unit tests (Vitest)

Run after Coder delivery:

```bash
cd frontend && npm run test:unit -- --run rulesDisplay deriveAdminUiMode
```

### 4.1 `[UNIT-RULES-DISPLAY]`

`rulesDisplay.ts` (or equivalent):

- Parses `contest_defaults.json` shape → non-empty «Основные очки» + «Бонусы» labels
- Russian labels for `exact_score`, `bonus_2_thresholds`, etc.

### 4.2 `[UNIT-UI-MODE-ROUNDS]`

`deriveAdminUiMode`:

- ACTIVE round + `deadlinePassed` → `canEnterResults === false`
- CLOSED round → `canEnterResults === true`
- `canCreateRound` true when no DRAFT and not disabled

### 4.3 `[UNIT-RESOLVE-ASSET]`

If exported: `resolveAssetUrl('/static/assets/default-team-logo.jpg')` prefixes `NEXT_PUBLIC_API_URL`.

---

## 5. Manual supervisor walkthrough

Use supervisor login. Paths: `/admin/…` **or** `/supervisor/…` depending on whether 1.13 landed — document which in report.

### 5.1 `[UI-PARAM-RULES]` Parameters page

1. Open settings → parameters on **RUNNING** contest (e.g. id=1).
2. **PASS** if:
   - Structural fields visible (teams, rounds, matches per round) — readonly when locked
   - **Scoring section not empty** — labels like «За точный счёт», «Бонус 1…» (not raw JSON keys)
   - Two-column layout approximates `supervisor_settings.jpg`
   - Lock banner mentions scoring/teams immutable

### 5.2 `[UI-PARAM-LIFE]` Lifecycle CTA

On same page (requires B12 from 1.12):

| Contest status | Expected control |
|----------------|----------------|
| RUNNING | Red **«Остановить конкурс»** → pause works, toast/banner |
| PAUSED | Green **«Запустить конкурс»** → resume |
| DRAFT (fresh contest) | Link to rounds / hint to activate |

Visible for **supervisor** role (not ADMIN-only).

### 5.3 `[UI-TEAMS-LOGO]` Teams logos

On DRAFT contest settings → teams:

1. Default logo visible (no broken image) — Network: `GET {API}/static/assets/default-team-logo.jpg` **200**
2. Upload custom logo → displays `{API}/static/teams/{cid}/{tid}.jpg` **200**

### 5.4 `[UI-ROUNDS-CREATE]` Create tour while RUNNING

On `/admin/rounds` with RUNNING contest, **no existing DRAFT**:

1. **«Создать тур»** / `RoundBuilderForm` visible (not hidden when viewing ACTIVE tour)
2. Submit draft → success toast; new round appears in selector as DRAFT

### 5.5 `[UI-ROUNDS-SIDEBAR]` Status sidebar

Select a tour:

1. Sidebar/card shows: status badge (Russian), team count, max matches, match count
2. ACTIVE tour shows info «ТУР АКТИВИРОВАН…»

### 5.6 `[UI-ROUNDS-CLOSE]` Close tour after deadline

Contest with ACTIVE round past deadline (test data round 9 or API-set deadline):

1. **«Закрыть тур»** visible on rounds page
2. Click → round becomes CLOSED; appears in results dropdown

### 5.7 `[UI-RESULTS-SAVE]` Results workflow

1. Select **CLOSED** tour on results page
2. Enter scores → **«Применить»** / save per row → success toast
3. All matches finished → **«Рассчитать»** → **«Опубликовать»** succeed
4. If only ACTIVE+deadline passed: amber banner + **«Закрыть тур»** on results page

### 5.8 `[UI-RESULTS-LABELS]` Russian match status

Match status column shows Russian (e.g. «Запланирован», «Завершён») — not raw `SCHEDULED`/`FINISHED`.

### 5.9 `[UI-PART-INVITE]` Invite modal

On DRAFT contest → participants → invite:

1. Modal shows **login**, **temp password**, **setup link** (copy buttons)
2. Table shows «Ожидает» / «Принято» via `participantStatusLabel`

### 5.10 `[UI-LOGIN-RESET]` Password recovery checkbox

On login modal and `/staff/login`:

1. Checkbox **«Забыли пароль?»** present, unchecked by default
2. Check → email field + **«Отправить ссылку для восстановления»**
3. Submit valid email → success message (privacy-safe, no email enumeration)
4. Invalid/network → error shown appropriately
5. Uncheck hides block

Requires 1.12 `POST /auth/request-password-reset`.

---

## 6. Optional Playwright smoke

If adding `supervisor_ui_fix_smoke.spec.ts`:

```ts
// Minimal: supervisor → parameters → scoring text visible
// supervisor → login modal → forgot password checkbox toggles email field
```

Run:

```bash
cd frontend && npx playwright test supervisor_ui_fix_smoke.spec.ts
```

---

## 7. Lint & build

```bash
cd frontend && npm run lint && npm run type-check && npm run format:check
cd frontend && npm run build
```

---

## 8. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-FE-INTEGRATION]` | `frontend_api_integration.md` changelog: resolveAssetUrl, lifecycle UI, login reset |
| `[DOC-UI-PAGES]` | Coder updated `agent_docs/ui/pages.md` paths if changed |

---

## 9. Exit criteria

| Gate | Requirement |
|------|-------------|
| **TEST_PASS** | All §4–§5 tags PASS; lint/build green |
| **TEST_FAIL** | `test_2.1.2_fix_supervisor.md` with screenshots/steps; assign @Coder |

**Order:** run **after** `tester_1.12_fix.md`; run **before** or **after** `tester_1.13_supervisor_rename.md` (adjust paths in steps if 1.13 already merged).

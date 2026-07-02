# Audit: `admin` vs `SUPERVISOR` vs `ADMIN` in documentation

> **Status:** REPORT ONLY — no files changed (per request).  
> **Date:** 2026-07-02  
> **Scope:** `docs/` (immutable specs), `manuals/`, `agent_docs/`, `README.md`, `.env.example`, `frontend/.env.local.example`  
> **Out of scope:** application code, API path strings, route segments, `config/settings.py` (env rename noted separately).

---

## 1. Canonical model (as documented today)

| Concept | Code / API reality | Who does what |
|--------|---------------------|---------------|
| **SUPERVISOR** | `users.role = SUPERVISOR` | **Organizer** — creates contest, invites participants, rounds, results, calculate/publish |
| **ADMIN** | `users.role = ADMIN` | **Technical staff / support** — lifecycle overrides, recalculate, restore deleted contest, create SUPERVISOR accounts, pre-deadline prediction visibility for troubleshooting |
| **`/admin/*` UI** | `frontend/src/app/admin/*` | **Organizer workspace** — reachable by `SUPERVISOR+` (both roles) |
| **`…/contests/{id}/admin/*` API** | `contest_ops.py`, `admin_rounds.py`, … | **Organizer operations** — `SUPERVISOR+` |
| **`/api/v1/admin/users/*` API** | `admin_users.py` | **Platform support only** — `ADMIN` creates global organizers |

**Root confusion:** paths and folders say `admin`, but most documented behaviour is **organizer (SUPERVISOR)** work. The **ADMIN role** is easy to read as “the admin panel user”.

**Approved replacement rules (2026-07-02 clarification):**

| Case | Action |
|------|--------|
| **ADMIN role / техподдержка** | In **documents only:** `admin` → **support** (проза, заголовки, env-имена) |
| **Организатор конкурса** | Слово `admin` **не убираем**; при необходимости дополняем: «…admin… **(supervisor)**» |
| **Пути `/admin/…`, `…/admin/…` в API** | **Не менять** ни в коде, ни в документах |
| **Код (routes, modules, handlers)** | **Не менять** |
| **Исключение — env** | `SEED_ADMIN_*` → `SEED_SUPPORT_*` (+ код настроек при отдельном коммите) |

**Already planned but deferred:** full path rename `admin → supervisor` in API/UI — [`coder_1.13_supervisor_rename.md`](../instructions/backend/coder_1.13_supervisor_rename.md) (not in current scope).

---

## 2. `docs/` — immutable specs (audited 2026-07-02)

> **Note:** `docs/` is **read-only** for agents (`.cursorrules`). Changes require human sync (`/docs-git-sync` / `/polish`). Below: line-level audit only.

### 2.1 Summary by file

| File | Hits | Verdict |
|------|------|---------|
| [docs/01_tech_regulations.md](../../docs/01_tech_regulations.md) | 16 | 5× **B** (support rename), 1× **C** (админ-панель), rest OK (Supervisor) |
| [docs/02_project_structure.md](../../docs/02_project_structure.md) | 3 | 1× **A-path** (keep), 1× false positive (`async support`), 1× OK (организатором) |
| [docs/03_user_scenarios.md](../../docs/03_user_scenarios.md) | 1 | 1× **B** |
| [docs/04_supervisor_scenario.md](../../docs/04_supervisor_scenario.md) | 22 | 7× **A-path** (keep), 2× **B**, rest OK |
| [docs/05_frontend.md](../../docs/05_frontend.md) | 2 | OK (Supervisor) |
| [docs/06_front_tests.md](../../docs/06_front_tests.md) | 2 | 1× **C** |
| [docs/roadmap.csv](../../docs/roadmap.csv) | 1 | OK (Supervisor) |

### 2.2 `01_tech_regulations.md` — line detail

| Line | Text (short) | Tag | Proposed doc edit |
|------|--------------|-----|-------------------|
| 21 | `### 1.1 Supervisor (Организатор)` | OK | — |
| 27 | `### 1.2 Admin (Технический администратор)` | **B** | `### 1.2 Support (Техническая поддержка)` + footnote `users.role = ADMIN` |
| 30 | Назначает Supervisor'ов | OK | — |
| 45 | Администратор прописывается в конфиге… назначает организатора | **B** | Support прописывается в конфиге… |
| 162 | `role: UserRole # SUPERVISOR, ADMIN, USER` | **B** | `# SUPERVISOR, ADMIN (support), USER` |
| 248 | Supervisor… через **админ-панель** | **C** | …через **админ-панель (supervisor)** или «панель организатора»; путь `/admin/*` не трогать |
| 313 | `[UC-13] Admin override + пересчет` | **B** | `[UC-13] Support override + пересчет` |

Остальные вхождения `Supervisor` / `организатор` — корректны.

### 2.3 `02_project_structure.md`

| Line | Text | Tag | Action |
|------|------|-----|--------|
| 10 | `async support` | — | **Не трогать** (ORM feature, не роль) |
| 28 | `POST /admin/results/apply` | **A-path** | **Не менять** путь; опционально сноска: «organizer API (supervisor)» |
| 46 | ввод матчей… **организатором** | OK | — |

### 2.4 `03_user_scenarios.md`

| Line | Text | Tag | Proposed edit |
|------|------|-----|---------------|
| 59 | `Admin меняет deadline в БД` (E2E) | **B** | `Support меняет deadline в БД` (тестовый хак техперсонала) |

### 2.5 `04_supervisor_scenario.md`

| Lines | Text | Tag | Action |
|-------|------|-----|--------|
| 14, 21, 29, 36, 45, 71 | `Маршрут: /admin/…` | **A-path** | **Не менять** URL |
| 81 | `только Admin override` | **B** | `только support override` (`ADMIN` role) |
| 114–127 | `POST /api/v1/admin/rounds` etc. | **A-path** | **Не менять** |
| 142 | `[UC-13] Admin override` | **B** | `[UC-13] Support override` |
| 1, 9, 42, 68, 93–106, 112 | Supervisor / e2e/supervisor_* | OK | — |

### 2.6 `05_frontend.md`, `06_front_tests.md`, `roadmap.csv`

| File | Line | Text | Tag | Proposed edit |
|------|------|------|-----|---------------|
| 05_frontend.md | 24, 56 | SUPERVISOR / Supervisor UI | OK | — |
| 06_front_tests.md | 12 | `supervisor_create_round.spec.ts` | OK | — |
| 06_front_tests.md | 13 | `admin flow` | **C** | `supervisor flow` или `admin flow (supervisor)` |
| roadmap.csv | 5 | Visitor/User/**Supervisor** | OK | — |

### 2.7 `docs/` — what is already well-defined

[01_tech_regulations.md](../../docs/01_tech_regulations.md) §1.1–1.2 **уже разделяет** Supervisor и Admin — после правки §1.2 станет эталоном для `manuals/` и `agent_docs/`.

[04_supervisor_scenario.md](../../docs/04_supervisor_scenario.md) заголовок и скриншоты `supervisor_*` — правильная терминология; путаница только в сегментах URL `admin` (оставляем как есть).

---

## 3. Environment files

### `/.env.example`

| Line / symbol | Current | Likely intent | Suggested doc rename |
|---------------|---------|---------------|----------------------|
| Comment L15 | `admin / supervisor` | bootstrap logins | `support / supervisor` |
| `SEED_ADMIN_PASSWORD` | tech staff password | **ADMIN role** | `SEED_SUPPORT_PASSWORD` (+ hash variant) |
| `SEED_SUPERVISOR_PASSWORD` | organizer password | **SUPERVISOR** | keep |

**Risk note:** Renaming env vars requires `config/settings.py`, `bootstrap_users.py`, tests, E2E — you said admin UI for support is not built yet, so **low runtime risk**, but **grep-wide** update needed when you execute.

### `/frontend/.env.local.example`

| Symbol | Current | Intent |
|--------|---------|--------|
| `E2E_ADMIN_PASSWORD` | matches `SEED_ADMIN_PASSWORD` | E2E login as **ADMIN/support** role |
| Comment L4 | `supervisor UI` | correct — organizer datetime |

Suggested: `E2E_SUPPORT_PASSWORD` when env rename lands.

### Related (not `.md`, for follow-up)

- `config/settings.py` — `seed_admin_login` (default `admin`), `SEED_ADMIN_*` field names
- `README.md` L44 — `SEED_ADMIN_PASSWORD`

---

## 4. Taxonomy of replacements

When you give the go-ahead, treat each hit as one of:

| Tag | Meaning | Doc action |
|-----|---------|------------|
| **A-path** | `/admin/…` or `…/admin/…` in URLs, curl, tables | **Do not rename** (matches code). Optional one-time gloss: «path `admin` = organizer (supervisor)» |
| **B-role** | ADMIN role, техподдержка, `login admin`, `SEED_ADMIN_*`, «Admin override» | **`admin` → `support`** in prose; enum `ADMIN` may stay with «(support)» |
| **C-organizer** | «admin UI», «админка», «admin flow» — **human text** about organizer | **Keep `admin` word** where tied to `/admin/` product name; **add `(supervisor)`** or replace with «организатор» / «supervisor» **only in free prose**, not in paths |
| **D-correct** | `notify_admin()`, existing «support/troubleshooting» | Optional `notify_support` in docs only |
| **E-code-ref** | `lib/admin/*`, file paths in citations | **No rename** |

---

## 5. `manuals/` — file-by-file

| File | ~hits | Primary issue | Tags |
|------|-------|---------------|------|
| [API_GUIDE.md](../../manuals/API_GUIDE.md) | 69 | RBAC mixes `SUPERVISOR+` with `/admin/*` paths; L174 “or **admin UI**” = organizer; L157 already says “support/troubleshooting” for ADMIN | A, B, C |
| [SUPERVISOR_TESTING_SCENARIOS.md](../../manuals/SUPERVISOR_TESTING_SCENARIOS.md) | 51 | “админка”, `/admin/*` everywhere; X-rows correctly say **ADMIN** for lifecycle | A, C, B |
| [FRONTEND_REFERENCE.md](../../manuals/FRONTEND_REFERENCE.md) | 45 | “Admin top nav”, “Supervisor **admin UI**”, route table `/admin/*` | C, A |
| [STATUS_REFERENCE.md](../../manuals/STATUS_REFERENCE.md) | 29 | “админка”, `/admin/…` API examples, `lib/admin/*` paths | A, C, E |
| [CONFIG.md](../../manuals/CONFIG.md) | 29 | `SEED_ADMIN_*`, `seed_admin_login`, bootstrap ADMIN | B |
| [DEV_SETUP.md](../../manuals/DEV_SETUP.md) | 21 | login table `admin` + `SEED_ADMIN_PASSWORD`; “admin shell” = organizer | B, C |
| [BOOTSTRAP_USERS.md](../../manuals/BOOTSTRAP_USERS.md) | 21 | §4 title “organizer API” but “Login as **admin**” = correct **support** login; L101 “admin UI” = organizer product UI | B, C |
| [ARCHITECTURE.md](../../manuals/ARCHITECTURE.md) | 11 | diagram “admin router”, “SUPERVISOR — admin ops”, lifecycle “ADMIN pause” | A, B |
| [DEPLOYMENT.md](../../manuals/DEPLOYMENT.md) | 5 | `SEED_ADMIN_PASSWORD`; “admin UI modal” = organizer invite modal | B, C |
| [DB_REFERENCE.md](../../manuals/DB_REFERENCE.md) | 3 | Correct: SUPERVISOR = organizer, ADMIN = technical | B (label only) |
| [SCORING_LOGIC.md](../../manuals/SCORING_LOGIC.md) | 2 | “admin-set” tiebreak = **ADMIN/support** | B |
| [MANUAL_SCORING_VERIFICATION.md](../../manuals/MANUAL_SCORING_VERIFICATION.md) | 1 | `POST …/admin/rounds/…/calculate` path | A |
| [README.md](../../manuals/README.md) | 1 | pointer to SUPERVISOR doc | — |

**Highest-impact manual:** `SUPERVISOR_TESTING_SCENARIOS.md` + `API_GUIDE.md` + `FRONTEND_REFERENCE.md` — most QA copy uses “админка” for organizer workspace.

---

## 6. `agent_docs/` — summary by area

**~70 markdown files** contain `admin`/`ADMIN` (many are historical test reports).

### 6.1 Living contracts (update early)

| File | Issue |
|------|--------|
| [contracts/frontend_api_integration.md](../contracts/frontend_api_integration.md) | `/admin/*` routing for SUPERVISOR; contest `…/admin/…` endpoint list |
| [contracts/admin_ui_status_matrix.md](../contracts/admin_ui_status_matrix.md) | **Filename** says admin; content = organizer UI phases; L353 “support” for ADMIN already |
| [contracts/contest_lifecycle_flow.md](../contracts/contest_lifecycle_flow.md) | “ADMIN sees all (support)” — good pattern to replicate |
| [contracts/ERROR_LOGGING.md](../contracts/ERROR_LOGGING.md) | `notify_admin()` — **D** (tech alerts) |
| [contracts/db_schema.md](../contracts/db_schema.md) | role enum ADMIN |
| [contracts/scoring_flow.md](../contracts/scoring_flow.md), [bonus_rules.md](../contracts/bonus_rules.md), [leaderboard_tiebreakers.md](../contracts/leaderboard_tiebreakers.md) | scattered `/admin/` path refs |

### 6.2 UI specs

| File | ~hits | Issue |
|------|-------|--------|
| [ui/pages.md](../ui/pages.md) | 51 | “Supervisor/**Admin**”, `/admin/layout` “admin shell” |
| [ui/components.md](../ui/components.md) | 44 | `components/admin/*` paths |
| [ui/forms_validation.md](../ui/forms_validation.md) | 14 | admin form validation |
| [ui/state_management.md](../ui/state_management.md) | 10 | `/admin/rounds` hooks |

### 6.3 Coder / tester instructions (organizer “admin UI” phrasing)

Heavy **C-organizer-ui** wording — safe to batch-replace “admin UI” → “supervisor UI” in prose:

- [instructions/coder_2.3.md](../instructions/coder_2.3.md) — “**Supervisor/Admin** operational UI”
- [instructions/coder_2.1.1.md](../instructions/coder_2.1.1.md), [coder_2.1.md](../instructions/coder_2.1.md), [coder_2.1.2_fix_supervisor.md](../instructions/coder_2.1.2_fix_supervisor.md)
- [instructions/coder_2.3.1_fix.md](../instructions/coder_2.3.1_fix.md), [coder_2.3.3_fix_setup.md](../instructions/coder_2.3.3_fix_setup.md), [coder_2.3.5_fix_deadline.md](../instructions/coder_2.3.5_fix_deadline.md)
- [instructions/tester_2.3.md](../instructions/tester_2.3.md), [tester_2.1.1.md](../instructions/tester_2.1.1.md), [tester_2.3.*.md](../instructions/)

Already documents the **path vs role** split:

- [instructions/backend/coder_1.12_fix.md](../instructions/backend/coder_1.12_fix.md) §9
- [instructions/backend/coder_1.13_supervisor_rename.md](../instructions/backend/coder_1.13_supervisor_rename.md)
- [instructions/backend/tester_1.13_supervisor_rename.md](../instructions/backend/tester_1.13_supervisor_rename.md)

### 6.4 Backend stage docs (`…/admin/…` API paths)

All reference **real endpoint paths** — tag **A-path** (add glossary, don’t rename path):

- [instructions/backend/coder_1.3.md](../instructions/backend/coder_1.3.md) — 34 hits
- [instructions/backend/coder_1.6.md](../instructions/backend/coder_1.6.md) — 44 hits
- [instructions/backend/coder_1.4.md](../instructions/backend/coder_1.4.md), [coder_1.5.md](../instructions/backend/coder_1.5.md), [coder_1.10_fix.md](../instructions/backend/coder_1.10_fix.md), [coder_1.14_data_fix.md](../instructions/backend/coder_1.14_data_fix.md)
- [instructions/backend/tester_1.4.1.md](../instructions/backend/tester_1.4.1.md), [tester_1.6.md](../instructions/backend/tester_1.6.md), …

### 6.5 Reports / progress (low priority)

Historical test reports (`test_2.3.md`, `test_1.*.md`, `bug_*.md`, `progress/stage_*.md`) — optional cleanup; not blocking for operators.

### 6.6 Already uses “support” correctly (use as template)

- [instructions/coder_2.2.md](../instructions/coder_2.2.md) — “ADMIN \| All scores (**support**)”
- [instructions/coder_1.16_fix_public_predictions.md](../instructions/coder_1.16_fix_public_predictions.md) — “Admin/**support**”
- [manuals/API_GUIDE.md](../../manuals/API_GUIDE.md) L157 — “support/troubleshooting”

---

## 7. Ambiguous phrases — manual decision list

| Phrase | Typical meaning | Doc action (per approved rules) |
|--------|-----------------|-------------------------------|
| “admin UI” / “админка” | Organizer workspace at `/admin/*` | Free prose: «интерфейс организатора (supervisor)»; path `/admin/*` unchanged |
| “admin shell” | Same | «supervisor shell» or «admin shell (supervisor)» |
| “Supervisor/Admin” (paired roles) | SUPERVISOR + ADMIN using same `/admin/*` UI | «SUPERVISOR и support (SUPERVISOR+)» |
| “Login as admin” | **Support** bootstrap user | «Login as support»; note `login: admin` until env rename |
| “Admin override” / UC-13 | **Support** technical override | «Support override» |
| “Admin меняет deadline в БД” | Test helper, support role | «Support меняет…» |
| “admin flow” (E2E docs) | Supervisor journey | «supervisor flow» or «admin flow (supervisor)» |
| `POST …/admin/recalculate` | Support-only API path | Path unchanged; prose «support recalculate» |
| `[E2E-ADMIN-RBAC]` | Tests access to `/admin/*` | Doc label → `[E2E-SUPERVISOR-RBAC]` (paths stay) |
| `notify_admin()` | Tech alert hook | Optional «notify_support()» in docs |

---

## 8. What should **not** be renamed in docs (without code change)

| Item | Reason |
|------|--------|
| URL paths `/admin/…`, `…/contests/{id}/admin/…` | Must match running API and Next routes |
| Source paths `src/app/admin/`, `lib/admin/`, `components/admin/` | Code references |
| OpenAPI / curl examples with real paths | Copy-paste must work |
| DB enum value `ADMIN` | Schema contract — add alias “(support)” in prose only |
| Bootstrap login `admin` in `settings.py` | Until code rename |

---

## 9. Suggested execution order (when approved)

1. **`docs/` immutable specs** (human sync) — 8 строк **B** + 2 строки **C** per §2.2–2.6; paths untouched.
2. **Glossary** — [manuals/README.md](../../manuals/README.md) + [API_GUIDE.md](../../manuals/API_GUIDE.md#role-based-access-control), mirror [01_tech_regulations.md](../../docs/01_tech_regulations.md) §1.
3. **Env rename** (separate commit) — `.env.example`, `frontend/.env.local.example`, `CONFIG.md`, `settings.py`, bootstrap scripts.
4. **Manuals** — **B** in CONFIG/BOOTSTRAP/DEV_SETUP; **C** for «админка» in SUPERVISOR_TESTING_SCENARIOS; **A-path** unchanged.
5. **agent_docs contracts** — glossaries; filename `admin_ui_status_matrix.md` optional rename later.
6. **agent_docs instructions** — batch **C** in prose; leave path literals.

---

## 10. Quick grep commands (for your review)

```bash
# docs/ immutable specs
grep -n -iE 'admin|админ' docs/01_tech_regulations.md docs/03_user_scenarios.md docs/04_supervisor_scenario.md docs/06_front_tests.md

# Organizer UI phrasing (living docs)
grep -riE 'admin UI|admin shell|админк' manuals/ agent_docs/ README.md

# Support rename candidates
grep -rE 'SEED_ADMIN|seed_admin|Admin override|Login as admin|Технический администратор' manuals/ agent_docs/ docs/ .env.example README.md

# Paths — must stay unchanged
grep -rE '/admin/|contests/\{id\}/admin' manuals/ agent_docs/ docs/
```

---

## 11. Counts (approximate)

| Area | Files with `admin`/`ADMIN` | Actionable prose edits |
|------|---------------------------|------------------------|
| `docs/` | 5 of 7 audited | **~10 lines** (mostly §1.2, UC-13, E2E) |
| `manuals/` | 13 | **~50–80** (CONFIG + QA «админка») |
| `agent_docs/` | ~70 | **~200+** (bulk «admin UI» → gloss); paths excluded |
| `.env.example` + frontend | 2 | **4 symbols** |

---

## 12. Delegation

No code changes made. After your review, typical split:

- **@Coder/docs** — glossaries + manuals + contracts (tags B, C, A-path notes)
- **@Coder** — env/settings rename (`SEED_SUPPORT_*`) if approved
- **Defer** — organizer path rename `…/admin/rounds` → `…/supervisor/…` cancelled; see `.trash/…/tester_1.13_supervisor_rename.md`
- **Planned execution:** [manuals/ADMIN_TO_SUPPORT_RENAME.md](../../manuals/ADMIN_TO_SUPPORT_RENAME.md)

---

## 13. Role rename `ADMIN` → `SUPPORT` (code impact)

> **Scope of this section:** renaming the **global role** stored in `users.role` and returned in JWT/API as `role`.  
> **Not in scope here:** organizer paths `…/contests/{id}/admin/rounds` (SUPERVISOR+ — separate track in `coder_1.13`).

### 13.1 Is it critical?

| Question | Answer |
|----------|--------|
| Сломает ли прод сейчас? | **Нет**, если не трогать код |
| Роль «нигде не задействована»? | **Нет** — RBAC, 2 UI-страницы, privacy, lifecycle |
| Стоит ли переименовать? | **Да**, пока один bootstrap-`admin` и нет продакшн-support-аккаунтов |
| Объём | ~35 файлов, 1 data-migration, перелогин после деплоя |

### 13.2 Что умеет только support (`ADMIN` сегодня)

| # | Capability | API / UI | Файл |
|---|------------|----------|------|
| 1 | Создать организатора (SUPERVISOR) | `POST /api/v1/admin/users/supervisor`, `/admin/users` | `admin_users.py`, `users/page.tsx` |
| 2 | Список soft-deleted конкурсов | `GET /api/v1/contests/deleted` | `contests.py` |
| 3 | Восстановить конкурс из снимка | `POST /api/v1/contests/{id}/restore`, `/admin/lifecycle` | `contests.py`, `DeletedContestsPanel` |
| 4 | Досрочно завершить конкурс | `POST /api/v1/contests/{id}/finish` | `contests.py` `require_finish_role` |
| 5 | Глобальный пересчёт | `POST …/contests/{id}/admin/recalculate` | `contest_ops.py` |
| 6 | Exceptional tiebreak | `PUT …/participants/{uid}/exceptional-tiebreak` | `contest_participants.py` |
| 7 | Все прогнозы до дедлайна | `GET …/predictions` (filter bypass) | `prediction_service.py` |
| 8 | Вернуть CANCELED/POSTPONED → SCHEDULED | UI match status | `matchScheduleEdit.ts`, `RoundManagementPanel` |

**SUPERVISOR+ (не exclusive):** pause/resume/delete конкурса, все `…/admin/rounds|matches`, большая часть `/admin/*` UI.

### 13.3 API: где `admin` в URL = **support** (не организатор)

Да — **уже есть** эндпоинты, где сегмент `admin` означает именно техподдержку, а не supervisor-операции:

#### A. Platform support router (только `ADMIN` / будущий `SUPPORT`)

| Method | Path | Role | Комментарий |
|--------|------|------|-------------|
| `POST` | `/api/v1/admin/users/supervisor` | ADMIN only | **Имя пути удачное** для support-плоскости; при рефакторинге → `/api/v1/support/users/supervisor` |

Источник: `src/api/v1/admin_users.py` (`prefix="/admin/users"`).

#### B. Contest-scoped, но **только support** (путь вводит в заблуждение)

| Method | Path | Role | Проблема |
|--------|------|------|----------|
| `POST` | `/api/v1/contests/{id}/admin/recalculate` | ADMIN only | `admin` в path = организатор у новичка; по факту — support |

Источник: `src/api/v1/contest_ops.py`. Фронт: `endpoints.ts` → `contestAdmin.recalculate`.

#### C. Contest lifecycle без `admin` в path, но **только support**

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/contests/deleted` | ADMIN |
| `POST` | `/api/v1/contests/{id}/restore` | ADMIN |
| `POST` | `/api/v1/contests/{id}/finish` | ADMIN (SUPERVISOR если `supervisor_training_mode`) |
| `PUT` | `/api/v1/contests/{id}/participants/{uid}/exceptional-tiebreak` | ADMIN |

#### D. Deprecated shims (ADMIN only, default contest)

| Method | Path | File |
|--------|------|------|
| `POST` | `/api/v1/admin/contest/pause\|resume\|finish` | `admin_contest.py` |
| `DELETE` | `/api/v1/admin/contest` | `admin_contest.py` |
| `PUT` | `/api/v1/admin/users/{uid}/exceptional-tiebreak` | `admin_contest.py` |
| `POST` | `/api/v1/admin/recalculate` | `admin_misc.py` |

На новом API pause/resume/delete — **SUPERVISOR+** (`contests.py`); legacy shims остались ADMIN-only.

#### E. Contest-scoped `…/admin/…` = **организатор (SUPERVISOR+)** — **не переименовывать в support**

`rounds`, `matches`, `calculate`, `publish`, `free-tour` — `RoleChecker(SUPERVISOR, ADMIN)`.

**Рекомендация по API (отдельный этап после роли):**

| Приоритет | Было | Стало (предложение) | Риск |
|-----------|------|---------------------|------|
| P1 | `POST /api/v1/admin/users/supervisor` | `POST /api/v1/support/users/supervisor` | Средний — один клиент (`endpoints.ts`) |
| P1 | `POST …/admin/recalculate` | `POST …/support/recalculate` | Средний — lifecycle UI |
| P2 | Deprecated `/api/v1/admin/contest/*` | удалить после миграции тестов | Низкий |
| **Не трогать** | `…/admin/rounds`, `…/admin/matches` | оставить до `coder_1.13` → `…/supervisor/…` | Высокий если смешать с support |

### 13.4 Code files — role `ADMIN` (rename checklist)

**🔴 Критично (сломает auth/RBAC при частичном rename):**

| File | What |
|------|------|
| `src/database/models.py` | `UserRole.ADMIN = "ADMIN"` → `SUPPORT = "SUPPORT"` |
| `alembic/versions/*` (new) | `UPDATE users SET role='SUPPORT' WHERE role='ADMIN'` |
| `config/settings.py` | `seed_admin_*` → `seed_support_*`, login default |
| `src/scripts/bootstrap_users.py` | role + env keys |
| `src/scripts/seed.py` | optional ADMIN seed |
| `frontend/src/types/api.ts` | `UserRole` union |
| `frontend/src/lib/auth/guards.ts` | role rank map |
| `frontend/src/lib/auth/resolvePostLoginPath.ts` | `case "ADMIN"` |
| `src/api/v1/contests.py` | `require_finish_role`, `require_restore_role`, `_admin` |
| `src/services/prediction_service.py` | `is_privileged = viewer_role == …` |

**🟠 Важно (support-only UI / behaviour):**

| File | What |
|------|------|
| `frontend/src/app/admin/lifecycle/page.tsx` | guard `role !== "ADMIN"` |
| `frontend/src/app/admin/users/page.tsx` | guard + create organizer |
| `frontend/src/app/contest/[contestId]/page.tsx` | `isAdminViewer` (pre-deadline matrix) |
| `frontend/src/lib/privacy/shouldShowScore.ts` | ADMIN bypass |
| `frontend/src/lib/admin/matchScheduleEdit.ts` | ADMIN restore match |
| `frontend/src/components/admin/RoundManagementPanel.tsx` | `isAdmin` for status restore |
| `src/api/v1/admin_users.py` | `_admin` dependency |
| `src/api/v1/contest_ops.py` | recalculate `_admin` |
| `src/api/v1/contest_participants.py` | exceptional tiebreak `_admin` |

**🟡 Массово, но механически (`SUPERVISOR+` — заменить `ADMIN` на `SUPPORT` в tuple):**

`admin_rounds.py`, `admin_results.py`, `admin_contest.py`, `contest_teams.py`, `contest_participants.py` (invite paths), `leaderboard_service.py` (`_STAFF_ROLES`).

**🟢 Тесты / E2E (обновить после кода):**

`tests/api/conftest.py` (`admin_api`), `test_auth_rbac_1_3.py`, `test_contest_lifecycle_1_3.py`, `frontend/e2e/fixtures/auth.ts`, `credentials.ts`, `adminApi.ts`, `z_admin_pause.spec.ts`, `auth_role_routing.spec.ts`, `prediction_privacy.spec.ts`.

### 13.5 Suggested commit order (role + paths)

1. **Docs + env** (`SEED_SUPPORT_*`, prose) — без breaking API.
2. **Role enum + migration + bootstrap** — JWT `role: "SUPPORT"`.
3. **Frontend guards** — lifecycle, users, shouldShowScore.
4. **Support-only API paths** — `/api/v1/support/…`, `…/support/recalculate` (optional aliases deprecated).
5. **Organizer paths** — отдельно по `coder_1.13` (`…/supervisor/…`, UI `/supervisor/…`).

---

## 14. 🔴 Самые критичные места для **ручной** правки (docs first)

Порядок: сначала то, что читают люди и от чего пляшут остальные доки.

### 14.1 Immutable specs (`docs/`)

| Pri | File | Lines | Действие |
|-----|------|-------|----------|
| **P0** | [docs/01_tech_regulations.md](../../docs/01_tech_regulations.md) | 27, 45, 162, 313 | §1.2 **Admin** → **Support**; UC-13 **Admin override** → **Support override** |
| **P0** | [docs/01_tech_regulations.md](../../docs/01_tech_regulations.md) | 248 | «админ-панель» → «админ-панель **(supervisor)**» |
| **P1** | [docs/03_user_scenarios.md](../../docs/03_user_scenarios.md) | 59 | «Admin меняет deadline» → «**Support** меняет deadline» |
| **P1** | [docs/04_supervisor_scenario.md](../../docs/04_supervisor_scenario.md) | 81, 142 | «Admin override» → «**Support** override» |
| **P1** | [docs/06_front_tests.md](../../docs/06_front_tests.md) | 13 | «admin flow» → «**supervisor** flow» |
| — | [docs/04_supervisor_scenario.md](../../docs/04_supervisor_scenario.md) | 14–127 | `/admin/…` **URL не менять** |

### 14.2 Living manuals (операторы)

| Pri | File | Что править |
|-----|------|-------------|
| **P0** | [manuals/API_GUIDE.md](../../manuals/API_GUIDE.md) | Таблица RBAC L152–157: строка **ADMIN** → **Support (ADMIN)**; exclusive endpoints §contests/deleted, restore, recalculate |
| **P0** | [manuals/CONFIG.md](../../manuals/CONFIG.md) + [.env.example](../../.env.example) | `SEED_ADMIN_*` → `SEED_SUPPORT_*`, комментарии |
| **P0** | [manuals/BOOTSTRAP_USERS.md](../../manuals/BOOTSTRAP_USERS.md) | «Login as admin» → «Login as **support**»; таблица `admin` → `ADMIN (support)` |
| **P1** | [manuals/SUPERVISOR_TESTING_SCENARIOS.md](../../manuals/SUPERVISOR_TESTING_SCENARIOS.md) | Строки X1, X3–X7: **ADMIN** → **support**; «админка» → «панель организатора (supervisor)»; `/admin/` не трогать |
| **P1** | [manuals/FRONTEND_REFERENCE.md](../../manuals/FRONTEND_REFERENCE.md) | «Supervisor admin UI» → «Supervisor UI»; `/admin/lifecycle`, `/admin/users` — пометить **(support only)** |

### 14.3 Glossary blurb (вставить в manuals/README или API_GUIDE)

```text
Терминология:
- Supervisor (организатор) — users.role=SUPERVISOR; UI и API тура/матчей по путям /admin/… (историческое имя).
- Support (техподдержка) — users.role=ADMIN (до переименования в SUPPORT); lifecycle, restore, recalculate, создание supervisor-аккаунтов.
- Путь /api/v1/admin/users/… — плоскость support, не организатор.
```

### 14.4 Когда дойдёте до кода (не сейчас)

| Pri | Что | Почему критично |
|-----|-----|-----------------|
| **P0** | `UserRole` + migration `users.role` | Иначе JWT и RBAC расходятся с БД |
| **P0** | `bootstrap_users.py` + `.env` | Иначе не войти после деплоя |
| **P1** | `prediction_service.py` + `shouldShowScore.ts` | Privacy regression |
| **P1** | `lifecycle/page.tsx`, `users/page.tsx` | Support UI недоступен |
| **P2** | `POST …/admin/recalculate` → `…/support/recalculate` | Путаница path vs role; не блокер для docs |

---

## 15. Status

- **2026-07-02:** Audit complete incl. `docs/` specs; §13–14 added for role/path rename planning.
- **No files modified** except this report.


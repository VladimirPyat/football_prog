# Manuals

Human-facing technical documentation for the Football Predictions Contest project.

## Index

| Document | Topic |
|----------|-------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System overview, layers, data flows, state machines |
| [DB_REFERENCE.md](DB_REFERENCE.md) | SQLAlchemy models, enums, constraints, migrations |
| [CONFIG.md](CONFIG.md) | Settings, env vars, seed script, contest defaults |
| [SCORING_LOGIC.md](SCORING_LOGIC.md) | Points, bonuses, tie-breakers, validation rules |
| [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) | Initial ADMIN/SUPERVISOR via `.env` + bootstrap script |
| [API_GUIDE.md](API_GUIDE.md) | FastAPI routes, auth, RBAC, contest lifecycle |
| [ERROR_LOGGING.md](ERROR_LOGGING.md) | Политика ошибок и логирования (RU) |
| [MANUAL_SCORING_VERIFICATION.md](MANUAL_SCORING_VERIFICATION.md) | Stage 1 sign-off: ручная проверка scoring + CANARY (RU) |

## Stage Coverage

| Stage | Documented in |
|-------|---------------|
| **0** — Database & configuration | `DB_REFERENCE.md`, `CONFIG.md`, `SCORING_LOGIC.md` (rules seeded) |
| **1.1** — Scoring engine | `SCORING_LOGIC.md` |
| **1.2** — Services & data loader | `API_GUIDE.md` (service layer), `CONFIG.md` (loader) |
| **1.2.1** — Lifecycle migration | `DB_REFERENCE.md` |
| **1.3** — HTTP API | `API_GUIDE.md`, `CONFIG.md`, `SCORING_LOGIC.md` (tie-break source) |
| **1.4** — Multi-contest + setup phase | `DB_REFERENCE.md`, `API_GUIDE.md` (contest-scoped routes) |
| **1.4** — Full HTTP E2E + manual sign-off | [MANUAL_SCORING_VERIFICATION.md](MANUAL_SCORING_VERIFICATION.md), `tests/manual/` |
| **1.5** — Errors, logging, docstrings | [ERROR_LOGGING.md](ERROR_LOGGING.md) |
| **1.6** — Bootstrap users & organizer API | [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) |
| **1.8** — Contest discovery & user contacts | [API_GUIDE.md](API_GUIDE.md#contest-discovery--user-contacts) |
| **1.7** — Leaderboard counts & invite accept | [API_GUIDE.md](API_GUIDE.md#multi-contest-api) (count_* fields, participant accept) |
| **1.9** — Team logo upload & static assets | [API_GUIDE.md](API_GUIDE.md#multi-contest-api), [CONFIG.md](CONFIG.md#team-logo-storage) |

Last synced: ARCHITECTURE.md added; Stage 1.7/1.9; OpenAPI v1.2.0.

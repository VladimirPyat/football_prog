# Manuals

Human-facing technical documentation for the Football Predictions Contest project.

## Index

| Document | Topic |
|----------|-------|
| [DB_REFERENCE.md](DB_REFERENCE.md) | SQLAlchemy models, enums, constraints, migrations |
| [CONFIG.md](CONFIG.md) | Settings, env vars, seed script, contest defaults |
| [SCORING_LOGIC.md](SCORING_LOGIC.md) | Points, bonuses, tie-breakers, validation rules |
| [API_GUIDE.md](API_GUIDE.md) | FastAPI routes, auth, RBAC, contest lifecycle |

## Stage Coverage

| Stage | Documented in |
|-------|---------------|
| **0** — Database & configuration | `DB_REFERENCE.md`, `CONFIG.md`, `SCORING_LOGIC.md` (rules seeded) |
| **1.1** — Scoring engine | `SCORING_LOGIC.md` |
| **1.2** — Services & data loader | `API_GUIDE.md` (service layer), `CONFIG.md` (loader) |
| **1.2.1** — Lifecycle migration | `DB_REFERENCE.md` |
| **1.3** — HTTP API | `API_GUIDE.md`, `CONFIG.md`, `SCORING_LOGIC.md` (tie-break source) |

Last synced from staged changes: Stage 1.2.1 migration + Stage 1.3 API integration.

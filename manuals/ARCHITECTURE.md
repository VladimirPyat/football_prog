# System Architecture

High-level view of the Football Predictions Contest backend. For endpoint lists, table columns, and scoring formulas, follow the links at the end — this document does not duplicate those specs.

## Table of Contents

- [Purpose](#purpose)
- [System Context](#system-context)
- [Layered Architecture](#layered-architecture)
- [Code Layout](#code-layout)
- [Data Model](#data-model)
- [Multi-Contest Model](#multi-contest-model)
- [Lifecycle State Machines](#lifecycle-state-machines)
- [Request & Data Flows](#request--data-flows)
- [Scoring Pipeline](#scoring-pipeline)
- [Security & Access](#security--access)
- [Cross-Cutting Concerns](#cross-cutting-concerns)
- [Further Reading](#further-reading)

## Purpose

The backend supports a **multi-contest** football prediction platform:

- Organizers configure contests (teams, participants, rules), run rounds, enter results, calculate and publish standings.
- Participants submit batch predictions before round deadlines.
- Visitors read public leaderboards and published results.
- Scoring rules live in `contests.rules_json`; a **pure** scoring engine computes points without touching the database.

**API surface:** OpenAPI v1.2.0 — [`agent_docs/contracts/api_v1.yaml`](../agent_docs/contracts/api_v1.yaml)  
**Primary prefix:** `/api/v1/contests/{contest_id}/…`

## System Context

```mermaid
flowchart LR
    subgraph clients [Clients]
        WEB[Web UI / Frontend]
        CLI[Scripts & tests]
    end

    subgraph backend [Backend — this repo]
        API[FastAPI / Uvicorn]
        SVC[Services]
        ENG[Scoring engine]
        DB[(SQLite / PostgreSQL)]
        FS[Static files]
    end

    WEB -->|JWT REST| API
    CLI -->|httpx / scripts| API
    API --> SVC
    SVC --> ENG
    SVC --> DB
    API --> FS
```

| Boundary | Technology |
|----------|------------|
| HTTP | FastAPI, Pydantic validation, OpenAPI |
| Persistence | SQLAlchemy 2 async, Alembic migrations |
| Auth | JWT (HS256), bcrypt passwords |
| Rules & config | `contests.rules_json`, `config/settings.py`, `.env` |
| Static assets | `/static/assets/*` (bundled), `/static/teams/*` (uploads) |

## Layered Architecture

```mermaid
flowchart TB
    subgraph http [HTTP layer]
        R[src/api/v1/* routers]
        H[src/api/handlers]
        D[src/api/deps.py]
    end

    subgraph domain [Domain layer]
        SV[src/services/*]
        SC[src/scoring/*]
    end

    subgraph infra [Infrastructure]
        ORM[src/database]
        CFG[config/settings.py]
        CORE[src/core — security, exceptions, logging]
    end

    R --> D
    R --> H
    R --> SV
    H --> SV
    SV --> SC
    SV --> ORM
    D --> CORE
    SV --> CORE
    R -->|AppError| EH[error_handlers]
```

**Principles:**

| Rule | Where |
|------|--------|
| Routers stay thin | Delegate to `services/` or shared `handlers/` |
| Business rules in services | Status machines, guards, transactions |
| Pure scoring | `src/scoring/` — no DB I/O; called from `scoring_persistence` |
| Typed domain errors | `AppError` → `{detail, code}` JSON; no `HTTPException` in services |
| Contest-scoped side effects | Auto-close expired rounds via dependency on contest routes |

Details: [API Guide — Architecture](API_GUIDE.md#architecture-updated)

## Code Layout

```
main.py              → app factory, CORS, routers, static mounts
config/settings.py   → env-backed Settings singleton
src/
  api/v1/            → REST endpoints (auth, contests, setup, predictions, admin)
  api/handlers/      → shared leaderboard / predictions response builders
  api/deps.py        → DB session, JWT user, RoleChecker, ContestContext, auto-close
  core/              → security, exceptions, logging
  database/          → models, async engine
  schemas/           → Pydantic DTOs (mirror OpenAPI components)
  scoring/           → engine, rules accessor, standings builder
  services/          → all mutable business logic
  scripts/           → seed, bootstrap_users, load_test_data
alembic/             → schema migrations
static/assets/       → default team logo (committed)
uploads/teams/       → supervisor uploads (gitignored)
```

## Data Model

Ten tables. Contest is the **aggregate root** for teams, rounds, and membership.

```mermaid
erDiagram
    users ||--o| contacts : has
    users ||--o{ contest_participants : enrolls
    contests ||--o{ contest_participants : has
    contests ||--o{ teams : contains
    contests ||--o{ rounds : contains
    rounds ||--o{ matches : contains
    teams ||--o{ matches : team1
    teams ||--o{ matches : team2
    users ||--o{ predictions : submits
    rounds ||--o{ predictions : for
    matches ||--o{ predictions : on
    users ||--o{ scores : earns
    rounds ||--o{ scores : per

    contests {
        int id PK
        string status
        bool is_locked
        json rules_json
    }
    contest_participants {
        int contest_id PK
        int user_id PK
        string status
        int exceptional_tiebreak_points
    }
    rounds {
        int id PK
        string status
        timestamptz deadline
    }
    scores {
        int user_id
        int round_id
        int total_with_bonus3
        int count_exact_high
    }
```

**Global vs per-contest:**

| Concept | Storage |
|---------|---------|
| Login, password, global role | `users.role` — one of `USER`, `SUPERVISOR`, `ADMIN` (support) |
| Playing in a contest | `contest_participants` — `PENDING` / `ACCEPTED` |
| Scoring rules | `contests.rules_json` (frozen when `is_locked`) |
| Manual tie-break override | `contest_participants.exceptional_tiebreak_points` (not in `rules_json`) |

Full column list: [`agent_docs/contracts/db_schema.md`](../agent_docs/contracts/db_schema.md) · [DB Reference](DB_REFERENCE.md)

## Multi-Contest Model

Stage 1.4+ supports **many contests** in one database. Each contest owns its teams, rounds, and participant rows.

```mermaid
flowchart LR
    U[users — global identity]
    C1[contest A]
    C2[contest B]
    U -->|contest_participants| C1
    U -->|contest_participants| C2
    SUP[SUPERVISOR] -->|GET /contests| C1
    SUP --> C2
    PL[USER] -->|GET /me/contests| C1
```

Legacy routes without `{contest_id}` resolve the default contest (`id=1`) for backward-compatible tests.

## Lifecycle State Machines

### Contest

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> RUNNING : first round activate\n(is_locked=true)
    RUNNING --> PAUSED : Support pause
    PAUSED --> RUNNING : Support resume
    RUNNING --> FINISHED : Support finish
    PAUSED --> FINISHED : Support finish
```

| Phase | `status` | `is_locked` | Typical operations |
|-------|----------|-------------|-------------------|
| Setup | `DRAFT` | `false` | Teams, invites, logos, PATCH rules |
| Operational | `RUNNING` | `true` | Predictions, results, calculate |
| Frozen | `PAUSED` | `true` | Read-only mutations; safe delete after grace |
| Terminal | `FINISHED` | `true` | Read-only; Support recalculate allowed |

Matrix of allowed operations: [`agent_docs/contracts/contest_lifecycle_flow.md`](../agent_docs/contracts/contest_lifecycle_flow.md)

### Round

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> ACTIVE : activate
    ACTIVE --> CLOSED : deadline / auto-close
    CLOSED --> CALCULATED : calculate
    CALCULATED --> PUBLISHED : publish
    CALCULATED --> CALCULATED : VOID match → recalculate
```

**Auto-close:** on every contest-scoped API call, `auto_close_expired_rounds` transitions `ACTIVE → CLOSED` when `now >= deadline` (sync, same transaction when possible).

## Request & Data Flows

### Prediction submit (participant)

```mermaid
sequenceDiagram
    participant C as Client
    participant R as contest_ops router
    participant D as deps
    participant P as prediction_service
    participant DB as Database

    C->>R: POST .../rounds/{id}/predictions
    R->>D: JWT + ContestContext + auto-close
    D->>DB: close expired rounds if any
    R->>P: submit_batch(user, round, items)
    P->>DB: load round, participant, matches
    P->>P: guards: ACTIVE, deadline, ACCEPTED
    P->>DB: upsert all predictions (atomic)
    R-->>C: 200 saved_count
```

Missing prediction = **no row** (never score `0` as “empty”). Batch must cover every match in the round.

### Calculate & publish (supervisor)

```mermaid
sequenceDiagram
    participant S as Supervisor
    participant R as admin router
    participant SP as scoring_persistence
    participant E as scoring engine
    participant DB as Database

    S->>R: POST .../calculate
    R->>SP: calculate_round(round_id)
    SP->>DB: load matches, predictions, rules_json
    SP->>E: score_round(...)
    E-->>SP: UserRoundScore per user
    SP->>DB: write scores, transition CALCULATED
    S->>R: POST .../publish
    R->>DB: transition PUBLISHED
```

After publish, public GET leaderboard/results include ETag caching.

## Scoring Pipeline

Rules are **data-driven** from `contests.rules_json`. The engine applies a fixed algorithm documented in the scoring contract.

```mermaid
flowchart LR
    subgraph inputs [Inputs per round]
        M[Match results]
        PR[Predictions]
        RU[rules_json]
    end

    subgraph engine [src/scoring]
        SR[ScoringRules accessor]
        ER[engine.score_round]
        ST[standings.build_standings]
    end

    subgraph outputs [Outputs]
        SC[scores table]
        LB[Leaderboard JSON]
    end

    M --> ER
    PR --> ER
    RU --> SR --> ER
    ER -->|UserRoundScore| SP[scoring_persistence]
    SP --> SC
    SC --> ST
    ST --> LB
```

| Stage | What happens |
|-------|----------------|
| **Base points** | Per match: one category — exact high, exact, diff+outcome, outcome, or miss |
| **Bonus 1** | Unique exact prediction multiplier |
| **Bonus 2** | Threshold by count of correct outcomes in round |
| **Bonus 3** | Round rank by base total (+ optional extra threshold) |
| **Tie-break** | Total → exact count → base without bonuses → diff count → manual override |
| **VOID** | Match points zeroed; bonuses recalculated for remaining matches |

Contract summary: [`agent_docs/contracts/scoring_flow.md`](../agent_docs/contracts/scoring_flow.md)  
Implementation & persistence: [SCORING_LOGIC.md](SCORING_LOGIC.md)

## Security & Access

```mermaid
flowchart TB
    REQ[HTTP request]
    REQ --> AUTH{Bearer JWT?}
    AUTH -->|public GET| PUB[leaderboard, results, /contests/public]
    AUTH -->|valid| RBAC[RoleChecker + contest guards]
    RBAC --> USER[USER — own predictions]
    RBAC --> SUP[SUPERVISOR — admin ops]
    RBAC --> ADM[Support — recalc, lifecycle, all predictions pre-deadline]
```

| Mechanism | Notes |
|-----------|--------|
| JWT payload | `{sub: user_id, role, exp}` |
| Invite flow | Temp password → `PENDING` participant → change password → `ACCEPTED` |
| Prediction privacy | Before deadline: USER/SUPERVISOR see own scores only; Support (ADMIN) sees all |
| Contest guards | `PAUSED` / `FINISHED` block mutating ops; `is_locked` blocks setup CRUD |

RBAC tables: [API Guide — RBAC](API_GUIDE.md#role-based-access-control)

## Cross-Cutting Concerns

| Concern | Implementation |
|---------|------------------|
| Errors | `src/core/exceptions.py` + `error_handlers.py` → `{detail, code}` |
| Logging | `LOG_LEVEL`, structured format at startup |
| HTTP cache | Public leaderboard/results: `Cache-Control` + ETag from score state |
| Migrations | Alembic async; URL from `DATABASE_URL` |
| Bootstrap | `seed.py` + `bootstrap_users.py` — see [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) |
| Test data | `load_test_data.py` + contracted CSVs — see [CONFIG.md](CONFIG.md) |

## Further Reading

| Topic | Document |
|-------|----------|
| Manuals index | [README.md](README.md) |
| HTTP API, services, endpoints | [API_GUIDE.md](API_GUIDE.md) |
| Tables, enums, migrations | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Points, bonuses, engine code | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
| Env vars, seed, loader | [CONFIG.md](CONFIG.md) |
| OpenAPI (authoritative routes) | [`api_v1.yaml`](../agent_docs/contracts/api_v1.yaml) |
| DB contract | [`db_schema.md`](../agent_docs/contracts/db_schema.md) |
| Scoring contract | [`scoring_flow.md`](../agent_docs/contracts/scoring_flow.md) |
| Lifecycle matrix | [`contest_lifecycle_flow.md`](../agent_docs/contracts/contest_lifecycle_flow.md) |
| Business rules (immutable) | [`docs/01_tech_regulations.md`](../docs/01_tech_regulations.md) |
| Project README | [`README.md`](../README.md) |

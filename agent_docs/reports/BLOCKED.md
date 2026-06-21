# BLOCKED — Stage 2 Frontend: Backend Prerequisites

> **Created:** 2026-06-21
> **Context:** Planning of Stage 2 (Frontend) per `agent_docs/plans/draft_2.md`.
> **Rule basis:** Frontend must integrate the real backend (no mocks, `docs/03_user_scenarios.md`). Several screens require endpoints/fields that **do not exist** in `agent_docs/contracts/api_v1.yaml` (v1.1.0). Per honesty rule, these are reported here instead of being silently stubbed/mocked.

## Summary

Six backend additions are required to fully deliver the approved Stage-2 UI. They were surfaced while reconciling `docs/03`, `docs/04`, the `docs/screens/*` reference screenshots, and the current API contract. Each has a documented frontend fallback if not delivered, so frontend work is **not fully blocked** — but the listed screens cannot reach "done" without them.

## Required additions

### B1 — `GET /api/v1/me/contests`
- **Why:** Users are invited to specific contests (no self-registration; see `supervisor_settings2.jpg`). An authenticated USER needs a «Конкурсы» picker listing **only** contests they belong to.
- **Current state:** `GET /api/v1/contests` is SUPERVISOR+ only. No user-scoped listing.
- **Storage:** `contest_participants` already links users↔contests (used by `/participants`, `exceptional-tiebreak`). No schema change expected.
- **Proposed response:** array of `{ id, name, status, role_in_contest, participant_status }`.
- **Blocks:** Sub-stage 2.1 (user navigation), parts of 2.2/2.4.
- **Fallback:** dev-only single contest via `NEXT_PUBLIC_DEFAULT_CONTEST_ID`.

### B2 — `GET /api/v1/contests/public`
- **Why:** Anonymous Visitor has no invitations but must browse public leaderboards/results. Needs a discovery list.
- **Current state:** no anonymous contest listing.
- **Proposed response:** running/visible contests, minimal fields `{ id, name, status }`, no auth.
- **Blocks:** Home discovery (2.1/2.4).
- **Fallback:** `NEXT_PUBLIC_DEFAULT_CONTEST_ID` single contest.

### B3 — `GET/PATCH /api/v1/auth/me/contacts`
- **Why:** Profile contacts (email, VK, TG, `notify_enabled`) per `docs/03` §2.
- **Current state:** `contacts` table exists in DB; **no HTTP endpoints**.
- **Proposed:** GET returns current contacts; PATCH updates partial fields + toggle.
- **Blocks:** Profile contacts UI (2.1).
- **Fallback:** read-only stub (degraded UX).

### B4 — Extend `ScoreDetail` with count fields
- **Why:** `user_leaderboard.jpg` shows non-zero columns **Точный кр. счет / Точный счет / Разница / Исход**. API returns only `points_base` + bonuses.
- **Current state:** `count_*` absent from `ScoreDetail` / `Leaderboard`.
- **Proposed:** add `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` (data exists in `scores`).
- **Blocks:** Leaderboard fidelity (2.4).
- **Fallback:** hide the four columns (visible deviation from screenshot).

### B5 — Team logo upload
- **Why:** `supervisor_settings3.jpg` shows a file picker (PNG/JPG/GIF ≤2MB). API `TeamCreateRequest` only accepts `logo_url: string`.
- **Proposed:** `POST /contests/{id}/teams/{team_id}/logo` (multipart) → stores file, returns `logo_url`; or accept multipart on team create/patch.
- **Blocks:** Teams admin upload (2.3).
- **Fallback:** plain `logo_url` text input.

### B6 — Confirm invite-accept flow
- **Why:** Participant status `PENDING → ACCEPTED` (`supervisor_settings2.jpg`). Invite endpoint currently only returns a temp password.
- **Question:** Is "accept" simply first login + forced password change flipping status, or is a dedicated endpoint required?
- **Blocks:** Accurate status display (2.3) — low risk.
- **Fallback:** display status as returned by `GET /participants`.

## Proposed resolution (per user decision 2026-06-21)

Document as Stage-2 prerequisites (this file + `plans/draft_2.md` §13). Backend implementation is a **separate task** to be scheduled before/alongside the dependent frontend sub-stage. `instructions/coder_2.md` will specify exact request/response contracts so backend and frontend can proceed in parallel. Where a prerequisite is undelivered, the documented fallback applies — **never** mock data.

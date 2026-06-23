# UI State Management (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§3.4–§3.6), `agent_docs/contracts/frontend_api_integration.md`.
> **Stack:** React Context + hooks (no Redux/Zustand). `localStorage` for JWT + caches. No external state libs.

---

## 1. Principles

- Minimal global state: only **Auth** and **Contest** are app-wide contexts.
- Everything else is local component state or per-hook fetch state.
- Derive UI mode from server data (`ContestOut`, `RoundOut`), never duplicate business rules.
- `NULL ≠ 0`: empty score inputs are `undefined`, never `0`, in form state.

---

## 2. Global contexts

### 2.1 AuthProvider — **Implemented (2.1)** → `frontend/src/providers/AuthProvider.tsx`

| Field | Type | Source |
|-------|------|--------|
| `user` | `UserOut \| null` | `GET /auth/me` on load |
| `isAuthenticated` | `boolean` | derived |
| `role` | `'USER'\|'SUPERVISOR'\|'ADMIN'\|null` | `user.role` |
| `isTempPassword` | `boolean` | `user.is_temp_password` |
| `login(login, pwd)` | fn | `POST /auth/login` → store token → hydrate `me` |
| `logout()` | fn | clear token → user=null → redirect `/` |
| `changePassword(old,new)` | fn | `POST /auth/change-password` |

- Token in `localStorage: fp_access_token`.
- On mount: if token → hydrate via `/auth/me`; on 401 → `logout()` silently (Visitor).
- Listens to a global `fp:unauthorized` event emitted by the API client on any 401 → `logout()`.

### 2.2 ContestProvider — **Implemented (2.1)** → `frontend/src/providers/ContestProvider.tsx`

| Field | Type | Notes |
|-------|------|-------|
| `contestId` | `number \| null` | active contest (from URL `/contest/[id]`, picker, or env default) |
| `contest` | `ContestOut \| null` | `GET /contests/{id}` |
| `isLocked` | `boolean` | `contest.is_locked` |
| `status` | contest status | DRAFT/RUNNING/PAUSED/FINISHED |
| `maxScore` | `number` | `rules_json.constraints.score_validation_range[1]` |
| `rules` | object | `rules_json` (scoring/bonus values for settings display) |
| `setContest(id)` | fn | switch active contest, refetch |

- Public pages set `contestId` from the route param.
- User «Конкурсы» list from `GET /me/contests` (B1); Visitor list from `GET /contests/public` (B2); Supervisor picker from `GET /contests`.
- **Fallback:** B1/B2 empty or error → `resolveDefaultContestId()` from `NEXT_PUBLIC_DEFAULT_CONTEST_ID`.

---

## 3. Data fetching pattern

Lightweight SWR-style hooks over the typed API client (no external SWR lib unless justified later).

| Hook | Endpoint | Cache |
|------|----------|-------|
| `useRounds(contestId)` | `GET /contests/{id}/rounds` | in-memory; refetch after admin mutations |
| `useLeaderboard(contestId, roundId?)` | `…/leaderboard` | ETag + `localStorage` seed |
| `useRoundResults(contestId, roundId)` | `…/rounds/{rid}/results` | ETag |
| `usePredictionsView(contestId, roundId)` | `GET …/predictions` | **never cached** (privacy) |
| `useMyContests()` | `GET /me/contests` (B1) | in-memory — **Implemented (2.1)** → `frontend/src/hooks/useMyContests.ts` |
| `usePublicContests()` | `GET /contests/public` (B2) | in-memory — **Implemented (2.1)** → `frontend/src/hooks/usePublicContests.ts` |
| `useContacts()` | `GET/PATCH /auth/me/contacts` (B3) | in-memory; **fallback:** readonly UI if GET fails — **Implemented (2.1)** → `frontend/src/hooks/useContacts.ts` |

Each hook returns `{ data, error, loading, refetch }`. Errors are typed `AppError` (`{status, detail, code?}`).

---

## 4. Caching

| Data | Strategy |
|------|----------|
| Public leaderboard / results | ETag `If-None-Match`; `304` → cached; optional `localStorage` for instant first paint |
| Rounds list | in-memory per contest; invalidate on admin round/match mutations |
| Predictions (pre-deadline) | no cache, always fresh |
| Auth user | context only; re-hydrate on reload |

`localStorage` keys: `fp_access_token`, `fp_etag:<url>`, `fp_cache:<url>` (public read-only data only — never predictions).

---

## 5. Deadline & phase-aware UI

`useDeadline(round)` → `{ deadlinePassed, secondsLeft, formatted }`:
- compares `now` vs `round.deadline` (UTC) every 1s via `setInterval`.
- `deadlinePassed` switches prediction form to readonly and shows «Дедлайн прошёл».
- Server is source of truth: `RoundPredictionsView.deadline_passed` overrides client clock if they disagree.

Phase derivation (mirrors plan §3.6) lives in a pure helper `deriveUiMode(contest, round)` → flags used by components (`canEditPredictions`, `canEditSetup`, `canEnterResults`, `mutationsDisabled`).

---

## 6. Optimistic updates

- Prediction save: optional optimistic render of submitted scores; on error roll back and show `detail`. Keep simple — re-fetch after save is acceptable for MVP.
- Admin mutations (activate/close/calculate/publish, VOID): no optimism; await response, then `refetch` affected lists. Show `ConfirmDialog` before destructive actions.

---

## 7. Provider tree

```
<AuthProvider>           // frontend/src/providers/AuthProvider.tsx
  <ContestProvider>      // frontend/src/providers/ContestProvider.tsx
    <ToastProvider>      // frontend/src/providers/ToastProvider.tsx
      <TempPasswordGuard />  // frontend/src/components/auth/TempPasswordGuard.tsx
      {app}
    </ToastProvider>
  </ContestProvider>
</AuthProvider>
```

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-22 | B1–B3 resolved note; fallback via `NEXT_PUBLIC_DEFAULT_CONTEST_ID`; contacts readonly fallback. |
| 2026-06-23 | Stage 2.1: provider/hook file paths; `fp:unauthorized` event name; `TempPasswordGuard` in tree. |

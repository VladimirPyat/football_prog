# UI State Management (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§3.4–§3.6), `agent_docs/contracts/frontend_api_integration.md`, **`agent_docs/contracts/admin_ui_status_matrix.md`**.
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
| `changePassword(old,new)` | fn | `POST /auth/change-password` → `resolvePostLoginPath(user)` |

- Post-login and post-change-password navigation uses `resolvePostLoginPath(user)` (2.1.1) — no hardcoded `/profile` for all roles.
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
| `setContest(id)` | fn | switch active contest, **invalidate + refetch** (2.3.4 F1 — fixes stale DRAFT vs RUNNING fixture) |

- Public pages set `contestId` from the route param.
- User «Конкурсы» list from `GET /me/contests` (B1); Visitor list from `GET /contests/public` (B2); Supervisor picker from `GET /contests`.
- **Fallback:** B1/B2 empty or error → `resolveDefaultContestId()` from `NEXT_PUBLIC_DEFAULT_CONTEST_ID`.
- **`setupReadonly`:** derived from fresh `contest.status` + `is_locked` after refetch — not cached stale state.

---

## 3. Data fetching pattern

Lightweight SWR-style hooks over the typed API client (no external SWR lib unless justified later).

| Hook | Endpoint | Cache |
|------|----------|-------|
| `useRounds(contestId)` | `GET /contests/{id}/rounds` | in-memory; refetch after admin mutations — **Implemented (2.2)** → `frontend/src/hooks/useRounds.ts` |
| `useLeaderboard(contestId, roundId, enabled?)` | `GET …/rounds/{rid}/leaderboard` | in-memory; ETag deferred — **Implemented (2.4)** → `frontend/src/hooks/useLeaderboard.ts` |
| `useRoundResults(contestId, roundId, enabled?)` | `GET …/rounds/{rid}/results` | in-memory; ETag deferred — **Implemented (2.4)** → `frontend/src/hooks/useRoundResults.ts` |
| `usePredictionsView(contestId, roundId)` | `GET …/predictions` | **never cached** (privacy) — **Implemented (2.2)** → `frontend/src/hooks/usePredictionsView.ts` |
| `usePredictionSubmit(contestId, roundId)` | `POST …/predictions` | no cache — **Implemented (2.2)** → `frontend/src/hooks/usePredictionSubmit.ts` |
| `useDeadline(round, deadlinePassed?)` | client clock vs `round.deadline` | 1s tick — **Implemented (2.2)** → `frontend/src/hooks/useDeadline.ts` |
| `useMaxScore()` | from `ContestProvider` rules | in-memory — **Implemented (2.2)** → `frontend/src/hooks/useMaxScore.ts` |
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

**Effective round status (2.3.5):** `effectiveRoundStatus(round, deadlinePassed)` in `roundEffectiveStatus.ts` — when API still returns `ACTIVE` but deadline has passed, UI routes as **CLOSED («Дедлайн»)** until refetch completes. Use for phase panels, badges, and results eligibility; keep API mutations on real `round.id`.

`useDeadline(round)` → `{ deadlinePassed, secondsLeft, formatted }`:
- compares `now` vs `round.deadline` (UTC) every 1s via `setInterval`.
- `deadlinePassed` switches prediction form to readonly and shows «Дедлайн прошёл».
- Server is source of truth: `RoundPredictionsView.deadline_passed` overrides client clock if they disagree.

**Deadline transition refetch (2.3.5 U1):** `useRoundMatches(contestId, roundId, { onDeadlinePassed })` fires once when `view.deadline_passed` flips `false → true`; pages wire `onDeadlinePassed: () => refetchRounds()` on `/admin/rounds` and `/admin/results`. Backend 1.16 auto-closes round on predictions GET.

Phase derivation lives in **`deriveAdminUiMode(contest, round, { deadlinePassed })`** — **Implemented (2.3)** → `frontend/src/lib/admin/deriveAdminUiMode.ts`. Client deadline checks: `frontend/src/lib/admin/deadlineRule.ts` (placement vs 24h **change** lockout — 2.3.1 F2).

| Hook | Endpoint | Cache |
|------|----------|-------|
| `useContestAdmin()` | `GET/PATCH /contests/{id}` | refetch on mutations — **2.3** |
| `useTeams(contestId)` | `GET/POST/PATCH/DELETE …/teams`, logo upload | refetch; emits `contest-setup-changed` — **2.3.4 F6** |
| `useParticipants(contestId)` | `GET/POST/DELETE …/participants`, tiebreak | refetch; emits `contest-setup-changed` — **2.3.4 F6** |
| `useAdminRounds(contestId)` | admin round CRUD + activate/calculate/publish | refetch on mutations + deadline transition — **2.3.5** |
| `useRoundMatches(contestId, roundId, opts?)` | `GET …/predictions` | never cached; optional `onDeadlinePassed` — **2.3.5** |
| `useAdminResults(contestId)` | `PUT …/result`, `PATCH …/status` | no cache — **2.3** |
| `useContestStartReadiness(contestId)` | teams + participants counts | refetch on `contest-setup-changed` — **2.3.4 F3** |

---

## 6. Optimistic updates

- Prediction save: optional optimistic render of submitted scores; on error roll back and show `detail`. Keep simple — re-fetch after save is acceptable for MVP.
- Admin mutations (activate/calculate/publish, VOID): no optimism; await response, then `refetch` affected lists. Show `ConfirmDialog` before destructive actions.
- Contest start (2.3.3–2.3.4): `onBeforeStart` saves parameters + rules, then `POST /start`; refetch contest on success.
- Round close: **no manual UI** — backend auto-close on deadline (1.16); UI refetches rounds via `onDeadlinePassed` (2.3.5).

---

## 7. Custom events (2.3.3–2.3.4)

| Event | Emitters | Listeners |
|-------|----------|-----------|
| `contest-setup-changed` | `useTeams`, `useParticipants` | `useContestStartReadiness` |
| `contest-list-changed` | delete contest success | `ContestPicker` refresh |

---

## 8. Provider tree

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
| 2026-06-24 | Stage 2.1.1: post-login routing via `resolvePostLoginPath` in `AuthProvider.login` / `changePassword`. |
| 2026-06-24 | Stage 2.3: `deriveAdminUiMode`, admin hooks (`useContestAdmin`, `useTeams`, …), `deadlineRule` client check. |
| 2026-06-28 | Stage 2.3.1: 24h policy (placement vs change lockout); `roundStatusHint`. |
| 2026-06-28 | Stage 2.3.4: ContestProvider refetch on id change; `useContestStartReadiness`; `contest-setup-changed` events. |
| 2026-06-28 | Stage 2.3.5: `effectiveRoundStatus`; `useRoundMatches.onDeadlinePassed`; rounds refetch on deadline transition. |
| 2026-06-28 | Stage 2.2: `usePredictionsView`, `usePredictionSubmit`, `useDeadline`, `useMaxScore`, `useRounds`. |
| 2026-07-08 | Stage 2.4: `useLeaderboard`, `useRoundResults`; `contestPublic` path builders; PUBLISHED gate via `shouldFetchPublicResults`. |

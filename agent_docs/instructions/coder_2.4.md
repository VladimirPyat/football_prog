# Coder Instructions — Stage 2.4: API Wiring — Leaderboard & Results

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Sub-stages **2.1**, **2.2**, and **2.3** at `TEST_PASS` (or equivalent verified handoff). **Backend:** `agent_docs/instructions/backend/coder_1.17_leaderboard_fix.md` at `READY_FOR_TEST` / `TEST_PASS` — `GET …/results` must return populated `results[].points`.
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.4, §4.3–§4.4, §11.1.
> **Specs:** `agent_docs/ui/{components,pages,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md`, `docs/03_user_scenarios.md` §1.
> **Screenshots:** `docs/screens/user_leaderboard.jpg`, `user_result.jpg` — **layout already implemented**; do not redesign.
> **Language policy:** UI copy Russian; code comments English; API `detail` as-is.

---

## 1. Objective

**Wire the existing public contest page to live API** — replace display mocks with real leaderboard and results data. Visual components (`LeaderboardTable`, `ResultsMatrix`, sticky columns, mobile compact) **already exist** under `frontend/src/components/contest/`; this stage is **data integration**, not a UI rebuild.

| Deliverable | Description |
|-------------|-------------|
| `useLeaderboard` | Fetch global or per-round leaderboard; map API → table rows |
| `useRoundResults` | Fetch results matrix; map API → `ResultsMatrix` props |
| API types | `LeaderboardOut`, `ScoreDetailOut`, `RoundResultsOut` in `types/api.ts` |
| Contest page wiring | Remove `contestDisplayMock.ts` usage; add loading/error/stub gates |
| `ResultsUnavailableMessage` | Stub when round not `PUBLISHED` (public gate) |
| ETag caching (optional) | Extend `lib/api/cache.ts` for LB/results GETs |

**Non-goals:**

- Rebuilding `LeaderboardTable` / `ResultsMatrix` layout or Tailwind styling
- `LeaderboardViewToggle` + `localStorage` view mode (current auto-compact on `<1024px` is **locked** — keep as-is)
- New admin features → **2.3**
- Newsletter / audit log → **Stage 3**
- Backend changes — if 1.17 not done, append `BLOCKED.md`; never keep mocks in production path

---

## 2. Backend prerequisites

| ID | Needed for 2.4 | Status |
|----|----------------|--------|
| B4 | `count_*` in leaderboard rows | **RESOLVED** (1.7) |
| — | `GET …/leaderboard` (global + per-round), ETag | **RESOLVED** |
| — | `GET …/rounds/{rid}/results` with `results[].points[]` | **1.17** — required before Results tab |

**Leaderboard** endpoints are ready today. **Results matrix** requires **1.17** (`base_points` per match, `total_without_bonus3` on rows).

If 1.17 is not merged yet: ship leaderboard wiring first; Results tab shows stub «Данные результатов временно недоступны» only if API returns empty `points` — do **not** fall back to mocks.

**Test data:** `dev_setup.py` — contest `id=1`; rounds 1–9 **PUBLISHED** with scores; round 10 **ACTIVE** / **CALCULATED** (no public results).

---

## 3. Public contest page — `/contest/[contestId]`

Single tabbed page (unchanged from 2.2). **Default tab** may stay **`predictions`** — do not change unless product asks.

### 3.1 Layout (all tabs)

- **Header:** `AppShell` (2.1)
- **Title:** contest name + welcome subtitle (existing copy)
- **`ContestRoundToolbar`:** `RoundSelector` + optional `ContestPicker` when authenticated
- **`PublicTabs`:** `Лидерборд` | `Прогнозы` | `Результаты`

Changing round refetches **active tab** data only.

**Global leaderboard (optional):** current UI is per-round only. Adding «Общий» to `RoundSelector` is **optional** — if skipped, always use `GET …/rounds/{rid}/leaderboard` for the selected round.

### 3.2 Tab «Лидерборд»

**Client gate (mandatory — 2.3.1):**

```ts
import { isRoundPubliclyVisible, ROUND_NOT_PUBLISHED_COPY } from '@/lib/contest/roundPublicVisibility';

if (!isRoundPubliclyVisible(selectedRound.status)) {
  // show stub — NO fetch
}
```

| Round status (public) | UI |
|-----------------------|-----|
| Not `PUBLISHED` | Stub: `ROUND_NOT_PUBLISHED_COPY` («Будет доступно после проверки организатором») |
| `PUBLISHED` | `useLeaderboard` → existing `LeaderboardTable` |

**API (after gate):**

| Selection | Endpoint |
|-----------|----------|
| Selected round N | `GET /api/v1/contests/{id}/rounds/{rid}/leaderboard` |
| Optional «Общий» | `GET /api/v1/contests/{id}/leaderboard` |

Visitor **no auth** required. Show `bonuses_pending` banner when API returns `bonuses_pending: true` (reuse copy from `RoundLeaderboardPreview` / `BONUSES_PENDING_FALLBACK_MESSAGE`).

### 3.3 Tab «Прогнозы»

**No regression** from 2.2 + **2.2.1**:

| Round phase | UI |
|-------------|-----|
| ACTIVE, `!deadline_passed`, non-ADMIN | `PredictionsVisitorStub` (or own-hint if authenticated) — **no fetch** for visitors |
| Post-deadline | Full matrix via `usePredictionsView` — **visitor without login** (2.2.1) |
| Authenticated pre-deadline | Privacy matrix per `shouldShowScore` |

**Do not** reintroduce `PredictionsLoginPrompt`.

### 3.4 Tab «Результаты»

**Client gate (same as leaderboard — 2.3.1):** public fetch only when `isRoundPubliclyVisible(status)` (`PUBLISHED` only). **Not** `CALCULATED` for visitors/users.

| Condition | UI |
|-----------|-----|
| Not `PUBLISHED` | `ResultsUnavailableMessage` with `ROUND_NOT_PUBLISHED_COPY` — **no fetch** |
| `PUBLISHED` | `useRoundResults` → existing `ResultsMatrix` |
| API `403` `RESULTS_NOT_AVAILABLE` | Same stub (never crash) |
| API `points` empty after 1.17 | Error state or one-line «Не удалось загрузить очки по матчам» — **never mock** |

**Results matrix** (existing component — keep visuals):

- Map `matches[]` → column headers + score sub-row
- Map `results[].points[].base_points` → `match_points` in **matches order**
- Map `total_without_bonus3` → `total_without_bonus`; `total` → `total`
- `-` for null bonus cells

---

## 4. Leaderboard & results — reuse existing UI

### 4.1 `LeaderboardTable` — **keep file** `components/contest/LeaderboardTable.tsx`

Do **not** move to `components/leaderboard/` or change column layout.

**Change only:**

- Props: accept API-mapped rows (same field names as today’s mock: `rank`, `user_name`, `predictions_count`, `count_*`, bonuses, totals)
- Remove `MockLeaderboardRow` import — use `ScoreDetailOut` + rank fields from `lib/leaderboard/mapLeaderboardRow.ts`

**Responsive behaviour (locked — do not change):**

- Desktop `≥1024px`: full 13 columns + horizontal scroll + sticky `Место` / `Фамилия`
- Mobile `<1024px`: auto-compact via `matchMedia` (shows subset + row detail modal) — **no** `LeaderboardViewToggle`, **no** `localStorage`

### 4.2 `ResultsMatrix` — **keep file** `components/contest/ResultsMatrix.tsx`

**Change only:**

- Props: typed API shapes via `mapRoundResultsRow.ts`
- Remove mock imports

### 4.3 Column mapping (leaderboard)

| UI (RU) | API field |
|---------|-----------|
| Место | `rank` |
| Фамилия Имя | `user_name` |
| Дано прогнозов | `predictions_count` |
| Точный кр. счет | `count_exact_high` |
| Точный счет | `count_exact` |
| Разница | `count_diff` |
| Исход | `count_outcome` |
| Бонус 1–3 | `bonus1` … `bonus3` |
| Очки без бонуса | `total_without_bonus3` |
| Очки с бонусами | `total_with_bonus3` |
| Всего очков | `total_with_bonus3` (+ tie-break badge if `exceptional_tiebreak_points > 0`) |

If B4 fields missing at runtime → log warning + hide four count columns (legacy fallback).

---

## 5. API layer & hooks

### 5.1 `lib/api/endpoints.ts`

Add global leaderboard builder:

```ts
export const contestPublic = {
  leaderboard: (contestId: number) => `/api/v1/contests/${contestId}/leaderboard`,
  roundLeaderboard: (contestId: number, roundId: number) =>
    `/api/v1/contests/${contestId}/rounds/${roundId}/leaderboard`,
  roundResults: (contestId: number, roundId: number) =>
    `/api/v1/contests/${contestId}/rounds/${roundId}/results`,
};
```

(`contestAdmin.rounds.leaderboard/results` may be reused — avoid duplicate path strings.)

### 5.2 `types/api.ts`

```ts
export interface MatchPointsOut {
  match_id: number;
  base_points: number | null;
}

export interface RoundResultRowOut {
  user_id: number;
  user_name: string;
  points: MatchPointsOut[];
  bonus1: number;
  bonus2: number;
  bonus3: number;
  total_without_bonus3: number;
  total: number;
  correct_outcomes: number;
}

export interface RoundResultsOut {
  round_id: number;
  matches: MatchOut[];
  results: RoundResultRowOut[];
}

export interface ScoreDetailOut { /* per api_v1.yaml ScoreDetail + rank fields */ }
export interface LeaderboardOut {
  contest_id: number;
  round_id: number | null;
  round_number: number | null;
  bonuses_pending?: boolean;
  bonuses_pending_message?: string | null;
  leaderboard: (ScoreDetailOut & {
    rank: number;
    predictions_count: number;
    exceptional_tiebreak_points: number;
    tiebreaker_status: string | null;
  })[];
}
```

### 5.3 `useLeaderboard(contestId, roundId, enabled)`

- `enabled === false` when stub gate active
- `apiGet<LeaderboardOut>(roundLeaderboard path, false)` — public, no auth required
- Return `{ data, loading, error, refetch }`

### 5.4 `useRoundResults(contestId, roundId, enabled)`

- Map response → `{ matches, rows }` for `ResultsMatrix`
- `mapRoundResultsRow`: `points[i].base_points` → `match_points[i]`; align with `matches` order

### 5.5 ETag caching (optional — phase 2)

If time permits, wire `lib/api/cache.ts` + `If-None-Match` for LB/results only. **Not blocking** for 2.4 handoff if documented as deferred in handoff note.

**Never** cache predictions GET.

---

## 6. Scope — files to create/modify

```
frontend/src/
  app/contest/[contestId]/page.tsx           # REMOVE mocks; wire hooks + stubs
  components/contest/LeaderboardTable.tsx     # Props: API row type (not Mock*)
  components/contest/ResultsMatrix.tsx       # Props: API-mapped rows (not Mock*)
  components/contest/LeaderboardRowDetail.tsx # Update row type import
  components/contest/ResultsRowDetail.tsx    # Update row type import
  components/contest/ResultsUnavailableMessage.tsx  # NEW — stub copy
  lib/leaderboard/mapLeaderboardRow.ts       # NEW — optional thin mapper
  lib/results/mapRoundResultsRow.ts          # NEW — points[] → match_points[]
  lib/api/endpoints.ts                       # contestPublic paths
  types/api.ts                               # LeaderboardOut, RoundResultsOut
  hooks/useLeaderboard.ts                    # NEW
  hooks/useRoundResults.ts                   # NEW
  lib/api/cache.ts                           # OPTIONAL — ETag

# DELETE usage (file may remain for tests or remove if unused):
  lib/mocks/contestDisplayMock.ts            # Remove imports from page.tsx

agent_docs/ui/components.md                  # Mark 2.4 API-wired ✅
agent_docs/ui/pages.md                       # /contest/[id] data layer ✅
agent_docs/ui/state_management.md            # useLeaderboard, useRoundResults
agent_docs/contracts/frontend_api_integration.md
agent_docs/progress/stage_2.md               # APPEND handoff
manuals/FRONTEND_REFERENCE.md                # APPEND §2.4
```

**Do not create** `components/leaderboard/LeaderboardViewToggle.tsx`, `useLeaderboardViewMode.ts`, or duplicate table components unless explicitly requested later.

Stable selectors (already partial — verify):

```tsx
<table data-testid="leaderboard-table" …>
<div data-testid="results-matrix" …>
<div data-testid="results-unavailable" …>
```

---

## 7. Unit tests (Vitest)

| File | Tests |
|------|-------|
| `lib/leaderboard/mapLeaderboardRow.test.ts` | API row → table row; B4 fields preserved |
| `lib/results/mapRoundResultsRow.test.ts` | `points[]` → `match_points[]`; null handling; order |
| `lib/contest/roundPublicVisibility.test.ts` | (existing) — gate used before fetch |
| `lib/results/roundResultsGuard.test.ts` | `shouldFetchPublicResults(status)` true only `PUBLISHED` |
| `lib/api/cache.test.ts` | OPTIONAL — 304 / ETag store |

Run: `npm run test:unit`.

---

## 8. Documentation maintenance (required)

| File | Updates |
|------|---------|
| `agent_docs/ui/components.md` | LeaderboardTable / ResultsMatrix **API-wired (2.4)**; mock removed |
| `agent_docs/ui/pages.md` | `/contest/[id]` — real GETs, PUBLISHED gate |
| `agent_docs/ui/state_management.md` | `useLeaderboard`, `useRoundResults` |
| `agent_docs/contracts/frontend_api_integration.md` | RoundResults `points` shape (post-1.17) |
| `manuals/FRONTEND_REFERENCE.md` | §2.4 — data hooks, stub copy, no visual change note |

---

## 9. Acceptance criteria (2.4 done)

Manual + `tester_2.4`:

- [ ] **Visitor** `/contest/1` → **Лидерборд** on **PUBLISHED** round shows **real** rows (not mock names like «Сидоров С.С.» from `contestDisplayMock`)
- [ ] **Non-published** round → `ROUND_NOT_PUBLISHED_COPY` stub; **no** leaderboard/results network request
- [ ] **13 columns** on desktop; B4 counts from API on loaded data
- [ ] **Mobile:** existing auto-compact behaviour unchanged (no regression)
- [ ] **Results** tab: round 10 (non-published) → stub; round 9 → matrix with **non-zero** per-match cells from API
- [ ] **Прогнозы:** visitor post-deadline matrix without login (2.2.1); privacy pre-deadline unchanged
- [ ] **No** `contestDisplayMock` imports in `page.tsx` or production components
- [ ] `npm run build` + `npm run test:unit` + lint/tsc/format pass
- [ ] Living docs + `FRONTEND_REFERENCE.md` §2.4 updated
- [ ] ETag — optional; if skipped, note in handoff

---

## 10. Implementation order

1. Confirm **1.17** merged / `GET …/results` returns `points[]`
2. `types/api.ts` + `endpoints.ts` paths
3. `mapLeaderboardRow.ts`, `mapRoundResultsRow.ts` + unit tests
4. `useLeaderboard`, `useRoundResults`
5. `ResultsUnavailableMessage.tsx`
6. Update `LeaderboardTable` / `ResultsMatrix` prop types (no layout change)
7. Wire `page.tsx` — remove mocks, add gates + loading/error
8. Remove dead mock imports; optional delete `contestDisplayMock.ts` if unused
9. Docs + `FRONTEND_REFERENCE.md` §2.4
10. Append handoff → `stage_2.md`

---

## 11. Handoff

```
## YYYY-MM-DD — Coder (2.4 API wiring — leaderboard & results)
- STATUS: READY_FOR_TEST
- Scope: replace contestDisplayMock with useLeaderboard/useRoundResults; PUBLISHED gate; existing UI preserved
- Backend dep: coder_1.17_leaderboard_fix (results[].points)
- Verified: npm run build, test:unit, lint/tsc/format; checklist §9
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.4
- Deferred (if any): ETag caching, global «Общий» leaderboard selector
- Next: agent_docs/instructions/tester_2.4.md
```

---

## 12. Explicitly OUT OF SCOPE

- Rebuilding leaderboard/results visual design
- `LeaderboardViewToggle` / `localStorage` compact-full toggle
- `react-window` virtualization
- Backend scoring / 1.17 (separate instruction)
- Pixel-perfect screenshot regression automation
- Docker / CI pipeline (Stage 3)

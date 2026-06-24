# Coder Instructions — Stage 2.4: Leaderboard, Results & E2E Integration

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Sub-stages **2.1**, **2.2**, and **2.3** at `TEST_PASS`. Backend B1–B6 **RESOLVED** — see `agent_docs/reports/BLOCKED.md` (B4 count columns required for full leaderboard).
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.4, §4.3–§4.4, §11.1.
> **Specs:** `agent_docs/ui/{components,pages,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md`, `docs/03_user_scenarios.md` §1.
> **Screenshots:** `docs/screens/user_leaderboard.jpg`, `user_predict.jpg`, `user_result.jpg` — binding layout/copy.
> **Language policy:** UI copy Russian; code comments English; API `detail` as-is.

---

## 1. Objective

Complete the **public tabbed contest page** (`/contest/[contestId]`): full **Лидерборд** (13 columns + responsive modes), **Результаты** matrix, integration polish, and ETag caching. Stage 2.4 is the **integration milestone** — all prior sub-stages must work together on one page.

| Deliverable | Description |
|-------------|-------------|
| `LeaderboardTable` | 13 columns per screenshot; B4 `count_*`; responsive compact/full |
| `LeaderboardViewToggle` | Mobile `<1024px`: «📊 Полная» / «Краткая»; persists in `localStorage` |
| Sticky columns | `Место` + `Фамилия Имя` sticky on horizontal scroll |
| `ResultsMatrix` | Points grid; only when round `CALCULATED`/`PUBLISHED` |
| `PublicContestPage` | Tabs + `RoundSelector` wired to all three data sources |
| ETag caching | Leaderboard + results public GETs |
| E2E-ready | Stable `data-testid` / roles for Playwright (`tester_2.4`) |

**Non-goals:**

- New admin features → already **2.3**
- Newsletter / audit log → **Stage 3**
- Visual regression `toHaveScreenshot()` → manual QA
- Backend changes — gaps → append `BLOCKED.md`, never mock

---

## 2. Backend prerequisites (verified)

| ID | Needed for 2.4 | Status |
|----|----------------|--------|
| B4 | `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` in leaderboard | **RESOLVED** (1.7) |
| — | `GET …/leaderboard` (global + round) | public, ETag |
| — | `GET …/rounds/{id}/results` | public when CALCULATED/PUBLISHED; else `RESULTS_NOT_AVAILABLE` |

**No open blockers for 2.4.** If API omits B4 fields at runtime → log warning + hide four count columns (legacy fallback only — report as regression in `BLOCKED.md`).

**Test data:** `load_test_data.py` — contest `id=1`; rounds 1–9 **PUBLISHED** with results; round 10 **ACTIVE** (no public results yet).

---

## 3. Public contest page — `/contest/[contestId]`

Per locked decision (draft §11.1): **single tabbed page**, not separate routes for tabs.

### 3.1 Layout (all tabs)

- **Header:** brand `Sport Prognosis` · auth buttons (from 2.1 `AppShell`)
- **Title:** `Конкурс спортивных прогнозов` + welcome subtitle (from screenshot)
- **`RoundSelector`:** `Выберите тур: [Тур N (Текущий) ▾]` — `GET …/rounds`
  - Default: current **ACTIVE** round (or highest number with data)
  - Changing round refetches active tab data; **does not reset** leaderboard view mode (see §4)
- **`PublicTabs`:** `Лидерборд` | `Прогнозы` | `Результаты`

Deep link (optional): `/contest/[id]?tab=results&round=9` or `/contest/[id]/round/[roundId]` redirect preserving tab.

### 3.2 Tab «Лидерборд»

**API:**

| Round selection | Endpoint |
|-----------------|----------|
| «Общий» / global aggregate | `GET /api/v1/contests/{id}/leaderboard` |
| Specific round N | `GET /api/v1/contests/{id}/rounds/{rid}/leaderboard` |

Use round id from `RoundSelector`. Visitor **no auth** required.

**Visitor entry:** from `/` discovery → `/contest/1` → **Лидерборд** tab shows table without login.

### 3.3 Tab «Прогнозы»

Wire **2.2** components (`PredictionsMatrix`, privacy, `OutcomeStatsFooter`). No regression.

| Round state | Message |
|-------------|---------|
| Current ACTIVE, `!deadline_passed`, Visitor | «Будет доступно после дедлайна» |
| Past / post-deadline | auth user → matrix; visitor → login prompt |

### 3.4 Tab «Результаты»

**Show matrix only when** round `status ∈ { CALCULATED, PUBLISHED }` (from rounds list **or** successful `GET …/results`).

| Condition | UI |
|-----------|-----|
| ACTIVE / DRAFT / CLOSED (not calculated) | `ResultsUnavailableMessage`: «Результаты будут доступны после подведения итогов» |
| CALCULATED / PUBLISHED | `ResultsMatrix` from `GET …/rounds/{rid}/results` |
| API `403/404` `RESULTS_NOT_AVAILABLE` | Same graceful message (never crash) |

**Results matrix** (per `user_result.jpg`):

- Header row: match pairs + actual scores sub-row
- Cells: per-match points (`PointsCell` — green when &gt;0)
- Right columns: `Бонус 1 · Бонус 2 · Итого без бон. · Бонус 3 · ИТОГ` (horizontal scroll)
- `-` for N/A bonus (NULL display)

---

## 4. Leaderboard table — columns & responsive behaviour

### 4.1 Full column set (13 columns)

Order binding (screenshot + draft §4.3):

| # | UI (RU) | API field |
|---|---------|-----------|
| 1 | Место | `rank` |
| 2 | Фамилия Имя | `user_name` |
| 3 | Дано прогнозов | `predictions_count` |
| 4 | Точный кр. счет | `count_exact_high` |
| 5 | Точный счет | `count_exact` |
| 6 | Разница | `count_diff` |
| 7 | Исход | `count_outcome` |
| 8 | Бонус 1 | `bonus1` |
| 9 | Бонус 2 | `bonus2` |
| 10 | Бонус 3 | `bonus3` |
| 11 | Очки без бонуса | `total_without_bonus3` |
| 12 | Очки с бонусами | `total_with_bonus3` |
| 13 | **Всего очков** | `total_with_bonus3` (+ optional tie-break badge if `exceptional_tiebreak_points` &gt; 0) |

**Styling:**

- Bonus cols (8–10): subtle yellow background (`bg-amber-50` or similar)
- **«Всего очков»:** green emphasis (`text-green-700`, `bg-green-50`), right-aligned — **both compact and full modes**

### 4.2 Breakpoints

```ts
const LEADERBOARD_DESKTOP_BP = 1024; // match Tailwind `lg`
```

| Viewport | Behaviour |
|----------|-----------|
| **Desktop `≥1024px`** | Always **full** 13 columns; wrapper `overflow-x-auto` if needed |
| **Mobile `<1024px`** | Show `LeaderboardViewToggle`; user picks **Краткая** or **📊 Полная** |

**Краткая (compact):** 3 columns only:

`Место | Фамилия Имя | Всего очков`

**Полная (full):** all 13 columns + horizontal scroll.

### 4.3 Sticky first column(s)

On **horizontal scroll** (full mode desktop + mobile full mode):

- Sticky left: **`Место` + `Фамилия Имя`** (single sticky block or two sticky cells with `position: sticky; left: 0` / cumulative left offset)
- `z-index` above scrolling cells; subtle shadow on scroll
- Compact mode: no horizontal scroll needed (3 cols fit)

Implement in `LeaderboardTable.tsx` with Tailwind `sticky left-0 bg-white z-10` (+ second column `left-[width-of-first]` if separate).

### 4.4 View mode persistence

```ts
const STORAGE_KEY = 'fp_leaderboard_view_mode'; // 'compact' | 'full'
```

- Read on mount; write on toggle change
- **Persist across round changes** and tab switches (same contest session)
- Default mobile: `'compact'` if unset (recommended UX)
- Desktop: ignore stored mode for layout (always full); still may write preference for when user resizes to mobile

### 4.5 `LeaderboardViewToggle`

- Visible only when `window.innerWidth < 1024` (use `matchMedia('(max-width: 1023px)')` + resize listener or CSS hide on `lg:`)
- Labels: **`📊 Полная`** | **`Краткая`** (segmented control)
- Active state visually distinct

### 4.6 Virtualization (optional performance)

Loader has ~10 participants — **native `<table>` scroll is sufficient for MVP**.

If row count **≥100** causes measurable jank:

1. Profile with React DevTools / Lighthouse
2. Propose adding **`react-window`** (`FixedSizeList`) — **requires explicit user approval** before new npm dependency
3. Document decision in `frontend_api_integration.md` update log

Do **not** add virtualization preemptively.

---

## 5. Caching (ETag)

Implement in `lib/api/cache.ts` (extend 2.1 stub):

```ts
// Pseudocode
const res = await fetch(url, { headers: etag ? { 'If-None-Match': etag } : {} });
if (res.status === 304) return cachedBody;
// store ETag from res.headers.get('ETag') → localStorage fp_etag:<url>
```

Apply to:

- `GET …/leaderboard`
- `GET …/rounds/{rid}/leaderboard`
- `GET …/rounds/{rid}/results`

**Never** cache predictions GET (2.2 rule).

`useLeaderboard(contestId, roundId?)` and `useRoundResults(contestId, roundId)` — expose `refetch()` for manual refresh button (optional subtle «Обновить»).

---

## 6. Scope — files to create/modify

```
frontend/src/
  app/contest/[contestId]/
    page.tsx                              # UPGRADE — full PublicContestPage
  components/
    contest/PublicContestPage.tsx         # orchestrates tabs + round + data hooks
    contest/PublicTabs.tsx                # extend from 2.2
    contest/RoundSelector.tsx             # extend — global vs round leaderboard source
    leaderboard/LeaderboardTable.tsx      # NEW — 13 cols, sticky, responsive
    leaderboard/LeaderboardViewToggle.tsx # NEW
    leaderboard/leaderboardColumns.ts     # NEW — column defs full/compact
    leaderboard/useLeaderboardViewMode.ts # NEW — localStorage + matchMedia
    results/ResultsMatrix.tsx             # NEW
    results/ResultsUnavailableMessage.tsx # NEW
    results/PointsCell.tsx                # if not exists
  lib/
    leaderboard/mapLeaderboardRow.ts
    api/cache.ts                          # ETag implementation
  hooks/
    useLeaderboard.ts                     # extend — global vs round, ETag
    useRoundResults.ts                    # extend — status guard + ETag

agent_docs/ui/components.md               # UPDATE LeaderboardTable, ResultsMatrix ✅
agent_docs/ui/pages.md                    # UPDATE /contest/[id] complete ✅
agent_docs/ui/state_management.md         # UPDATE caching + view mode
agent_docs/contracts/frontend_api_integration.md
agent_docs/progress/stage_2.md            # APPEND handoff
manuals/FRONTEND_REFERENCE.md             # APPEND §2.4 routes, components, editable copy
```

Add stable selectors for E2E:

```tsx
<table data-testid="leaderboard-table" …>
<div data-testid="leaderboard-view-toggle" …>
<div data-testid="results-unavailable" …>
```

---

## 7. Unit tests (Vitest)

| File | Tests |
|------|-------|
| `leaderboard/leaderboardColumns.test.ts` | Full mode 13 headers; compact 3; API field mapping |
| `leaderboard/useLeaderboardViewMode.test.ts` | localStorage read/write; default compact |
| `lib/api/cache.test.ts` | 304 returns cached; new ETag stored |
| `results/roundResultsGuard.test.ts` | `canShowResults(status)` true only CALCULATED/PUBLISHED |

Run: `npm run test:unit`.

---

## 8. Documentation maintenance (required)

### 8.1 Living specs (`agent_docs/`)

Update living docs **Implemented (2.4)** + paths. New backend gap → `BLOCKED.md` append-only.

| File | Updates |
|------|---------|
| `agent_docs/ui/components.md` | `LeaderboardTable`, `ResultsMatrix`, toggle |
| `agent_docs/ui/pages.md` | Complete `/contest/[id]` tabbed page |
| `agent_docs/ui/state_management.md` | ETag cache, `useLeaderboardViewMode` |
| `agent_docs/contracts/frontend_api_integration.md` | Leaderboard/results GET, ETag |

### 8.2 Human frontend map (`manuals/FRONTEND_REFERENCE.md`) — required

Append to **§ Stage 2.4** (do not overwrite prior stages). Goal: a human can find leaderboard/results labels and tab copy without searching the repo.

For **routes** (upgrade existing `/contest/[contestId]` row or add sub-features): document tab labels «Лидерборд», «Прогнозы», «Результаты», round selector copy.

For **each new or materially changed component** add a row:

| Component | Source file | Editable copy (Russian strings) | Notes |

Include at minimum for 2.4:

- `PublicContestPage`, `LeaderboardTable`, `LeaderboardViewToggle`, `ResultsMatrix`, `ResultsUnavailableMessage`
- Column headers (13-col full / 3-col compact), toggle labels «Краткая» / «📊 Полная», empty/unavailable messages

Append one row to **Update log** at the bottom of `FRONTEND_REFERENCE.md`.

---

## 9. Acceptance criteria (2.4 done)

Manual + `tester_2.4`:

- [ ] **Visitor** opens `/contest/1` → **Лидерборд** without login; ≥1 row with `rank`, `user_name`, `total`
- [ ] **13 columns** on desktop; B4 count columns populated (non-zero spot-check on loaded data)
- [ ] **Mobile `<1024px`:** toggle **Краткая** / **📊 Полная** works; preference survives round change
- [ ] **Sticky** `Место`+`Фамилия` on horizontal scroll (full mode)
- [ ] **Green** «Всего очков» in compact and full modes
- [ ] **Results** tab: round 10 → graceful message; round 9 → matrix with points
- [ ] **Прогнозы** tab: no regression from 2.2
- [ ] **ETag:** second fetch sends `If-None-Match` (Network tab or unit test)
- [ ] **Integration E2E** green (see `tester_2.4.md`): user flows + supervisor flows + RBAC
- [ ] `npm run build` + `npm run test:unit` pass
- [ ] Living docs updated; `BLOCKED.md` — no new open blockers (or documented)
- [ ] `manuals/FRONTEND_REFERENCE.md` §2.4 appended (routes + components + copy)

---

## 10. Implementation order

1. `leaderboardColumns.ts` + unit tests
2. `useLeaderboardViewMode` + toggle component
3. `LeaderboardTable` (desktop full → sticky → compact mode)
4. `useLeaderboard` + ETag cache
5. `ResultsMatrix` + `ResultsUnavailableMessage` + `useRoundResults`
6. `PublicContestPage` — wire tabs + round selector
7. Upgrade `/contest/[id]/page.tsx`
8. `data-testid` pass for E2E
9. Update docs + verify B4 fields in network response
10. Append `manuals/FRONTEND_REFERENCE.md` §2.4
11. Append handoff → `stage_2.md`

---

## 11. Handoff

```
## YYYY-MM-DD — Coder (2.4 leaderboard & integration)
- STATUS: READY_FOR_TEST
- Scope: full tabbed contest page, LeaderboardTable responsive, ResultsMatrix, ETag
- UI: 13 cols, mobile toggle, sticky cols, localStorage view mode
- Verified: npm run build, npm run test:unit; checklist §9
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.4
- Next: agent_docs/instructions/tester_2.4.md
```

---

## 12. Explicitly OUT OF SCOPE

- `react-window` unless perf issue confirmed + user approves dependency
- Pixel-perfect screenshot regression automation
- Docker / CI pipeline (Stage 3)
- OpenAPI codegen

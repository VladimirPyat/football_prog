# Fix 2.4.1 — Leaderboard UI polish + round persistence

**Prerequisite:** `agent_docs/instructions/backend/fix_1.18_leaderboard_cumulative.md` at `TEST_PASS`
(API must expose `scope=total`, `predictions_count`, `total_bonus_points`).
**Scope:** frontend only.

---

## 1. Goals

| # | Issue | Fix |
|---|-------|-----|
| G1 | Leaderboard shows single-round totals | Request `GET …/rounds/{id}/leaderboard?scope=total` |
| G2 | Switching tabs resets round to «last active» | Keep `selectedRoundId` when changing leaderboard ↔ predictions ↔ results |
| G3 | Table headers cramped (`text-xs`), letters misaligned | Two-row grouped headers; `text-sm` minimum; no `text-[10px]` in LB table |
| G4 | Wrong total columns: «Очки с бонусами» duplicates «Всего очков» | Map columns per reference screenshot (`docs/screens/user_leaderboard.jpg` + user Excel mock) |
| G5 | Exact-score and bonus headers not grouped | Grouped `<thead>` rows (see §3) |

---

## 2. API wiring (G1)

### `useLeaderboard.ts`

Append `?scope=total` to round leaderboard URL:

```ts
contestPublic.roundLeaderboard(contestId, roundId) + "?scope=total"
```

(or add optional param to `endpoints.ts` helper).

Global leaderboard endpoint is unchanged (not used by contest page today).

### Types

Extend `LeaderboardEntryOut` with `total_bonus_points: number` and ensure `points_base`
is typed (already returned by API). Update `mapLeaderboardRow.ts`.

---

## 3. Leaderboard column layout (G4, G5)

Reference: user mock (28 тур) + `leaderboard.csv` semantics.

### Final columns (desktop, when `showCountColumns`)

| Col | Header row 1 | Header row 2 | Data field |
|-----|--------------|--------------|------------|
| … | Место | — | `rank` |
| … | Фамилия Имя | — | `user_name` |
| … | Дано прогнозов | — | `predictions_count` |
| 4–5 | **Точный счёт** (colSpan=2) | «крупный» / «счёт» | `count_exact_high` / `count_exact` |
| 6 | Разница | — | `count_diff` |
| 7 | Исход | — | `count_outcome` |
| 8–10 | **Бонус** (colSpan=3) | «1» / «2» / «3» | `bonus1` / `bonus2` / `bonus3` |
| 11 | Всего очков (без бонусов) | — | `points_base` |
| 12 | Всего бонусных очков | — | `total_bonus_points` |
| 13 | ИТОГО очков | — | `total_with_bonus3` (green highlight) |

**Remove** columns «Очки без бонуса» (`total_without_bonus3`) and «Очки с бонусами»
(duplicate of total). `total_without_bonus3` stays in API for results matrix; not shown on LB.

### Implementation notes

- Add `GroupedColumnHeader` (or extend `MultiLineColumnHeader`) for two-row `<thead>`:
  - row 1: group labels with `colSpan`;
  - row 2: sub-labels only where needed (empty cells under single-column headers use `rowSpan={2}`).
- Reuse pattern from `ResultsMatrix.tsx` (two header rows) but with proper grouping.
- Table base: `text-sm` or `text-base` (match `ResultsMatrix`); **drop `text-xs`** from LB headers.
- Widen narrow digit columns slightly if headers still clip (`COL_DIGIT2` min-width tweak OK).
- `LeaderboardRowDetail.tsx` (mobile modal): mirror new labels; show `points_base`,
  `total_bonus_points`, `total_with_bonus3`; remove duplicate «Очки с бонусами».

### `mapLeaderboardRow.ts`

```ts
export interface LeaderboardTableRow {
  // …existing…
  points_base: number;
  total_bonus_points: number;
  // keep total_without_bonus3 out of table row OR optional for detail only
}
```

Populate `total_bonus_points` from API; fallback `bonus1+bonus2+bonus3` only if field absent
(defensive, remove after 1.18 ships).

---

## 4. Round persistence across tabs (G2)

**File:** `frontend/src/app/contest/[contestId]/page.tsx`

**Current bug:** `handleTabChange` calls `pickDefaultRound(visibleRounds, newTab)` and overwrites
user's selection.

**Fix:**
- `handleTabChange` → only `setTab(newTab)`; do **not** reset `selectedRoundId`.
- Keep initial default in `useEffect` when `selectedRoundId == null` only (first load).
- If selected round becomes invisible after filter change, fall back to `pickDefaultRound` once.

Predictions tab may still default to ACTIVE round on **first visit** (when no selection yet);
after user picks a round on any tab, that ID persists across tab switches.

---

## 5. Tests

### Unit

- `mapLeaderboardRow.test.ts` — `points_base`, `total_bonus_points` mapping.
- New or updated test for grouped header component (snapshot or role/text assertions).

### E2E (update existing 2.4 specs)

- `contest_leaderboard_stub.spec.ts`:
  - assert non-zero `predictions_count` after 1.18 (e.g. contains `72` or column not all zeros);
  - assert «ИТОГО» / cumulative leader name matches API (e.g. `Ларин` on round 9);
  - scope query sent (optional: intercept or trust API data).
- Re-run: `npm run test:unit`, `npm run lint`, `npm run type-check`, targeted E2E LB specs.

---

## 6. Explicitly out of scope

- Demo `user` in predictions matrix — backend/bootstrap fix (separate TODO).
- Results matrix column layout (already uses «Итого без бон.» / «ИТОГО» — different table).
- Mobile compact mode: may hide count columns as today; modal detail must show full fields.

---

## 7. Handoff

- Append entry to `agent_docs/progress/stage_2.md`.
- Manual check: round 9 LB — `Ларин` #1, predictions 72, ИТОГО 436, bonuses sum 128.

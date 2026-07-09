# Fix 2.5.2 — Leaderboard & Results table styling harmonization

**Source:** manual QA screenshot (Jul 2026), participant `/contest/[id]` leaderboard tab.
**Prerequisite:** fix 2.5 / 2.5.1 shipped.
**Scope:** frontend only — no API, DB, or contract changes.

---

## 1. Goals

| # | Issue | Target |
|---|-------|--------|
| G1 | Inconsistent header font sizes; text overlap on narrow columns | Uniform `text-sm font-medium` headers; widen columns via `min-w` |
| G2 | `COL_DIGIT3` bakes in `font-semibold`; body sizes differ | Body uniform `text-sm`; emphasis via bold/color only |
| G3 | Bonus columns too narrow; count columns uneven | Equal-width groups: count×4, bonus×3, total×3 |
| G4 | «Всего очков (без бонусов)» + «Всего бонусных очков» as separate rowSpan=2 columns overlap | Group under «Сумма очков» with sub-headers «без бонусов» / «бонусы» |
| G5 | ResultsMatrix uses `text-base` + `MultiLineColumnHeader` (`text-xs`) — visually different | Match Leaderboard: `text-sm`, shared header helper, same column widths/colors |

---

## 2. Affected files

| File | Change |
|------|--------|
| `frontend/src/lib/table/columnStyles.ts` | Widen `COL_DIGIT2`/`COL_DIGIT3`; remove `font-semibold` from totals |
| `frontend/src/lib/table/headerLabel.tsx` | **New** — shared multiline header renderer |
| `frontend/src/lib/table/tableHeaderStyles.ts` | **New** — shared `TH_*` thead classes |
| `frontend/src/components/contest/LeaderboardTable.tsx` | «Сумма очков» group; import shared helpers; uniform typography |
| `frontend/src/components/contest/ResultsMatrix.tsx` | `text-sm`; shared headers/widths/colors; sticky name column |

**Out of scope:** `MultiLineColumnHeader.tsx` (keep for other consumers), backend, `docs/`, contracts.

---

## 3. Step-by-step instructions

### 3.1 `columnStyles.ts`

- `COL_DIGIT2`: `min-w-[3.25rem]` — shared by count columns (крупный, —, Разница, Исход) and bonus 1/2/3.
- `COL_NAME`: `min-w-[7rem] max-w-[11rem]` — participant name column (leaderboard + results).
- `COL_DIGIT3`: `min-w-[4.5rem]` — shared by total columns (без бонусов, бонусы, ИТОГО) and «Дано прогнозов» header.
- Remove `font-semibold` from `COL_DIGIT3`.

### 3.2 Shared helpers

Extract from `LeaderboardTable`:
- `headerLabel(lines)` → `lib/table/headerLabel.tsx` with `text-sm font-medium`, `whitespace-nowrap` per line.
- `TH_BASE`, `TH_STICKY`, `TH_GROUP`, `TH_BONUS`, `TH_TOTAL` → `lib/table/tableHeaderStyles.ts`.

### 3.3 `LeaderboardTable.tsx`

**Grouped header (desktop, `showCountColumns`):**

Row 1: … «Бонус» colSpan=3 → **«Сумма очков» colSpan=2** → «ИТОГО очков» rowSpan=2.

Row 2 sub-headers: «без бонусов» | «бонусы» (map to `points_base` | `total_bonus_points`).

**Compact / no-count branch:** shorten labels to «без бонусов» / «бонусы» (single row).

**Body:** all numeric cells `text-sm`; ИТОГО `font-bold text-green-700`; positive counts `font-medium text-green-600`.

### 3.4 `ResultsMatrix.tsx`

- Table: `text-sm` (not `text-base`).
- Replace `MultiLineColumnHeader` with `headerLabel` + `TH_*` classes.
- Match columns: `COL_DIGIT2` for match points + bonuses; `COL_DIGIT3` for totals.
- Sticky first column: `TH_STICKY left-0` on name header + body `sticky left-0`.
- Keep `roundLabel` sub-row and per-match score sub-row unchanged functionally.
- ИТОГО column: `TH_TOTAL` + `bg-green-50 font-bold text-green-700` in body.

---

## 4. Acceptance criteria

- [ ] All header cells same font size/weight (`text-sm font-medium`).
- [ ] No header text overlap at default desktop width; horizontal scroll OK.
- [ ] Bonus columns 1/2/3 equal width; count columns equal; total columns equal.
- [ ] «Точный счёт» group: top span + «крупный» / «—» sub-columns (— = exact score, not high).
- [ ] «Сумма очков» group: top span + «без бонусов» / «бонусы» sub-columns; ИТОГО separate after group.
- [ ] Results tab table visually matches Leaderboard styling.
- [ ] `npm run lint`, `npm run type-check`, `npm run test:unit` pass.

---

## 5. Verification commands

```bash
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run test:unit
```

**Manual:** `/contest/[id]` as USER → Лидерборд tab: verify headers, groups, no overlap; Results tab: same visual treatment.

---

## 6. Non-goals

- Column order or data semantics in ResultsMatrix (bonus 3 after «Итого без бон.» stays).
- Mobile compact layout redesign beyond width/typography fixes.
- New E2E tests (manual QA sufficient for styling).

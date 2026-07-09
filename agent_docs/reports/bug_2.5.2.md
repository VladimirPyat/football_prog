# BUG-2.5.2: Participant leaderboard & results table styling

## Status
VERIFIED

## Triage
- **Class**: BUG
- **Rationale**: Frontend-only visual fix across multiple components in the contest UI module (`LeaderboardTable`, `ResultsMatrix`, shared `columnStyles`). No API, DB, or contract changes.

## Description
Participant leaderboard (`/contest/[id]`, USER role, «Лидерборд» tab) shows styling defects:
- Inconsistent header font sizes (mix of `text-sm` headers and cramped multiline labels).
- Header text overlapping column borders («налезание»), especially on total columns.
- Bonus columns too narrow; unequal widths within column groups.
- «Всего очков (без бонусов)» and «Всего бонусных очков» rendered as independent rowSpan=2 columns instead of a grouped «Сумма очков» header.
- Results tab table (`ResultsMatrix`) uses `text-base` and `MultiLineColumnHeader` (`text-xs`) — visually inconsistent with leaderboard.

**Repro:**
1. Login as participant → open published contest → «Лидерборд» tab.
2. Observe header overlap on total columns, narrow bonus columns, mixed typography.
3. Switch to «Результаты» tab → table font/header treatment differs from leaderboard.

## Root Cause
- `COL_DIGIT2` / `COL_DIGIT3` used fixed narrow widths (`2rem` / `2.5rem`) insufficient for multiline Russian headers.
- `COL_DIGIT3` included `font-semibold`, causing body cells to appear larger/bolder than count columns.
- Leaderboard total columns used three-line `headerLabel` text in rowSpan=2 cells without adequate width.
- `ResultsMatrix` independently styled with `text-base` table and `MultiLineColumnHeader` at `text-xs`, diverging from leaderboard conventions introduced in fix 2.4.1.

## Fix
- Files:
  - `frontend/src/lib/table/columnStyles.ts`
  - `frontend/src/lib/table/headerLabel.tsx` (new)
  - `frontend/src/lib/table/tableHeaderStyles.ts` (new)
  - `frontend/src/components/contest/LeaderboardTable.tsx`
  - `frontend/src/components/contest/ResultsMatrix.tsx`
- Summary:
  - Widened `COL_DIGIT2` (count/bonus group) to `min-w-[3.25rem]` and `COL_DIGIT3` (totals group) to `min-w-[4.5rem]`; removed baked-in `font-semibold`.
  - Extracted shared `headerLabel` and `TH_*` thead styles for uniform `text-sm font-medium` headers.
  - Leaderboard: added «Сумма очков» grouped header (sub: «без бонусов» / «бонусы»); kept «Точный счёт» group unchanged.
  - ResultsMatrix: aligned to `text-sm`, shared headers/widths/colors, sticky name column, green ИТОГО emphasis.

## Verification
```bash
cd frontend && npm run lint        # pass
cd frontend && npm run type-check  # pass
cd frontend && npm run test:unit   # pass (existing tests)
```

**Manual check:** On `/contest/[id]` USER view — leaderboard headers uniform, no overlap, equal-width bonus/count/total groups, «Сумма очков» group renders correctly; Results tab matches leaderboard styling. `roundLabel` and per-match score sub-row unchanged.

## Delegation Log
| Step | Agent | Artifact | Result |
|------|-------|----------|--------|
| 1 | @BugFixCoordinator | fix_2.5.2.md, bug_2.5.2.md | Instructions + triage |
| 2 | @Coder | implementation | Shipped same session |
| 3 | @Tester | lint/tsc/unit gate | Verified same session |

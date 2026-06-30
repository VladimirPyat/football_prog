# BUG-2.2.4: Prediction form layout + matrix/table UX

## Status
VERIFIED

## Triage
- **Class**: BUG
- **Rationale**: Multiple frontend components (predictions matrix, LB/results tables); no contract changes.

## Description

### Original (score validation)
On the predict form page, entering a score > max misaligns the row. Team names in score input area should be short.

### Extended (matrix / tables)
1. Predictions tab: remove bootstrap staff rows (Admin User); use normal font sizes; fit width without tiny text.
2. Results tab: larger fonts.
3. Mobile LB/Results: tap row → modal with full participant stats.
4. Desktop LB: multi-line column headers; uniform column widths (2-digit / 3-digit / adaptive name).

## Root Cause
- `ScoreInput` error text broke flex alignment.
- Staff bootstrap users enrolled as participants appear in API entries.
- Matrix used `text-[10px]` headers; mock tables gated or not mobile-interactive.
- No modal for compact row drill-down.

## Fix
- `ScoreInput` / `PredictionMatchRow` — fixed error slot, short team labels.
- `filterMatrixEntries.ts` — exclude Admin/Supervisor User from matrix.
- `PredictionsMatrix` — `text-sm`, wider columns, `TeamColumnHeader size="normal"`.
- `ResultsMatrix` — `text-base`, mobile row modal via `DetailModal`.
- `LeaderboardTable` — `MultiLineColumnHeader`, `columnStyles.ts`, mobile row modal.
- `LeaderboardRowDetail` / `ResultsRowDetail` — full drill-down content.

## Verification
- `npm run lint` — pass
- `npm run type-check` — pass
- Manual: predictions tab no Admin User; mobile LB/Results row tap opens modal; score > 20 stable layout.

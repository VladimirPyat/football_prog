# BUG-2.5.4: Stale contest on admin settings + missing correct_outcomes column

## Status
VERIFIED

## Triage
- **Class**: BUG
- **Rationale**: Two related frontend defects spanning provider, admin shell, results mapping, and table components. No API/DB contract changes; `correct_outcomes` already exists in `RoundResultRowOut`.

## Description

### Issue 1 — Wrong initial teams/matches count on settings page
**Repro:** Open `/admin/settings/parameters`. `total_teams`, `matches_per_round`, `total_rounds` show values from a previously selected contest. Switch contest in header and back — correct values appear.

**Root cause:** `ContestProvider` does not clear stale `contest` when `contestId` changes before async fetch completes. `AdminPageShell` only shows loading when `loading && !contest`, so stale contest renders. `ContestParametersForm` initializes from stale `contest` prop.

### Issue 2 — Missing `correct_outcomes` in results matrix
**Request:** Show count of correctly guessed outcomes in round results table (Bonus 2 input). Label **«Исход»** per `LeaderboardTable` convention.

**API:** `RoundResultRowOut.correct_outcomes` already returned; no backend changes.

## Root Cause
1. `setContestId(id, true)` updates `contestId` but leaves prior `contest` object until fetch resolves.
2. `mapRoundResultsRow` omits `correct_outcomes`; `ResultsMatrix` / `ResultsRowDetail` have no column for it.

## Fix
- Files:
  - `frontend/src/providers/ContestProvider.tsx` — clear contest when id changes before fetch
  - `frontend/src/hooks/useContestAdmin.ts` — treat id mismatch as loading (`isStale`)
  - `frontend/src/components/admin/AdminPageShell.tsx` — block render on stale/missing contest
  - `frontend/src/app/admin/settings/parameters/page.tsx` — key form by `contest.id`
  - `frontend/src/lib/results/mapRoundResultsRow.ts` — map `correct_outcomes`
  - `frontend/src/lib/results/mapRoundResultsRow.test.ts` — assert mapping
  - `frontend/src/components/contest/ResultsMatrix.tsx` — «Исход» column before bonuses
  - `frontend/src/components/contest/ResultsRowDetail.tsx` — mobile detail field
- Summary: Clear stale contest state on switch; guard admin shell; expose `correct_outcomes` in results UI.

## Verification
```bash
cd frontend && npm run lint       # ✔ No ESLint warnings or errors
cd frontend && npm run type-check # ✔ pass
cd frontend && npm run test:unit  # ✔ 35 files, 175 tests passed
```

## Delegation Log
| Step | Agent | Artifact | Result |
|------|-------|----------|--------|
| 1 | @BugFixer | bug_2.5.4.md, fix_2.5.4.md | Created |
| 2 | @BugFixer | frontend implementation | Done |

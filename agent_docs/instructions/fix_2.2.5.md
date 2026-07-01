# Fix instructions: BUG-2.2.5

> **Status:** Implemented

## Objective
Fix prediction submit validation, post-deadline matrix completeness, and DRAFT round visibility for participants in contest «тест1» (2 matches/round).

## Non-goals
- Leaderboard / Results tab publish gating (unchanged — PUBLISHED only)
- Admin round management UI
- Changing batch-all-or-nothing semantics (still require all **actual** round matches)

## Affected files

### Frontend
- `frontend/src/components/predictions/PredictionForm.tsx`
- `frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx`
- `frontend/src/app/contest/[contestId]/page.tsx`
- `frontend/src/components/contest/RoundSelector.tsx`
- `frontend/src/components/predictions/PredictionsMatrix.tsx`
- `frontend/src/components/predictions/OutcomeStatsFooter.tsx`
- `frontend/src/components/predictions/TeamColumnHeader.tsx`
- `frontend/src/lib/contest/participantRoundFilter.ts` (new, small helper)
- `frontend/src/lib/contest/fetchContestDetails.ts` (optional: expose `matches_per_round`)

### Backend
- `src/services/prediction_service.py`
- `src/api/handlers/predictions.py`
- `src/schemas/contest.py` + `src/services/contest_discovery_service.py` (optional)
- `src/api/v1/contest_ops.py` (optional DRAFT filter)

## Step-by-step

### 1. Fix batch validation (Bug 1)

**Frontend `PredictionForm.tsx`:**
- Remove dependency on `matchesPerRound` prop for submit gating.
- Use `const requiredCount = matchIds.length`.
- `batchComplete = filledCount === requiredCount && requiredCount > 0`.
- `predictionBatchSchema(maxScore, requiredCount)`.

**Backend `prediction_service.py`:**
- Load `round_matches` before count check.
- Replace `len(items) != matches_per_round` with `len(items) != len(round_match_ids)`.
- Keep existing `submitted_match_ids != round_match_ids` validation.

### 2. Full participant matrix (Bug 2)

**Backend `build_round_predictions_view()`:**
- Query ACCEPTED `contest_participants` for `contest_id`, join `users`.
- Exclude ADMIN/SUPERVISOR staff accounts from matrix (mirror frontend `filterParticipantEntries` or filter server-side).
- For each participant, attach predictions from `visible_predictions()` output.
- Entry shape:
  - Has predictions → `{ user_id, user_name, submitted: true, predictions: [...] }`
  - No predictions → `{ user_id, user_name, submitted: false, predictions: null }`
- Sort entries by `user_name` or `user_id` consistently.

**Frontend `PredictionsMatrix.tsx`:**
- Integrate `OutcomeStatsFooter` as `<tfoot>` inside the same `<table>`.
- Change table class to `text-base` (match `ResultsMatrix`).
- Widen match header cells or reuse `ResultsMatrix` column classes.

**Frontend `page.tsx`:**
- Remove separate stats `<table>` wrapper; pass `showStats={deadline_passed}` to matrix.

**Frontend `shouldShowScore.ts`:**
- No change required if entries include all participants.

### 3. Hide DRAFT rounds (Bug 3)

**New helper `participantRoundFilter.ts`:**
```ts
export function filterParticipantVisibleRounds(rounds: RoundOut[]): RoundOut[] {
  return rounds.filter((r) => r.status !== "DRAFT");
}
```

**Apply in:**
- `contest/[contestId]/page.tsx` — filter before `ContestRoundToolbar` and `pickDefaultRound`.
- `contest/[contestId]/predict/[roundId]/page.tsx` — filter toolbar rounds.
- Optionally redirect/block if user navigates directly to `/predict/{draftRoundId}`.

**Optional backend:** filter DRAFT in `list_rounds` when caller is not SUPERVISOR+.

### 4. Optional: participant contest shell

Add `matches_per_round` to `UserContestOut` and populate from `Contest` in `list_user_contests()`. Update `buildParticipantContestShell()` to use API value instead of hardcoded 8.

### 5. Pre-deadline predictions tab (participant UX)

**`contest/[contestId]/page.tsx`:**
- Before deadline, USER/SUPERVISOR/visitor on «Прогнозы» tab → `PredictionsVisitorStub` (no matrix fetch).
- ADMIN still sees full matrix pre-deadline.
- Logged-in participants get hint: own prediction via «Сделать прогноз».

**`PredictionsVisitorStub.tsx`:**
- Add `showOwnPredictionHint` prop for participant copy.

### 6. Remove score range hint from prediction form

**`PredictionMatchRow.tsx`:**
- Remove `0–{maxScore}` label to the right of each match row.

## Acceptance criteria

1. USER on «тест1» round 2 (2 matches): Save enabled when both scores filled; POST returns 200.
2. After deadline: matrix lists **all** ACCEPTED participants; users without predictions show `—` in all match cells.
3. Statistics row aligns under match columns; team headers readable (not tiny 10px in 2.5rem cells).
4. Round selector for participants does **not** list DRAFT rounds (round 3 hidden until activated).
5. «Сделать прогноз» link still targets ACTIVE round only (`UserNavMenu` — already uses `activeRound`).
6. Before deadline: USER/SUPERVISOR on «Прогнозы» tab see stub (not matrix); own scores on `/predict/…` form.
7. Prediction form rows do not show `0–{maxScore}` range hint.

## Verification commands

```bash
uv run ruff check src/
uv run pytest tests/api/test_predictions_flow_1_3.py -q
cd frontend && npm run test && npm run lint && npm run type-check
```

Manual: `manuals/SUPERVISOR_TESTING_SCENARIOS.md` §11.3–11.7 checklists X3, X5.

# BUG-2.2.5: Prediction form submit, matrix participants, DRAFT round visibility

## Status
OPEN

## Triage
- **Class**: BUG
- **Rationale**: Three related defects across prediction UI and API handlers; no schema or API shape changes required beyond enriching `entries` with all ACCEPTED participants (already specified in `manuals/testing/SUPERVISOR_TESTING_SCENARIOS.md` §11).

## Description

Manual QA on contest **«тест1»**, round 2 with **2 matches** (`matches_per_round = 2`).

| # | Symptom | Repro |
|---|---------|-------|
| 1 | Cannot submit predictions — hint «Заполните прogнозы на все матчи тура» and disabled Save even when both match rows are filled | Login as USER → `/contest/{id}/predict/{round2_id}` → fill 2/2 scores → Save disabled |
| 2 | After deadline, predictions tab does not show all participants; layout issues (narrow columns, stats misaligned) | `/contest/{id}` → Прогнозы → select closed round after deadline → missing rows for users without predictions |
| 3 | Inactive (DRAFT) round 3 visible in participant round selector | `/contest/{id}` → round dropdown lists «Тур 3» while status is DRAFT |

## Root Cause

### Bug 1 — Submit blocked by wrong match count

**Primary (frontend):** `PredictionForm` validates batch completeness against `contest.matches_per_round`, not the actual matches returned by the API.

For USER participants, `GET /contests/{id}` returns **403** (SUPERVISOR+ only). `fetchContestDetails()` falls back to `buildParticipantContestShell()` with **hardcoded `matches_per_round: 8`**.

```34:34:frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx
  const matchesPerRound = contest?.matches_per_round ?? data.matches.length;
```

```80:80:frontend/src/components/predictions/PredictionForm.tsx
  const batchComplete = filledCount === matchesPerRound && matchIds.length === matchesPerRound;
```

With 2 actual matches and `matchesPerRound = 8`: `filledCount = 2`, `batchComplete = false` → hint + disabled button.

**Secondary (backend):** `submit_batch()` rejects on `len(items) != contest.matches_per_round` before validating against actual round match IDs. If contest config and round match count ever diverge, API also fails.

```93:97:src/services/prediction_service.py
    if len(items) != matches_per_round:
        raise ValidationError(
            f"Укажите прогнозы на все матчи тура: ожидается {matches_per_round}, "
            f"получено {len(items)}"
        )
```

### Bug 2 — Matrix missing participants + layout

**Backend:** `build_round_predictions_view()` builds `entries` only from users who have rows in `predictions` table. ACCEPTED participants without predictions (e.g. «Вика» in §11 manual) are omitted entirely — violates X3 («пустая строка»).

```87:108:src/api/handlers/predictions.py
    entries = []
    for uid, preds in by_user.items():
        ...
```

No join with `contest_participants WHERE status = ACCEPTED`.

**Frontend layout:**
- `PredictionsMatrix` uses `text-sm` table and `TeamColumnHeader size="normal"` → `text-xs` headers in 2.5rem-wide columns (`w-10`), smaller than page body and `ResultsMatrix` (`text-base`).
- `OutcomeStatsFooter` is rendered in a **separate** `<table>` in `page.tsx`, not as `<tfoot>` of the matrix table → column widths diverge; stats row appears misaligned relative to match columns.

**Note:** `shouldShowScore()` post-deadline logic is correct for empty cells (`—`) once entries include all participants.

### Bug 3 — DRAFT rounds visible to participants

**Backend:** `GET /contests/{id}/rounds` is public and returns **all** rounds including DRAFT.

```71:81:src/api/v1/contest_ops.py
@router.get("/rounds", response_model=list[RoundOut])
async def list_rounds(...):
    ...
    return await rounds_to_out(session, list(rounds))
```

**Frontend:** `RoundSelector` maps all rounds with no status filter. `useRounds()` passes the full list to `ContestRoundToolbar` on both `/contest/[id]` and predict page.

Manual expectation X5: «Тур DRAFT не в форме прогноза — только ACTIVE»; DRAFT should not appear in participant round picker.

## Status
FIXED

## Fix

Implemented in fix 2.2.5 — see `agent_docs/instructions/fix_2.2.5.md`.

### Frontend
- `PredictionForm`: batch validation uses actual `matchIds.length`, not hardcoded `matches_per_round`
- `participantRoundFilter.ts`: DRAFT rounds hidden for USER/visitor
- `PredictionsMatrix`: stats in `<tfoot>`, `text-base`, wider columns
- `PredictionsVisitorStub.tsx`: pre-deadline stub with optional hint for participants
- `PredictionMatchRow.tsx`: removed `0–{maxScore}` hint
- Pre-deadline «Прогнозы» tab: stub for USER/SUPERVISOR/visitor; ADMIN keeps full matrix

### Backend
- `prediction_service.py`: validate against actual round match count
- `predictions.py`: all ACCEPTED USER participants in matrix entries

### Recommended — Frontend

| File | Change |
|------|--------|
| `frontend/src/components/predictions/PredictionForm.tsx` | Derive `requiredMatchCount = matchIds.length`; use for `batchComplete` and `predictionBatchSchema` instead of `matchesPerRound` prop |
| `frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx` | Remove or stop passing misleading `matchesPerRound`; optionally drop prop entirely |
| `frontend/src/lib/contest/fetchContestDetails.ts` | Extend participant shell: add `matches_per_round` to `UserContestOut` **or** read from round/predictions context only |
| `frontend/src/lib/contest/participantRoundFilter.ts` (new) | `filterParticipantVisibleRounds(rounds)` → exclude `status === "DRAFT"` |
| `frontend/src/components/contest/RoundSelector.tsx` | Accept optional `rounds` pre-filtered, or filter internally via prop `hideDraft?: boolean` |
| `frontend/src/app/contest/[contestId]/page.tsx` | Pass filtered rounds to toolbar; guard `pickDefaultRound` against DRAFT |
| `frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx` | Same DRAFT filter on toolbar |
| `frontend/src/components/predictions/PredictionsMatrix.tsx` | Move `OutcomeStatsFooter` into same `<table>` as `<tfoot>`; bump table to `text-base`; widen match columns or match `ResultsMatrix` styling |
| `frontend/src/components/predictions/TeamColumnHeader.tsx` | Increase `normal` size to `text-sm` (align with matrix body) |

### Recommended — Backend

| File | Change |
|------|--------|
| `src/services/prediction_service.py` | Replace `len(items) != matches_per_round` with `len(items) != len(round_match_ids)` (load round matches first) |
| `src/api/handlers/predictions.py` | Join `contest_participants` (ACCEPTED, role USER) + `users`; merge with prediction data; emit entry per participant with `submitted: bool`, `predictions: null` when none |
| `src/schemas/contest.py` + `contest_discovery_service.py` | (Optional) Add `matches_per_round` to `UserContestOut` so participant shell is accurate |
| `src/api/v1/contest_ops.py` | (Optional) Filter DRAFT from `list_rounds` for unauthenticated / USER callers; keep full list for SUPERVISOR+ |

## Verification

```bash
# Frontend unit
cd frontend && npm run test -- src/lib/validation/prediction.test.ts

# Backend API (after fix)
uv run pytest tests/api/test_predictions_flow_1_3.py -q
# Add regression: round with 2 matches, contest matches_per_round=2, USER submit 2/2 → 200
# Add regression: GET predictions after deadline includes ACCEPTED participant with no predictions
# Add regression: list rounds as USER excludes DRAFT

# Manual (manuals/testing/SUPERVISOR_TESTING_SCENARIOS.md §11)
# X3, X5, save with 2 matches on «тест1»
```

## Delegation Log
| Step | Agent | Artifact | Result |
|------|-------|----------|--------|
| 1 | @BugFixer | `agent_docs/reports/bug_2.2.5.md` | Investigation complete |
| 2 | @Coder | `agent_docs/instructions/fix_2.2.5.md` | Pending |
| 3 | @Tester | Regression tests | Pending |

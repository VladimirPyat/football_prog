# Coder Instructions — Stage 2.3.2 Backend: Edit Match Result on CALCULATED

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3.2 frontend (`coder_2.3.2_fix_tours.md`) — or may ship in parallel after frontend readonly on `CALCULATED`.
> **Related:** `manuals/API_GUIDE.md`, `manuals/STATUS_REFERENCE.md`, `agent_docs/contracts/contest_lifecycle_flow.md`.
> **Follow-up tester:** extend `tester_2.3.2_fix_tours.md` or add `tester_2.3.2_backend_calculated_edit.md`.
> **Language policy:** API `detail` Russian; code comments English.

---

## 1. Objective

Allow supervisor to **correct match scores after «Рассчитать»** without VOID, by extending `PUT …/result` to tours in `CALCULATED` status with automatic `recalculate_round`.

| ID | Problem | Target |
|----|---------|--------|
| **B1** | `set_result` rejects `CALCULATED` (`ROUND_NOT_CLOSED`) | Accept `CLOSED` **and** `CALCULATED` |
| **B2** | Scores in `scores` table stale after manual fix | Auto `recalculate_round` after PUT on `CALCULATED` |
| **B3** | Frontend readonly on `CALCULATED` (2.3.2) | Unlock edit in `deriveAdminUiMode` + `matchResultsGating` (§5) |
| **B4** | Docs / tests | API_GUIDE, STATUS_REFERENCE, pytest |

**Non-goals:**

- `set_result` on `PUBLISHED` (supervisor readonly; future ADMIN — separate stage).
- Kickoff guard on API (`now >= match.date_time`) — deferred until external match feeds.
- New endpoints; reopen `CALCULATED`→`CLOSED`.

---

## 2. Current behaviour (why change is needed)

```67:71:src/services/match_service.py
    if RoundStatus(round_.status) != RoundStatus.CLOSED:
        raise ContestRuleError(
            "Результат можно внести только на закрытом туре",
            code="ROUND_NOT_CLOSED",
        )
```

**Today:** after `POST …/calculate`, the only way to fix a wrong score is **VOID** match → `recalculate_round` via `change_status`.

**Product ask:** re-type scores on «Результаты» while tour is `CALCULATED`, then publish.

---

## 3. Backend implementation (B1, B2)

**File:** `src/services/match_service.py` — `set_result`

### 3.1 Allowed round statuses

```python
allowed_round = {RoundStatus.CLOSED, RoundStatus.CALCULATED}
if RoundStatus(round_.status) not in allowed_round:
    raise ContestRuleError(
        "Результат можно внести только на закрытом или рассчитанном туре",
        code="ROUND_NOT_CLOSED",
    )
```

Keep `PUBLISHED` rejected (not in set).

### 3.2 Auto-recalculate on CALCULATED

After setting scores and `match.status = FINISHED`:

```python
if RoundStatus(round_.status) == RoundStatus.CALCULATED:
    from services.scoring_persistence import recalculate_round
    await recalculate_round(session, round_id=round_.id, contest_id=contest_id)
```

Mirror pattern from `change_status` when `new_status == VOID` and round is `CALCULATED`.

### 3.3 Invariants (unchanged)

- `now >= round.deadline` (`DEADLINE_NOT_PASSED`).
- Score range `0..max_score`.
- Contest `RUNNING` (`assert_contest_running`).
- Re-PUT with same scores may recalc again — acceptable; optional skip if unchanged.

### 3.4 Error codes

| Case | HTTP | `code` |
|------|------|--------|
| `PUBLISHED` round | 403 | `ROUND_NOT_CLOSED` |
| Before deadline | 403 | `DEADLINE_NOT_PASSED` |
| `DRAFT` / `ACTIVE` | 403 | `ROUND_NOT_CLOSED` |

No router changes — same `PUT /api/v1/contests/{id}/admin/matches/{match_id}/result` in `contest_ops.py`.

---

## 4. Tests (B4)

**New:** `tests/api/test_results_calculated_edit_2_3_2.py`

| Case | Expected |
|------|----------|
| `CLOSED` → PUT result | 200, `FINISHED`, scores in match row |
| `CALCULATED` → PUT result (changed scores) | 200, `scores` rows updated, GET staff LB reflects change |
| `PUBLISHED` → PUT result | 403 |
| `CALCULATED` → PUT → publish still works | 200 publish |

Reuse `loaded_api` fixture pattern from `tests/api/test_operational_gaps_1_4.py`.

**Unit (optional):** extend `tests/unit/test_services_1_2.py` if direct `set_result` tests exist.

---

## 5. Frontend unlock (B3)

After backend merges, update files from `coder_2.3.2_fix_tours.md`:

**`matchResultsGating.ts`:**

```ts
// CALCULATED: allow re-edit for FINISHED matches (kickoff always passed)
round.status === "CALCULATED" && match.status === "FINISHED"
```

**`deriveAdminUiMode.ts`:**

```ts
canEnterResults =
  (roundStatus === "CLOSED" || roundStatus === "CALCULATED") && !disableAllMutations;
resultsReadonly = roundStatus === "PUBLISHED" || disableAllMutations;
```

**`MatchResultRow`:** enable inputs when `canEnterMatchResult()` on `CALCULATED`.

**Copy on `CALCULATED`:** «Можно исправить счёт — очки пересчитаются автоматически. После „Опубликовать“ правка недоступна.»

If frontend 2.3.2 ships first with `CALCULATED` readonly, this section is the **only delta** for frontend in the backend PR.

---

## 6. Documentation

| File | Update |
|------|--------|
| `manuals/API_GUIDE.md` | § `match_service.set_result` — `CLOSED` \| `CALCULATED`; recalc on CALCULATED |
| `manuals/STATUS_REFERENCE.md` | Row `CALCULATED` / Results: «правка счёта + авто-пересчёт»; VOID still valid |

---

## 7. Verification

```bash
uv run pytest tests/api/test_results_calculated_edit_2_3_2.py -q
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -q
uv run ruff check src/services/match_service.py
uv run mypy src/services/match_service.py
cd frontend && npm run test:unit  # if B3 frontend unlock included
```

**Manual:** round 10 `CALCULATED` on fixture → change one match score on Результаты → staff LB preview updates → publish.

---

## 8. Acceptance criteria

- [ ] `PUT result` returns 200 on `CALCULATED` tour
- [ ] `scores` table and staff LB update without manual recalculate call
- [ ] `PUT result` on `PUBLISHED` still 403
- [ ] VOID path unchanged
- [ ] Frontend unlock on `CALCULATED` (or documented as follow-up commit)
- [ ] API_GUIDE + STATUS_REFERENCE updated

---

## 9. Handoff

1. Append `agent_docs/progress/stage_2.md`
2. Tester tag: `[API-RESULT-CALCULATED]`

**Execution order:**

1. `coder_2.3.2_fix_tours.md` (frontend; `CALCULATED` scores readonly + hint about VOID)
2. **`coder_2.3.2_backend_calculated_edit.md`** (this file)
3. Tester covers both

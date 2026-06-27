# Coder Instructions — Stage 2.3.2 Fix: Tours & Results Tab UX

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3.1 (`coder_2.3.1_fix.md`); Stage **1.14** (`coder_1.14_data_fix.md`) — dev fixture with rounds 1–9 `PUBLISHED`, 10 `CALCULATED`, 11 `CLOSED` (**mandatory before manual QA**, §7).
> **QA feedback:** 2026-06-27 — supervisor walkthrough `/admin/rounds` + `/admin/results`; revised same day (match-kickoff gating, lifecycle clarity).
> **Related:** `manuals/API_GUIDE.md`, `manuals/STATUS_REFERENCE.md`, `manuals/DEV_SETUP.md`, `agent_docs/instructions/coder_1.14_data_fix.md`, `agent_docs/instructions/coder_2.3.2_backend_calculated_edit.md` (score edit after calculate — **separate backend stage**).
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.2_fix_tours.md`
> **Language policy:** UI copy Russian; code comments English; API `detail` Russian.

---

## 1. Objective

Align **Туры** and **Результаты** with supervisor mental model: match-level **«Идёт»** (display), kickoff-gated score entry, clear **Дедлайн → Рассчитан → Опубликован** pipeline, no participant LB on Туры, human validation messages.

**Primary strategy:** **frontend-only** — kickoff gating, UX, lifecycle copy. **No `src/` changes** in this stage.

Score edit on `CALCULATED` remains **API-forbidden** until `coder_2.3.2_backend_calculated_edit.md` (UI readonly + VOID hint until then).

| ID | Area | Problem | Target |
|----|------|---------|--------|
| **T1** | New tour form | Empty match date → cryptic error | «Укажите дату и время для каждого матча» |
| **T2** | `ACTIVE` tour | Duplicate «Сохранить изменения» | One save button |
| **T3** | Туры `CALCULATED` | Participant LB preview | Match scores + statuses only; CTA «Перейти к результатам» |
| **T4** | Туры `PUBLISHED` | Same | Match table + «Перейти к результатам» |
| **T5** | Туры `CLOSED` | Unclear next step | Read-only + `matchPhaseLabel` «Идёт»; CTA «Перейти к результатам» |
| **T6** | Результаты copy | «Проверить публичные результаты» | «Результаты участников» |
| **T7** | Результаты gating | Round/match availability unclear | Kickoff-based row edit on `CLOSED` (§3) |
| **T8** | Результаты edit | `FINISHED` rows locked on `CLOSED` | Re-edit on **`CLOSED` only**; `CALCULATED` readonly (§5) |
| **T9** | Результаты preview | No preview before publish | Staff LB preview on `CALCULATED` (§6) |
| **T10** | Результаты publish | — | «Опубликовать» only when `CALCULATED` (unchanged API) |
| **T11** | Lifecycle UX | Supervisor confused CLOSED→CALCULATED | Inline hints + §2 diagram on both tabs |
| **T12** | Dev QA fixture | DB lacks status matrix after loader / manual tests mutated data | Run **1.14 finalize** before manual QA; re-run on handoff (§7) |

**Non-goals:** `/admin`→`/supervisor` rename; real full predictions matrix (2.4); bulk `FINISHED` without scores; changing 2.3.1 deadline policy.

---

## 2. Locked lifecycle — rounds vs matches (READ FIRST)

### 2.1 Two layers (do not conflate)

| Layer | Enum | Who changes it |
|-------|------|----------------|
| **Tour** | `rounds.status` | API: `close`, `calculate`, `publish` |
| **Match** | `matches.status` | API: `PUT …/result` → `FINISHED`; `PATCH …/status` → VOID/POSTPONED/CANCELED |

**LOCKED:** `FINISHED` is set **only** by `set_result` with both scores. There is no «завершить матч без счёта».

### 2.2 Display-only «Идёт» (not a DB status)

Already in `matchPhaseLabel()` (`format.ts`):

- On tour **`CLOSED`** («Дедлайн»): if `match.status === SCHEDULED` and `now >= date_time` → show **«Идёт»**.
- DB stays `SCHEDULED` until supervisor saves a score → `FINISHED`.

Extend usage to **Результаты** table status column (same helper).

**No API change** for «Идёт».

### 2.3 End-to-end pipeline (supervisor-facing)

```text
ACTIVE (прогнозы)
    │  deadline passed (+ auto-close or «Закрыть тур»)
    ▼
CLOSED («Дедлайн»)          ← тур в списке «Результаты»
    │  per match: kickoff passed → «Идёт» (display)
    │  supervisor: PUT result → FINISHED + score1/score2
    │  (scores editable while tour still CLOSED — §5)
    │  all matches terminal (FINISHED | VOID | CANCELED)
    ▼
POST …/calculate
    ▼
CALCULATED («Рассчитан»)    ← очки в `scores`; staff preview LB; scores readonly in UI *
    ▼
POST …/publish
    ▼
PUBLISHED («Опубликован»)   ← публичная таблица; match scores readonly

* Edit on CALCULATED → `coder_2.3.2_backend_calculated_edit.md`
```

**Key clarification for UI copy:**

| Supervisor question | Answer |
|---------------------|--------|
| Когда тур на «Результаты»? | `round.status ∈ {CLOSED, CALCULATED, PUBLISHED}` after prediction deadline (today’s API). |
| Когда можно ввести счёт матча? | Tour `CLOSED` **and** `now >= match.date_time` — **UI gate** (§3). API: `PUT result` only on `CLOSED` today. |
| Когда «Рассчитать»? | Tour `CLOSED` and every match is `FINISHED` \| `VOID` \| `CANCELED` (existing `allFinished`). |
| Когда «Опубликовать»? | Tour `CALCULATED` only (`POST …/publish`). |
| Когда «Результаты участников»? | Preview on `CALCULATED` (staff API); full public matrix later on `PUBLISHED` (stub OK for now). |
| Когда можно править счёт после «Рассчитать»? | **Сейчас:** только VOID + пересчёт. **После backend 2.3.2:** `PUT result` на `CALCULATED` — см. `coder_2.3.2_backend_calculated_edit.md`. |

### 2.4 Match status «not synced» — expected behaviour

Loader/fixture may leave `CLOSED` tour with `SCHEDULED` matches (no scores) — **valid**. UI shows «Запланирован» or «Идёт» by clock, not by stale DB label.

Do **not** add a cron/sync job to flip `SCHEDULED`→`FINISHED` without scores. Sync happens only via `PUT …/result`.

---

## 3. Match kickoff gating (T7) — frontend helper

**New file:** `frontend/src/lib/admin/matchResultsGating.ts`

```ts
/** True when supervisor may enter/edit score for this match on Результаты. */
export function canEnterMatchResult(
  match: { status: string; date_time: string },
  round: { status: string },
  now: Date = new Date(),
): boolean;

/** True when at least one match in round is open or finished (for hints). */
export function roundHasStartedMatches(matches: { date_time: string }[], now?: Date): boolean;
```

**Rules (LOCKED for 2.3.2):**

| Condition | `canEnterMatchResult` |
|-----------|------------------------|
| `round.status === CLOSED` | `now >= Date.parse(match.date_time)` AND match not `VOID`/`CANCELED` |
| `round.status === CALCULATED` | `false` (readonly until backend 2.3.2; VOID still works) |
| `round.status === PUBLISHED` | `false` |
| `round.status === ACTIVE` / `DRAFT` | `false` |

**`MatchResultRow`:** when `!canEnterMatchResult` and match not terminal → disabled inputs + hint **«Матч ещё не начался»** (or show kickoff time).

**`ResultsEntryPanel`:** optional banner on `CLOSED` tour: «Счёт можно вносить после времени начала каждого матча».

**Round selector:** keep listing all `CLOSED`/`CALCULATED`/`PUBLISHED` tours (no filter by kickoff). Gating is **per row**, not per tour disappearance.

> **API note:** Kickoff is UI-only. Score edit on `CALCULATED` blocked by API until `coder_2.3.2_backend_calculated_edit.md`.

---

## 4. Implementation — Туры

### 4.1 T1 — Missing match date (`RoundBuilderForm` / `admin.ts`)

In `roundBuilderSchema` `superRefine`:

- Per match: empty/invalid `date_time` → `Укажите дату и время для каждого матча`.
- Compute `earliest` only from valid dates.

### 4.2 T2 — Duplicate save (`RoundManagementPanel.tsx`)

Remove duplicate «Сохранить изменения» block for `ACTIVE` (~lines 430–450). Keep one button.

### 4.3 T3–T5 — `RoundPhasePanel.tsx`

| Panel | Content | CTA |
|-------|---------|-----|
| `CLOSED` | Table: матч, дата, статус (`matchPhaseLabel`), счёт if any | **«Перейти к результатам»** only |
| `CALCULATED` | Table with scores; **no** `RoundLeaderboardPreview` | **«Перейти к результатам»** |
| `PUBLISHED` | Same table | **«Перейти к результатам»**; remove «Отменить» |

**Remove:** «Опубликовать» on Туры; «Матчи завершены» bulk button (superseded by §3 — FINISHED requires score).

**Remove:** «Просмотр прогнозов участников» stub (optional, low priority).

### 4.4 T11 — Lifecycle hints

Update `roundStatusHint("CLOSED")` to mention kickoff + Результаты tab, e.g.:

> «Дедлайн прошёл. После начала матча внесите счёт на вкладке „Результаты“, затем „Рассчитать“.»

---

## 5. Implementation — Результаты

### 5.1 T6 — Button label

| Before | After |
|--------|-------|
| «Проверить публичные результаты» | **«Результаты участников»** |

### 5.2 T8 — Score edit policy (`CLOSED` only in this stage)

**Problems today:**

1. `MatchResultRow` sets `disabled={scoresReadonly || finished}` — cannot re-edit on `CLOSED`.
2. After «Рассчитать», API rejects `PUT result` on `CALCULATED` — workaround: **VOID** (unchanged until backend stage).

**Target (frontend 2.3.2):**

| Tour status | Score inputs | «Применить» |
|-------------|--------------|-------------|
| `CLOSED` | Editable if `canEnterMatchResult()` | `PUT …/result` |
| `CALCULATED` | **Readonly** | hidden; hint + VOID |
| `PUBLISHED` | Readonly | hidden |

**`deriveAdminUiMode`:**

```ts
canEnterResults = roundStatus === "CLOSED" && !disableAllMutations;
resultsReadonly = roundStatus !== "CLOSED" || disableAllMutations;
canCalculate = roundStatus === "CLOSED" && allTerminal && !disableAllMutations;
canPublish = roundStatus === "CALCULATED" && !disableAllMutations;
```

**`MatchResultRow`:** remove blanket `finished` disable when `CLOSED` and `canEnterMatchResult()`.

**Copy:**

- `CLOSED`: «Проверьте счета перед „Рассчитать“.»
- `CALCULATED`: «Счёт зафиксирован. Исправление — через „Отменить матч“ (VOID) или после обновления backend (2.3.2-backend).»

### 5.3 T9 — «Результаты участников» preview

| Tour status | Button state | Action |
|-------------|--------------|--------|
| `CLOSED` | Disabled | `title="Сначала рассчитайте тур"` |
| `CALCULATED` | **Enabled** | Open modal/drawer with `RoundLeaderboardPreview` (staff GET LB — already 200 for supervisor on `CALCULATED` per 2.3.1) |
| `PUBLISHED` | Enabled | Stub «Полная матрица прогнозов — в следующих версиях» OR link to public contest page (product choice; stub OK) |

Move `RoundLeaderboardPreview` from Туры to Результаты (CALCULATED preview).

### 5.4 T10 — Action buttons order

Footer actions for selected tour:

1. **Рассчитать** — `CLOSED` + `allTerminal` (existing).
2. **Опубликовать** — `CALCULATED` only (existing).
3. **Результаты участников** — per §5.3.

### 5.5 Status column on Результаты

Use `matchPhaseLabel(match.status, match.date_time, round.status)` for `CLOSED`; `matchStatusLabel` for `CALCULATED`/`PUBLISHED`.

---

## 6. API — no changes in this stage

| Operation | Today | 2.3.2 frontend |
|-----------|-------|----------------|
| `PUT …/result` | `CLOSED` only | UI calls only on `CLOSED` |
| `PUT …/result` on `CALCULATED` | **403** `ROUND_NOT_CLOSED` | UI does not offer edit — backend fix separate |
| VOID on `CALCULATED` | recalc | unchanged |

See `coder_2.3.2_backend_calculated_edit.md` for `CALCULATED` PUT + recalc.

---

## 7. Dev fixture — 1.14 finalize (T12) — MANDATORY

Manual QA for T3–T5, T7–T10 requires contest `id=1` with **all round phases**. Default loader leaves rounds 1–9 `CLOSED` without `scores`, round 10 `ACTIVE`, no round 11 — see `coder_1.14_data_fix.md` §3.

**Coder MUST run finalize** before §9 manual walkthrough and **again** before `READY_FOR_TEST` if manual steps mutated rounds 10/11.

### 7.1 Fresh DB (recommended before first manual QA)

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
# ↑ includes finalize_dev_fixture(profile=manual) per 1.14
```

### 7.2 Repair existing DB (after manual testing or stale state)

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
```

Does **not** start servers; idempotent repair via `src/scripts/finalize_dev_fixture.py` (1.14 §6).

### 7.3 Expected matrix after finalize

| Round | Status | Use in 2.3.2 |
|-------|--------|--------------|
| 1–9 | `PUBLISHED` | T4 — Туры panel |
| 10 | `CALCULATED` | T3, T9 — preview on Результаты |
| 11 | `CLOSED`, `SCHEDULED` matches | T5, T7, T8 — kickoff + score entry |

### 7.4 Verify before manual QA

```bash
sqlite3 football.db "
SELECT r.number, r.status,
       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows
FROM rounds r
WHERE r.contest_id = 1 AND r.number >= 9
ORDER BY r.number;
"
```

**Expected:**

| number | status | score_rows |
|--------|--------|------------|
| 9 | `PUBLISHED` | 10 |
| 10 | `CALCULATED` | 10 |
| 11 | `CLOSED` | 0 |

Rounds 1–8 must also be `PUBLISHED` with 10 score rows each (full matrix — see `coder_1.14_data_fix.md` §7.1).

If verify fails and `--finalize-fixture-only` does not fix → **BLOCKED**: 1.14 not merged or `finalize_dev_fixture.py` missing.

### 7.5 Docs

Add or update QA reset callout in `manuals/DEV_SETUP.md` (1.14 §8): `--finalize-fixture-only` restores matrix after supervisor manual tests.

---

## 8. Files to touch (frontend only)

```
frontend/src/lib/admin/matchResultsGating.ts          # NEW
frontend/src/lib/admin/matchResultsGating.test.ts     # NEW
frontend/src/lib/admin/format.ts                    # hints (T11)
frontend/src/lib/validation/admin.ts                # T1
frontend/src/lib/admin/deriveAdminUiMode.ts         # T8
frontend/src/lib/admin/deriveAdminUiMode.test.ts
frontend/src/components/admin/RoundManagementPanel.tsx
frontend/src/components/admin/RoundPhasePanel.tsx
frontend/src/components/admin/ResultsEntryPanel.tsx
frontend/src/components/admin/MatchResultRow.tsx
frontend/src/components/admin/RoundLeaderboardPreview.tsx

manuals/STATUS_REFERENCE.md    # lifecycle hints (no CALCULATED PUT yet)
manuals/DEV_SETUP.md           # T12 QA reset
```

**No `src/` or `tests/api/` in this stage.**

---

## 9. Verification

### 9.1 Fixture (before manual QA)

Run §7.1 or §7.2, then §7.4 verify script. **Do not** start manual walkthrough on stale loader-only DB.

### 9.2 Frontend

```bash
cd frontend && npm run test:unit && npm run lint && npm run type-check
```

### 9.3 Manual (round 11, **after** §7 finalize)

1. Туры → tour 11 «Дедлайн»: matches show «Идёт» if kickoff passed.
2. Результаты → same tour: pre-kickoff rows disabled; post-kickoff → enter score → `FINISHED`.
3. Re-edit score on `CLOSED` before «Рассчитать».
4. «Рассчитать» → `CALCULATED`; scores readonly; preview «Результаты участников».
5. «Опубликовать» → `PUBLISHED` (optional — re-run §7.2 after if restoring matrix for tester).

### 9.4 Handoff restore

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
sqlite3 football.db "SELECT number, status FROM rounds WHERE contest_id=1 AND number >= 9 ORDER BY number;"
# Expect: 9 PUBLISHED, 10 CALCULATED, 11 CLOSED
```

---

## 10. Acceptance criteria

- [ ] T1–T7, T9–T11 as above
- [ ] T8: re-edit on **`CLOSED` only**; `CALCULATED` readonly + VOID hint
- [ ] **T12:** §7.4 verify passed **before** manual QA; `--finalize-fixture-only` run on handoff if manual mutated DB
- [ ] **No** `src/` changes (except `manuals/DEV_SETUP.md` T12 callout)
- [ ] Backend edit on `CALCULATED` → separate `coder_2.3.2_backend_calculated_edit.md`

---

## 11. Handoff

On `READY_FOR_TEST`:

1. Run §9.4 (finalize + verify) so tester gets full status matrix
2. Append `agent_docs/progress/stage_2.md` — note `fixture: 1.14 finalize OK`
3. Hand off to `tester_2.3.2_fix_tours.md`

| Tag | Description |
|-----|-------------|
| `[UI-MATCH-KICKOFF-GATE]` | T7 row enable/disable |
| `[UI-MATCH-PHASE-LABEL]` | «Идёт» on Туры + Результаты |
| `[UI-RESULTS-REEDIT-CLOSED]` | T8 score fix on CLOSED |
| `[UI-RESULTS-PREVIEW-CALC]` | T9 staff LB modal |
| `[UI-TOUR-PHASE-PANELS]` | T3–T5 |
| `[LIFECYCLE-HINTS]` | T11 |
| `[FIXTURE-RESET]` | T12 — 1.14 finalize before QA + on handoff |

---

## 12. Relation to other stages

| Stage | Note |
|-------|------|
| **2.3.2 backend** | `coder_2.3.2_backend_calculated_edit.md` — PUT on `CALCULATED` + UI unlock |
| **2.3.1** | LB gate, phase panels |
| **1.14** | **Prerequisite** — `finalize_dev_fixture`; T12 repair via `--finalize-fixture-only` |
| **2.4** | Full «Результаты участников» matrix |
| **Future** | External feeds + kickoff on API |

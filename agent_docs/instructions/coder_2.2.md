# Coder Instructions — Stage 2.2: Predictions & Privacy

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Sub-stages **2.1**, **2.1.1**, and **2.3** at `TEST_PASS` (auth shell, role routing, admin UI). Backend prediction API Stage 1.3+ (`GET/POST …/predictions`, privacy filter). See `agent_docs/reports/BLOCKED.md`.
> **Dev note:** Until 2.3 invite UI replaces bootstrap seed, use demo `user/user` from `bootstrap_users.py` (2.1.1) for prediction E2E — see `agent_docs/reports/todo.md`.
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.2, §3.6, §7.3.
> **Specs:** `agent_docs/ui/{components,pages,forms_validation,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md`, `agent_docs/contracts/admin_ui_status_matrix.md` (§10–11 — public LB/results vs predictions), `agent_docs/contracts/contest_lifecycle_flow.md` §3.3–3.4, `docs/03_user_scenarios.md` §3–§4.
> **Screenshots:** `docs/screens/user_predict.jpg` — prediction form + matrix layout reference.
> **Language policy:** UI copy Russian; code comments English; API `detail` shown as-is.

---

## 1. Objective

Implement **user prediction entry** and **privacy-aware predictions viewing**. All business rules must be visible in the UI (disabled controls, masks, banners), not only enforced by API errors.

| Deliverable | Description |
|-------------|-------------|
| `PredictionForm` | Batch-only save; score `0..maxScore`; Edit/Save toggle; readonly after deadline |
| `ScoreInput` | Integer-only; **empty ≠ `0`**; rejects non-numeric and out-of-range; **never POST empty as 0** |
| `PredictionsMatrix` | Прогнозы tab — privacy pre-deadline; full matrix post-deadline (authenticated) |
| `DeadlineCountdown` + `DeadlineWarningBanner` | Countdown; **warning when &lt;24h** to deadline |
| Privacy helpers | `shouldShowScore`, `PrivacyMask` — render from API `entries`, never infer hidden scores |
| Routes | `/contest/[id]/predict/[roundId]`; upgrade `/contest/[id]` with **Прогнозы** tab |
| Hooks | `usePredictionsView`, `usePredictionSubmit`, `useDeadline`, `useMaxScore` |

**Non-goals:**

- Full **Лидерборд** / **Результаты** tab polish (13 columns, points matrix) → **2.4**
- Supervisor admin UI → **2.3** (shipped — reuse `roundLabel.ts`, `roundPublicVisibility.ts` from admin work)
- Playwright E2E full suite → **tester_2.2**
- Mock API data

**Cross-stage rules (2.3.1+ — apply in 2.2 even for stubs):**

| Area | Rule | Source |
|------|------|--------|
| Public **Лидерборд** / **Результаты** tabs | Fetch only when `isRoundPubliclyVisible(round.status)` (`PUBLISHED`); else stub + **skip GET** | `lib/contest/roundPublicVisibility.ts`, `admin_ui_status_matrix.md` §10 |
| Stub copy (LB / Результаты) | **«Будет доступно после проверки организатором»** — not «после подведения итогов» | 2.3.1 F12, `ROUND_NOT_PUBLISHED_COPY` |
| **Прогнозы** tab | Privacy by **`deadline_passed`**, not by `PUBLISHED` — matrix rules unchanged (§3.4, §5.3) | `contest_lifecycle_flow.md` §3.3, `admin_ui_status_matrix.md` §11 |
| Round labels in `RoundSelector` | `Тур N` / **`ДопТурN`** via `formatRoundTitle()` | `lib/admin/roundLabel.ts` (2.3.4) |
| `RoundOut` API | May include `kind`, `supplementary_index`, `source_round_numbers` — use in selector labels | `types/api.ts`, 2.3.4 |
| User **&lt;24h warning** on predict form | Unchanged — independent of supervisor 24h **deadline change** lockout (2.3.1 F2) | This doc §3.3 |

---

## 2. Backend contract (verified)

| Endpoint | Auth | Notes |
|----------|------|-------|
| `GET /api/v1/contests/{id}/rounds` | public | Round list + statuses |
| `GET …/rounds/{rid}/predictions` | **Bearer required** (401 without token) | `deadline_passed`, `entries[]`, `matches[]` |
| `POST …/rounds/{rid}/predictions` | USER+ | Batch-only; all matches required |

**Privacy (server-side, mirror in UI):**

| Viewer | Pre-deadline | Post-deadline |
|--------|--------------|---------------|
| Visitor (no token) | No API call → stub «Будет доступно после дедлайна» | No anonymous GET → **login prompt** on Прогнозы tab (see §5.4) |
| USER / SUPERVISOR | Own scores visible; others → `predictions: null` → **`PrivacyMask`** «Прогноз сделан» | Full matrix from API |
| ADMIN | All scores (support) | Full matrix |

**Score range:** `maxScore = contest.rules_json.constraints.score_validation_range[1]` — **never hardcode 20** in validation or labels.

**Test data:** `load_test_data.py --reset` → contest `id=1` **RUNNING**; after **`coder_1.14` full profile** rounds **1–9 `PUBLISHED`**, **10 `CALCULATED`**, **11 `CLOSED`** — not ACTIVE round 10 by default. For prediction entry E2E/manual use **`dev_setup.py --ensure-running-only --e2e`** (or API helper) to restore **round 10 ACTIVE** with future deadline. Demo `user/user` enrolled via `bootstrap_users.py` (2.1.1). See `agent_docs/instructions/backend/coder_1.14_data_fix.md` §6.

---

## 3. UI rules (mandatory)

### 3.1 Batch-only predictions

- Form state: `Record<matchId, { score1?: number; score2?: number }>` — empty cells are **`undefined`**, not `0`.
- **`0` is valid** only when user **explicitly typed** `0` in both fields for that match.
- Submit **«Сохранить прогноз»** enabled only when `filledCount === matches.length === matches_per_round`.
- Partial fill (e.g. 7/8) → button **disabled** + optional hint «Заполните прогнозы на все матчи тура».
- POST sends exactly `matches_per_round` items; handle API `400` incomplete batch.

**Empty field ≠ zero (LOCKED — same rule as admin results, `coder_2.3` / `MatchResultRow`):**

| Rule | Requirement |
|------|-------------|
| UI state | Cleared input → `undefined` or `""` in local state — **not** `0` |
| Validation | **Do not** use `z.coerce.number()` on score fields — `""` coerces to `0` and sends a fake prediction |
| POST body | Include a match in `predictions[]` **only** when both `score1` and `score2` are explicit integers |
| Batch build | Filter/map: skip matches with missing either side; if count &lt; `matches_per_round` → disable submit (do not pad with `0`) |
| UX | Optional per-cell error on Save attempt: «Укажите счёт»; prefer disabling Save until batch complete |

Reference implementation (admin results, Stage 2.3.2): `lib/validation/admin.ts` → `matchResultSchema` (union `number | ""`, reject empty before transform).

### 3.2 Score validation (`ScoreInput`)

**Anti-pattern (forbidden):**

```ts
// WRONG — empty string becomes 0 and is sent to API
z.coerce.number().int().min(0).max(maxScore)
```

Use explicit optional/required flow:

```ts
// max from useMaxScore() / contest context — see §6 for batch schema
```

| Input | UI behaviour |
|-------|--------------|
| empty | `undefined`; does **not** count toward batch; **must not** appear in POST as `0` |
| `0` | valid; counts as filled only when user typed it |
| `abc`, `-`, `1.5` | reject on input or blur; inline error |
| `maxScore + 1` | disable submit + inline «Максимум {maxScore}» |
| API `SCORE_OUT_OF_RANGE` 422 | highlight cell + toast |

Label hint per match: «0–{maxScore}» (dynamic).

**`ScoreInput` implementation checklist:**

- `value`: `number | ""` (controlled); `onChange`: empty string stays `""`, not coerced to `0`
- Parent form aggregates only cells where both scores are defined integers
- «Сохранить прогноз» disabled until all matches filled — same as partial batch rule

### 3.3 Deadline UX

Implement `useDeadline(round)` per `state_management.md`:

| Signal | UI behaviour |
|--------|--------------|
| `now < deadline` | Form editable (if round ACTIVE + user ACCEPTED); show `DeadlineCountdown` |
| `secondsLeft <= 24h` and `> 0` | Show **`DeadlineWarningBanner`** (amber): «До дедлайна осталось менее 24 часов. Успейте сохранить прогноз.» |
| `now >= deadline` OR `deadline_passed` from API | Inputs **readonly**; Save/Edit disabled; countdown → «Дедлайн прошёл» |
| POST after deadline | expect `403` `DEADLINE_PASSED` → toast + force readonly |

**Server wins:** if `RoundPredictionsView.deadline_passed === true` but client clock disagrees → trust API.

**Auto-close (backend 1.16):** `GET …/predictions` runs lazy round close when `now >= deadline`; `deadline_passed` in response is authoritative. Optional poll/refetch on Прогнозы tab (60s) reveals full matrix after deadline without reload — same pattern as admin `useRoundMatches.onDeadlinePassed` (2.3.5), but participant UI only needs predictions refetch.

### 3.4 Privacy matrix (`PredictionsMatrix`)

Pure helper `lib/privacy/shouldShowScore.ts`:

```ts
export function shouldShowScore(
  entry: { user_id: number; predictions: unknown[] | null },
  viewer: { id: number; role: 'USER' | 'SUPERVISOR' | 'ADMIN' } | null,
  deadlinePassed: boolean,
): boolean {
  if (deadlinePassed) return entry.predictions !== null;
  if (!viewer) return false;
  if (viewer.role === 'ADMIN') return entry.predictions !== null;
  if (entry.user_id === viewer.id) return entry.predictions !== null;
  return false;
}
```

| Cell | Render |
|------|--------|
| show score | `ScoreCell` `N:M` |
| hide (submitted) | `PrivacyMask` «Прогноз сделан» |
| not submitted | «—» or empty |
| visitor pre-deadline (no fetch) | page stub only — no matrix |

**Never** reconstruct hidden scores client-side.

### 3.5 Edit flow

1. Load existing via `GET …/predictions` → prefill form for **current user** row only.
2. After save → readonly view + button **«Редактировать»** (until deadline).
3. Edit → re-enable inputs; Save → POST batch again (full replace).

### 3.6 Guards

| Guard | Route |
|-------|-------|
| `requireAuth` | `/contest/[id]/predict/[roundId]` |
| `requireNotTempPassword` | predict page + POST |
| `requireRole USER+` | predict (SUPERVISOR may use separate USER login to play — same privacy rules) |

`PARTICIPANT_NOT_ACCEPTED` (403) → banner «Смените временный пароль» + link `/change-password`.

Round not **ACTIVE** (for POST) / contest **PAUSED** / **FINISHED** → disable form + explain. Viewing **Прогнозы** matrix on past rounds (`deadline_passed`) is allowed for **CLOSED / CALCULATED / PUBLISHED** — visibility is deadline-based, not publish-based.

---

## 4. Scope — files to create/modify

```
frontend/src/
  app/contest/[contestId]/
    page.tsx                              # UPGRADE: RoundSelector + PublicTabs (Прогнозы live; Лидерборд/Результаты stub → 2.4)
    predict/[roundId]/page.tsx            # NEW — PredictionForm page
  components/
    contest/PublicTabs.tsx                # NEW — Лидерборд | Прогнозы | Результаты
    contest/RoundSelector.tsx             # NEW — dropdown Тур N
    predictions/PredictionForm.tsx
    predictions/PredictionMatchRow.tsx
    predictions/ScoreInput.tsx
    predictions/DeadlineCountdown.tsx
    predictions/DeadlineWarningBanner.tsx
    predictions/PredictionsMatrix.tsx
    predictions/PrivacyMask.tsx
    predictions/PredictionsVisitorStub.tsx
    predictions/PredictionsLoginPrompt.tsx
    predictions/OutcomeStatsFooter.tsx    # optional in 2.2 if matrix visible; full polish 2.4
  lib/
    privacy/shouldShowScore.ts
    privacy/formatPredictionCell.ts
    contest/roundPublicVisibility.ts     # EXISTS — reuse isRoundPubliclyVisible, ROUND_NOT_PUBLISHED_COPY
    admin/roundLabel.ts                  # EXISTS — reuse formatRoundTitle in RoundSelector
    validation/prediction.ts              # Zod batch schema
    validation/score.ts                   # reusable score field
  hooks/
    usePredictionsView.ts
    usePredictionSubmit.ts
    useDeadline.ts
    useMaxScore.ts                        # or derive from ContestProvider
  lib/api/endpoints.ts                    # extend predictions paths

agent_docs/ui/components.md               # UPDATE §3 predictions + paths
agent_docs/ui/pages.md                    # UPDATE §1 predict + contest tabs ✅
agent_docs/ui/forms_validation.md         # UPDATE PredictionForm paths
agent_docs/ui/state_management.md         # UPDATE hooks §3
agent_docs/contracts/frontend_api_integration.md
agent_docs/progress/stage_2.md            # APPEND handoff
manuals/FRONTEND_REFERENCE.md             # APPEND §2.2 routes, components, editable copy
```

Enable profile link **«Сделать прогноз»** → `/contest/{activeContestId}/predict/{activeRoundId}` (resolve ACTIVE round from `useRounds`).

---

## 5. Pages & API mapping

### 5.1 Prediction entry — `/contest/[contestId]/predict/[roundId]`

**Sources:**

- `GET /contests/{id}` — `matches_per_round`, rules
- `GET …/rounds` — round selector labels
- `GET …/rounds/{rid}/predictions` — prefill + `matches[]`
- `POST …/rounds/{rid}/predictions` — `{ predictions: [{ match_id, score1, score2 }] }`

**Layout (per `user_predict.jpg`):**

- Header: contest title + `RoundSelector`
- `DeadlineCountdown` + conditional `DeadlineWarningBanner`
- List: venue/time, `TeamA [score1] : [score2] TeamB` per match
- Footer: **Сохранить прогноз** / **Редактировать** (state-dependent)

Redirect unknown round → nearest ACTIVE or list error.

### 5.2 Contest page — `/contest/[contestId]`

Upgrade from 2.1 placeholder:

| Tab | 2.2 behaviour |
|-----|---------------|
| **Лидерборд** | Minimal stub or basic `LeaderboardTable` if trivial — **not blocking** for 2.2. **Mandatory gate:** call `GET …/leaderboard` only when selected round is **`PUBLISHED`** (or global LB which excludes non-published server-side). Non-published round → `ROUND_NOT_PUBLISHED_COPY` stub, **no fetch** (2.3.1 F12). Full 13-column polish → **2.4**. |
| **Прогнозы** | **`PredictionsMatrix`** for selected round — privacy by `deadline_passed` (§5.3). **Not** gated by `PUBLISHED`. |
| **Результаты** | Stub with **`ROUND_NOT_PUBLISHED_COPY`** until round **`PUBLISHED`**; skip `GET …/results` otherwise. Full matrix → **2.4**. |

**`RoundSelector`** — behaviour **depends on active tab**:

| Tab | Round list / default |
|-----|----------------------|
| **Прогнозы** | Default = current **ACTIVE** round (open predictions) if any; else latest round with `deadline_passed` for matrix view. All rounds selectable; label via `formatRoundTitle(round)`. |
| **Лидерборд** / **Результаты** | Prefer **`PUBLISHED`** rounds for data fetch; non-published selection → stub (optional: show in dropdown disabled + tooltip `ROUND_NOT_PUBLISHED_SECONDARY`). |

Post-deadline on **Прогнозы**: authenticated users see **full matrix** for rounds where `deadline_passed === true` (including `CLOSED`, `CALCULATED`, `PUBLISHED`).

### 5.3 Прогнозы tab — authenticated USER+

1. `usePredictionsView(contestId, roundId)` — **no cache** (refetch on tab focus).
2. If `!deadline_passed`: render matrix with `PrivacyMask` for others; own row full scores.
3. If `deadline_passed`: render all submitted scores.
4. `OutcomeStatsFooter` below matrix when `deadline_passed` (compute П1/Х/П2 from visible entries).

### 5.4 Прогнозы tab — Visitor

| Round phase | UI |
|-------------|-----|
| Current ACTIVE, `!deadline_passed` | `PredictionsVisitorStub`: «Будет доступно после дедлайна» — **no API call** |
| Past round / `deadline_passed` | `PredictionsLoginPrompt`: «Войдите, чтобы просмотреть прогнозы участников» + **Вход** button (API requires Bearer) |

Document in `frontend_api_integration.md` — not a blocker; backend returns 401 for anonymous GET by design.

### 5.5 Profile shortcut

`/profile` → **Сделать прогноз** links to active round predict URL when ACTIVE round exists and deadline not passed; else disabled with tooltip.

---

## 6. Validation (Zod)

Per `forms_validation.md` — export from `lib/validation/prediction.ts` and `lib/validation/score.ts`.

**Score field (single cell / blur):** reject empty before treating as number — mirror `matchResultSchema` in `admin.ts`:

```ts
export function scoreInputSchema(maxScore: number) {
  const field = z.union([z.number(), z.literal("")]);
  return field.superRefine((val, ctx) => {
    if (val === "") {
      ctx.addIssue({ code: "custom", message: "Укажите счёт" });
      return;
    }
    if (!Number.isInteger(val) || val < 0 || val > maxScore) {
      ctx.addIssue({ code: "custom", message: `Допустимый диапазон: 0–${maxScore}` });
    }
  });
}
```

**Batch (POST payload):** build array only from matches with **both** scores as integers; then validate length:

```ts
export function predictionBatchSchema(maxScore: number, matchCount: number) {
  const score = z.number().int().min(0).max(maxScore);
  return z.object({
    predictions: z
      .array(z.object({ match_id: z.number().int(), score1: score, score2: score }))
      .length(matchCount),
  });
}
```

Call `predictionBatchSchema` only after the form layer has confirmed every match has two explicit numbers — never pass coerced values from empty inputs.

Separate `scoreInputSchema(maxScore)` for single-field blur validation in `ScoreInput`.

---

## 7. Unit tests (Vitest) — add in 2.2

| File | Tests |
|------|-------|
| `lib/validation/score.test.ts` | 0 valid; **empty rejected (not coerced to 0)**; max+1 rejected; non-int rejected |
| `lib/validation/prediction.test.ts` | 7/8 fails schema; 8/8 passes; **partial object with undefined scores must not serialize as 0**; uses dynamic maxScore |
| `lib/privacy/shouldShowScore.test.ts` | pre-deadline own vs other; post-deadline all; ADMIN bypass; visitor null |
| `lib/privacy/deadlineWarning.test.ts` | `shouldShowDeadlineWarning(secondsLeft)` true when ≤24h and >0 |

Run: `npm run test:unit`.

---

## 8. Documentation maintenance (required)

### 8.1 Living specs (`agent_docs/`)

Update living docs with **Implemented (2.2)** + file paths; append update log rows.

| File | Updates |
|------|---------|
| `agent_docs/ui/components.md` | Prediction components + paths |
| `agent_docs/ui/pages.md` | `/contest/[id]/predict/*`, Прогнозы tab |
| `agent_docs/ui/forms_validation.md` | Score/prediction Zod schemas |
| `agent_docs/ui/state_management.md` | `usePredictionsView`, `usePredictionSubmit`, etc. |
| `agent_docs/contracts/frontend_api_integration.md` | Predictions GET/POST, privacy matrix; note public LB/results **client gate** `PUBLISHED` (backend may 403 `RESULTS_NOT_AVAILABLE` — handle gracefully) |

Append update log rows — do not delete prior content.

### 8.2 Human frontend map (`manuals/FRONTEND_REFERENCE.md`) — required

Append to **§ Stage 2.2** (do not overwrite prior stages). Goal: a human can find and edit UI copy (footer, banners, button labels) without searching the repo.

For **each new route** add a row:

| Route | Page file | Role / guard | Main features |

For **each new or materially changed component** add a row:

| Component | Source file | Editable copy (Russian strings) | Notes |

Include at minimum for 2.2:

- `/contest/[contestId]/predict/[roundId]` — prediction form page
- `/contest/[contestId]` — Прогнозы tab wiring
- `PredictionForm`, `PredictionsMatrix`, `PrivacyMask`, `DeadlineCountdown`, `DeadlineWarningBanner`, `PublicTabs`, `RoundSelector`
- Any new banners, stubs, or button labels («Сохранить прогноз», «Редактировать», «Прогноз сделан», deadline messages)

Append one row to **Update log** at the bottom of `FRONTEND_REFERENCE.md`.

If integration reveals missing backend behaviour (e.g. anonymous post-deadline GET), append to `BLOCKED.md` — do not mock.

---

## 9. Acceptance criteria (2.2 done)

Manual + automated (`tester_2.2`):

- [ ] **Batch:** 7/8 filled → **Сохранить** disabled; 8/8 → enabled → save → reload shows data
- [ ] **Empty ≠ zero:** cleared cell → submit disabled; **no** `{ score1: 0, score2: 0 }` in POST unless user typed 0:0
- [ ] **Score 0** accepted and stored (not treated as empty)
- [ ] **Invalid:** non-numeric blocked; `maxScore+1` blocked in UI; API 422 surfaced
- [ ] **maxScore** from contest rules (label «0–N»), not hardcoded 20
- [ ] **Pre-deadline privacy:** USER sees own scores; others → «Прогноз сделан»; ADMIN sees all
- [ ] **LB/Results stubs:** non-`PUBLISHED` round → «Будет доступно после проверки организатором»; no spurious leaderboard/results fetch
- [ ] **Прогнозы not publish-gated:** matrix works on `ACTIVE` / post-deadline `CLOSED`/`CALCULATED`/`PUBLISHED` by `deadline_passed`
- [ ] **Visitor pre-deadline:** stub «Будет доступно после дедлайна» (no matrix)
- [ ] **Post-deadline:** authenticated user sees **full matrix**; form readonly
- [ ] **Deadline warning:** banner when &lt;24h remain
- [ ] **Deadline passed:** countdown «Дедлайн прошёл»; Edit/Save disabled; POST → 403 handled
- [ ] **Edit flow:** Save → **Редактировать** → change → Save again
- [ ] Profile **Сделать прогноз** → active round predict page
- [ ] `npm run build` + `npm run test:unit` pass
- [ ] Living docs updated
- [ ] `manuals/FRONTEND_REFERENCE.md` §2.2 appended (routes + components + copy)

---

## 10. Implementation order

1. `useMaxScore`, `score` / `prediction` Zod schemas + unit tests
2. `shouldShowScore` + privacy unit tests
3. `ScoreInput`, `PredictionMatchRow`, `PredictionForm`
4. `useDeadline`, `DeadlineCountdown`, `DeadlineWarningBanner`
5. `usePredictionsView`, `usePredictionSubmit`
6. Page `/contest/[id]/predict/[roundId]` + guards
7. `RoundSelector`, `PublicTabs`, `PredictionsMatrix`, visitor stub / login prompt
8. Upgrade `/contest/[id]` — Прогнозы tab
9. Profile «Сделать прогноз» link
10. Update `agent_docs/ui/*`, `frontend_api_integration.md`
11. Append `manuals/FRONTEND_REFERENCE.md` §2.2
12. Append handoff → `stage_2.md`

---

## 11. Handoff

Append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Coder (2.2 predictions & privacy)
- STATUS: READY_FOR_TEST
- Scope: PredictionForm, PredictionsMatrix, deadline UX, privacy helpers
- UI rules: batch-only, 0..maxScore, **empty≠0 (no coerce)**, NULL≠0, 24h warning, privacy pre/post deadline
- Verified: npm run build, npm run test:unit; manual checklist §9
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.2
- Next: agent_docs/instructions/tester_2.2.md
```

---

## 12. Explicitly OUT OF SCOPE

- Full leaderboard 13-column table (B4 counts) → **2.4**
- Results matrix / points cells → **2.4**
- Admin round/deadline editing → **2.3**
- Playwright E2E → **tester_2.2**
- OutcomeStatsFooter full visual polish if time-constrained (matrix privacy is blocking)

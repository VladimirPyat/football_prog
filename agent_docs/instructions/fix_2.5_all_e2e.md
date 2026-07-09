# Fix 2.5 — E2E QA batch (frontend)

**Source:** manual QA during supervisor + participant E2E pass (Jul 2026).
**Prerequisite:** `agent_docs/instructions/fix_1.20_all_e2e.md` at `TEST_PASS` (API exposes `team1_short`/`team2_short`; contest structure validation aligned).
**Status:** `IMPLEMENTED` — Jul 2026.

---

## 1. Goals

| # | Issue | Current behaviour | Target |
|---|-------|-------------------|--------|
| F1 | Odd teams + round-robin on contest setup | `deriveRoundRobinStructure(15)` → `matches_per_round: 7.5` shown in readonly input | Do **not** auto-fill fractional values; show hint; block save until even teams or «Произвольное количество» |
| F2 | Invite modal shows useless temp password | Modal lists login + temp password + link; temp login blocked when `enforce_password_setup=true` | **LOCKED:** show login + setup link only; API still returns `temp_password` (hidden in UI) |
| F3 | Predictions matrix team headers | `shortenTeamLabel(fullName)` → «Спар» from «Спартак» | **LOCKED:** separate API fields `team1_short` / `team2_short`; full names stay in `team1`/`team2` |
| F4 | Supervisor «Результаты участников» | `RoundLeaderboardPreview` — rank + total only | Same `ResultsMatrix` as participants see (per-match points, bonuses, totals) |

---

## 2. Root causes (verified)

### F1 — `ContestParametersForm.tsx`

```ts
const applyRoundRobinDerived = (teams: number) => {
  const derived = deriveRoundRobinStructure(teams); // totalTeams / 2 — can be fractional
  setMatchesPerRound(derived.matches_per_round);
  setTotalRounds(derived.total_rounds);
};
```

Called on every `handleTotalTeamsChange` when `isRoundRobin`. Input is `readOnly` but still **displays** `7.5`. Zod `contestParametersSchema` rejects non-integer `matches_per_round`, but UX is confusing.

### F2 — `ParticipantInviteModal.tsx`

Renders `tempPassword` and includes it in clipboard text. Backend still returns the field (fix 1.20 keeps it for dev/E2E); production flow is `/auth/setup?token=…` only.

### F3 — `formatTeamPair.ts` + consumers

`TeamColumnHeader`, `PredictionsMatrix`, `ResultsMatrix` pass `match.team1` (full name) into `formatTeamPairStacked` → heuristic truncation.

`PredictionMatchRow` uses full names in title line (correct) but `shortenTeamLabel` beside score inputs (fix to use short fields).

### F4 — `ResultsEntryPanel.tsx`

CALCULATED modal embeds `RoundLeaderboardPreview` (3-column LB). PUBLISHED shows stub `ConfirmDialog` («в следующих версиях»). API `GET …/results` already returns full matrix data; `useRoundResults` + `ResultsMatrix` exist on public contest page.

---

## 3. Required changes

### 3.1 Contest setup — odd teams in round-robin (F1)

**Files:** `ContestParametersForm.tsx`, `lib/validation/admin.ts`, `lib/validation/admin.test.ts`

1. Extend `deriveRoundRobinStructure` (or add helper `isValidRoundRobinTeamCount(n)`) — return `null` / throw when `totalTeams` is odd or < 2.
2. `applyRoundRobinDerived`: if odd teams → **do not** set `matchesPerRound` / `totalRounds`; leave empty string state or previous valid values; set field-level hint.
3. «Матчей в туре» / «Туров» inputs when round-robin + odd teams:
   - `value=""` (or placeholder `—`)
   - `readOnly` stays true
   - helper text (Russian):  
     *«Для круговой системы нужно чётное число команд, либо включите «Произвольное количество»»*
4. `contestParametersSchema`: when `is_round_robin` and odd `total_teams` → fail with same message on `total_teams` path (block submit).
5. Optional: add even-team note to existing bullet list (§240–245) — *«число команд должно быть чётным»*.

**Do not** change behaviour when «Произвольное количество» is checked (`is_round_robin=false`).

### 3.2 Invite modal — hide temp password (F2)

**Files:** `ParticipantInviteModal.tsx`, `app/admin/settings/participants/page.tsx`

1. Remove «Временный пароль» row from modal UI.
2. Update body copy: participant confirms via link; after setup they log in with **chosen** password.
3. `copyCredentials` → copy `Логин: …\nСсылка: …` only.
4. Keep `temp_password` in API response type (`ParticipantInviteOut`) — E2E fixtures may still read it; do not log it to console.
5. If `ENFORCE_PASSWORD_SETUP=false` in dev, still hide password in modal (single UX); dev scripts use API directly.

### 3.3 Team short names in matrices (F3)

**Prerequisite:** API returns `team1_short`, `team2_short` on `MatchOut`.

**Files:** `types/api.ts`, `TeamColumnHeader.tsx`, `PredictionsMatrix.tsx`, `ResultsMatrix.tsx`, `mapRoundResultsRow.ts`, `PredictionMatchRow.tsx`, `lib/teams/formatTeamPair.ts`

1. Extend `MatchOut`:

```ts
team1_short?: string;
team2_short?: string;
```

2. Add helper `displayTeamShort(match, side: 'team1' | 'team2'): string`  
   → `match.team1_short ?? shortenTeamLabel(match.team1)` (fallback for stale caches).

3. `TeamColumnHeader` — accept `team1Short`/`team2Short` props **or** full `MatchOut`; render shorts directly (no `formatTeamPairStacked` truncation). Keep `title` with full `team1 — team2`.

4. Update all matrix call sites to pass short fields.

5. `PredictionMatchRow` — compact labels beside inputs use `displayTeamShort`; main line keeps `match.team1 — match.team2`.

6. Unit tests in `formatTeamPair.test.ts` (create if missing): fallback behaviour when shorts absent.

### 3.4 Supervisor results preview — full matrix (F4)

**Files:** `ResultsEntryPanel.tsx`, new `RoundResultsPreview.tsx` (recommended), optionally retire slim `RoundLeaderboardPreview` from this flow

1. Replace CALCULATED modal content with component that:
   - calls `useRoundResults(contest.id, roundId, true)` (same endpoint as public page)
   - renders `ResultsMatrix` with `roundLabel={`Тур ${n}`}`
   - shows `bonuses_pending` banner when API indicates postponed-match scoring (reuse `roundScoringPending` copy)
   - badge: *«Предпросмотр — тур ещё не опубликован»* (keep from current preview)

2. **PUBLISHED** rounds: replace `ConfirmDialog` stub with the same `RoundResultsPreview` (results are public; supervisor gets identical view).

3. Modal layout: widen to `max-w-6xl` or full-viewport scroll; matrix is wide.

4. `RoundLeaderboardPreview` may remain for other uses or be deleted if unused — grep before removal.

### 3.5 E2E / unit test updates

| Test file | Change |
|-----------|--------|
| `lib/validation/admin.test.ts` | odd teams + round-robin → schema fail; even teams → derive unchanged |
| `e2e/supervisor_results_preview.spec.ts` | After opening modal, expect `data-testid="results-matrix"` and per-match point cells (not only «Таблица тура» / rank column) |
| `e2e/visitor_predictions_public.spec.ts` or new spec | Matrix header shows configured short name (fixture team with distinct `short_name` ≠ name prefix) |
| Optional admin setup E2E | Enter 15 teams, round-robin → hint visible, save blocked |

Vitest: `cd frontend && npm run test -- --run` relevant files.  
Lint: `npm run lint`, `npm run type-check`, `npm run format:check`.

---

## 4. UI copy (Russian)

| Key | Text |
|-----|------|
| `round_robin_odd_teams` | Для круговой системы нужно чётное число команд, либо включите «Произвольное количество» |
| `invite_modal_body` | Передайте участнику логин и ссылку для подтверждения. По ссылке участник задаст пароль и примет участие в конкурсе. |
| `preview_badge` | Предпросмотр — тур ещё не опубликован |

---

## 5. Out of scope

- Backend validation (fix 1.20)
- Enabling temp-password login in production
- Predictions privacy / deadline rules
- Mobile compact layout changes to `ResultsMatrix` (reuse as-is)

---

## 6. Handoff

- Append progress entry to `agent_docs/progress/stage_2.md`.
- Manual check: `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — parameters §, participants invite §, results preview §.

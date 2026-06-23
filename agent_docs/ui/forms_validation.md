# Forms & Validation (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§5.3, §7.3), `docs/01_tech_regulations.md` (§6), `agent_docs/contracts/frontend_api_integration.md`.
> **Validation lib:** Zod. **Principle:** client validation mirrors backend but backend is the source of truth — always handle API errors too.

---

## 1. Cross-cutting rules

| Rule | Implementation |
|------|----------------|
| Score range | `0 ≤ score ≤ maxScore`, integer; `maxScore` from `contest.rules_json.constraints.score_validation_range[1]` — **never hardcode 20** |
| `NULL ≠ 0` | empty input = `undefined` in state, never `0`; submit only when user typed; `0` is a valid entered value |
| Batch-only predictions | submit enabled only when **all** `matches_per_round` filled (100%); partial → disabled |
| Deadline | inputs readonly when `deadline_passed`; never submit after deadline (also enforced by 403) |
| 24h rule | round deadline must be `≤ first_match_date − 24h` |
| Immutable | disable when `is_locked` (setup) or round status ≥ CLOSED (predictions) |
| Privacy | render from API `entries`; never infer hidden scores client-side |
| Errors | map `422` Pydantic field errors + domain `code` to inputs/toasts (`detail` shown verbatim, Russian) |

---

## 2. Form schemas

### LoginForm — **Implemented (2.1)** → `frontend/src/lib/validation/login.ts`
```ts
z.object({ login: z.string().min(1), password: z.string().min(1) })
```
401 → show `detail` («Неверный логин или пароль»).

### ChangePasswordForm — **Implemented (2.1)** → `frontend/src/lib/validation/changePassword.ts`
```ts
z.object({
  old_password: z.string().min(1),
  new_password: z.string().min(8),          // confirm min length with backend
  confirm: z.string()
}).refine(d => d.new_password === d.confirm, { path:['confirm'], message:'Пароли не совпадают' })
```

### PredictionForm  (batch)
```ts
const score = (max:number) => z.number().int().min(0).max(max);
const prediction = (max:number) => z.object({
  match_id: z.number().int(),
  score1: score(max),
  score2: score(max),
});
const predictionBatch = (max:number, count:number) =>
  z.object({ predictions: z.array(prediction(max)).length(count) });
```
- Each `ScoreInput`: integer only; reject non-numeric (`"abc"`) and out-of-range (`"25"`); empty = `undefined`.
- Submit button: enabled only when filled count === `matches_per_round`.
- After save: switch to readonly with `Редактировать`; re-enable until deadline.
- Errors: `SCORE_OUT_OF_RANGE` (422) → highlight cell; `DEADLINE_PASSED` (403) → set readonly + toast; `400` incomplete → keep disabled.

### ContactsForm  (B3) — **Implemented (2.1)** → `frontend/src/lib/validation/contacts.ts`
```ts
z.object({
  email: z.string().email().optional().or(z.literal('')),
  vk_id: z.string().optional(),
  tg_id: z.string().optional(),
  notify_enabled: z.boolean(),
})
```

### CreateContestForm  (SETUP)
```ts
z.object({
  name: z.string().min(1),
  slug: z.string().optional(),
  total_teams: z.number().int().positive(),
  matches_per_round: z.number().int().positive(),
  total_rounds: z.number().int().positive(),
  is_round_robin: z.boolean(),
}).superRefine((d, ctx) => {
  if (d.is_round_robin) {
    if (d.matches_per_round !== d.total_teams/2)
      ctx.addIssue({ code:'custom', path:['matches_per_round'], message:'Должно быть = команды / 2' });
    if (d.total_rounds !== (d.total_teams-1)*2)
      ctx.addIssue({ code:'custom', path:['total_rounds'], message:'Должно быть = (команды − 1) × 2' });
  }
})
```
(Round-robin math per `docs/01` §3.2.)

### ContestParametersForm
- Same fields as create; **all readonly when `is_locked`**. Scoring/bonus values shown from `rules_json` (display-only here). PATCH `/contests/{id}`; `CONTEST_LOCKED` (403) → keep readonly + banner.

### TeamForm
```ts
z.object({
  name: z.string().min(1),
  short_name: z.string().min(1).max(4),     // «Сокращение (до 4 символов)»
  logo_url: z.string().url().optional(),    // or file upload (B5)
})
```
Logo: B5 multipart upload; fallback to `logo_url` text. File: PNG/JPG/GIF ≤2MB (client-check size/type).

### ParticipantInviteForm
```ts
z.object({
  email: z.string().email(),
  first_name: z.string().min(1),
  last_name: z.string().min(1),
  login: z.string().optional(),             // auto from email if omitted
})
```
On success show returned `temp_password`. Disabled when locked.

### RoundBuilderForm
```ts
z.object({
  number: z.number().int().positive(),
  deadline: z.string().datetime(),
  matches: z.array(z.object({
    team1_id: z.number().int(),
    team2_id: z.number().int(),
    date_time: z.string().datetime(),
  })).min(1).max(matchesPerRound),
}).superRefine((d, ctx) => {
  // unique teams within round
  const ids = d.matches.flatMap(m => [m.team1_id, m.team2_id]);
  if (new Set(ids).size !== ids.length)
    ctx.addIssue({ code:'custom', path:['matches'], message:'Команда не может играть дважды в туре' });
  // 24h rule
  const firstMatch = Math.min(...d.matches.map(m => Date.parse(m.date_time)));
  if (Date.parse(d.deadline) > firstMatch - 24*3600*1000)
    ctx.addIssue({ code:'custom', path:['deadline'], message:'Дедлайн должен быть ≥ 24ч до первого матча' });
})
```
- `team1_id !== team2_id` per match.
- After activation: only match status + date editable (per `supervisor_tours.jpg`); deadline locked <24h.

### MatchResultForm / ResultsEntryGrid
```ts
z.object({
  score1: z.number().int().min(0).max(maxScore),
  score2: z.number().int().min(0).max(maxScore),
  status: z.literal('FINISHED'),
})
```
- Available only after round CLOSED (else 403). `Применить` → calculate; inputs lock after apply.
- `Отменить` (VOID) → `PATCH …/matches/{id}/status {status:'VOID'}` with `ConfirmDialog`.

### FreeTourModal
```ts
z.object({
  deadline: z.string().datetime(),
  matches: z.array(z.object({
    match_id: z.number().int(),             // POSTPONED only
    new_date_time: z.string().datetime(),
  })).min(1),
})
```
Only `POSTPONED` matches selectable; teams readonly.

### TiebreakForm  (ADMIN)
```ts
z.object({ points: z.number().int().min(0) })
```
`PUT …/participants/{user_id}/exceptional-tiebreak`; allowed even when locked.

### CreateSupervisorForm  (ADMIN)
```ts
z.object({
  login: z.string().min(1),
  password: z.string().min(8),
  first_name: z.string().min(1),
  last_name: z.string().min(1),
  is_temp_password: z.boolean().default(false),
})
```
Duplicate login → `400 VALIDATION_ERROR`.

---

## 3. Error mapping summary

| Code / HTTP | Field/action |
|-------------|--------------|
| 422 Pydantic | map `loc` → input |
| `SCORE_OUT_OF_RANGE` 422 | score cell |
| `VALIDATION_ERROR` 400 | form-level (incomplete batch, duplicate) |
| `DEADLINE_PASSED` 403 | predictions readonly |
| `CONTEST_LOCKED` 403 | setup readonly |
| `CONTEST_NOT_RUNNING` 403 | disable mutations + banner |
| `ILLEGAL_TRANSITION` 409 | toast (round/match step) |
| `GRACE_PERIOD_ACTIVE` 400 | delete dialog message |

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-21 | Initial Zod schemas + cross-cutting rules for all Stage-2 forms; mirrors `docs/01` §6 and API error contract. |
| 2026-06-23 | Stage 2.1: Zod export paths for login, changePassword, contacts under `frontend/src/lib/validation/`. |

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
| 24h rule | **Placement:** `now < deadline < earliest_match` on create/set. **Change lockout:** supervisor may move deadline only while `now <= deadline − deadline_rule_hours` (2.3.1 F2 — not «first match must be ≥24h away») |
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

### CreateContestForm  (SETUP) — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`createContestSchema`)
```ts
z.object({
  name: z.string().min(1),
  slug: z.string().optional(),
})
```
Structural defaults (`total_teams`, `matches_per_round`, `total_rounds`, `is_round_robin`) come from backend `contest_defaults_path` on create — set on Parameters page (2.3.3 S1.1). Slug help: «Короткое имя для ссылки (латиница, цифры, дефисы)…».

### ContestParametersForm — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`contestParametersSchema`)
```ts
// fields: total_teams, matches_per_round, total_rounds, is_round_robin (+ rules via rulesEditor)
```
- **Round-robin:** when `is_round_robin=true`, `deriveRoundRobinStructure(totalTeams)` auto-fills `matches = teams/2`, `rounds = (teams−1)×2`; fields read-only (2.3.3 S1.2).
- **«Произвольное количество»** checkbox = `!is_round_robin` — free manual values when checked.
- **`buildRulesJsonPatch(formState)`** merges scoring/bonus into PATCH payload (2.3.4 F2).
- **All readonly when `is_locked`**. PATCH `/contests/{id}`; `CONTEST_LOCKED` (403) → keep readonly + banner.
- Start flow: save (incl. rules) via `onBeforeStart`, then `POST /start` (2.3.3–2.3.4).

### TeamForm — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`teamFormSchema`)
```ts
z.object({
  name: z.string().min(1),
  short_name: z.string().min(1).max(4),     // «Сокращение (до 4 символов)»
  logo_url: z.string().url().optional(),    // or file upload (B5)
})
```
Logo: B5 multipart upload; fallback to `logo_url` text. File: PNG/JPG/GIF ≤2MB (client-check size/type).

### ParticipantInviteForm — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`participantInviteSchema`)
```ts
z.object({
  email: z.string().email(),
  first_name: z.string().min(1),
  last_name: z.string().min(1),
  login: z.string().optional(),             // auto from email if omitted
})
```
On success show returned `temp_password`. Disabled when locked.

### RoundBuilderForm — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`roundBuilderSchema`)
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
  // placement: deadline before first match and in the future
  const firstMatch = Math.min(...d.matches.map(m => Date.parse(m.date_time)));
  if (Date.parse(d.deadline) >= firstMatch)
    ctx.addIssue({ code:'custom', path:['deadline'], message:'Дедлайн должен быть раньше первого матча' });
})
```
- `team1_id !== team2_id` per match.
- Match kickoff may be &lt;24h away; 24h rule applies only to **changing** deadline on ACTIVE tour (`deadlineRule.isDeadlineChangeAllowed` — 2.3.1 F2).
- **ACTIVE:** no team swap in UI; kickoff reschedule until match start; cancel/postpone allowed (2.3.1 F3).

### MatchResultForm / ResultsEntryGrid — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`matchResultSchema`)
```ts
z.object({
  score1: z.number().int().min(0).max(maxScore),
  score2: z.number().int().min(0).max(maxScore),
  status: z.literal('FINISHED'),
})
```
- Available only after round CLOSED (else 403). `Применить` → calculate; inputs lock after apply.
- `Отменить` (VOID) → `PATCH …/matches/{id}/status {status:'VOID'}` with `ConfirmDialog`.

### FreeTourModal — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`freeTourSchema`)
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

### TiebreakForm  (ADMIN) — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`tiebreakSchema`)
```ts
z.object({ points: z.number().int().min(0) })
```
`PUT …/participants/{user_id}/exceptional-tiebreak`; allowed even when locked.

### CreateSupervisorForm  (ADMIN) — **Implemented (2.3)** → `frontend/src/lib/validation/admin.ts` (`createOrganizerSchema`)
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
| `DEADLINE_CHANGE_CLOSED` 403 | deadline picker on ACTIVE (within 24h of current deadline) |
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
| 2026-06-24 | Stage 2.3: admin Zod schemas in `frontend/src/lib/validation/admin.ts`; client 24h rule in `lib/admin/deadlineRule.ts`. |
| 2026-06-28 | Stage 2.3.1: 24h placement vs change lockout; RoundBuilder deadline validation updated. |
| 2026-06-28 | Stage 2.3.3: slim `createContestSchema`; `deriveRoundRobinStructure` on Parameters. |
| 2026-06-28 | Stage 2.3.4: `buildRulesJsonPatch`; start readiness validation mirrors backend 422. |

# Coder Instructions — Stage 2.3.4 QA Follow-up (Frontend, chat-driven)

> **Status gate:** `IMPLEMENTED` (manual QA chat 2026-06-28; not part of `coder_2.3.3_fix_setup.md`)
> **Prerequisite:** `agent_docs/instructions/coder_2.3.3_fix_setup.md` shipped (start button, slim create modal, delete UI)
> **Backend dependency:** `agent_docs/instructions/backend/coder_1.15_qa_followup.md` (start guards, supplementary rounds API, `bonuses_pending`)
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.4_qa_followup.md`
> **Reference:** `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — S1.2, S1.12, S2.23
> **Language policy:** UI copy Russian; code comments English

---

## 1. Objective

Capture **frontend** changes from supervisor manual QA chat (2026-06-28) — **outside** `coder_2.3.3_fix_setup.md`.

| ID | QA ref | Area | Problem (reported) | Target |
|----|--------|------|-------------------|--------|
| **F1** | S1.2 | Contest context | Stale contest after create/switch; parameters appear as stubs | `ContestProvider` refetch on id change; remove debug bar |
| **F2** | S1.2 | Rules / bonuses | Compact bonus stub; rules not saved before start | `RulesEditorPanel` + `buildRulesJsonPatch`; auto-save via `onBeforeStart` |
| **F3** | S1.12 | Start without readiness | Start allowed when teams/participants incomplete | Readiness panel + disabled «Запустить конкурс» (variant 2) |
| **F4** | S2.23 | Free / supplementary tours | «Тур N» for postponed matches confusing | **ДопТур1/2/3** labels + source round hint |
| **F5** | Scoring UX | Bonuses shown while postponed matches pending | Note from `bonuses_pending` on LB preview + results |
| **F6** | Setup refresh | Teams/participants changes don't update start panel | `contest-setup-changed` custom event |

**Non-goals:**

- Items already in `coder_2.3.3_fix_setup.md` (modal slimming, start CTA wiring, delete button baseline)
- `/admin` → `/supervisor` rename
- Implementing deferred bonus engine logic (backend contract only)

---

## 2. F1 — Contest context & debug cleanup

### 2.1 `ContestProvider`

When `contestId` changes (create, picker switch):

- Invalidate/refetch contest query so Parameters page shows **current** DRAFT fields, not cached RUNNING fixture
- Ensure `setupReadonly` derives from fresh `status` + `is_locked`

### 2.2 Remove debug artefacts

Delete (do not leave behind):

- `ContestSetupDebugBar` component and usages
- `contestSetupLog` helper

---

## 3. F2 — Rules editor & persistence (S1.2)

### 3.1 Replace stub with editor

Remove readonly `RulesDisplayPanel` usage on Parameters. Wire `RulesEditorPanel`:

- Structured fields for bonus rules (not compact one-line stub)
- On DRAFT + unlocked: editable; after start: readonly display

### 3.2 PATCH `rules_json`

`frontend/src/lib/admin/rulesEditor.ts`:

- `buildRulesJsonPatch(formState)` → partial `rules_json` for `PATCH /contests/{id}`
- Unit tests in `rulesEditor.test.ts`

`ContestParametersForm.tsx` — include rules in save payload.

### 3.3 Auto-save before start

`ContestLifecycleActions.tsx`:

- `onBeforeStart?: () => Promise<void>` prop from Parameters page
- Flow: save parameters (incl. rules) → then `POST /start`
- On validation error: toast, abort start

---

## 4. F3 — Start readiness UI (variant 2)

### 4.1 Data

`frontend/src/lib/admin/contestStartReadiness.ts`:

```ts
type StartReadiness = {
  teamsReady: boolean;
  teamsCreated: number;
  teamsRequired: number;
  participantsReady: boolean;
  acceptedCount: number;
  minAccepted: number; // 2
  canStart: boolean;
  blockers: string[];   // Russian messages
};
```

`useContestStartReadiness.ts` — loads teams + participants for current contest.

### 4.2 UI

`ContestStartReadinessPanel.tsx` — checklist above start button:

- «Команды: X из Y»
- «Принятые участники: N (минимум 2)»
- List `blockers` when `!canStart`

`ContestLifecycleActions.tsx`:

- `startBlocked = !readiness.canStart`
- Disable «Запустить конкурс» + `title` with first blocker
- Mirror backend 422 messages where possible

### 4.3 Tests

`contestStartReadiness.test.ts` — matrix for teams/participants combinations.

E2E: extend `admin_setup.spec.ts` — `fulfillStartPrerequisites` in `adminApi.ts` before start assertions.

---

## 5. F4 — ДопТур labels (S2.23)

### 5.1 Helpers

`frontend/src/lib/admin/roundLabel.ts`:

| Function | Output example |
|----------|----------------|
| `formatRoundTitle(round)` | `ДопТур1` or `Тур 3` |
| `formatRoundOptionLabel(round)` | `ДопТур1 (из тура 2) — Черновик` |

Uses API fields: `kind`, `supplementary_index`, `source_round_numbers`.

`RoundOut` type extended in `frontend/src/types/api.ts`.

### 5.2 Consumers

| Component | Usage |
|-----------|-------|
| `RoundManagementPanel.tsx` | Round selector, activate modal |
| `ResultsEntryPanel.tsx` | Round dropdown |
| `FreeTourModal.tsx` | Context copy for supplementary creation |
| `collectPostponedMatches.ts` | Group labels |

### 5.3 Tests

`roundLabel.test.ts` — REGULAR vs SUPPLEMENTARY cases.

---

## 6. F5 — Bonuses pending UI

### 6.1 Client helper

`frontend/src/lib/admin/roundScoringPending.ts` — parse `bonuses_pending` + `bonuses_pending_message` from leaderboard response.

### 6.2 Display

| Component | When |
|-----------|------|
| `RoundLeaderboardPreview.tsx` | Info callout above standings |
| `ResultsEntryPanel.tsx` | Note near round header when entering results |

Copy: use `bonuses_pending_message` from API when present; fallback Russian template.

---

## 7. F6 — Setup change events

Emit `contest-setup-changed` on CustomEvent bus when:

- Team created/deleted (`useTeams.ts`)
- Participant invited/removed/status changed (`useParticipants.ts`)

`useContestStartReadiness` subscribes → refetch counts without full page reload.

---

## 8. S1.2 readonly after start

After successful start (`RUNNING` + `is_locked`):

- Structural fields disabled (existing S1.4 from 2.3.3)
- **Rules section** switches to readonly structured view (not empty stub)
- No «Сохранить параметры» button

---

## 9. File checklist

| File | Change |
|------|--------|
| `frontend/src/providers/ContestProvider.tsx` | Stale context fix |
| `frontend/src/components/admin/RulesEditorPanel.tsx` | Wired on Parameters |
| `frontend/src/components/admin/ContestParametersForm.tsx` | Rules save, `onBeforeStart` |
| `frontend/src/lib/admin/rulesEditor.ts` | NEW |
| `frontend/src/lib/admin/rulesEditor.test.ts` | NEW |
| `frontend/src/components/admin/ContestLifecycleActions.tsx` | Readiness gate, `onBeforeStart` |
| `frontend/src/components/admin/ContestStartReadinessPanel.tsx` | NEW |
| `frontend/src/hooks/useContestStartReadiness.ts` | NEW |
| `frontend/src/lib/admin/contestStartReadiness.ts` | NEW |
| `frontend/src/lib/admin/contestStartReadiness.test.ts` | NEW |
| `frontend/src/lib/admin/roundLabel.ts` | NEW |
| `frontend/src/lib/admin/roundLabel.test.ts` | NEW |
| `frontend/src/lib/admin/roundScoringPending.ts` | NEW |
| `frontend/src/components/admin/RoundLeaderboardPreview.tsx` | Pending note |
| `frontend/src/components/admin/ResultsEntryPanel.tsx` | ДопТур labels + pending note |
| `frontend/src/components/admin/RoundManagementPanel.tsx` | ДопТур labels |
| `frontend/src/components/admin/FreeTourModal.tsx` | Supplementary copy |
| `frontend/src/lib/admin/collectPostponedMatches.ts` | Label helpers |
| `frontend/src/hooks/useTeams.ts`, `useParticipants.ts` | `contest-setup-changed` |
| `frontend/src/types/api.ts` | `RoundOut` enrichment |
| `frontend/e2e/fixtures/adminApi.ts` | `fulfillStartPrerequisites`, `inviteParticipant` |
| `frontend/e2e/admin_setup.spec.ts` | Start prerequisites |
| `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | S1.2, S2.23 updates |

**Removed:** `ContestSetupDebugBar`, `contestSetupLog`

**Optional cleanup:** `RulesDisplayPanel.tsx` if unused — delete in follow-up.

---

## 10. Acceptance criteria

- [ ] New DRAFT contest shows editable parameters (not locked fixture state)
- [ ] Rules save via PATCH and persist; auto-save before start
- [ ] Start button disabled until teams full + ≥2 ACCEPTED; panel shows why
- [ ] Supplementary rounds labeled **ДопТурN** with source round
- [ ] `bonuses_pending` note visible on results/LB when API sets flag
- [ ] No debug bar with `contestId=…`
- [ ] `npm run lint`, `npm run type-check`, `npm run test:unit` pass
- [ ] E2E `admin_setup.spec.ts` green with prerequisite helpers

---

## 11. Execution order

```text
1. coder_2.3.3_fix_setup.md           (baseline setup UX)
2. backend/coder_1.15_qa_followup.md  (API fields + start guards)
3. coder_2.3.4_qa_followup.md (this)  — frontend QA follow-up
```

Frontend F4/F5 require backend supplementary + `bonuses_pending` fields; F3 requires start validation 422.

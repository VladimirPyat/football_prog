# Coder Instructions — Stage 2.2.1 Patch: Visitor Predictions After Deadline (Frontend)

> **Status gate:** `INSTRUCTIONS_READY`
> **Type:** **Patch** on top of shipped **2.2** — do **not** edit `agent_docs/instructions/coder_2.2.md` or `tester_2.2.md` (historical baseline). This doc overrides **runtime behaviour** only where noted below (visitor post-deadline UX).
> **Prerequisite:** `agent_docs/instructions/backend/coder_1.16_fix_public_predictions.md` merged / API deployed locally
> **Follow-up tester:** `agent_docs/instructions/tester_2.2.1.md`
> **Specs:** `docs/03_user_scenarios.md` §4, `agent_docs/contracts/frontend_api_integration.md` §5.4, `agent_docs/ui/pages.md`
> **Language policy:** UI copy Russian; code comments English

---

## 1. Objective

After backend **1.16 public predictions** fix, Visitor on **Прогнозы** tab must see the **full matrix post-deadline without login**. Pre-deadline behaviour unchanged (stub, no API).

**Patch scope:** replaces 2.2 §5.4 visitor post-deadline **login prompt** with public matrix — without rewriting the 2.2 instruction file.

| ID | Problem | Target |
|----|---------|--------|
| **V1** | `visitorPostDeadline` → `PredictionsLoginPrompt` | Fetch public GET; render `PredictionsMatrix` |
| **V2** | `visitorPreDeadline` uses `status === ACTIVE` only | Use **deadline not passed** (ACTIVE + `now < deadline`) |
| **V3** | `fetchPredictions` false for all guests | Guest fetches when **not** pre-deadline |
| **V4** | Docs still say visitor 401 post-deadline | Sync UI specs + integration contract |

**Non-goals:**

- Predict form `/predict/[roundId]` for Visitor (still requires login — out of scope)
- Leaderboard / results tabs (unchanged)
- Editing `coder_2.2.md` / `tester_2.2.md` (patch-only stage)

---

## 2. Root cause (verified)

`frontend/src/app/contest/[contestId]/page.tsx`:

```ts
const visitorPreDeadline =
  !isAuthenticated && tab === "predictions" && selectedRound?.status === "ACTIVE";

const visitorPostDeadline =
  !isAuthenticated && tab === "predictions" && selectedRound != null && selectedRound.status !== "ACTIVE";
```

| Bug | Effect |
|-----|--------|
| Pre-deadline gate ignores `deadline` | ACTIVE round **after** deadline still shows stub instead of matrix |
| Post-deadline = `status !== ACTIVE` | CLOSED/PUBLISHED rounds show login prompt instead of public matrix |
| `fetchPredictions = isAuthenticated && …` | Guest never calls GET even when API allows it |

`shouldShowScore` already supports Visitor post-deadline (`viewer: null`, `deadlinePassed: true` → show scores). No change required unless tests need one explicit case.

---

## 3. V2 — Pre-deadline gate (LOCKED)

### 3.1 Reuse deadline helper

Use existing `isDeadlinePassedNow` from `frontend/src/lib/admin/roundEffectiveStatus.ts` (mirrors API `deadline_passed`).

**Optional refactor (preferred):** move to shared module to avoid admin import on public page:

`frontend/src/lib/contest/deadline.ts`:

```ts
export { isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
```

Or import directly from `roundEffectiveStatus.ts` if refactor skipped.

### 3.2 Visitor pre-deadline condition

```ts
const visitorPreDeadline =
  !isAuthenticated &&
  tab === "predictions" &&
  selectedRound != null &&
  selectedRound.status === "ACTIVE" &&
  !isDeadlinePassedNow(selectedRound.deadline);
```

Show `PredictionsVisitorStub` — **no GET** (API would 403).

---

## 4. V1 / V3 — Fetch + render for guest post-deadline (LOCKED)

### 4.1 Remove `visitorPostDeadline` branch

Delete:

- `visitorPostDeadline` variable
- `PredictionsLoginPrompt` render on Прогнозы tab
- `!visitorPostDeadline` guards on matrix render / `usePredictionsView` enable

### 4.2 Enable fetch

```ts
const shouldFetchPredictions =
  tab === "predictions" &&
  effectiveRoundId != null &&
  !visitorPreDeadline &&
  (isAuthenticated || selectedRound != null);
```

For guests: fetch on **any** selected round where not `visitorPreDeadline` (includes PUBLISHED round 9, CLOSED/CALCULATED past tours, ACTIVE after deadline).

```ts
const { data: predictionsData, loading: predictionsLoading } = usePredictionsView(
  contestId,
  effectiveRoundId,
  shouldFetchPredictions,
);
```

### 4.3 `usePredictionsView` — public GET

`apiGet` already omits Bearer when no token. No change **unless** you added `auth: false` explicitly — not required.

Handle **403** `PREDICTIONS_NOT_PUBLIC` gracefully (edge: guest on ACTIVE pre-deadline if client clock skew): show `PredictionsVisitorStub` or `ErrorState` with same copy — prefer stub for consistency.

### 4.4 Matrix render

Keep existing block; pass `viewer={user}` (`null` for guest). `PredictionsMatrix` + `shouldShowScore` show all scores when `deadlinePassed`.

Show `OutcomeStatsFooter` when `predictionsData.deadline_passed` — including for Visitor.

---

## 5. Default round selection (verify)

`pickDefaultRound` for `predictions` tab prefers **ACTIVE** round — correct for participants.

Visitor smoke (tester) uses **round 9** explicitly in E2E for post-deadline public view. No mandatory change; optional: when guest opens tab, if only historical rounds have passed deadline, default ACTIVE stub is still correct UX.

---

## 6. Components

| Component | Action |
|-----------|--------|
| `PredictionsVisitorStub` | Keep — pre-deadline only |
| `PredictionsLoginPrompt` | **Remove** — see §6.1 |
| `PredictionsMatrix` | Add `data-testid="prediction-score"` on visible score cells (not on `PrivacyMask`) — for `[E2E-VISITOR-PRED-PUBLIC]` |
| `PrivacyMask` | Unchanged |

### 6.1 Delete `PredictionsLoginPrompt` (LOCKED)

Component is dead after this patch — no other call sites.

1. Remove import and all usage from `frontend/src/app/contest/[contestId]/page.tsx`.
2. **Move** (do not `rm`) source file to trash:

```bash
mkdir -p .trash/frontend/src/components/predictions
mv frontend/src/components/predictions/PredictionsLoginPrompt.tsx \
   .trash/frontend/src/components/predictions/PredictionsLoginPrompt.tsx
```

3. Grep repo — zero remaining imports of `PredictionsLoginPrompt`.
4. Update living docs that list the component:
   - `agent_docs/ui/components.md` — remove row if present
   - `manuals/FRONTEND_REFERENCE.md` — remove `PredictionsLoginPrompt` row (§2.2 predictions table)

---

## 7. Unit tests (Vitest)

| ID | File | Case |
|----|------|------|
| `[UNIT-PRIVACY-VISITOR-POST]` | `shouldShowScore.test.ts` | `viewer: null`, `deadlinePassed: true`, entry with predictions → `true` |
| `[UNIT-DEADLINE-GATE]` | `deadline.test.ts` (optional) | `isDeadlinePassedNow` past/future ISO |

Run: `cd frontend && npm run test:unit`

---

## 8. Docs sync

| File | Change |
|------|--------|
| `agent_docs/ui/pages.md` | `/contest/[id]` Прогнозы: visitor pre-deadline stub; post-deadline public matrix; no login prompt |
| `agent_docs/ui/components.md` | Remove `PredictionsLoginPrompt` |
| `manuals/FRONTEND_REFERENCE.md` | Remove `PredictionsLoginPrompt` row |
| `agent_docs/contracts/frontend_api_integration.md` | §5.4 visitor row (if backend doc not yet merged — coordinate) |

**Do not edit** `coder_2.2.md` — patch documented here and in contracts only.

---

## 9. File checklist

| File | Change |
|------|--------|
| `frontend/src/app/contest/[contestId]/page.tsx` | §3–4 logic; drop `PredictionsLoginPrompt` |
| `.trash/frontend/src/components/predictions/PredictionsLoginPrompt.tsx` | moved from `frontend/src/components/predictions/` |
| `frontend/src/lib/contest/deadline.ts` | NEW (optional re-export) |
| `frontend/src/lib/privacy/shouldShowScore.test.ts` | visitor post-deadline case |
| `agent_docs/ui/pages.md`, `ui/components.md`, `manuals/FRONTEND_REFERENCE.md` | visitor behaviour; remove login prompt component |

---

## 10. Acceptance criteria

- [ ] Guest on `/contest/1`, round **10** ACTIVE future deadline → stub, no matrix, no login prompt
- [ ] Guest on round **9** (post-deadline) → matrix with visible scores, no login required
- [ ] `PredictionsLoginPrompt.tsx` moved to `.trash/`; no imports remain
- [ ] Logged-in USER pre-deadline privacy unchanged
- [ ] `npm run lint`, `type-check`, `format:check`, `build`, `test:unit` pass

---

## 11. Execution order

```text
1. backend/coder_1.16_fix_public_predictions.md
2. coder_2.2.1.md (this)
3. tester_2.2.1.md
```

Mark `READY_FOR_TEST` in `agent_docs/progress/stage_2.md` when done.

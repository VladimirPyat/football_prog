# Coder Instructions — Stage 2.3.5 Fix: Deadline UI Sync (Frontend)

> **Status gate:** `IMPLEMENTED`
> **Prerequisite:** Stage 2.3.1–2.3.2 round status panels shipped; `coder_2.3.4_qa_followup.md` optional
> **Backend dependency:** `agent_docs/instructions/backend/coder_1.16_fix_deadline.md` (per-round auto-close)
> **Follow-up tester:** (optional) when created
> **Reference:** `manuals/STATUS_REFERENCE.md` §2 (`CLOSED` → UI «Дедлайн»), `manuals/API_GUIDE.md` auto-close section
> **Language policy:** UI copy Russian; code comments English

---

## 1. Objective

When round **deadline passes** while the admin UI is open, supervisor must see **«Дедлайн»** phase immediately — not stale **«Активен»** with a manual «Закрыть тур» button.

| ID | Problem | Target |
|----|---------|--------|
| **U1** | `rounds[].status` cached as `ACTIVE` after deadline | Refetch rounds when `deadline_passed` flips true |
| **U2** | `RoundPhasePanel` hidden until manual close | Treat expired ACTIVE as CLOSED for display |
| **U3** | Results tab misses tour in dropdown | Include auto-closed round in eligible list |
| **U4** | Sidebar badge «Активен» after deadline | Effective status badge «Дедлайн» |

**Non-goals:**

- Client-side prediction submit (participant UI not in scope)
- Polling / WebSocket scheduler — refetch on API signal is enough
- Changing backend deadline rules

---

## 2. Root cause (verified)

- `useAdminRounds` loads `GET /contests/{id}/rounds` once; status cached.
- `useRoundMatches` loads predictions view → `deadline_passed` updates independently.
- `RoundManagementPanel.isPhaseRound` checks only `round.status`, not `deadlinePassed`.
- `RoundStatusSidebar` shows manual «Закрыть тур» when `ACTIVE && deadlinePassed`.

After backend 1.16, any predictions GET also closes the round — refetch rounds will return `CLOSED`. UI must **react** without full page reload.

---

## 3. U2 — Effective round status helper (LOCKED)

### 3.1 New module

`frontend/src/lib/admin/roundEffectiveStatus.ts`:

```ts
import type { RoundOut, RoundStatus } from "@/types/api";

/** Display/status logic: ACTIVE + deadline passed → behave as CLOSED (Дедлайн). */
export function effectiveRoundStatus(
  round: Pick<RoundOut, "status">,
  deadlinePassed: boolean,
): RoundStatus {
  if (round.status === "ACTIVE" && deadlinePassed) return "CLOSED";
  return round.status;
}

export function isPhaseRoundStatus(status: RoundStatus): boolean {
  return status === "CLOSED" || status === "CALCULATED" || status === "PUBLISHED";
}
```

Unit tests: `roundEffectiveStatus.test.ts` — ACTIVE+true→CLOSED; ACTIVE+false→ACTIVE; CLOSED unchanged.

### 3.2 Usage

Replace raw `round.status` with `effectiveRoundStatus(round, deadlinePassed)` for:

- Phase panel routing (`isPhaseRound`)
- Status badge / hint (`RoundStatusSidebar`, `deriveAdminUiMode` where round phase matters)
- Results round selector eligibility

**Keep** API mutations using real `round.id` and server status after refetch.

---

## 4. U1 — Refetch rounds on deadline transition

### 4.1 `useRoundMatches`

Add optional callback:

```ts
export function useRoundMatches(
  contestId: number,
  roundId: number | null,
  options?: { onDeadlinePassed?: () => void },
)
```

When `view.deadline_passed` transitions `false → true`, call `onDeadlinePassed()` once per round session (use ref to avoid loops).

### 4.2 `admin/rounds/page.tsx`

```ts
const { rounds, refetch: refetchRounds, ... } = useAdminRounds(contestId);
const { deadlinePassed, ... } = useRoundMatches(contestId, selectedRoundId, {
  onDeadlinePassed: () => void refetchRounds(),
});
```

### 4.3 `admin/results/page.tsx`

Same pattern for `activeRound` predictions hook — refetch rounds when active tour hits deadline so dropdown gains `CLOSED` entry.

---

## 5. U3 — Results page round selection

`ResultsEntryPanel` / `results/page.tsx`:

| Before | After |
|--------|-------|
| `eligible = rounds.filter(status ∈ CLOSED, CALCULATED, PUBLISHED)` | Also include round where `effectiveRoundStatus(r, deadlinePassedForRound)` is `CLOSED` |

Minimal approach: after U1 refetch, server returns `CLOSED`. Fallback: pass `activeDeadlinePassed` and treat `activeRound` as eligible when true.

Ensure selected round switches to CLOSED phase panel on Results (scores entry enabled per `matchResultsGating`).

---

## 6. U4 — Remove redundant manual close UX

When backend 1.16 ships:

| Component | Change |
|-----------|--------|
| `RoundStatusSidebar` | If `effectiveRoundStatus === "CLOSED"` and server still catching up, show «Дедлайн» hint — **hide** «Закрыть тур» (auto-close handles it) |
| `RoundManagementPanel` | Remove or demote manual close CTA when `deadlinePassed` (optional: keep as fallback if API returns error) |

Copy for post-deadline hint (LOCKED):

```text
Дедлайн прогнозов прошёл. Прогнозы закрыты; ввод результатов — на вкладке «Результаты».
```

---

## 7. `deriveAdminUiMode` alignment

Pass `deadlinePassed` (already supported). Ensure:

- `showDeadlinePassedHint` — keep for ACTIVE+passed until refetch completes
- `canEnterResults` / results gating uses `effectiveRoundStatus` not raw `ACTIVE`

---

## 8. File checklist

| File | Change |
|------|--------|
| `frontend/src/lib/admin/roundEffectiveStatus.ts` | NEW |
| `frontend/src/lib/admin/roundEffectiveStatus.test.ts` | NEW |
| `frontend/src/hooks/useRoundMatches.ts` | `onDeadlinePassed` callback |
| `frontend/src/app/admin/rounds/page.tsx` | Wire refetch |
| `frontend/src/app/admin/results/page.tsx` | Wire refetch + eligible rounds |
| `frontend/src/components/admin/RoundManagementPanel.tsx` | `effectiveRoundStatus` for phase routing |
| `frontend/src/components/admin/RoundStatusSidebar.tsx` | Effective badge; hide manual close |
| `frontend/src/components/admin/ResultsEntryPanel.tsx` | Eligible rounds fallback |
| `frontend/src/lib/admin/deriveAdminUiMode.ts` | Effective status if needed |

Optional E2E: extend `supervisor_*.spec.ts` — patch deadline to past via API, reload predictions, assert badge «Дедлайн».

---

## 9. Acceptance criteria

- [ ] Page open before deadline → after deadline UI shows «Дедлайн» phase without manual «Закрыть тур»
- [ ] `/admin/results` lists the tour for score entry after deadline
- [ ] No regression: ACTIVE before deadline still shows «Активен» / prediction window copy
- [ ] `npm run lint`, `npm run type-check`, `npm run test:unit` pass
- [ ] Works with backend 1.16 (round auto-closes on predictions GET)

---

## 10. Execution order

```text
1. backend/coder_1.16_fix_deadline.md  — per-round auto-close
2. coder_2.3.5_fix_deadline.md (this)  — UI sync + refetch
```

Frontend-only deploy before backend: `effectiveRoundStatus` still improves UX; full results entry needs 1.16.

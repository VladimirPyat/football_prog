# Fix 2.5.4 — Stale contest state & correct_outcomes column

**Source:** `agent_docs/reports/bug_2.5.4.md`
**Scope:** frontend only — no API, DB, or contract changes.

---

## 1. Goals

| # | Issue | Target |
|---|-------|--------|
| G1 | Admin settings shows stale `total_teams` / `matches_per_round` / `total_rounds` on contest switch | Clear contest in provider; treat id mismatch as loading in admin shell |
| G2 | Results matrix missing `correct_outcomes` | Map field and show «Исход» column before bonus columns |

---

## 2. Issue 1 — Stale contest

### `frontend/src/providers/ContestProvider.tsx`
In `setContestId`, when `fetchDetails` is true and `prev.id !== id`, call `setContest(null)` before `fetchContestDetails`.

### `frontend/src/hooks/useContestAdmin.ts`
- `isStale = contest != null && contest.id !== effectiveId`
- Expose `loading: loading || isStale`

### `frontend/src/components/admin/AdminPageShell.tsx`
Show `LoadingState` when `loading || !contest || contest.id !== contestId`.

### `frontend/src/app/admin/settings/parameters/page.tsx`
- Remove bare `if (!contest) return null` that bypasses shell loading
- Add `key={contest.id}` on `ContestParametersForm`

---

## 3. Issue 2 — correct_outcomes

### `frontend/src/lib/results/mapRoundResultsRow.ts`
Add `correct_outcomes: number` to `ResultsMatrixRow`; map from `row.correct_outcomes`.

### `frontend/src/lib/results/mapRoundResultsRow.test.ts`
Assert `correct_outcomes` is preserved.

### `frontend/src/components/contest/ResultsMatrix.tsx`
- Desktop header: `<th className={TH_GROUP COL_DIGIT2}>{headerLabel(["Исход"])}</th>` before bonus 1
- Body cell before bonus columns
- Score row: `colSpan={5}` (was 4)

### `frontend/src/components/contest/ResultsRowDetail.tsx`
Add «Исход» row in bonus section before «Бонус 1».

---

## 4. Acceptance criteria

- [ ] Switching contest in admin header immediately shows loading; parameters form shows correct values without round-trip
- [ ] Results matrix desktop shows «Исход» column with per-user counts
- [ ] Mobile detail modal shows «Исход» value
- [ ] Lint, type-check, unit tests pass

---

## 5. Verification

```bash
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run test:unit
```

**Manual:** `/admin/settings/parameters` — switch contests, verify counts. Contest results tab — verify «Исход» column matches leaderboard convention.

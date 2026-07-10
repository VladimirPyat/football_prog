# Frontend Design Consistency Audit

**Date:** 2026-07-10  
**Scope:** Visual/styling consistency (not pixel-perfect design). Goal: similar UI patterns share one implementation so fixes propagate automatically.  
**Refs:** `agent_docs/ui/design_system.md` (new), `agent_docs/ui/components.md`, fix 2.5.2 (`lib/table/*`).

---

## Executive summary

The project has a **component catalogue** (`agent_docs/ui/`) and a **partial shared styling layer** (`frontend/src/lib/table/`), but agent instructions only require updating the catalogue — not reusing or extending shared styles. As a result:

- Contest leaderboard and results tables were unified in fix 2.5.2, but **predictions matrix and all admin tables still use independent styles**.
- **~25 files** duplicate primary button classes; **6 admin tables** duplicate table shell/header markup.
- Three catalogue entries (`StatusChip`, `EmptyState`, `RoleBadge`) were **never implemented**; status colours are copy-pasted instead.
- `RoundLeaderboardPreview` rebuilds a mini leaderboard instead of reusing `LeaderboardTable`.

**Recommendation:** Extract P0 table and P1 button/badge primitives first (~2–3 focused sub-tasks), then migrate consumers file-by-file. No visual redesign required — consolidation only.

---

## Current shared layer (what works)

| Asset | Location | Consumers |
|-------|----------|-----------|
| Column width tokens | `lib/table/columnStyles.ts` | Leaderboard, Results, Predictions (name col only) |
| Header cell styles | `lib/table/tableHeaderStyles.ts` | Leaderboard, Results |
| Multiline header helper | `lib/table/headerLabel.tsx` | Leaderboard, Results |
| Loading / error / confirm / modal | `components/ui/*` | Widespread but not universal |

Fix 2.5.2 proved the model: changing `COL_DIGIT2` width fixed both leaderboard and results headers. **The same approach must extend to admin tables and predictions.**

---

## Findings by category

### 1. Tables — high impact

#### 1.1 Contest tables (Type A)

| Component | Shell | Header tokens | Column tokens | Issue |
|-----------|-------|---------------|---------------|-------|
| `LeaderboardTable` | ✅ contest shell | ✅ `TH_*` | ✅ `COL_*` | Reference implementation |
| `ResultsMatrix` | ✅ contest shell | ✅ `TH_*` | ✅ `COL_*` | Reference implementation |
| `PredictionsMatrix` | ❌ no outer shell | ❌ inline `px-2 py-2` | ⚠️ `COL_NAME` only | `text-base` on table; headers don't use `headerLabel` / `TH_*`; team cols `min-w-[4.5rem]` vs results `3.25rem` |

**Impact:** User sees three tabs on `/contest/[id]` with visibly different table treatment.

#### 1.2 Admin tables (Type B) — all ad-hoc

| Component | File | Header padding | Row border | Wrapper |
|-----------|------|----------------|------------|---------|
| `ParticipantsTable` | admin | `px-4 py-2` | `border-t border-gray-200` | border on wrapper ✅ |
| `RoundPhasePanel` → `MatchTable` | admin | `px-3 py-2` | `border-t border-gray-200` | border on wrapper ✅ |
| `ResultsEntryPanel` | admin | `px-3 py-2` | via `MatchResultRow` | border on wrapper ✅ |
| `RoundManagementPanel` | admin | `px-3 py-2` | via `MatchEditorRow` | ❌ no border on wrapper |
| `RoundLeaderboardPreview` | admin | `px-3 py-2 text-xs` | `border-t border-gray-100` | border on wrapper ✅ |

**Common pattern (should be one component):**
```tsx
<div className="overflow-x-auto border border-gray-200 rounded-lg">
  <table className="min-w-full text-sm">
    <thead className="bg-gray-50">…</thead>
  </table>
</div>
```
Copied 5× with minor padding drift (`px-3` vs `px-4`, `text-xs` vs `text-sm`).

#### 1.3 Admin preview (Type C) — missed reuse opportunity

`RoundLeaderboardPreview` fetches leaderboard API and renders a 3-column stub table.  
`RoundResultsPreview` correctly wraps `ResultsMatrix`.

**Proposal:** Refactor `RoundLeaderboardPreview` to use `LeaderboardTable` with props:
```ts
{ rows, showCountColumns: false, compact: true, maxRows?: 10 }
```
Any leaderboard styling fix then applies to public tab **and** admin CALCULATED preview.

#### 1.4 Duplicated cell renderers

| Logic | Locations |
|-------|-----------|
| Green highlight for positive points | `LeaderboardTable.PointsCell`, `ResultsMatrix.MatchPointsCell`, `ResultsMatrix.TotalCell` |
| Amber bonus column background | `LeaderboardTable`, `ResultsMatrix` (inline `bg-amber-50/50`) |
| Prediction score pill | `PredictionsMatrix.ScoreCell` (inline, not exported) |

---

### 2. Buttons — high impact (~25 files)

Primary button class duplicated with **4 variants**:

| Variant | Example files | Diff |
|---------|---------------|------|
| `rounded` (no shadow) | `TeamForm`, `RoundPhasePanel`, `PredictionForm` | baseline |
| `rounded-lg shadow` | `ContestLifecycleActions` | + shadow, + lg radius |
| `rounded w-full` | `LoginForm`, `ChangePasswordForm` | full width |
| `rounded px-3 py-1` | `AdminTopNav` | smaller |

Secondary/cancel buttons are more consistent (`border border-gray-300 rounded hover:bg-gray-50`) but still duplicated ~15×.

**Proposal:** Single `Button` component with `variant` + `size` + `fullWidth` props. Estimated **~120 lines removed**, one place to fix hover/disabled states.

---

### 3. Status badges & chips — medium impact

Documented `StatusChip` in catalogue §2 — **not implemented**.

| Location | Implementation |
|----------|----------------|
| `RoundStatusSidebar` | Local `STATUS_BADGE` map (round statuses) |
| `ContestList` | Local `STATUS_LABELS` + `bg-gray-100` badge |
| `ResultsEntryPanel` | Inline `bg-green-50 text-green-700` for published |
| `RoundLeaderboardPreview` / `RoundResultsPreview` | Inline `bg-blue-100 text-blue-700` preview badge |
| `components.md` §2 | Colour map for round + match statuses |

**Proposal:** `StatusChip({ kind, status })` + `PreviewBadge` for admin preview label. Colour map lives once in `lib/ui/statusColors.ts`.

---

### 4. Banners & callouts — medium impact

Repeated info/warning patterns:

| Pattern | Classes | Occurrences |
|---------|---------|-------------|
| Info hint | `text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2` | `ResultsEntryPanel`, `RoundPhasePanel`, `RoundStatusSidebar`, `RoundManagementPanel` |
| Warning | `text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2` | `RoundLeaderboardPreview`, `RoundResultsPreview`, `LockBanner` (variant) |
| Error inline | `text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2` | `RoundManagementPanel`, forms |

Lock/Contest status banners (`LockBanner`, `ContestStatusBanner`) are correctly extracted. **Inline hints are not.**

**Proposal:** `Callout({ variant: 'info' | 'warning' | 'error', children })`.

---

### 5. Empty & loading states — low/medium impact

| Pattern | Current |
|---------|---------|
| `LoadingState` | Used in many places ✅ |
| `EmptyState` | **Catalogued, not built** — each page: `<p className="text-gray-500 py-8 text-center">`, `<td colSpan>`, etc. |
| Inline loading | `RoundLeaderboardPreview`: `<p className="text-xs … animate-pulse">` instead of `LoadingState` |

---

### 6. Modals — low impact

| Component | Overlay | Panel |
|-----------|---------|-------|
| `ConfirmDialog` | `bg-black/40` | `rounded-lg shadow-lg max-w-md` |
| `DetailModal` | `bg-black/50` | `rounded-t-xl sm:rounded-lg shadow-xl` |
| `TiebreakForm` in `ParticipantsTable` | `bg-black/40` | custom inline (duplicate of ConfirmDialog shell) |
| `ParticipantInviteModal` | similar | similar |

**Proposal:** Optional `Modal` base; lower priority than tables/buttons.

---

### 7. Form fields — low impact (consistent enough)

Most forms share: `w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100`.  
Minor drift in compact inputs (`MatchEditorRow`: `px-1 py-0.5 text-xs`). Acceptable until form density becomes an issue.

---

### 8. Documentation & process gaps

| Gap | Detail |
|-----|--------|
| No reuse mandate | Coder instructions say «update components.md» but not «reuse design_system.md» |
| Phantom catalogue entries | `StatusChip`, `EmptyState`, `RoleBadge` listed as if they exist |
| `MultiLineColumnHeader` | Orphan component — superseded by `headerLabel` + `TeamColumnHeader` in fix 2.5.2; candidate for removal |
| Tab patterns undocumented | `PublicTabs` (pill) vs `SettingsSubNav` (underline) — intentional or drift? Should be documented as two allowed patterns |

---

## Proposed optimization roadmap

### Phase 0 — Documentation (this audit) ✅

- [x] Create `agent_docs/ui/design_system.md`
- [x] Update `agent_docs/ui/components.md` with reuse rules + shared layer section
- [x] This report

### Phase 1 — P0: Table consolidation (1 coder task)

1. Add `DataTable` + `AdminTable` shells and `TH_ADMIN` to `lib/table/tableHeaderStyles.ts`
2. Extract `PointsCell`, `TotalCell`, `ScoreCell`
3. Migrate `PredictionsMatrix` to shared contest table stack
4. Migrate admin tables: `ParticipantsTable`, `RoundPhasePanel`, `ResultsEntryPanel`, `RoundManagementPanel`
5. Refactor `RoundLeaderboardPreview` → `LeaderboardTable`

**Acceptance:** Changing `TH_ADMIN` padding updates all admin tables; changing `COL_DIGIT2` updates all three contest tabs.

### Phase 2 — P1: Actions & feedback (1 coder task)

1. `Button` component — migrate all submit/CTA buttons
2. `StatusChip` + `PreviewBadge` — migrate badge usages
3. `Callout` — migrate info/warning banners
4. `EmptyState` — implement and replace inline empty messages

### Phase 3 — P2: Forms & cleanup (optional)

1. `Input` / `Select` / `FieldError` primitives
2. `Modal` base extraction
3. Remove `MultiLineColumnHeader.tsx` if unused
4. Document tab bar variants in design_system.md

---

## Files to touch (Phase 1 migration list)

| File | Change |
|------|--------|
| `frontend/src/components/ui/DataTable.tsx` | **new** |
| `frontend/src/components/ui/AdminTable.tsx` | **new** |
| `frontend/src/lib/table/tableHeaderStyles.ts` | add `TH_ADMIN`, `TD_ADMIN` |
| `frontend/src/components/predictions/PredictionsMatrix.tsx` | adopt shared stack |
| `frontend/src/components/admin/ParticipantsTable.tsx` | use `AdminTable` |
| `frontend/src/components/admin/RoundPhasePanel.tsx` | use `AdminTable` |
| `frontend/src/components/admin/ResultsEntryPanel.tsx` | use `AdminTable` |
| `frontend/src/components/admin/RoundManagementPanel.tsx` | use `AdminTable` |
| `frontend/src/components/admin/RoundLeaderboardPreview.tsx` | reuse `LeaderboardTable` |
| `frontend/src/components/contest/LeaderboardTable.tsx` | extract cell atoms to `ui/` |

---

## Metrics (baseline)

| Metric | Count |
|--------|-------|
| Files with inline `bg-blue-600` button | 25+ |
| Ad-hoc admin `<table>` implementations | 5 |
| Contest tables using full `lib/table` stack | 2 / 3 |
| Catalogue components not implemented | 3 (`StatusChip`, `EmptyState`, `RoleBadge`) |
| Shared table style modules | 3 (`columnStyles`, `tableHeaderStyles`, `headerLabel`) |

---

## Recommendations for agent workflow

1. Add to **every future** `coder_*.md` / `fix_*.md` UI section:
   > Before styling: read `agent_docs/ui/design_system.md`. Reuse `components/ui/*` and `lib/table/*`. Do not duplicate Tailwind class strings for tables, buttons, badges, or callouts.

2. Add **tester checklist** item:
   > If fix touches table/button styling, verify all tables of the same taxonomy type (A/B/C) still match.

3. Consider a lightweight **lint rule** (future): grep for forbidden duplicates like `bg-blue-600 text-white` outside `Button.tsx`.

---

## Summary

The frontend is functionally complete but **styling is fragmented**. The fix 2.5.2 pattern (shared tokens in `lib/table/`) is the right architecture — it just wasn't extended to admin UI or predictions. Consolidation is incremental, low-risk, and does not require design changes — only moving duplicated markup into shared components so **one fix updates all similar views**.

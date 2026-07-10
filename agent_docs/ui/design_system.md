# Design System & Shared UI Primitives (Stage 2+)

> **Living document** — see update log at the bottom.
> **Purpose:** Single source of truth for **visual consistency** across pages. When styling is fixed in one place, all consumers inherit the change.
> **Refs:** `agent_docs/ui/components.md` (component catalogue), `docs/02_project_structure.md` (Tailwind only, no external UI libs, no animations).

---

## 1. Maintenance rules (mandatory for all frontend work)

| Rule | Action |
|------|--------|
| **Reuse before invent** | Before adding Tailwind classes inline, check `frontend/src/components/ui/` and `frontend/src/lib/table/`. Extend existing primitives; do not copy-paste class strings. |
| **Update docs on change** | Any new shared primitive → add to this file + `components.md`. Any page-specific table that should be shared → note here before shipping. |
| **Fix once, apply everywhere** | Table header fix → update `lib/table/tableHeaderStyles.ts`, not individual `<th>` in each page. Button fix → update `Button` component, not 30 files. |
| **Catalogue sync** | `components.md` lists *what* exists; this file lists *how to style and reuse*. Both must stay in sync after each UI sub-stage. |
| **Coder instructions** | Every `coder_*.md` / `fix_*.md` that touches UI must include: «Check `agent_docs/ui/design_system.md`; reuse shared primitives; update catalogue if new.» |

---

## 2. Layer model

```
┌─────────────────────────────────────────────────────────┐
│  Pages (app/*) — layout only, no ad-hoc table styles    │
├─────────────────────────────────────────────────────────┤
│  Domain components (contest/*, admin/*, predictions/*)  │
│  — compose primitives, pass data                        │
├─────────────────────────────────────────────────────────┤
│  Shared UI (components/ui/*) — Button, Badge, Table…  │
├─────────────────────────────────────────────────────────┤
│  Style tokens (lib/ui/*, lib/table/*) — Tailwind consts │
└─────────────────────────────────────────────────────────┘
```

**Target:** domain components import from `components/ui` and `lib/table`; pages never define their own `<table>` shell classes.

---

## 3. Implemented shared styling (use these)

### 3.1 Contest data tables — `frontend/src/lib/table/`

| Module | Exports | Used by | Not yet used by |
|--------|---------|---------|-----------------|
| `columnStyles.ts` | `COL_RANK`, `COL_NAME`, `COL_DIGIT2`, `COL_DIGIT3`, `adaptiveNameClass()` | `LeaderboardTable`, `ResultsMatrix`, `PredictionsMatrix` (partial) | Admin tables |
| `tableHeaderStyles.ts` | `TH_BASE`, `TH_STICKY`, `TH_GROUP`, `TH_BONUS`, `TH_TOTAL` | `LeaderboardTable`, `ResultsMatrix` | `PredictionsMatrix`, all admin tables |
| `headerLabel.tsx` | `headerLabel(lines[])` — multiline thead text | `LeaderboardTable`, `ResultsMatrix` | `PredictionsMatrix`, admin tables |

**Contest table shell (public):**
```tsx
<div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
  <table className="border-collapse text-sm w-max max-w-full">…</table>
</div>
```

### 3.2 Generic UI — `frontend/src/components/ui/`

| Component | Status | Notes |
|-----------|--------|-------|
| `LoadingState` | ✅ Implemented | Use for all fetch spinners; do not inline `<p>Загрузка…</p>` |
| `ErrorState` | ✅ Implemented | Use for fetch failures |
| `ConfirmDialog` | ✅ Implemented | Destructive confirms |
| `DetailModal` | ✅ Implemented | Mobile-friendly detail sheet (leaderboard/results compact mode) |
| `Toast` | ✅ Implemented | Via `ToastProvider` |

### 3.3 Status colour map (from `components.md`)

Documented in catalogue §2. **Not yet extracted** into `StatusChip` — colours duplicated in `RoundStatusSidebar`, `ContestList`, inline badges.

---

## 4. Planned shared primitives (extract next)

Priority order reflects audit in `agent_docs/reports/frontend_design_consistency_audit.md`.

### P0 — Tables

| Primitive | Target path | Replaces inline styles in |
|-----------|-------------|---------------------------|
| `DataTable` shell | `components/ui/DataTable.tsx` | Wrapper + scroll + border; props: `children`, `testId?`, `variant?: 'contest' \| 'admin'` |
| `AdminTable` | `components/ui/AdminTable.tsx` | Thin wrapper: `DataTable variant="admin"` + standard `<thead>` row using `TH_ADMIN` tokens |
| `TH_ADMIN` tokens | `lib/table/tableHeaderStyles.ts` | `px-3 py-2 text-left text-sm font-medium text-gray-700` — used by 6+ admin tables |
| `PointsCell` / `TotalCell` | `components/ui/PointsCell.tsx` | Duplicated in `LeaderboardTable` and `ResultsMatrix` |
| `ScoreCell` (prediction) | `components/predictions/ScoreCell.tsx` | Inline in `PredictionsMatrix` |

**Migration:** `PredictionsMatrix` must adopt `tableHeaderStyles` + contest shell (fix 2.5.2 scope extension).

### P1 — Actions & feedback

| Primitive | Target path | Notes |
|-----------|-------------|-------|
| `Button` | `components/ui/Button.tsx` | Variants: `primary`, `secondary`, `danger`, `dangerOutline`, `ghostLink`. Sizes: `sm`, `md`. **~25 files** duplicate `bg-blue-600` strings today. |
| `StatusChip` | `components/ui/StatusChip.tsx` | Props: `{ kind: 'round' \| 'match' \| 'contest', status }`. Centralize colour map from `components.md` §2. |
| `PreviewBadge` | `components/ui/PreviewBadge.tsx` | «Предпросмотр — тур ещё не опубликован» — duplicated in `RoundLeaderboardPreview`, `RoundResultsPreview` |
| `Callout` | `components/ui/Callout.tsx` | Info/warning/error banners (`bg-blue-50`, `bg-amber-50`, `bg-red-50`) — 10+ inline copies |
| `EmptyState` | `components/ui/EmptyState.tsx` | Documented in catalogue but **never implemented**; each page uses ad-hoc `<p className="text-gray-500">` |

### P2 — Forms & navigation

| Primitive | Target path | Notes |
|-----------|-------------|-------|
| `Input` / `Select` / `Label` / `FieldError` | `components/ui/form/*` | Standard field: `w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100` |
| `FormActions` | `components/ui/FormActions.tsx` | Primary + cancel button row |
| `TabBar` | `components/ui/TabBar.tsx` | Unify `PublicTabs` (pill) and `SettingsSubNav` (underline) behind `variant` prop OR document as intentional two patterns |
| `Modal` base | `components/ui/Modal.tsx` | Extract shared overlay from `ConfirmDialog`, `DetailModal`, custom modals (`TiebreakForm`, `ParticipantInviteModal`) |

---

## 5. Table taxonomy

| Type | Example | Shared stack | Current compliance |
|------|---------|--------------|-------------------|
| **A. Contest scoreboard** | Leaderboard, Results matrix | `lib/table/*` + contest shell | ✅ Leaderboard, Results — ✅; Predictions — ⚠️ partial |
| **B. Admin CRUD list** | Participants, match lists | `AdminTable` + `TH_ADMIN` | ❌ 6 files, all ad-hoc |
| **C. Admin preview (subset)** | `RoundLeaderboardPreview` | Should reuse `LeaderboardTable` with `compact`/`columns` props | ❌ separate simplified table |
| **D. List (non-tabular)** | `ContestList` | `ListPanel` (future) | ⚠️ one-off, acceptable for now |

**Key rule:** Type A and C must share the same column/header tokens. Type B shares admin tokens only.

---

## 6. Button & badge token reference (target — extract to `lib/ui/classes.ts`)

```ts
// Primary action
"px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"

// Secondary / cancel
"px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"

// Success (publish, start)
"px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"

// Danger text link (delete row)
"text-sm text-red-600 hover:underline"

// Round status badge base
"inline-block text-xs font-semibold px-2 py-1 rounded"
```

**Current drift:** mix of `rounded` vs `rounded-lg`, `shadow` vs no shadow, `font-medium` vs none across 25+ button call sites.

---

## 7. Checklist for new UI work

- [ ] Does a shared primitive already exist? (grep `components/ui`, `lib/table`, `lib/ui`)
- [ ] If adding a table: which taxonomy type (A/B/C)? Use matching shell + header tokens.
- [ ] If adding a button: use `Button` (once extracted) or match token reference §6.
- [ ] If adding a status indicator: use `StatusChip` (once extracted).
- [ ] Updated `components.md` + this file + update log?
- [ ] No new inline duplicate of strings already in `lib/table` or `lib/ui`.

---

## Update log

| Date | Change |
|------|--------|
| 2026-07-10 | Initial design system doc after frontend consistency audit. Documented existing `lib/table/*`, planned P0–P2 extractions, maintenance rules. |

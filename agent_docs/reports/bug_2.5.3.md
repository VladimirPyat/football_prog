# BUG-2.5.3: Shared UI primitives & design-system rollout

## Status
VERIFIED (unit/lint/tsc)

## Triage
- **Class**: ENHANCEMENT (frontend consistency)
- **Rationale**: Extract shared components and migrate pages to unified table/button/modal patterns. No API changes.

## Description
Frontend had fragmented inline Tailwind across pages — tables, buttons, banners, modals duplicated. Contest results/leaderboard rendered differently on public vs admin preview. Round selection not persisted across reloads.

## Fix
### New shared layer (`frontend/src/components/ui/`)
- `Button`, `Modal`, `DataTable`, `AdminTable`, `Callout`, `EmptyState`, `StatusChip`, `PreviewBadge`, `Select`, `PointsCell`

### Contest views (single entry points)
- `ContestResultsView` — public tab + admin preview modal
- `ContestLeaderboardView` — public tab + `RoundLeaderboardPreview`

### Round persistence
- `usePersistedRoundSelection` + `fp_selected_round:{contestId}:{scope}` in localStorage
- Scopes: `contest-public`, `predict`, `admin-rounds`, `admin-results`
- Admin results: `?round=` URL deep link

### Migrations
- `PredictionsMatrix`, admin tables (`ParticipantsTable`, `RoundPhasePanel`, `ResultsEntryPanel`, `RoundManagementPanel`) → shared table stack
- `LeaderboardTable`, `ResultsMatrix` → `DataTable` + `PointsCell`
- `LoginModal`, `ConfirmDialog`, tiebreak modal → `Modal`
- Pages: contest, predict, admin rounds/results → persisted round hook

### Docs
- `agent_docs/ui/design_system.md` (new)
- `agent_docs/instructions/fix_2.5.3.md`
- `agent_docs/reports/frontend_design_consistency_audit.md` (baseline audit)

## Remaining (deferred P2)
- `Input` / `FormField` primitives for form inputs (styling already consistent via shared class string)
- `DetailModal` → base `Modal` (low priority; mobile bottom-sheet layout differs)

## Verification
```bash
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run test:unit
```

**Manual:** Select tour on `/contest/[id]` → reload → same tour. Admin `/admin/results?round=N` opens round N. Leaderboard/results/predictions tables visually aligned.

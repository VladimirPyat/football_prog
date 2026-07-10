# Fix 2.5.3 — Shared UI primitives & design-system rollout

**Source:** `agent_docs/reports/frontend_design_consistency_audit.md` (Jul 2026).
**Prerequisite:** fix 2.5.2 shipped (`lib/table/*` for contest scoreboards).
**Scope:** frontend only — no API, DB, or contract changes.

---

## 1. Goals

| # | Issue | Target |
|---|-------|--------|
| G1 | Inline Tailwind duplicated across 25+ files (buttons, tables, banners) | Shared `components/ui/*` primitives; fix once → apply everywhere |
| G2 | Results / leaderboard rendered differently on public vs admin preview | `ContestResultsView`, `ContestLeaderboardView` — single entry points |
| G3 | Admin tables (participants, matches, results entry) ad-hoc markup | `DataTable` / `AdminTable` + `TH_ADMIN` tokens |
| G4 | `PredictionsMatrix` not on shared table stack | Adopt `lib/table/*` + contest `DataTable` shell |
| G5 | Round selection not persisted; admin results ignores `?round=` deep link | `usePersistedRoundSelection` + `fp_selected_round:{contestId}:{scope}` in localStorage |
| G6 | Custom modal shells (login, preview, tiebreak) duplicate overlay markup | `Modal` base component |
| G7 | Agent instructions lack reuse mandate | Update `design_system.md`, `components.md`; coder rule in §0 |

---

## 2. New files

| File | Purpose |
|------|---------|
| `frontend/src/components/ui/Button.tsx` | `variant` + `size` + `fullWidth` |
| `frontend/src/components/ui/Modal.tsx` | Overlay + panel shell |
| `frontend/src/components/ui/DataTable.tsx` | Contest vs admin table wrapper |
| `frontend/src/components/ui/AdminTable.tsx` | Admin thead + `AdminTh` |
| `frontend/src/components/ui/Callout.tsx` | info / warning / error banners |
| `frontend/src/components/ui/EmptyState.tsx` | Centred empty message |
| `frontend/src/components/ui/StatusChip.tsx` | Round / match / contest badges |
| `frontend/src/components/ui/PreviewBadge.tsx` | Admin «Предпросмотр» label |
| `frontend/src/components/ui/PointsCell.tsx` | Shared numeric cell (green highlight) |
| `frontend/src/components/ui/Select.tsx` | Styled `<select>` |
| `frontend/src/lib/contest/pickDefaultRound.ts` | Default round by tab (public) |
| `frontend/src/lib/contest/roundSelectionStorage.ts` | localStorage get/set |
| `frontend/src/hooks/usePersistedRoundSelection.ts` | Persist + validate + default |
| `frontend/src/components/contest/ContestResultsView.tsx` | Results matrix + fetch states |
| `frontend/src/components/contest/ContestLeaderboardView.tsx` | Leaderboard + fetch states |

---

## 3. Modified files (migration)

### Tables
- `lib/table/tableHeaderStyles.ts` — add `TH_ADMIN`, `TD_ADMIN`, `TR_ADMIN_BORDER`
- `PredictionsMatrix.tsx` — shared stack
- `LeaderboardTable.tsx`, `ResultsMatrix.tsx` — `DataTable`, `PointsCell`
- `ParticipantsTable.tsx`, `RoundPhasePanel.tsx`, `ResultsEntryPanel.tsx`, `RoundManagementPanel.tsx` — `AdminTable`
- `RoundLeaderboardPreview.tsx` — reuse `LeaderboardTable`

### Pages / panels
- `app/contest/[contestId]/page.tsx` — `usePersistedRoundSelection`, shared views, `Callout`
- `app/contest/[contestId]/predict/[roundId]/page.tsx` — persisted round + `router.push`
- `app/admin/rounds/page.tsx`, `app/admin/results/page.tsx` — persisted round; results reads `?round=`
- `ResultsEntryPanel.tsx` — `Modal` + `ContestResultsView`
- `LoginModal.tsx` — `Modal`
- `ParticipantsTable.tsx` — `Modal` for tiebreak
- `RoundSelector.tsx` — `Select`

### Buttons
Migrate inline `bg-blue-600` / cancel patterns to `<Button>` across admin + auth + layout components.

---

## 4. Round persistence rules

**Storage key:** `fp_selected_round:{contestId}:{scope}`

| Scope | Page | Default when no stored value |
|-------|------|------------------------------|
| `contest-public` | `/contest/[id]` | `pickDefaultRound(rounds, tab)` |
| `predict` | `/contest/[id]/predict/[rid]` | ACTIVE round, else last non-DRAFT |
| `admin-rounds` | `/admin/rounds` | Last round in list |
| `admin-results` | `/admin/results` | Last eligible round; URL `?round=` overrides on first load |

Stored value is kept while round remains in the allowed list; cleared automatically when invalid.

---

## 5. Acceptance criteria

- [ ] Changing `TH_ADMIN` padding updates all admin tables.
- [ ] `ContestResultsView` used on public «Результаты» tab and admin preview modal.
- [ ] `ContestLeaderboardView` used on public tab and `RoundLeaderboardPreview`.
- [ ] Round selection survives page reload on contest + admin pages (same contest).
- [ ] `/admin/results?round=N` opens round N.
- [ ] `PredictionsMatrix` matches leaderboard/results table typography.
- [ ] `npm run lint`, `npm run type-check`, `npm run test:unit` pass.

---

## 6. Verification

```bash
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run test:unit
```

**Manual:** Public contest page → select tour 5 → reload → still tour 5. Admin results deep link `?round=`. Preview modals use same results table as public tab.

---

## 7. Non-goals

- Full form field extraction (`Input` everywhere) — defer to P2
- `LeaderboardViewToggle` / localStorage compact mode (explicitly out per 2.4)
- Visual redesign / new colours

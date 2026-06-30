# BUG-2.2.2: Frontend UX — auth shell, navigation, LB/Results display

## Status
VERIFIED

## Triage
- **Class**: BUG
- **Rationale**: Multiple frontend components (AppShell, LoginForm, ProfileMenu, contest tabs) in the same module; no API contract changes; behaviour/UI fixes scoped to Stage 2.1/2.2 deliverables.

## Description
Frontend built per `coder_2.1.md` / `coder_2.2.md` needs UX fixes:

1. Login form lacks password visibility toggle.
2. Header shows «Личный кабинет» instead of `user.login`; footer should show login for authenticated users.
3. No global responsive sidebar; profile-only menu pattern; «Конкурсы» should be removed from user nav.
4. Header missing live date/time under brand; username dropdown menu on all pages.
5. Predictions/Results tables use full team names — horizontal scroll.
6. Leaderboard and Results tabs are stubs; need mock tables per `user_leaderboard.jpg` / `user_result.jpg` with mobile compact modes.

## Root Cause
Stage 2.4 (full LB/Results) not shipped; shell/nav patterns implemented only on `/profile`; AppShell header copy hardcoded.

## Fix
- `LoginForm.tsx` — password visibility toggle
- `AppShell.tsx` — datetime under brand, username dropdown, footer login, USER sidebar wrap
- `UserNavMenu.tsx`, `UserSidebarLayout.tsx`, `UserMenuDropdown.tsx`, `HeaderDateTime.tsx` — global nav
- `LeaderboardTable.tsx`, `ResultsMatrix.tsx`, `contestDisplayMock.ts` — mock LB/Results per screenshots
- `formatTeamPair.ts`, `PredictionsMatrix.tsx` — short team column headers
- `profile/page.tsx` — sidebar moved to AppShell

## Verification
- `npm run lint` — pass
- `npm run type-check` — pass
- Manual: login password toggle; header login + datetime; sidebar on user pages; LB/Results mock on published round

## Delegation Log
| Step | Agent | Artifact | Result |
|------|-------|----------|--------|
| 1 | @BugFixCoordinator | reports + instructions | done |
| 2 | @Coder | frontend implementation | done |

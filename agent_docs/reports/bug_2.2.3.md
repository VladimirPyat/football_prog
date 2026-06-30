# BUG-2.2.3: Frontend UX follow-up (mobile nav, header, contest picker, mock tables)

## Status
VERIFIED

## Triage
- **Class**: BUG
- **Rationale**: UI fixes across layout and contest pages; no contract changes.

## Description
Follow-up to BUG-2.2.2:

1. Mobile menu button should be hamburger left of brand (standard pattern), not full-width bar in content.
2. Header `user` login duplicated (span + dropdown); dropdown menu redundant — link to profile/contacts only.
3. Contest picker missing for USER role — should appear above round selector on contest/predict pages.
4. Predictions matrix: stack short home/away team names vertically; narrower columns.
5. Mock leaderboard/results not visible — gated by `PUBLISHED` round status.

## Root Cause
- Mobile toggle lived in `UserSidebarLayout` content area, not header.
- `UserMenuDropdown` duplicated sidebar nav; extra `header-user-login` span for staff pattern leaked to USER.
- `ContestPicker` only rendered in header for staff.
- Mock tables hidden behind `isRoundPubliclyVisible` stub gate.

## Fix
- `UserNavProvider` + `MobileMenuButton` in header; slide-in drawer in `UserSidebarLayout`.
- Header: single `Link` to `/profile` with `user.login`.
- `ContestRoundToolbar`: `ContestPicker` above `RoundSelector` on contest + predict pages.
- `TeamColumnHeader` stacked labels; narrower matrix columns.
- LB/Results tabs always render mock components (removed publish stub gate).

## Verification
- `npm run lint` — pass
- `npm run type-check` — pass

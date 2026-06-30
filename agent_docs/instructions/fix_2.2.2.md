# Fix Instructions — BUG-2.2.2: Frontend UX polish

> **Scope:** `frontend/` only. No backend or contract changes.
> **Reference:** `coder_2.1.md`, `coder_2.2.md`, `docs/screens/user_leaderboard.jpg`, `docs/screens/user_result.jpg`.

## Objective

Fix auth shell, global user navigation, and public contest LB/Results display.

## Files to create

| File | Purpose |
|------|---------|
| `src/lib/teams/formatTeamPair.ts` | Short team-pair labels for matrix columns |
| `src/lib/mocks/contestDisplayMock.ts` | Mock LB + Results per screenshots |
| `src/components/layout/HeaderDateTime.tsx` | Live date/time under brand |
| `src/components/layout/UserNavMenu.tsx` | Shared nav (no «Конкурсы») |
| `src/components/layout/UserMenuDropdown.tsx` | Header username dropdown |
| `src/components/layout/UserSidebarLayout.tsx` | Desktop sidebar + mobile toggle |
| `src/components/contest/LeaderboardTable.tsx` | 13-col + mobile compact (3 point cols) |
| `src/components/contest/ResultsMatrix.tsx` | Points grid + mobile (hide bonuses) |

## Files to modify

| File | Change |
|------|--------|
| `src/components/auth/LoginForm.tsx` | Password show/hide toggle |
| `src/components/layout/AppShell.tsx` | Datetime, username dropdown, footer login, USER sidebar wrap |
| `src/components/profile/ProfileMenu.tsx` | Re-export or remove — use `UserNavMenu` |
| `src/app/profile/page.tsx` | Drop local sidebar grid |
| `src/app/contest/[contestId]/page.tsx` | Wire LB/Results mock components |
| `src/components/predictions/PredictionsMatrix.tsx` | Short team headers |

## Acceptance criteria

1. Login password field has visibility toggle button.
2. Authenticated header shows `user.login` (not «Личный кабинет»); footer shows login for any authenticated role.
3. USER pages: left sidebar on `md+`, hamburger on mobile, larger mobile fonts.
4. User nav: Контакты, Сделать прогноз, Просмотр результатов, stats placeholder — **no** Конкурсы.
5. Brand area shows current date/time (updates every minute).
6. Username dropdown duplicates nav links on all pages.
7. Published rounds: LB + Results show mock data from screenshots.
8. Mobile LB: Место, Фамилия, Очки без бонуса, Очки с бонусами, Всего очков.
9. Mobile Results: match points + ИТОГ only (bonuses hidden).
10. Matrix columns use `formatTeamPairShort()` — minimal width.

## Verification

```bash
cd frontend && npm run lint && npm run type-check
```

Manual smoke on `/profile`, `/contest/1` (LB/Results tabs, published round).

# Todo frontend fix — participants login column + E2E credentials

> **Status:** Done  
> **Scope:** Item 8 from user request + E2E alignment after demo user removal

## 1. Participants table — login column (item 8)

- `ParticipantsTable.tsx`: add **Логин** column between name and email.
- `ParticipantOut` already includes `login` from API — no backend change.

## 2. E2E credentials after demo user removal

- `credentials.ts`: remove `DEMO_USER_*`; default USER fallback → contracted `shutov` / `user`.
- `auth.ts`: replace `loginAsDemoUser` with `loginAsContractedUser` (shutov/user).
- Update all E2E specs that imported `loginAsDemoUser`.
- `adminApi.ts`: update comment on `DEV_SETUP_E2E_HYBRID` (contracted user, not demo).

## Non-goals

- Clone wizard UI (deferred).

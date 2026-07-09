# BUG-2.5.1: Supervisor admin header duplication + round builder match time

## Status
VERIFIED (implementation in same session)

## Triage
- **Class**: BUG
- **Rationale**: Frontend-only layout + form UX; no API/contract changes; multiple components in admin shell.

## Description
Supervisor admin shows duplicate contest picker (global header + admin nav), duplicate branding/date in admin nav, and round builder leaves datetime empty when adding matches.

**Repro:**
1. Login as supervisor → `/admin/results`
2. Observe contest picker in top header AND in admin card
3. Observe «SportPrognosis» + date above tabs inside admin nav
4. `/admin/rounds` → create tour → add second match → datetime empty

## Root Cause
- `AppShell` renders `ContestPicker` for all staff routes including `/admin/*`
- `AdminTopNav` repeats branding row above tabs
- `RoundBuilderForm` uses `emptyMatch()` without inheriting prior datetime

## Fix
- Files: `AppShell.tsx`, `AdminTopNav.tsx`, `RoundBuilderForm.tsx`, `roundBuilderDefaults.ts`, `adminApi.ts` (E2E helper)
- Summary: hide header picker on admin; restructure admin nav; prefill match datetime on add

## Verification
- Vitest roundBuilderDefaults
- eslint + tsc

## Delegation Log
| Step | Agent | Artifact | Result |
|------|-------|----------|--------|
| 1 | @BugFixCoordinator | fix_2.5.1.md, bug_2.5.1.md | Instructions ready |
| 2 | @Coder | implementation | Shipped same session |

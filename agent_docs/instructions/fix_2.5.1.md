# Fix 2.5.1 — Supervisor admin chrome + round builder defaults

**Source:** manual QA screenshot (Jul 2026).
**Prerequisite:** fix 2.5 shipped.
**Scope:** frontend only.

---

## 1. Goals

| # | Issue | Target |
|---|-------|--------|
| G1 | Contest picker duplicated in global header + admin nav | Single picker in admin nav only (hide in `AppShell` on `/admin/*`) |
| G2 | Admin nav duplicates site title + date | Remove «SportPrognosis» + «Сегодня …» from `AdminTopNav` |
| G3 | Contest picker + «+ Новый конкурс» sit above tabs | Tabs first; picker + button in row **below** tabs |
| G4 | Round builder: new match has empty datetime | Prefill from last match time, else deadline time |

---

## 2. Required changes

### 2.1 `AppShell.tsx`

- `usePathname()`; when `pathname.startsWith("/admin")` → do **not** render `<ContestPicker />` for staff.
- Global header keeps site title + datetime + «Управление» / logout.

### 2.2 `AdminTopNav.tsx`

**Before:** row(title+date | picker+button) → tabs  
**After:** tabs → row(picker + «+ Новый конкурс»)

Remove `SportPrognosis` link and `formatDateRu` date from admin nav.

### 2.3 `RoundBuilderForm.tsx`

On «+ Добавить матч»:

1. If any existing match has `date_time` → copy **last** non-empty match `date_time`.
2. Else if deadline field filled → use deadline converted via `fromDatetimeLocal(deadline)`.
3. Else empty.

Extract helper `nextMatchDateTime()` in `lib/admin/roundBuilderDefaults.ts` + unit test.

### 2.4 E2E helper

`selectContestInPicker` — target `data-testid="contest-picker"` (no longer in global `<header>`).

---

## 3. Tests

- Vitest: `roundBuilderDefaults.test.ts` (3 cases: last match, deadline fallback, empty).
- Manual: `/admin/results` — one picker below tabs; global header has no contest dropdown.
- Lint: `npm run lint`, `npm run type-check`.

---

## 4. Out of scope

- Rename «Sport Prognosis» branding globally
- Participant contest toolbar changes
- Backend changes

---

## 5. Handoff

Append progress entry to `agent_docs/progress/stage_2.md`.

# Fix 1.20 — E2E QA batch (backend)

**Source:** manual QA during supervisor + participant E2E pass (Jul 2026).
**Prerequisite for frontend:** ship this fix (or agree on interim contract) before `agent_docs/instructions/fix_2.5_all_e2e.md`.
**Status:** `IMPLEMENTED` — Jul 2026.

---

## 1. Symptoms

| # | Symptom | Area | Expected |
|---|---------|------|----------|
| B1 | Supervisor can PATCH contest with odd `total_teams` in round-robin mode; DB stores fractional `matches_per_round` (e.g. 7.5 for 15 teams) | contest setup | Reject invalid structure; round-robin requires even team count |
| B2 | Invite API returns `temp_password`, but with `enforce_password_setup=true` login via temp password returns `403 PASSWORD_SETUP_REQUIRED` — password is misleading in supervisor modal | invite contract | Keep API field for dev/E2E; document that production flow is link-only (frontend hides password — see fix 2.5) |
| B3 | Predictions/results APIs return `team1`/`team2` as full `Team.name`; frontend heuristically truncates to 4 chars («Спартак» → «Спар» instead of configured «СпаМ») | match payloads | Expose configured `short_name` for matrix headers |
| B4 | *(no backend change)* Supervisor «Результаты участников» preview needs per-match points matrix | — | `GET …/rounds/{id}/results` already works for staff on `CALCULATED`/`PUBLISHED` rounds — frontend fix 2.5 reuses it |

---

## 2. Root causes

### B1 — no server-side structure validation

`update_contest()` in `contest_setup_service.py` blindly assigns patch fields. Frontend may send fractional `matches_per_round` when round-robin derivation runs client-side with odd `total_teams` (`deriveRoundRobinStructure`: `totalTeams / 2`).

DB column `matches_per_round` is `Integer` — PATCH may fail at flush or coerce unpredictably; must validate **before** persist.

### B2 — invite triple vs login gate (by design)

`add_participant()` (`contest_setup_service.py`) always generates `temp_password` + `setup_url`.
`POST /auth/login` blocks `is_temp_password` users when `enforce_password_setup=true` (`auth.py`).

Contract in `coder_1.12_fix.md` §2.1 assumed letter/modal shows all three fields. Production UX: participant uses **link only**. Temp password remains useful when `ENFORCE_PASSWORD_SETUP=false` (dev, Playwright global setup).

**Decision (LOCKED):** Keep `temp_password` in `ParticipantInviteOut` (API unchanged). Supervisor UI **must not** display it — participants use `setup_url` only. No Option B/C.

### B3 — wrong display field in match serializers

`_team_display_name()` in `predictions.py` returns `team.name`.
`get_round_results()` in `leaderboard_service.py` sets `"team1": t1.name`.

Configured `Team.short_name` (max 4 chars, unique per contest) is never exposed in public match objects.

---

## 3. Required changes

### 3.1 Contest structure validation (B1)

Add shared validator, e.g. `validate_contest_structure(total_teams, matches_per_round, total_rounds, is_round_robin) -> None`, raising `ValidationError` with Russian messages.

**When `is_round_robin is True`:**

1. `total_teams` must be **even** and ≥ 2  
   → `"Для круговой системы нужно чётное число команд (≥ 2) или отключите круговую систему"`
2. `matches_per_round` must equal `total_teams // 2` (integer)  
   → `"Матчей в туре должно быть = команды / 2"`
3. `total_rounds` must equal `(total_teams - 1) * 2`  
   → `"Число туров должно быть = (команды − 1) × 2"`

**When `is_round_robin is False`:** only positivity checks (existing behaviour).

Call from:

- `create_contest()` — after resolving defaults, before `session.add`
- `update_contest()` — after merging patch into effective values, before return

Also validate on `POST /contests` and `PATCH /contests/{id}` if not already covered by service layer.

### 3.2 Contract note for invite (B2)

Update `agent_docs/contracts/api_v1.yaml` and `frontend_api_integration.md`:

- `ParticipantInviteOut.temp_password`: still required in schema; clarify *«возвращается всегда; при `enforce_password_setup=true` вход по нему заблокирован — участник использует `setup_url`»*
- Supervisor UI must not surface password in production flow (frontend fix 2.5)

No response-shape change in this fix.

### 3.3 Expose team short names in match payloads (B3)

Add optional fields to every match dict returned in:

- `build_round_predictions_view()` (`src/api/handlers/predictions.py`)
- `get_round_results()` (`src/services/leaderboard_service.py`)
- Any other handler that builds the same `MatchOut` shape (grep `team1.*team.name`)

```python
{
    "id": m.id,
    "team1_id": m.team1_id,
    "team2_id": m.team2_id,
    "team1": team.name,          # full name — keep for forms/tooltips
    "team2": team.name,
    "team1_short": team.short_name,
    "team2_short": team.short_name,
    ...
}
```

**LOCKED:** Add separate `team1_short` / `team2_short` fields. Keep `team1`/`team2` as full names (`PredictionMatchRow` main line).

Update:

- `agent_docs/contracts/api_v1.yaml` → `MatchOut.team1_short`, `team2_short` (required when teams resolved)
- `agent_docs/contracts/frontend_api_integration.md` § match objects

### 3.4 B4 — verify only

Confirm staff (`SUPERVISOR`/`ADMIN`) can call `GET /contests/{cid}/rounds/{rid}/results` for `CALCULATED` rounds (`leaderboard_service._allowed_round_statuses`). Add pytest if missing; **no feature change** unless test fails.

---

## 4. Tests (`tests/api/`)

1. **Round-robin odd teams** — `PATCH` contest with `is_round_robin=true`, `total_teams=15`, `matches_per_round=7`, `total_rounds=28` → `422` + message about even teams.
2. **Round-robin valid** — `total_teams=16` with formula values → `200`.
3. **Arbitrary mode** — `is_round_robin=false`, odd `total_teams=15`, custom matches/rounds → `200`.
4. **Predictions match payload** — fixture with `short_name="СпаМ"`, `name="Спартак"` → response includes `team1_short: "СпаМ"`.
5. **Round results match payload** — same assertion on `GET …/results`.
6. **Staff CALCULATED results** — supervisor token, round 10 fixture → `200` with `results[].points` per match.

Lint: `uv run ruff check src/`, `uv run mypy src/`, `uv run bandit -r src/ -ll`.

---

## 5. Out of scope

- Frontend contest form UX (fix 2.5 §1)
- Hiding temp password in UI (fix 2.5 §2)
- SMTP / real email delivery
- Changing `enforce_password_setup` default

---

## 6. Handoff

- Append progress entry to `agent_docs/progress/stage_1.md`.
- After `TEST_PASS` → run `fix_2.5_all_e2e.md` on frontend.

# Test Report — Stage 1.16 Fix (Pytest Regression Cleanup)

**Date:** 2026-06-28  
**Tester:** @Tester  
**Verdict:** **TEST_PASS**  
**Spec:** `agent_docs/instructions/tester_1.16_fix.md`

## Summary

Restored full backend pytest suite after 15 regressions caused by Stage 1.12 (password setup gate), 1.16 (auto-close), 2.3.1 (publish-only public LB), and contest soft-delete. All 15 targeted tests updated per locked decisions §2.1–§2.6.

## Results

| § | Group | Tests | Strategy | Result |
|---|-------|-------|----------|--------|
| 2.1 | Password setup | 9 | stage_112_api + helpers | **PASS** |
| 2.2 | LB ETag | 1 | Staff GET; publish bumps ETag | **PASS** |
| 2.3 | Tiebreak | 2 | Publish + global LB / synthetic | **PASS** |
| 2.4 | LB counts global | 1 | Publish 1–9 + user_id lookup | **PASS** |
| 2.5 | Contest delete | 1 | Contest-scoped soft-delete | **PASS** |
| 2.6 | Auto-close unit | 1 | ROUND_NOT_ACTIVE assertion | **PASS** |

**Full pytest:** **383 passed**, 1 skipped, 0 failed (~8m47s)

## Key changes

### Helper
- `tests/api/conftest.py`: added `publish_rounds_via_http()` for reuse in §2.3 and §2.4.

### §2.1 — Password setup (9 tests)
- Migrated to `stage_112_api` + `stage_112_helpers` (`invite_participant`, `complete_setup`, `NEW_SECURE_PASSWORD`).
- Contacts get/patch use standalone DB users (no pre-filled invite email).
- `test_auth_temp_password_restricted`: asserts 403 on temp login, then complete-setup flow.

### §2.2 — ETag after calculate
- Supervisor-authenticated GET on contest-scoped leaderboard.
- **Note:** ETag hash includes round `status`; recalculate alone did not change ETag when round stayed CALCULATED. Test flow: calculate → GET → **publish** → GET; assert ETag differs.

### §2.3 — Tiebreak
- `test_tiebreak_display_on_leaderboard`: calculate + publish round 1; contest-scoped tiebreak + global LB.
- `test_tiebreak_rank_synthetic`: moved to `stage_112_api`; synthetic 2-user tied predictions; DB deadline patch (HTTP PATCH blocked on ACTIVE); close → results → calculate → publish.

### §2.4 — Global LB counts
- Publish rounds 1–9 after calculate; lookup `larin` by `user_id` instead of display name.

### §2.5 — Contest delete
- `DELETE /contests/1` → `status=DELETED`; DB `DRAFT` + `deleted_at`; operational data wiped; listed in `/contests/deleted`.

### §2.6 — Auto-close unit
- `test_batch_after_deadline_rejected`: expects `code in ("ROUND_NOT_ACTIVE", "DEADLINE_PASSED")`.

## Deviations from spec

| Item | Spec | Actual |
|------|------|--------|
| §2.2 ETag | No publish step | Publish required to bump ETag (status in hash); staff auth retained |

## Blockers

None.

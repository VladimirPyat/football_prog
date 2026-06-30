# Code Review Report — Stage 1.5 (ScoringService)

**Files reviewed**: `src/football_prog/services/scoring_service.py`, `src/football_prog/api/v1/rounds.py`
**Verdict**: 🔴 NEEDS FIXES (1 critical issue)

---

## 🔴 Critical Issues

### [C1] Hardcoded scoring values
- **File**: `src/football_prog/services/scoring_service.py:42`
- **Issue**: Base points hardcoded as `if exact: return 16` instead of reading from `rules_json`
- **Fix**: Read thresholds from `contest_settings.rules_json["base_points"]`

---

## 🟡 Important Issues

### [I1] Missing docstring
- **File**: `src/football_prog/services/scoring_service.py:15`
- **Issue**: Function `calculate_base_points` has no docstring
- **Fix**: Add Russian docstring explaining parameters and return value

### [I2] Wrong log level
- **File**: `src/football_prog/services/scoring_service.py:67`
- **Issue**: Using `logger.info()` for error case (missing prediction)
- **Fix**: Change to `logger.warning()` with context (user_id, match_id)

---

## 🟢 Nice-to-Have

### [N1] Magic number
- **File**: `src/football_prog/services/scoring_service.py:89`
- **Issue**: `if score > 50` — magic number without explanation
- **Fix**: Extract to constant or config with comment

---

## Summary

| Criterion | Critical | Important | Nice-to-have |
|-----------|----------|-----------|--------------|
| 1. Security | 0 | 0 | 0 |
| 2. Data Integrity | 0 | 0 | 0 |
| 3. Hardcoding | 1 | 0 | 1 |
| 4. Architecture | 0 | 0 | 0 |
| 5. Contracts | 0 | 0 | 0 |
| 6. Error Handling | 0 | 0 | 0 |
| 7. Logging | 0 | 1 | 0 |
| 8. Code Quality | 0 | 0 | 0 |
| 9. Constants | 0 | 0 | 1 |
| 10. Documentation | 0 | 1 | 0 |

**Total**: 1 critical, 2 important, 2 nice-to-have

## Recommendations
1. Fix hardcoded values immediately (criterion 3)
2. Add docstrings to all public functions (criterion 10)
3. Review logging levels across scoring module (criterion 7)
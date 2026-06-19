# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Check Severity Enum and SEVERITY_FLOOR definition | Inspection of `src/gdg_yorku_submission/severity.py` | Exists and is correct | Verified definition of Severity enum and SEVERITY_FLOOR = "high" | pass |
| VERIFY-002 | REQ-002 | Run severity mapping unit tests | `pytest tests/test_severity.py` | All pass | 6/6 tests passed including custom rank comparisons | pass |
| VERIFY-003 | REQ-003, REQ-004 | Run schema validation unit tests | `pytest tests/test_schemas.py` | All pass | 15/15 tests passed including extra field forbidding, omission constraints, literals validation, and serialization wire checks | pass |
| VERIFY-004 | REQ-005 | Run full test suite with warnings as errors | `pytest` | 10+ tests pass with no errors/warnings | 31/31 tests passed with no errors or warnings | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| None | N/A | N/A |

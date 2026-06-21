# Verification Ledger - Task 14

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Import / compiler integrity | `pytest tests/test_coordinator.py` | pass | 20 passed | pass |
| VERIFY-002 | REQ-002 | No High Omission test | `pytest tests/test_report_validator.py` | pass | passed | pass |
| VERIFY-003 | REQ-003 | Conservation Ledger check | `pytest tests/test_report_validator.py` | pass | passed | pass |
| VERIFY-004 | REQ-004 | Exact Severity Counts test | `pytest tests/test_report_validator.py` | pass | passed | pass |
| VERIFY-005 | REQ-005 | Merge Severity Constraint test | `pytest tests/test_report_validator.py` | pass | passed | pass |
| VERIFY-006 | REQ-006 | Evidence Ref Range Check test | `pytest tests/test_report_validator.py` | pass | passed | pass |
| VERIFY-007 | REQ-007 | Contested K-cap test | `pytest tests/test_report_validator.py` | pass | passed | pass |

## Skipped checks

None.

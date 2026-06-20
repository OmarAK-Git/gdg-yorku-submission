# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Budget lease checks | `pytest tests/test_correctness_agent.py` | pass | pass | pass |
| VERIFY-002 | REQ-002 | Grounded correctness review | `pytest tests/test_correctness_agent.py` | pass | pass | pass |
| VERIFY-003 | REQ-003 | No-spec fallback handling | `pytest tests/test_correctness_agent.py` | pass | pass | pass |
| VERIFY-004 | REQ-004 | Output correctness validation | `pytest tests/test_correctness_agent.py` | pass | pass | pass |
| VERIFY-005 | REQ-001..4 | Full test suite check | `pytest` | pass | pass (200 tests passed) | pass |
| VERIFY-006 | REQ-001 | Budget exhaustion failed status | `pytest tests/test_correctness_agent.py -k test_budget_exhausted_integration_status` | pass | pass | pass |
| VERIFY-007 | REQ-004 | Coordinate translation mapping | `pytest tests/test_correctness_agent.py -k test_coordinate_translation_mapping` | pass | pass | pass |
| VERIFY-008 | REQ-004 | Grounding citation check | `pytest tests/test_correctness_agent.py -k test_grounding_checks_require_spec_cite` | pass | pass | pass |
| VERIFY-009 | REQ-004 | Ordering and lower-bounds | `pytest tests/test_correctness_agent.py -k test_evidence_ref_ordering_and_lower_bound_checks` | pass | pass | pass |
| VERIFY-010 | REQ-001 | Production credentials check | `pytest tests/test_correctness_agent.py -k test_gemini_client_production_loud_failure_when_missing_creds` | pass | pass | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| None | N/A | N/A |

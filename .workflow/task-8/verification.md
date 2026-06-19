# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Nonce generation | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-002 | REQ-002 | Prompt corpus files & redacted check | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-003 | REQ-003 | XML nonced boundaries | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-004 | REQ-004 | Content breakout neutralization | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-005 | REQ-004 | Path injection protection | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-006 | REQ-004 | Nonce unguessability / negative breakout | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-007 | REQ-004 | Line count preservation (R5) | pytest tests/test_evidence_plane.py | pass | pass | complete |
| VERIFY-008 | REQ-004 | Determinism / reproducibility | pytest tests/test_evidence_plane.py | pass | pass | complete |

## Skipped checks
- End-to-end request pipeline verification of the redacted corpus contract (deferred to the integration tests in Task 23).

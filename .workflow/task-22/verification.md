# Verification Ledger - Task 22 Revisions

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-22-01 | REQ-22-R1 | Production HTTP Client Path | `pytest tests/test_blast_radius.py -k test_orbit_client_query_symbol_real_http` | pass | pass | completed |
| VERIFY-22-02 | REQ-22-R2 | Severity Cap below Floor | `pytest tests/test_blast_radius.py -k test_agent_severity_cap` | pass | pass | completed |
| VERIFY-22-03 | REQ-22-R3 | Performance Guards (Deduplication, Cache, Budget) | `pytest tests/test_blast_radius.py -k "test_agent_symbol_count_cap or test_agent_wall_clock_budget_termination"` | pass | pass | completed |
| VERIFY-22-04 | REQ-22-R4 | Redaction Line-Map & out-of-bounds skipping | `pytest tests/test_blast_radius.py -k "test_agent_non_identity_line_map or test_agent_out_of_bounds_skipping"` | pass | pass | completed |
| VERIFY-22-05 | REQ-22-R5 | Invariant & Integration (Merges, Omissions, Claims, Determinism) | `pytest tests/test_blast_radius.py -k "test_blast_coordinator_merge_and_omission or test_agent_determinism"` | pass | pass | completed |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live production Orbit service | No live instance available for tests. | Low. Covered by unit tests mocking requests. |

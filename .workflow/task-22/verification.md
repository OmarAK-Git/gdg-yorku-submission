# Verification Ledger - Task 22 Revisions (Real Graph Integration)

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-22-01 | REQ-22-R1 | Graph Client POST and Parsing | `pytest tests/test_blast_radius.py -k test_client_transport_post` | pass | pass | completed |
| VERIFY-22-02 | REQ-22-R1 | Traversal payload and parsing | `pytest tests/test_blast_radius.py -k test_client_transport_fetch_definitions_and_parse` | pass | pass | completed |
| VERIFY-22-03 | REQ-22-R2 | Happy Path Scan & Mappings | `pytest tests/test_blast_radius.py -k test_agent_happy_path_scan` | pass | pass | completed |
| VERIFY-22-04 | REQ-22-R3 | Severity Cap at MEDIUM | `pytest tests/test_blast_radius.py -k test_severity_cap` | pass | pass | completed |
| VERIFY-22-05 | REQ-22-R4 | Coordinate boundary skipping | `pytest tests/test_blast_radius.py -k test_coordinate_skip` | pass | pass | completed |
| VERIFY-22-06 | REQ-22-R4 | Non-identity line map verbatim coordinates | `pytest tests/test_blast_radius.py -k test_agent_non_identity_line_map_uses_orbit_coords` | pass | pass | completed |
| VERIFY-22-07 | REQ-22-R5 | Failsafes and unconfigured state | `pytest tests/test_blast_radius.py -k test_failsafe_handling` | pass | pass | completed |
| VERIFY-22-08 | REQ-22-R5 | Failsafes for auxiliary fetch failure and unreachable host | `pytest tests/test_blast_radius.py -k "test_failsafe_health_check_failed_unreachable or test_failsafe_auxiliary_fetch_exception"` | pass | pass | completed |
| VERIFY-22-09 | REQ-22-R5 | Coordinator compile conservation | `pytest tests/test_blast_radius.py -k test_compiler_conservation_and_omission` | pass | pass | completed |
| VERIFY-22-10 | REQ-22-R5 | Shuffled input determinism | `pytest tests/test_blast_radius.py -k test_agent_determinism_shuffled_input` | pass | pass | completed |
| VERIFY-22-11 | REQ-22-R5 | Orbit metadata redaction | `pytest tests/test_blast_radius.py -k test_orbit_metadata_redaction` | pass | pass | completed |
| VERIFY-22-12 | REQ-22-R5 | E2E API review route integration | `pytest tests/test_blast_radius.py -k test_api_e2e_integration` | pass | pass | completed |
| VERIFY-22-13 | REQ-22-R6 | Non-overlapping coordinate regression | `pytest tests/test_blast_radius.py -k test_client_non_overlapping_fixtures_uses_calls_coords` | pass | pass | completed |
| VERIFY-22-14 | REQ-22-R7 | Limit & Truncation Warnings | Checked logs in `python scripts/orbit_smoke.py` showing `Definitions query reached the limit of 500 rows and was truncated.` | log warning | log warning | completed |
| VERIFY-22-15 | REQ-22-R8 | BOM Tolerant Parsing | Verified parser executes successfully against payload with/without UTF-8 BOM | pass | pass | completed |
| VERIFY-22-16 | REQ-22-R6 | Transport verification of fetch_calls columns | `pytest tests/test_blast_radius.py -k test_client_transport_fetch_calls_and_parse` | pass | pass | completed |

## Skipped checks

*None.* All checks have been executed and verified (including live connectivity diagnostics).

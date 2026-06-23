# Review - Task 22 Revisions (Real Graph Integration)

## Spec compliance review
- **Real Graph Queries**: Implemented traversal query DSL construction matching `.orbit-captures/q-*.json` (filtering by project path). Asserted post transport payloads and response parsing in `test_client_transport_fetch_definitions_and_parse`.
- **Project Path configured**: Added constructor and environment support for `ORBIT_PROJECT_PATH` to anchor traversals.
- **Severity Cap**: Implemented a load-bearing cap in `agent.py` setting `severity = Severity.MEDIUM` if naturally exceeding `MEDIUM` (due to >=10 dependents or CRITICAL/HIGH vulnerabilities). Verified via `test_severity_cap`.
- **Coordinate skips**: Checked coordinates against `original_line_count` and normalized paths against the in-memory corpus. Verified lower bound, upper bound, inverted coordinates, and missing file skipping in `test_coordinate_skip`.
- **Orbit coordinates verbatim check**: Verified that coordinates returned by Orbit represent original-repo coordinates and are not double-mapped/shifted by `map_line`. Asserted in `test_agent_non_identity_line_map_uses_orbit_coords`.
- **Redaction Safety**: Routed all Orbit-sourced metadata (FQNs, paths, MR titles, vulnerability descriptions, pipelines) through the run's `RedactionContext`. Verified in `test_orbit_metadata_redaction`.
- **Failsafes**: Ensured that unreachable hosts or auxiliary query failures degrade to partial/empty status. Verified in `test_failsafe_handling`, `test_failsafe_health_check_failed_unreachable`, and `test_failsafe_auxiliary_fetch_exception`.
- **Determinism**: Shuffled node/edge results in test mock responses and verified identical provisional ID generation and ordering in `test_agent_determinism_shuffled_input`.
- **Self-Sufficient Calls**: Modified `fetch_calls` to fetch full definition columns (`id`, `name`, `fqn`, `file_path`, `start_line`, `end_line`, `definition_type`) for both `src` and `dst` nodes. This avoids silent drops of targets not present in `definitions` query results. Verified via `test_client_non_overlapping_fixtures_uses_calls_coords`.
- **Raised limits and warning logs**: Increased default query limits to `500` and logged warning logs when limit is hit to handle large repositories without silent truncation.
- **BOM tolerant parsing**: Decoded graph response bytes using `utf-8-sig` to handle files starting with UTF-8 BOM.

## Code quality review
- Cleaned up AST extraction scanning logic and retired old dead `/api/v1/blast-radius` client paths.
- Removed dead vulnerability severity mapping branches in `agent.py` and directly mapped to `MEDIUM` when `num_vulns > 0`.
- The test suite is fast, deterministic, and self-contained.

## Risk review
- **Orbit Metadata leaks**: Fully mitigated by integrating run-specific `RedactionContext` into all fetched strings from Orbit.
- **Slow APIs**: Checked wall-clock timer budget to avoid blocking FastAPI threads.

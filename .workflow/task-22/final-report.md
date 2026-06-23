# Final Report - Task 22 Revisions (Real Graph Integration)

## Summary
The Orbit blast-radius agent has been refactored to utilize the real Orbit Knowledge Graph API directly. The dead `/api/v1/blast-radius` placeholder REST client path and local AST scanning/extraction code have been retired. 

Under the new design:
1. `OrbitClient` performs real Traversal queries based on standard query DSL shapes from `.orbit-captures/q-*.json`.
2. All graph traversals are anchored to the `Project` node filtered by `ORBIT_PROJECT_PATH`.
3. A connectivity check (`health_check`) executes a cheap Project node traversal probe.
4. `run_blast_radius_review(orch)` fetches Definitions, Calls, Imports, Vulnerabilities, Pipelines, and Merge Requests, maps them to `ImpactGraph`, and evaluates blast summaries.
5. Invariants are strictly checked:
   - Severity is scaled by blast size, clamped strictly at `MEDIUM` (below the high severity threshold floor) to allow the coordinator to prune findings.
   - Files are normalized (forward-slash, case-insensitive) and resolved against the in-memory corpus.
   - Coordinates are checked against `original_line_count`, and out-of-bound coordinates or missing files are skipped.
   - Coordinates use original coordinates verbatim without `map_line` shifts, verified via a non-identity redaction map test.
   - Stable deterministic provisional IDs are computed via sha256.
   - All external Orbit-derived strings (vulnerability descriptions, pipeline URLs, MR titles, FQNs, import paths) are explicitly redacted using the run-specific `RedactionContext`.
   - Failed queries gracefully degrade, failing safe to `"disabled"` (unconfigured) or `"unavailable"` (unreachable).
   - Omitted low-severity blast findings flow through coordinator compilation conforming to conservation rules.

### Round 3 Improvements
- **Self-Sufficient Calls Coordinates**: The `fetch_calls` query now requests `id`, `name`, `fqn`, `file_path`, `start_line`, `end_line`, and `definition_type` for both `src` and `dst` nodes, ensuring that target nodes contain coordinates even if they are not returned in the separate `fetch_definitions` query result (e.g. due to pagination/truncation).
- **Raised Limits & Truncation Warnings**: The default limit for all queries has been increased to `500`. The client checks if `row_count >= limit` and logs a warning when a result has been truncated. Specifying exact Definition columns in `fetch_definitions` prevents server-side query payload complexity limits.
- **BOM Tolerant Parsing**: Response bodies are decoded using `utf-8-sig` in `execute_query` (`orbit_graph.py`) to prevent failure if GitLab responses contain a UTF-8 Byte Order Mark (BOM).
- **Product Decision**: We have adopted the recommended decision to keep blast findings advisory: emit `LOW` severity by default for blast findings, elevating to `MEDIUM` only if the dependents count is $\ge 3$. `MEDIUM` is enforced as the deliberate absolute ceiling.
- **Vulnerability severity cosmetics**: Dead critical/high vulnerability severity branches have been simplified to directly set `severity = Severity.MEDIUM` if vulnerabilities are present.

All 333 tests pass successfully, and live execution via `python scripts/orbit_smoke.py` verifies zero silent drops.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-22-R1: Graph API Client | Verified by `test_client_transport_post` and `test_client_transport_fetch_definitions_and_parse` checking POST parameters, bearer headers, DSL body format (no BOM), and result envelope parsing. |
| REQ-22-R2: Project Anchor | Verified by `test_client_transport_post` and fetcher tests ensuring queries filter by `ORBIT_PROJECT_PATH`. |
| REQ-22-R3: Severity Cap | Verified by `test_severity_cap` ensuring large blast radius findings and critical vulnerabilities cap at `MEDIUM`. Blast findings are kept advisory (LOW if < 3 dependents). |
| REQ-22-R4: Coordinate Validity | Verified by `test_coordinate_skip` and `test_agent_non_identity_line_map_uses_orbit_coords`. |
| REQ-22-R5: Invariants & Safety | Verified by `test_failsafe_handling`, `test_failsafe_health_check_failed_unreachable`, `test_failsafe_auxiliary_fetch_exception`, `test_orbit_metadata_redaction`, `test_compiler_conservation_and_omission`, `test_agent_determinism_shuffled_input`, and `test_api_e2e_integration`. |
| REQ-22-R6: Self-Sufficient Calls | Verified by `test_client_transport_fetch_calls_and_parse` and `test_client_non_overlapping_fixtures_uses_calls_coords` ensuring that query payloads explicitly request coordinates columns and target coordinates are successfully extracted from `fetch_calls` nodes when absent from `fetch_definitions`. |
| REQ-22-R7: Limit & Truncation Warnings | Verified in tests and live logs. Default limits raised to `500` for definitions, calls, and imports. |
| REQ-22-R8: BOM Tolerant Parsing | Verified by parsing payloads correctly with or without UTF-8 BOM signatures in `execute_query`. |

## Files changed
- [orbit_client.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/blast_radius/orbit_client.py) - client query limits, columns, and truncation warning logs
- [orbit_graph.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/blast_radius/orbit_graph.py) - BOM-tolerant response decoding (`utf-8-sig`)
- [agent.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/blast_radius/agent.py) - vulnerability severity branch cleanup
- [orbit_smoke.py](file:///c:/Users/oalan/gdg-yorku-submission/scripts/orbit_smoke.py) - coordinate join diagnostic update
- [test_blast_radius.py](file:///c:/Users/oalan/gdg-yorku-submission/tests/test_blast_radius.py) - non-overlapping coordinate regression test and transport fetch_calls test

## Verification performed
- Full test suite run using `pytest`: 333 tests passed, 0 failures.
- Live integration check run using `python scripts/orbit_smoke.py` outputting `SILENTLY DROPPED: 0 (0%)`.

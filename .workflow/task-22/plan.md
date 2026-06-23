# Workflow Plan - Task 22 Revisions (Orbit Graph API Integration)

## Goal
Implement the real Orbit Knowledge Graph integration into the blast-radius agent, deprecate the dead `/api/v1/blast-radius` placeholder endpoint and AST-scanning code, and verify it against critical invariants. Address Round 3 requirements for live coordinate-joins, pagination/limits, utf-8-sig response parsing, and severity cosmetics.

## Scope

### In scope
- **Real Graph Queries**: Update `OrbitClient` to construct real traversal queries conforming to v2.9.1 Graph Query DSL.
- **Support Project Path**: Allow configuring `ORBIT_PROJECT_PATH` to anchor all queries in the Project node.
- **Offline / Fake mode**: Allow injecting `OrbitQueryResult` objects into `OrbitClient` keyed by query kind / entity to support tests.
- **Cheap Health Probe**: Add a connectivity check using a Project traversal query.
- **Blast-Radius Invariants**:
  - Scale severity by blast size, clamped strictly at `MEDIUM` (below the high severity threshold floor) to allow the coordinator to prune findings.
  - Keep blast findings advisory: emit `LOW` unless dependents $\ge 3$ (stated threshold), and document `MEDIUM` as the deliberate ceiling.
  - Validate coordinates against corpus files, skipping out-of-bounds line mappings or missing files.
  - Return `"disabled"` when configuration is absent, and `"unavailable"` when health checks or core queries fail.
  - Generate stable deterministic provisional IDs.
  - Preserve LLM compiler conservation properties.
  - Maintain the prompt/data safety trust boundary by redacting all metadata derived from Orbit.
- **Coordinate Join Fix**: Select coord-bearing columns for `src`/`dst` in `fetch_calls` query to avoid silent drops of targets missing in `fetch_definitions`.
- **Query limits**: Raise limits to `500` to prevent truncation of larger repos and log a warning if row counts hit the limit.
- **UTF-8 BOM**: Decode responses with `utf-8-sig` in `orbit_graph.py`.
- **Vulnerability severity clamp cleanup**: Clean up dead vuln severity branches.
- **Thorough Test Suite**: Verify via comprehensive unit tests including a non-overlapping definitions/calls regression test.

### Out of scope
- Live connection to actual GitLab instances during automated CI testing (use fake/mock responses).

## Requirements

| ID | Requirement | Description |
|---|---|---|
| REQ-22-R1 | Real Graph API | Implement POST `/query` transport and parse standard Traversal result envelope with nodes & edges. |
| REQ-22-R2 | Project Anchor | Anchor all traversals in the `Project` node filtered by `ORBIT_PROJECT_PATH`. |
| REQ-22-R3 | Invariant Capping | Cap blast finding severities at `MEDIUM` max. Keep blast findings advisory (LOW if < 3 dependents). |
| REQ-22-R4 | Coordinate Validity | Skip findings referencing missing files or line bounds exceeding `original_line_count`. |
| REQ-22-R5 | Invariant & Integration | Ensure determinism, conservation, failsafe, metadata redaction, and E2E integration stability. |
| REQ-22-R6 | Self-Sufficient Calls | Fetch coordinates directly in `fetch_calls` to avoid dropped targets on non-overlapping results. |
| REQ-22-R7 | Limit & Truncation Warnings | Raise query limits to 500 and log warnings on truncation limits. |
| REQ-22-R8 | BOM Tolerant Parsing | Decode query response payloads using `utf-8-sig` in execute_query. |

## Implementation Plan

| Task | Description | Files affected |
|---|---|---|
| TASK-22-01 | Refactor `orbit_client.py` constructor, health check, queries, and fake lookup | `orbit_client.py` |
| TASK-22-02 | Rewrite `agent.py` to use graph fetchers, compute blast summaries, and validate boundaries | `agent.py` |
| TASK-22-03 | Update `__init__.py` to clean up exports | `__init__.py` |
| TASK-22-04 | Implement test suite covering transport, happy paths, coordinate skipping, budget, failsafes, determinism, and compilation conservation | `test_blast_radius.py` |
| TASK-22-05 | Add Non-Overlapping coordinate regression test & update limits and warning checks | `test_blast_radius.py` |
| TASK-22-06 | Update smoke test script diagnostic logic | `orbit_smoke.py` |

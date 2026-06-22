# Workflow Plan - Task 22 Revisions (Orbit Blast-Radius)

## Goal
Refine the optional Orbit blast-radius specialist/agent and its test suite to fully cover production code paths, handle performance constraints, align with the redaction line-map contract, fix claim/duplicate symbol edge cases, and add negative/violating invariant tests.

## Scope

### In scope
- **Production HTTP Test Coverage**: Test the production HTTP path of `OrbitClient` querying the live `/api/v1/blast-radius` endpoint.
- **Severity Cap**: Cap blast-radius finding severities at `MEDIUM` so they do not cause floor-level flooding and remain prunable by the coordinator.
- **Performance Guards**: Deduplicate symbols across files, implement an in-memory cache, cap the number of queried symbols, and introduce a run-level wall-clock query budget.
- **Redaction Line-Map Contract**: Map coordinates back to the original file system using `cf.map_line()` and enforce coordinate/existence bounds checks.
- **Merge & Omission Verification**: Test coordinator merges and omissions of blast-radius findings.
- **Claim & Duplicate Improvements**: Fix trailing colons on dependencies-only claims, and prefer the most-qualified symbol to avoid duplicate findings per import line.
- **Robust Invariant Testing**: Add negative tests (violating invariants, out-of-bounds mapping, and determinism check).

### Out of scope
- Integration with a live, external network GitLab instance (mocking via `urllib.request.urlopen` is used).

## Requirements

| ID | Requirement | Description |
|---|---|---|
| REQ-22-R1 | Production Path Coverage | Mock-test the real HTTP branch in `OrbitClient.query_symbol` asserting headers and mapping. |
| REQ-22-R2 | Severity Cap | Cap blast-radius finding severities at `MEDIUM` max. |
| REQ-22-R3 | Performance Guards | Implement deduplication, caching, a symbol count cap (max 20), and a run-level wall-clock budget (max 2.0s). |
| REQ-22-R4 | Redaction Line-Map | Map coordinates to the original file coordinate system via `cf.map_line()` and skip out-of-bounds symbols. |
| REQ-22-R5 | Invariant & Integration Verification | Verify coordinator merges, omissions, claim dependencies, duplicate-symbol mitigation, and determinism. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-22-01 | REQ-22-R1 | Test asserts correct HTTP URL, headers, and parsed payload mapping for production `query_symbol`. |
| AC-22-02 | REQ-22-R2 | Assert that blast-radius findings never exceed `MEDIUM` severity. |
| AC-22-03 | REQ-22-R3 | Verify that total query time is bounded, duplicate symbol queries are cached, and query count is capped. |
| AC-22-04 | REQ-22-R4 | Verify that a non-identity redaction map correctly shifts coordinates and out-of-bounds entries are skipped. |
| AC-22-05 | REQ-22-R5 | Assert merges, omissions, dependencies in claims, duplicate symbols filtered per-line, and anchor determinism. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-22-01 | Add `urllib.parse` import and real HTTP path test | `orbit_client.py`, `test_blast_radius.py` | pending |
| TASK-22-02 | Cap severity below floor (max MEDIUM) | `agent.py` | pending |
| TASK-22-03 | Implement symbol deduplication, caching, count cap, and wall-clock budget | `agent.py` | pending |
| TASK-22-04 | Map coordinates via `cf.map_line()` and skip out-of-bounds | `agent.py` | pending |
| TASK-22-05 | Fix claim builder formatting for dependencies & deduplicate symbols per line | `agent.py` | pending |
| TASK-22-06 | Add tests for merge, omission, non-identity map, out-of-bounds skipping, and determinism | `test_blast_radius.py` | pending |

# Workflow Plan - Task 4: FastAPI Walking Skeleton + Orchestrator Seam

## Goal
Implement the FastAPI web application skeleton (with the zip upload endpoint) and the Orchestrator seam interface (with both plain-Python in-process and stub ADK implementations) passing identical conformance tests.

## Scope

### In scope
- Define a clear, thin `Orchestrator` abstraction interface in `src/gdg_yorku_submission/orchestrator.py`.
- Implement `InProcessOrchestrator` using plain Python in-memory state.
- Implement `AdkOrchestrator` as a stub conforming to the same interface.
- Implement the FastAPI application in `src/gdg_yorku_submission/app.py` with an upload endpoint that accepts a `.zip` archive, validates it (aborting on invalid input), runs the review process via the orchestrator using stub specialists, and returns a schema-valid `ReviewReport`.
- Write a comprehensive conformance test suite in `tests/test_orchestrator_conformance.py` that verifies both implementations behave identically across all orchestrator state transitions (`start_run`, `write_findings`, `read_state`, `run_specialist`, `finalize_ids`, `compile_report`).
- Write API skeleton unit tests in `tests/test_api_skeleton.py` to verify the upload endpoint with mock ZIPs, checking that ingestion failures abort and that specialist failures write `failed` without aborting the run.

### Out of scope
- Real LLM calls for correctness, security, or coordinator agents (stubbed with mock behavior for this task).
- Real zip extraction/ingestion filters (to be implemented in Task 5). For this task, we will do basic zip format verification.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | **Orchestrator Interface**: Define the abstract base interface with methods: `start_run`, `write_findings`, `read_state`, `run_specialist`, `finalize_ids`, and `compile_report`. |
| REQ-002 | **In-Process Implementation**: Implement `InProcessOrchestrator` using in-memory state. |
| REQ-003 | **Stub ADK Implementation**: Implement `AdkOrchestrator` mimicking the ADK workflow and passing the same conformance tests. |
| REQ-004 | **State Transitions & Error Isolation**: Specialists run inside isolated try/except blocks in `run_specialist`. Specialist errors mark status as `failed` but do not abort the overall run. Ingestion failures abort. |
| REQ-005 | **ID Finalization in Orchestrator**: Call `finalize_finding_ids` during `finalize_ids` and update perspective status findings to use finalized IDs. |
| REQ-006 | **FastAPI Upload Endpoint**: Expose a POST upload endpoint that accepts zip files and returns a compiled schema-valid `ReviewReport`. |
| REQ-007 | **Conformance & API Tests**: Write tests ensuring that the two orchestrators behave identically and the API behaves correctly under successes and failures. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 / REQ-002 / REQ-003 | Both `InProcessOrchestrator` and `AdkOrchestrator` classes implement the `Orchestrator` interface. |
| AC-002 | REQ-004 | Calling `run_specialist` with a function that raises an exception records a `failed` status for that perspective but does not crash the orchestrator. |
| AC-003 | REQ-005 | Finalized IDs are correctly propagated to both the report findings list and the perspective statuses. |
| AC-004 | REQ-006 | FastAPI upload endpoint returns a valid `ReviewReport` instance matching the schemas defined in `schemas.py`. |
| AC-005 | REQ-007 | `pytest tests/test_orchestrator_conformance.py` and `pytest tests/test_api_skeleton.py` pass. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Create and implement the `Orchestrator` interface and its two implementations. | `src/gdg_yorku_submission/orchestrator.py`, `src/gdg_yorku_submission/orchestration/__init__.py` | pending |
| TASK-002 | Write the conformance tests for the two orchestrators. | `tests/test_orchestrator_conformance.py` | pending |
| TASK-003 | Implement the FastAPI skeleton app with the zip upload endpoint. | `src/gdg_yorku_submission/app.py` | pending |
| TASK-004 | Write API skeleton tests for upload, stub execution, failure handling. | `tests/test_api_skeleton.py` | pending |
| TASK-005 | Run all tests and verify conformance. | - | pending |

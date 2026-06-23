# Workflow Plan - Task 23: End-to-End Tests

## Goal
Implement comprehensive end-to-end integration tests to verify the complete review pipeline, including all ingestion stages, specialist execution, LLM-based coordinator compilation, secret scanning and redaction invariants, and robust fallback to deterministic terminal reports.

## Scope

### In scope
- Creation of `tests/test_e2e_integration.py` containing:
  - Full end-to-end integration tests using `FastAPI`'s `TestClient` and direct `Orchestrator` execution.
  - Tests covering both `InProcessOrchestrator` and `AdkOrchestrator`.
  - Assertions validating the complete flow: zip extraction -> secret gate preflight -> corpus exposure model categorization -> correctness/security/blast-radius specialist executions -> coordinator compilation -> validator validation checks -> final response.
  - Verification that prompt-exposed secrets are promoted to `HIGH` severity findings and tracked via the `AccountingLedger`.
  - Verification of strict secret redaction invariants: ensuring raw secrets never appear in the generated prompt context, the serialized JSON report, validator warnings, or logs.
  - Verification of fallback paths: validating that `compile_report` falls back to `compile_terminal_report` on coordinator failure (malformed JSON, coordinator call error) or coordinator validator invariant rejection (e.g. omitting a high-severity finding).
  - Validation of coordinator validator coordinates check: ensuring out-of-bounds `evidence_ref` or invalid files are appropriately identified and rejected/stripped.

### Out of scope
- Real LLM calls (these are covered in Task 24 - Real-LLM Smoke Script). We will use fake/mock Gemini clients as per `tests/conftest.py` setup.
- Modifying core application files (unless we discover bugs/defects during test implementation).

## Requirements

| ID | Requirement |
|---|---|
| REQ-23-R1 | **Full E2E Integration Run**: Verify zip ingestion, specialist execution (correctness, security, blast radius), coordination, validation, and final report structure. |
| REQ-23-R2 | **Secret Redaction Invariants**: Ensure raw secrets are redacted at the corpus layer, prompt layer, and final output report boundary (including warnings). |
| REQ-23-R3 | **Fallback Guarantee**: Ensure the compiler falls back to a zero-LLM deterministic terminal report on coordinator crash/invalid output or validation violation. |
| REQ-23-R4 | **Coordinate Validity**: Ensure invalid/out-of-bounds coordinates are either stripped by fallback logic or cause validation rejection on the coordinated path. |
| REQ-23-R5 | **Offline Guarantee**: Assert that the suite runs in a completely isolated offline mode, verifying that `use_fake` is enabled on the client and no live API calls are attempted. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-23-01 | REQ-23-R1 | End-to-end HTTP `/review` test client run succeeds with a Pydantic-validated `ReviewReport` containing expected findings, ledger entries, and status structures. |
| AC-23-02 | REQ-23-R2 | Test validates that raw credentials (Google API keys, DB passwords, etc.) are absent from final JSON report (including `validator_warnings`) and prompt text, and that correct salted fingerprints and placeholders are present. |
| AC-23-03 | REQ-23-R3 | Mocking a failing coordinator (JSON parse error or invalid schema) causes the orchestrator to fall back to a terminal report with `compilation_mode == "terminal_fallback"`. |
| AC-23-04 | REQ-23-R4 | Mocking a coordinator that attempts to omit a `HIGH` finding or references invalid files/lines causes validator failure and subsequent terminal report fallback. |
| AC-23-05 | REQ-23-R5 | The test suite explicitly asserts that the client's `use_fake` is True and mock responses are utilized rather than calling out to external AI APIs. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Create `.workflow/task-23/` state files and matrices. | `.workflow/task-23/*` | completed |
| TASK-002 | Implement `tests/test_e2e_integration.py` covering E2E runs, secret redaction, offline guarantee, and fallback. | `tests/test_e2e_integration.py` | pending |
| TASK-003 | Run pytest to verify all tests (including the new E2E tests) pass. | None | pending |


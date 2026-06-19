# Workflow Plan - Task 2: Core Schemas + Severity Mapping

## Goal
Implement Pydantic core data schemas for findings and reports, standardise severity values, and build a robust mapping module to convert legacy severities to the new standard enums.

## Scope

### In scope
- Define Pydantic v2 schemas in `src/gdg_yorku_submission/schemas.py`:
  - `Location`
  - `Finding`
  - `ReportFinding` (inherits/extends Finding, includes `recommended_next_action` and `merged_from`)
  - `PerspectiveStatus`
  - `GateStatus`
  - `GateFinding`
  - `AccountingLedger` (with `included`, `merged`, and `omitted` lists)
  - `ReviewReport`
- Implement severity vocabulary mapping in `src/gdg_yorku_submission/severity.py`:
  - Enums for `Severity` (critical, high, medium, low, info) and `FindingStatus` / `PerspectiveStatus`.
  - Mapping: `blocker` -> `critical`, `security-blocker` -> `high`, `major` -> `medium`, `minor` -> `low`, `observational` / `hygiene` -> `info`.
  - Case-insensitive parsing and normalization of input string severities.
  - Define reporting floor as a constant: `SEVERITY_FLOOR = Severity.HIGH` (value = `high`).
- Implement unit tests under `tests/test_schemas.py` and `tests/test_severity.py`.

### Out of scope
- Orchestration ID-finalization execution logic (deferred to Task 3/4).
- Actually executing zip extraction (deferred to Task 5).
- Secret scanner implementation (deferred to Task 7).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Standardised Severity Enums & Floor: Define `Severity` enum and a global constant `SEVERITY_FLOOR` set to `high`. |
| REQ-002 | Severity Mapping: Map legacy values (blocker -> critical, security-blocker -> high, major -> medium, minor -> low, observational/hygiene -> info) case-insensitively and handle parsing edge cases. |
| REQ-003 | Pydantic Finding Schemas: Define `Location`, `Finding`, `ReportFinding`, `GateFinding` models with strict validation. |
| REQ-004 | Pydantic Report & Ledger Schemas: Define `PerspectiveStatus`, `GateStatus`, `AccountingLedger`, and `ReviewReport` models. |
| REQ-005 | Test Coverage: Implement comprehensive unit tests for both schemas and severity mapping. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `Severity` is an enum with values: critical, high, medium, low, info. `SEVERITY_FLOOR` is set to `high` and defined in a single, central place. |
| AC-002 | REQ-002 | Legacy severity mapping parses blocker, security-blocker, major, minor, observational, hygiene properly. Unrecognized values raise a ValueError. |
| AC-003 | REQ-003 | `Finding` requires `id`, `source_agent`, `perspective`, `severity`, `location`, `claim`, `evidence_ref`, `status`. `ReportFinding` inherits/extends `Finding` and adds `recommended_next_action` (optional str) and `merged_from` (list of strs). |
| AC-004 | REQ-004 | `ReviewReport` validates successfully against all required fields specified in `spec.md`, including `accounting_ledger` and `gate_status`. |
| AC-005 | REQ-005 | `pytest tests/test_schemas.py` and `pytest tests/test_severity.py` pass. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Implement `Severity` enum, `SEVERITY_FLOOR`, and mapping functions. | `src/gdg_yorku_submission/severity.py` | pending |
| TASK-002 | Define all Pydantic models for findings, reports, and ledger. | `src/gdg_yorku_submission/schemas.py` | pending |
| TASK-003 | Add unit tests for severity mapping. | `tests/test_severity.py` | pending |
| TASK-004 | Add unit tests for Pydantic models. | `tests/test_schemas.py` | pending |
| TASK-005 | Run tests and verify coverage/lint errors. | - | pending |

# Workflow Plan - Task 13

## Goal
Implement the coordinator agent using Gemini to group and merge findings within the same perspective and source agent, outputing a consolidated report. Integrate a deterministic validator and a terminal report fallback for reliability.

## Scope

### In scope
- Create a coordinator module `src/gdg_yorku_submission/coordinator/compiler.py`.
- Define Pydantic models for the coordinator's Gemini input/output schemas.
- Implement the coordinator agent logic to compile and consolidate findings.
- Implement the deterministic validator logic to check report/finding conservation invariants, severity max-rules, perspective/source isolation, and coordinate range limits.
- Integrate the coordinator compilation and validator into `Orchestrator.compile_report()` (in `src/gdg_yorku_submission/orchestrator.py`).
- Implement the deterministic terminal report fallback on coordinator failure or validator rejection.
- Write unit and integration tests in `tests/test_coordinator.py`.

### Out of scope
- Implementing the optional Blast-radius agent (Task 6 details, or Day 7 task).
- Implementing full frontend rendering logic or CLI demo hooks (Tasks 17, 18).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | **Coordinator Agent**: Implement a schema-locked Gemini client wrapper to consolidate, group, and merge input findings, providing recommended next actions. |
| REQ-002 | **Merge Constraints**: Coordinator merges must be restricted to the same perspective and same source agent. Merged findings must carry `merged_from` containing all constituent IDs, and have severity equal to the max of constituents. |
| REQ-003 | **Deterministic Validator**: Validate report invariants: schema validity, stable-ID attribution, conservation accounting (Included U Merged U Omitted U Contested = All Inputs), high/critical non-omission, no severity downgrade on merge, no unknown IDs, and evidence-coordinate existence. |
| REQ-004 | **Terminal Report Fallback**: On retry exhaustion, budget exhaustion, or coordinator error/timeout, emit a deterministic terminal report with zero LLM cost, where every input is included verbatim and omissions/merges are empty. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Coordinator outputs a structured JSON response containing consolidated findings with recommended next actions and merged_from populated. |
| AC-002 | REQ-002 | Merged findings have the correct severity (max of constituents) and location (derived from constituent coordinates). Cross-perspective/cross-agent merges are disallowed. |
| AC-003 | REQ-003 | The validator rejects any compiled report that omits a high/critical finding, introduces an unknown ID, downgrades severity, or has out-of-bounds coordinates. |
| AC-004 | REQ-004 | On validator rejection, the compiler attempts regeneration up to R=2 times. If still invalid, or on LLM error/budget exhaustion, the orchestrator successfully returns a valid deterministic terminal report. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Define schemas and prompt for the Coordinator Compiler | `src/gdg_yorku_submission/coordinator/compiler.py` | pending |
| TASK-002 | Implement the Coordinator compiler agent and deterministic validator | `src/gdg_yorku_submission/coordinator/compiler.py` | pending |
| TASK-003 | Integrate the Coordinator compilation flow in Orchestrator `compile_report()` | `src/gdg_yorku_submission/orchestrator.py` | pending |
| TASK-004 | Implement the deterministic terminal report fallback generator | `src/gdg_yorku_submission/orchestrator.py` or `src/gdg_yorku_submission/coordinator/compiler.py` | pending |
| TASK-005 | Write comprehensive unit and integration tests | `tests/test_coordinator.py` | pending |

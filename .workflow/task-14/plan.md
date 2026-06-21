# Workflow Plan - Task 14

## Goal
Implement and refine the report validator logic in `src/gdg_yorku_submission/coordinator/validator.py` to enforce deterministic report invariants (conservation accounting, high/critical non-omission, exact severity matching, coordinate boundary checks, and contested K-cap), and verify it with comprehensive unit tests in `tests/test_report_validator.py`.

## Scope

### In scope
- Create `src/gdg_yorku_submission/coordinator/validator.py` containing:
  - `parse_evidence_ref` helper function.
  - Refined `validate_report_invariants()` enforcing all required invariants.
- Update `src/gdg_yorku_submission/coordinator/__init__.py` and `src/gdg_yorku_submission/coordinator/compiler.py` to import `validate_report_invariants` and `parse_evidence_ref` from `validator.py`.
- Implement new validation checks:
  - Verify every input finding ID is accounted for exactly once (no duplicates, no omissions of high/critical).
  - Verify finding existence: every finding listed under `included` or `contested` in the ledger must actually exist in `report.findings` or `report.contested_items`.
  - Verify no orphan findings: every finding in `report.findings` or `report.contested_items` must be tracked in the ledger under `included` or `contested` respectively.
  - Verify merge severity is exactly equal to the deterministic max of its constituents.
  - Verify `severity_counts` matches actual finding counts in `report.findings` only (active findings).
  - Verify evidence_ref path/line coordinates are within bounds of the ingested corpus.
  - Enforce contested K-cap: number of contested findings with severity < `high` (i.e. medium, low, info) must be capped at `K` (let's define `K = 3` or `K = 5` and make it clear).
- Create `tests/test_report_validator.py` testing all validation failure modes.

### Out of scope
- Modifying the coordinator compiler LLM generation logic itself.
- Upgrading to full security debate (Task 21).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | **Validator Refactoring**: Move validator logic to a separate module `src/gdg_yorku_submission/coordinator/validator.py`. |
| REQ-002 | **No High Omission**: Reject any report that drops or omits a high/critical finding. |
| REQ-003 | **Conservation Ledger Integrity**: Ensure every input ID is accounted for exactly once (Included U Merged U Omitted U Contested = All Inputs). No orphan findings in findings lists, and every ledger-included/contested ID must exist in the findings list. |
| REQ-004 | **Exact Severity Counts**: Verify `severity_counts` matches active findings counts. |
| REQ-005 | **Merge Severity Constraint**: Verify merged finding severity is exactly the max of constituents. |
| REQ-006 | **Evidence Ref Range Check**: Verify `evidence_ref` citations (and finding locations) are within the corpus bounds (syntactic existence check). |
| REQ-007 | **Contested K-cap**: Limit the number of contested items below the high floor to a threshold `K = 3`. High/critical contested items are exempt and enumerated in full. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `validate_report_invariants` is imported from `validator.py` and all existing compiler/orchestrator tests continue to pass. |
| AC-002 | REQ-002 | Report omitting a high/critical finding fails validation. |
| AC-003 | REQ-003 | Report with duplicate accounting, missing ledger tracking, orphan findings, or ledger entries missing from findings fails validation. |
| AC-004 | REQ-004 | Report with incorrect `severity_counts` fails validation. |
| AC-005 | REQ-005 | Merges with severity unequal to max of constituents fail validation. |
| AC-006 | REQ-006 | Finding referencing out-of-bounds lines/paths in `evidence_ref` or `location` fails validation. |
| AC-007 | REQ-007 | Report containing more than 3 contested findings with severity < `high` fails validation. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Create `src/gdg_yorku_submission/coordinator/validator.py` and refactor logic from `compiler.py` | `src/gdg_yorku_submission/coordinator/validator.py`, `src/gdg_yorku_submission/coordinator/compiler.py`, `src/gdg_yorku_submission/coordinator/__init__.py` | pending |
| TASK-002 | Implement enhanced checks: severity_counts matching, bidirectional ledger/finding existence, contested K-cap | `src/gdg_yorku_submission/coordinator/validator.py` | pending |
| TASK-003 | Create `tests/test_report_validator.py` covering all ACs | `tests/test_report_validator.py` | pending |
| TASK-004 | Run pytest validation and ensure zero regressions | tests | pending |

# Workflow Plan - Task 15 (Revised with Gatekeeper Fixes)

## Goal
Address gatekeeper findings and feedback for Task 15. Ensure validator retry feedback is sanitized against prompt-injections, deduplicate K-cap remediation logic, test real-path validator failures, assert zero-LLM token fallback, classify non-remediable errors to save budget, and fix crash-safety binding scope bugs.

## Scope

### In scope
- Hoist imports and remove redundant active findings filter in `compiler.py`.
- Sanitize error messages in retry prompts to prevent delimiter escape injections.
- Extract `remediate_contested_kcap` into a single shared helper in `validator.py`.
- Sort contested findings below the high floor by severity rank so higher-severity findings survive K-cap truncation.
- Classify errors into coordinator-remediable and non-remediable, immediately skipping retries to save budget if all validation errors are non-remediable.
- Fix mock validator scope binding mismatch in `never-fails` crash test.
- Write robust real-path tests verifying retries on real-path validator violations, zero-LLM fallback token assertions, and correct K-cap remediation behavior.

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | **Prompt-Injection Safe Retry**: Sanitize validation error details in compiler retries to prevent delimiter/nonce escape payloads. |
| REQ-002 | **Unified K-cap Remediation**: Extract one shared, severity-sorted K-cap remediation helper used consistently. |
| REQ-003 | **Remediability Classification**: Classify validator errors and bypass retries if none are coordinator-remediable. |
| REQ-004 | **Robust Invariant Testing**: Test retries on actual validator-only errors without mocking the validator. |
| REQ-005 | **Zero-LLM Verification**: Assert zero LLM token/cost usage during terminal fallback compilation. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Untrusted breakout payloads in validation feedback errors are sanitized (e.g. delimiters replaced). |
| AC-002 | REQ-002 | A unified `remediate_contested_kcap` helper prioritizes higher severity (Medium > Low > Info) and is used across `compiler.py` and `orchestrator.py`. |
| AC-003 | REQ-003 | If all errors are non-remediable (e.g. location out of bounds), no retries occur. |
| AC-004 | REQ-004 | Unit tests assert that a real validator-only error triggers a retry and that the call count is exactly bounded. |
| AC-005 | REQ-005 | Unit tests assert that no LLM calls are made during terminal report compilation. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-005 | Refactor/deduplicate K-cap remediation and report building into shared helpers in `validator.py` | `src/gdg_yorku_submission/coordinator/validator.py`, `src/gdg_yorku_submission/coordinator/compiler.py`, `src/gdg_yorku_submission/orchestrator.py` | completed |
| TASK-006 | Implement error sanitization and error remediability checks in `compiler.py` | `src/gdg_yorku_submission/coordinator/compiler.py` | completed |
| TASK-007 | Refactor existing tests and add comprehensive tests for prompt injection, zero-LLM usage, and real-path validation failures | `tests/test_coordinator.py` | completed |

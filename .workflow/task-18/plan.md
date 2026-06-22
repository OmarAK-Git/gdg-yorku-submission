# Workflow Plan - Task 18 (Out-of-Band Validator-Rejection Demo Hook)

## Goal
Build and verify a CLI demo hook (`python -m gdg_yorku_submission.demo_hooks`) that runs the report validator against a deliberately corrupted in-memory report and prints the validation errors, ensuring it is isolated from the HTTP path.

## Scope

### In scope
- Create `src/gdg_yorku_submission/demo_hooks.py` with actions `drop-high`, `corrupt-location`, `corrupt-evidence-ref`, and `leak-secret`.
- Create `tests/test_validator_demo_hook.py` to verify validator rejection errors using exact-delta assertions, raw secret masking checks, and HTTP/production path isolation.
- Create `docs/demo-script.md` to document the demo CLI usage and context.

### Out of scope
- Exposing the validation corruption hook over HTTP/FastAPI.
- Modifying the core report validator rules or schema structures.

## Requirements
| ID | Requirement |
|---|---|
| REQ-18-1 | **Out-of-Band CLI execution**: A CLI hook command of the form `python -m gdg_yorku_submission.demo_hooks <action> <zip_path>` must run the ingestion, secret scan, and deterministic security specialists on the zip archive. |
| REQ-18-2 | **Negative Control & Manual Corruption**: Verify the uncorrupted report compiles cleanly with 0 errors (negative control). Support actions: `drop-high` (omits high-severity finding), `corrupt-location` (coordinates out of bounds), `corrupt-evidence-ref` (evidence coordinates out of bounds), and `leak-secret` (raw secret in finding path, verifying masking in validation output). |
| REQ-18-3 | **HTTP Isolation**: Ensure that `demo_hooks.py` is not imported by any production FastAPI module and not reachable via any HTTP endpoint or console entry points. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-18-1 | REQ-18-1 | CLI runs successfully with action and zip path arguments, exiting with non-zero exit code on failure. |
| AC-18-2 | REQ-18-2 | The uncorrupted baseline validation returns exactly `[]`. Direct and subprocess tests check exact validation error deltas. `leak-secret` asserts raw secret is absent from redacted error strings and replaced with a valid placeholder. |
| AC-18-3 | REQ-18-3 | Unit tests verify that `gdg_yorku_submission.demo_hooks` is never imported by production code and is not registered in `pyproject.toml`. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-18-1 | Implement `src/gdg_yorku_submission/demo_hooks.py` | `src/gdg_yorku_submission/demo_hooks.py` | completed |
| TASK-18-2 | Implement `tests/test_validator_demo_hook.py` | `tests/test_validator_demo_hook.py` | completed |
| TASK-18-3 | Implement `docs/demo-script.md` | `docs/demo-script.md` | completed |
| TASK-18-4 | Run verification and update memory bank / workflow reports | None | completed |

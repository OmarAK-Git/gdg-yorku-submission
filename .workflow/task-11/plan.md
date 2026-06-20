# Workflow Plan - Task 11

## Goal
Implement deterministic Python AST security checkers for common vulnerabilities to ensure a reliable security perspective baseline before LLM-based debate checks.

## Scope

### In scope
- Create `src/gdg_yorku_submission/security/` package.
- Implement AST checks for:
  - SQL Injection (SQLi)
  - Unsafe subprocess command execution (`shell=True`)
  - Unsafe deserialization (`pickle`, `yaml`)
  - Missing authorization on HTTP write routes (Flask, FastAPI)
  - Path traversal vulnerabilities (`open`, `os.path.join`, `Path`)
  - SSL verification disabled (`verify=False`)
- Implement language detection on the uploaded corpus:
  - Non-Python files trigger `complete_limited` status with appropriate reason.
  - unsupported_language_count metadata populated.
- Modify `orchestrator.py` `run_specialist` to support returning custom status/reasons.
- Integrate the real security scanner into `app.py`.
- Implement unit tests in `tests/test_security_deterministic.py`.

### Out of scope
- Implementing the LLM correctness agent adapter (Task 12).
- Implementing security debate loop upgrades (Tasks 20, 21).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Create deterministic AST checkers for SQLi, shell=True, unsafe deserialization, missing auth, path traversal, and verify=False. |
| REQ-002 | Detect corpus language(s) from the manifest/corpus; flag unsupported languages in metadata and map security perspective status to `complete_limited`. |
| REQ-003 | Modify `run_specialist` to allow specialist functions to customize perspective status/reason. |
| REQ-004 | Integrate the deterministic security baseline checker into the API execution path in `app.py`. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Python AST checks find vulns (and don't false positive on safe code) and return schema-valid findings. |
| AC-002 | REQ-002 | Non-Python upload yields `complete_limited` status with reason detailing unsupported languages, setting `unsupported_language_count` in metadata. |
| AC-003 | REQ-003 | Specialists can set custom status/reasons without breaking backwards compatibility. |
| AC-004 | REQ-004 | API `/review` POST execution runs the real AST checks on uploaded files and outputs them in the report. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Modify `run_specialist` in `orchestrator.py` | `src/gdg_yorku_submission/orchestrator.py` | pending |
| TASK-002 | Implement security baseline scanners in `src/gdg_yorku_submission/security/` | `src/gdg_yorku_submission/security/deterministic.py` | pending |
| TASK-003 | Integrate AST scanner into `app.py` | `src/gdg_yorku_submission/app.py` | pending |
| TASK-004 | Implement test cases in `tests/test_security_deterministic.py` | `tests/test_security_deterministic.py` | pending |

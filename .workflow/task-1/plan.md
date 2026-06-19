# Workflow Plan - Task 1

## Goal
Establish a clean project baseline and build a provenance & commit window guard that enforces that all Git history starts ≥ 2026-06-17.

## Scope

### In scope
- Verify git history commit window (author & commit date ≥ 2026-06-17) using `scripts/check_commit_window.py` and `tests/test_commit_window.py`.
- Create a `NOTICE.md` detailing the provenance/history of any adapted/copied code (no old Git history imported).
- Set up root configurations: `README.md`, `.gitignore`, `pyproject.toml`.
- Initialize `src/gdg_yorku_submission/__init__.py` and configure `pytest`.

### Out of scope
- Implementation of schemas, api routes, scanners, or other code review logic.

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Commit window checker script `scripts/check_commit_window.py` that fails if any commit author/commit date is before 2026-06-17. |
| REQ-002 | Test suite `tests/test_commit_window.py` verifying check_commit_window behavior (passing/failing cases). |
| REQ-003 | `NOTICE.md` containing a provenance table detailing components, sources, and status (e.g. copied/adapted/new). |
| REQ-004 | Configuration files (`pyproject.toml`, `.gitignore`, `README.md`) matching standards. |
| REQ-005 | Running `pytest` succeeds without warnings/failures. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Running `python scripts/check_commit_window.py` returns exit code 0 when all commits are valid, and exit code 1 otherwise. |
| AC-002 | REQ-002 | `pytest tests/test_commit_window.py` passes. |
| AC-003 | REQ-003 | `NOTICE.md` exists and contains a table mapping component, source, copied/adapted/new, license, date, and notes. |
| AC-004 | REQ-004 | `README.md`, `.gitignore`, and `pyproject.toml` are present and properly configured. |
| AC-005 | REQ-005 | Running `pytest` runs correctly. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Create `.gitignore`, `pyproject.toml`, and package files | `.gitignore`, `pyproject.toml`, `src/gdg_yorku_submission/__init__.py` | pending |
| TASK-002 | Create provenance document | `NOTICE.md` | pending |
| TASK-003 | Implement commit window checker script | `scripts/check_commit_window.py` | pending |
| TASK-004 | Implement test for commit window checker | `tests/test_commit_window.py` | pending |
| TASK-005 | Configure README and verify baseline tests | `README.md`, tests/ | pending |

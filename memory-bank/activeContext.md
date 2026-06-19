# Active Context

## Current State
- The workspace baseline is established. The commit window validator (`scripts/check_commit_window.py`), provenance notice (`NOTICE.md`), `README.md`, `.gitignore`, and `pyproject.toml` are implemented and verified.
- Pytest test suite is initialized and passes.

## Active Focus
- Launching Sprint 1 / **Task 2 — Core Schemas + Severity Mapping**:
  - Define core review findings and report schemas using Pydantic.
  - Implement severity map from legacy/divergent client labels to standardized enums.
  - Write validation checks.

## Next Steps
1. Create `src/gdg_yorku_submission/schemas.py` to house Pydantic models for `Finding`, `ReviewReport`, etc.
2. Create `src/gdg_yorku_submission/severity.py` with the severity mapping logic (Blocker/Major/Minor -> Standard).
3. Implement unit tests under `tests/test_schemas.py` and `tests/test_severity.py`.

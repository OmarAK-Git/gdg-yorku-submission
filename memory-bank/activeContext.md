# Active Context

## Current State
- The workspace baseline is established. The commit window validator (`scripts/check_commit_window.py`), provenance notice (`NOTICE.md`), `README.md`, `.gitignore`, and `pyproject.toml` are implemented and verified.
- Pytest test suite is initialized and passes.

## Active Focus
- Launching Sprint 1 / **Task 3 — Collision-Safe Deterministic Finding IDs**:
  - Implement stable ID generation with occurrence ordinals for co-located findings to ensure ID collision safety.

## Next Steps
1. Create `src/gdg_yorku_submission/finding_ids.py` to house ID generation.
2. Implement unit tests under `tests/test_finding_ids.py` verifying same anchor properties, tiebreakers, and occurrences.
3. Ensure `map_severity` is explicitly called at every finding emit point when building future specialist/gate pipelines.

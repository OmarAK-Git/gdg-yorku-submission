# Active Context

## Current State
- Core Pydantic V2 schemas and legacy-to-standard severity mapping are defined.
- Stable, collision-safe ID generation, automatic non-prose key merging, and occurrence ordinal finalization are implemented and verified under `src/gdg_yorku_submission/finding_ids.py`.
- FastAPI walking skeleton (`src/gdg_yorku_submission/app.py`) and the `Orchestrator` abstraction seam (`src/gdg_yorku_submission/orchestrator.py`) with both plain-Python in-process and stub ADK implementations are completed.
- Full pytest suite (76 tests) passes with no warnings or errors.

## Active Focus
- Preparing for Sprint 2 / **Task 5 — Hardened Zip Extraction**:
  - Implement zip extraction safety checks (size caps, count caps, directory traversal blocks, entry skipping).

## Next Steps
1. Create `src/gdg_yorku_submission/ingest.py` and implement extraction sanitization.
2. Define skip reasons manifest structure and aggregate limits checker.
3. Write unit tests in `tests/test_ingest.py` verifying all edge cases, traversal attacks, caps, and skipped files.

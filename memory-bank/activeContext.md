# Active Context

## Current State
- Core Pydantic V2 schemas and legacy-to-standard severity mapping are defined.
- Stable, collision-safe ID generation, automatic non-prose key merging, and occurrence ordinal finalization are implemented and verified under `src/gdg_yorku_submission/finding_ids.py`.
- Full pytest suite (38 tests) passes with no warnings or errors.

## Active Focus
- Preparing for Sprint 1 / **Task 4 — FastAPI Walking Skeleton + Orchestrator Seam**:
  - Implement the upload API endpoint with stubs, Orchestrator seam interface, and plain-Python vs. ADK conformance test.

## Next Steps
1. Define the internal `Orchestrator` interface and its plain-Python in-process implementation under `src/gdg_yorku_submission/orchestrator.py` or similar.
2. Setup a FastAPI application walking skeleton with upload endpoint stubbing.
3. Implement conformance tests verifying that the Orchestrator seam functions identically for both in-process and ADK modes.

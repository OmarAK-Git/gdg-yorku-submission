# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Full pytest suite (120 tests) passes with no warnings or errors.

## Active Focus
- Preparing for Sprint 3 / **Task 9 — Source-of-Truth Discovery**:
  - Discover SPEC.md, DESIGN.md, allowed README headers, and define fallback behavior when no spec is found.

## Next Steps
1. Implement spec file discovery logic.
2. Define no-spec fallback behavior when no spec document is found in the repository.
3. Integrate Source-of-Truth discovery into the Specialist Correctness agent flow.

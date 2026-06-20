# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Task 9 (Source-of-Truth Discovery) and Task 10 (Rewrite Correctness Rubric/Methodology) are completed and verified.
- Task 11 (Deterministic Python AST Baseline security checkers) is completed, integrated, and verified.
- Full pytest suite (172 tests) passes successfully with no warnings or errors.

## Active Focus
- **Task 12 — Correctness Agent Adapter**: Implement Vertex AI Gemini correctness agent correctly grounded via evidence-refs and budget-aware.

## Next Steps
1. Design correctness agent adapter in `src/gdg_yorku_submission/correctness/`.
2. Implement unit and integration tests for the correctness adapter.
3. Verify via pytest.

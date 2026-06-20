# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Full pytest suite (120 tests) passes with no warnings or errors.
- Task 9 (Source-of-Truth Discovery) and Task 10 (Rewrite Correctness Rubric/Methodology) are completed and verified (155 tests passing).
- Moving forward in Sprint 3: Correctness Agent & Baseline Security.

## Active Focus
- **Task 11 — Deterministic Security Baseline Pass (Python AST)**: Implement deterministic Python AST checkers.

## Next Steps
1. Create/refactor `src/gdg_yorku_submission/security/deterministic.py`.
2. Implement unit tests in `tests/test_security_deterministic.py`.
3. Verify via pytest.
4. Update `memory-bank/progress.md`.

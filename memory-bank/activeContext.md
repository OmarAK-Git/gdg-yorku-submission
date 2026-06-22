# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Task 9 (Source-of-Truth Discovery) and Task 10 (Rewrite Correctness Rubric/Methodology) are completed and verified.
- Task 12 (Correctness Agent Adapter) is completed, integrated, and verified, passing all 200 tests.
- Task 13 (Coordinator Compiler) is completed and verified, passing all tests.
- Task 14 (Conservation Validator) is completed and verified, implementing full conservation, routing, severity counts, and contested K-cap checks.
- Task 15 (Bounded Regeneration + Deterministic Terminal Report) is completed and verified, implementing validator retry feedback loops and zero-LLM fallbacks.
- Task 18 (Out-of-Band Validator-Rejection Demo Hook) and Task 19 (Debate Data Model schemas) are completed and verified.

## Active Focus
- Preparing for close-out and E2E demo scripts. Tasks 20 and 21 are fully completed.

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This has been implemented successfully in Task 14.
- **Tag for Task 16/24**: Correctness grounding and coordinate boundaries validation have been verified E2E via the demo sample tests; actual LLM correctness detection is deferred to Task 24.


## Next Steps
1. Wire optional Orbit Blast-Radius (Task 22).
2. End-to-end integration tests and close-out documentation (Tasks 23-26).

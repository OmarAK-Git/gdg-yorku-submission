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
- Implementing optional upgrades (Crucible Debate loop). Task 19 is completed.

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This has been implemented successfully in Task 14.
- **Tag for Task 16/24**: Correctness grounding and coordinate boundaries validation have been verified E2E via the demo sample tests; actual LLM correctness detection is deferred to Task 24.
- **Tag for Task 19/20/21**: The new `validate_completeness()` and `get_contested_with_kcap()` guards are implemented in `DebateLedger` but not yet wired to any report compiling path. When building Task 20/21 (debate loop/adapter) and the Task 14 validator updates, these methods must be called to ensure all debate candidates are resolved and the contested K-cap is correctly enforced, with corresponding end-to-end integration tests.


## Next Steps
1. Port the Crucible Debate Loop structure and stop conditions (Task 20).

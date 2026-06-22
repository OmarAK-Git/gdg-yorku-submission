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
- Task 18 (Out-of-Band Validator-Rejection Demo Hook) is completed and verified.

## Active Focus
- All core review pipeline features, frontends, and out-of-band validator-rejection hooks are now completed and verified.

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This has been implemented successfully in Task 14.
- **Tag for Task 16/24**: Correctness grounding and coordinate boundaries validation have been verified E2E via the demo sample tests; actual LLM correctness detection is deferred to Task 24.

## Next Steps
1. Choose whether to implement optional Upgrades (Crucible Debate loop in Tasks 19-22) or proceed to Close-out (E2E integration test Task 23 and Real-LLM smoke scripts Task 24).

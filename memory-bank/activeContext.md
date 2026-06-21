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

## Active Focus
- **Task 16 — Pinned Demo Sample**: Build and verify demo repo `samples/driftstore` to trigger required review findings.

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This has been implemented successfully in Task 14.
- **Tag for Task 16/24**: Correctness has only run with the synthetic placeholder finding. Those tasks must produce and assert on a real Gemini-grounded finding's content through a no-monkeypatch path.

## Next Steps
1. Build the demo repository under `samples/driftstore` to trigger expected correctness, AST, and secret scanning findings.
2. Verify that complete E2E runs on the demo repository produce the desired findings and pass the coordination phase cleanly.


# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Task 9 (Source-of-Truth Discovery) and Task 10 (Rewrite Correctness Rubric/Methodology) are completed and verified.
- Task 24 (Real-LLM Smoke Script & Gate Review Updates) is completed and verified, establishing ADC-first auth for Gemini and Claude Vertex clients, updating models, capping Claude reasoning effort, surfacing warnings, and introducing redaction and live test suite coverage.

## Active Focus
- Preparing documentation, setup instructions, architecture writeup, and user instructions (Task 25).

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This has been implemented successfully in Task 14.
- **Tag for Task 16/24**: Correctness grounding and coordinate boundaries validation have been verified E2E via the demo sample tests; actual LLM correctness detection is verified in dry-run/fake mode and live smoke test structure in Task 24.

## Next Steps
1. Finalize README setup writeup and demo recording (Tasks 25-26).

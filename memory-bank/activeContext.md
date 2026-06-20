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

## Active Focus
- **Task 14 — Conservation Validator**: Validate reports deterministic invariants (no high omission, correct merge severity, coordinate existence).

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. For the validator's evidence-existence check, we validate against the full loaded corpus file line count. This allows correct references to any lines within the actual file while avoiding out-of-bounds citations.
- **Tag for Task 16/24**: Correctness has only run with the synthetic placeholder finding. Those tasks must produce and assert on a real Gemini-grounded finding's content through a no-monkeypatch path.

## Next Steps
1. Extend and refine report validation logic for conservation invariants, severity max-rules, and coordinate checks.
2. Verify via pytest.


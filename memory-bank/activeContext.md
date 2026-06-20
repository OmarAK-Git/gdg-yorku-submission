# Active Context

## Current State
- Core Pydantic V2 schemas, legacy-to-standard severity mapping, collision-safe ID finalization, and FastAPI walking skeleton / Orchestrator abstraction seam are completed and verified.
- Hardened Zip Extraction (Task 5) is completed and verified.
- Exposure-Model Prompt Corpus (Task 6) is implemented and verified.
- Secret Scanner + Redaction Invariant (Task 7) is completed, porting the secret gate detection, redaction invariant, and salted hash fingerprints.
- Evidence-Plane Prompt Builder (Task 8) is completed, building a nonced, sanitized, and redacted prompt representation of the prompt-exposed corpus.
- Task 9 (Source-of-Truth Discovery) and Task 10 (Rewrite Correctness Rubric/Methodology) are completed and verified.
- Task 12 (Correctness Agent Adapter) is completed, integrated, and verified, passing all 200 tests.

## Active Focus
- **Task 13 — Coordinator Compiler**: Implement coordinator agent to group/merge findings within the same perspective/source and output a consolidated report.

## Deferred Constraints (from Sprint 3 Gate)
- **Tag for Task 13–14**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. When the validator's evidence-existence check is built, first define how the SoT span is set — inject `sot_text` as the spec block, or constrain the evidence plane's SoT entry to the allowlisted span — and document the choice.
- **Tag for Task 16/24**: Correctness has only run with the synthetic placeholder finding. Those tasks must produce and assert on a real Gemini-grounded finding's content through a no-monkeypatch path.

## Next Steps
1. Design coordinator agent adapter in `src/gdg_yorku_submission/coordinator/`.
2. Implement unit and integration tests for the coordinator compiler.
3. Verify via pytest.


# Progress

## Project Status
- **Phase**: Sprint 3: Correctness Agent & Baseline Security
- **Overall Completion**: 50.0% (13 / 26 tasks complete)

## Completed Tasks
- [x] Task 1: Fresh Repo Baseline + Provenance Guard
- [x] Task 2: Core Schemas + Severity Mapping
- [x] Task 3: Collision-Safe Deterministic Finding IDs
- [x] Task 4: FastAPI Walking Skeleton + Orchestrator Seam
- [x] Task 5: Hardened Zip Extraction
- [x] Task 6: Exposure-Model Prompt Corpus
- [x] Task 7: Secret Scanner + Redaction Invariant
- [x] Task 8: Evidence-Plane Prompt Builder (Nonced)
- [x] Task 9: Source-of-Truth Discovery
- [x] Task 10: Rewrite Correctness Rubric/Methodology
- [x] Task 11: Deterministic Security Baseline Pass (Python AST)
- [x] Task 12: Correctness Agent Adapter
- [x] Task 13: Coordinator Compiler
- [x] Sprint 2 Gate Review Fixes (Task 7 context threading, Task 8 pre-conditions, state preservation, precise virtualenv skips, descope documentation, and HTTP E2E tests)

## In Progress Tasks
*None*

## Upcoming Tasks (Sprint 4)
- [ ] Task 14: Conservation Validator

## Gaps, Issues, and Risks
- **Google ADK integration**: High dependency risk. Mitigated by Orchestrator abstraction seam allowing a plain Python fallback.
- **Claude debate loop complexity**: High token/time risk. Mitigated by deterministic baseline running first and debate acting as a strict cuttable upgrade.
- **Secret leaks**: Checked system-wide using a single `RedactionContext`.
- **Commit window constraints**: Mandatory check for author/commit timestamps ≥ 2026-06-17.
- **Tag for Task 13–14 (Deferred Constraint)**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. When the validator's evidence-existence check is built, first define how the SoT span is set — inject `sot_text` as the spec block, or constrain the evidence plane's SoT entry to the allowlisted span — and document the choice.
- **Tag for Task 16/24 (Deferred Constraint)**: Correctness has only run with the synthetic placeholder finding. Those tasks must produce and assert on a real Gemini-grounded finding's content through a no-monkeypatch path.


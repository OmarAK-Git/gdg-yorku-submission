# Progress

## Project Status
- **Phase**: Sprint 5: Coordination & Validation (Demo prep)
- **Overall Completion**: 73.1% (19 / 26 tasks complete)

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
- [x] Task 14: Conservation Validator
- [x] Task 15: Bounded Regeneration + Deterministic Terminal Report
- [x] Task 16: Pinned Demo Sample
- [x] Task 17: Frontend Report Viewer
- [x] Task 18: Out-of-Band Validator-Rejection Demo Hook
- [x] Task 19: Debate Data Model
- [x] Sprint 2 Gate Review Fixes (Task 7 context threading, Task 8 pre-conditions, state preservation, precise virtualenv skips, descope documentation, and HTTP E2E tests)

## In Progress Tasks
*None*

## Upcoming Tasks (Sprint 5 & Close-Out)
*None* (Ready for upgrades or close-out phase)

## Gaps, Issues, and Risks
- **Google ADK integration**: High dependency risk. Mitigated by Orchestrator abstraction seam allowing a plain Python fallback.
- **Claude debate loop complexity**: High token/time risk. Mitigated by deterministic baseline running first and debate acting as a strict cuttable upgrade.
- **Secret leaks**: Checked system-wide using a single `RedactionContext`.
- **Commit window constraints**: Mandatory check for author/commit timestamps ≥ 2026-06-17.
- **Tag for Task 13–14 (Deferred Constraint)**: The correctness agent discards `sot_result.sot_text` and feeds the full file into the evidence plane, bypassing the README heading-allowlist. When the validator's evidence-existence check is built, first define how the SoT span is set — inject `sot_text` as the spec block, or constrain the evidence plane's SoT entry to the allowlisted span — and document the choice.
- **Tag for Task 16/24 (Deferred Constraint)**: Correctness grounding and coordinate boundaries validation have been verified E2E via the demo sample tests; actual LLM correctness detection is deferred to Task 24.
- **Tag for Task 19/20/21 (Deferred Constraint)**: The new `validate_completeness()` and `get_contested_with_kcap()` guards are implemented in `DebateLedger` but not yet wired to any report compiling path. In Task 20/21, they must be called to ensure all debate candidates are resolved and the contested K-cap is correctly enforced.


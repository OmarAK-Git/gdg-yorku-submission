# Progress

## Project Status
- **Phase**: Sprint 3: Correctness Agent & Baseline Security
- **Overall Completion**: 46.2% (12 / 26 tasks complete)

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
- [x] Sprint 2 Gate Review Fixes (Task 7 context threading, Task 8 pre-conditions, state preservation, precise virtualenv skips, descope documentation, and HTTP E2E tests)

## In Progress Tasks
*None*

## Upcoming Tasks (Sprint 4)
- [ ] Task 13: Coordinator Compiler

## Gaps, Issues, and Risks
- **Google ADK integration**: High dependency risk. Mitigated by Orchestrator abstraction seam allowing a plain Python fallback.
- **Claude debate loop complexity**: High token/time risk. Mitigated by deterministic baseline running first and debate acting as a strict cuttable upgrade.
- **Secret leaks**: Checked system-wide using a single `RedactionContext`.
- **Commit window constraints**: Mandatory check for author/commit timestamps ≥ 2026-06-17.

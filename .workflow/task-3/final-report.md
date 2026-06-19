# Final Report

## Summary

Successfully implemented stable, collision-safe ID generation and finalization logic for findings, addressing all 11 gaps from code review and ensuring airtight sorting for negative and float discriminators:
- Resolves cross-perspective merges (Gap 2) by including `perspective` in anchor hashes and enforcing checks in `merge_finding_objects`.
- Resolves falsy 0 values (Gap 3) by checking key presence and checking `is not None` instead of truthiness.
- Resolves LLM duplicate collapsing (Gap 4) by keeping identical claim LLM findings separate and assigning ordinals.
- Resolves status merge precedence (Gap 5) by explicitly tracking and testing `active` > `contested` > `advisory` precedence.
- Resolves merged_from stripping (Gap 6) by retaining `merged_from_provisional` in finalized metadata.
- Resolves numeric tiebreaker sorting (Gap 7) with type-safe sign and magnitude comparison (`None` -> `Numeric` -> `String`).
- Resolves stable sorting and output list determinism (Gap 10) by sorting finalized findings semantically using path, line, agent, perspective, and input index.
- Resolves heterogeneous batch set conservation (Gap 1) with property-style tests.
- Formally documents metadata key contracts (Gap 11).

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001: Deterministic Anchors | `src/gdg_yorku_submission/finding_ids.py` computes SHA-256 anchors with perspective included |
| REQ-002: Non-Prose Key Merging | `finalize_finding_ids` collapses same non-prose keys and checks key presence |
| REQ-003: Prose-Free Sort Tiebreaker | Tiebreaker sorts numerically for numbers (handles negatives/floats) and lexicographically for strings |
| REQ-004: Ordinal-Based Finalization | Finalized IDs are stable ordinals and LLM findings do not collapse |
| REQ-005: Test Coverage | `tests/test_finding_ids.py` contains 11 comprehensive tests attacking all boundaries |

## Files changed

- `src/gdg_yorku_submission/__init__.py`
- `src/gdg_yorku_submission/finding_ids.py`
- `tests/test_finding_ids.py`

## Verification performed

- Ran `python scripts/check_commit_window.py` (Passed).
- Ran `python -m pytest` (42/42 tests passed successfully).

## Known gaps

*None*

## Follow-up tasks

- **Task 4**: FastAPI Walking Skeleton + Orchestrator Seam

## Archive decision

- Accepted

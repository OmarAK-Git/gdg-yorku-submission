# Workflow Plan - Task 3: Collision-Safe Deterministic Finding IDs

## Goal
Implement a stable, collision-safe ID generation system for findings using deterministic anchors, non-prose discriminators, and occurrence ordinals to handle co-located findings.

## Scope

### In scope
- Implement anchor hashing logic using `source_agent`, `normalized_path`, `line_start`, `rule_or_category`, and `stable_symbol`.
- Implement ID-finalization logic that:
  - Groups provisional findings by their anchors.
  - Detects findings with identical non-prose keys (based on `sub_rule` / `sub_category` and non-prose evidence anchors like `token_offset` or `ast_node_id`).
  - Merges findings that collapse to the same non-prose key.
  - Sorts remaining findings in each anchor group by a prose-free key: `(sub_rule, non_prose_anchor, claim_sha)`.
  - Assigns a per-anchor occurrence ordinal (0, 1, 2...) and freezes the finalized IDs.
- Write unit tests verifying:
  - Stable IDs across runs with same anchor.
  - Prose changes don't affect single-finding IDs.
  - Collision-safety and distinct stable IDs for co-located same-category findings.
  - Tiebreaker ordering correctness.
  - Automatic merging of detector-backed findings with identical non-prose keys.

### Out of scope
- Integration into the `Orchestrator` execution flow (deferred to Task 4).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Deterministic Anchors: Generate finding anchors using a hash of `source_agent`, `normalized_path`, `line_start`, `rule_or_category`, and `stable_symbol`. |
| REQ-002 | Non-Prose Key Merging: Automatically merge findings sharing the same anchor and same non-prose key. |
| REQ-003 | Prose-Free Sort Tiebreaker: Sort findings in the same anchor group by `(sub_rule, non_prose_anchor, claim_sha)`. |
| REQ-004 | Ordinal-Based Finalization: Assign stable occurrence ordinals and freeze final IDs. |
| REQ-005 | Test Coverage: Thoroughly test all happy paths, boundary cases, and negative conditions. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Anchor hashes are calculated deterministically from non-prose metadata. |
| AC-002 | REQ-002 | Findings with identical `(sub_rule, non_prose_anchor)` are merged (combining claims, severities, evidence, metadata) rather than assigned ordinals. |
| AC-003 | REQ-003 | Tiebreaker sorting strictly follows: sub-rule/sub-category -> non-prose anchor -> claim SHA. |
| AC-004 | REQ-004 | Final IDs are stable, collision-free, and frozen as hex digests of `anchor_hash:ordinal`. |
| AC-005 | REQ-005 | `pytest tests/test_finding_ids.py` passes successfully with no errors or warnings. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Create `src/gdg_yorku_submission/finding_ids.py` and implement anchor hashing, merging, and finalization logic. | `src/gdg_yorku_submission/finding_ids.py` | pending |
| TASK-002 | Write unit tests checking stable IDs, ordinals, tiebreakers, merging, and collision safety. | `tests/test_finding_ids.py` | pending |
| TASK-003 | Run the full test suite and confirm everything passes. | - | pending |

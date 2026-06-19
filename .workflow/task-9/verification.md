# Verification Ledger - Task 9

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Precedence discovery check | `pytest tests/test_sot_discovery.py -k test_precedence` | all pass | pass | pass |
| VERIFY-002 | REQ-002 | Case-insensitivity check | `pytest tests/test_sot_discovery.py -k test_case_tolerance` | all pass | pass | pass |
| VERIFY-003 | REQ-003 | README extraction check | `pytest tests/test_sot_discovery.py -k test_readme_extraction` | all pass | pass | pass |
| VERIFY-004 | REQ-004 | README heading termination check | `pytest tests/test_sot_discovery.py -k test_readme_code_block_handling` | all pass | pass | pass |
| VERIFY-005 | REQ-005 | No-spec fallback check | `pytest tests/test_sot_discovery.py -k test_no_spec_fallback` | all pass | pass | pass |
| VERIFY-006 | Redaction Invariant | Redaction precondition check | `pytest tests/test_sot_discovery.py -k test_unredacted_corpus_raises_runtime_error` | all pass | pass | pass |
| VERIFY-007 | Exposure Invariant | Gitignored file skip check | `pytest tests/test_sot_discovery.py -k test_gitignored_spec_skipped` | all pass | pass | pass |
| VERIFY-008 | Empty Spec | Empty/whitespace file fallback check | `pytest tests/test_sot_discovery.py -k test_empty_spec_skipped` | all pass | pass | pass |
| VERIFY-009 | Determinism | Case collision determinism check | `pytest tests/test_sot_discovery.py -k test_case_collision_determinism` | all pass | pass | pass |
| VERIFY-010 | Trust Boundary | Adversarial text pass-through check | `pytest tests/test_sot_discovery.py -k test_adversarial_content_verbatim` | all pass | pass | pass |
| VERIFY-011 | All | Full test suite check | `pytest` | all 150 pass | 150 pass | pass |

## Skipped checks
- **Tilde & Indented Code Blocks in Markdown (Cosmetic)**: Markdown extraction supports standard backtick code blocks (` ``` `). Tilde fences (` ~~~ `) and 4-space indented blocks are out of scope for README-as-SoT parsing.

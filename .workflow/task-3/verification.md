# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Verify anchor hashing logic | `pytest tests/test_finding_ids.py -k test_anchor` | Anchor matches expected SHA-256 hash | Checked deterministic generation, path backslash normalization, and perspective inclusion | pass |
| VERIFY-002 | REQ-002 | Verify non-prose key merging | `pytest tests/test_finding_ids.py -k test_merging` | Detector-backed findings collapse into single merged finding | Merged overlapping findings, maximum severity resolved, claims concatenated, status priority followed | pass |
| VERIFY-003 | REQ-003, REQ-004 | Verify ordinal-based ID finalization and stable sorting | `pytest tests/test_finding_ids.py -k test_finalization` | Findings sorted and assigned correct ordinals and stable IDs | Verified stable ID assignment, numeric sorting, LLM ordinals, and input index tiebreaker sorting | pass |
| VERIFY-004 | REQ-005 | Run the entire test suite with pytest | `pytest` | All tests pass, including the new finding_ids ones | 42/42 tests passed successfully | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| None | N/A | N/A |

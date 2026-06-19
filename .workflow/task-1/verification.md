# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Commit window script check | `python scripts/check_commit_window.py` | Exit code 0 | Script ran successfully on active branches/tags and output: "All commits are within the allowed window (>= 2026-06-17)." | pass |
| VERIFY-002 | REQ-002 | Run unit tests | `pytest tests/test_commit_window.py` | All tests pass | 10 tests passed (including CLI integrations and boundaries) | pass |
| VERIFY-003 | REQ-003 | Document existence | Inspect `NOTICE.md` contents | Provenance table present | `NOTICE.md` updated to remove pre-emptive completion dates for unbuilt items | pass |
| VERIFY-004 | REQ-004 | Config check | Inspect configs | Configs present and sound | `.gitignore`, `pyproject.toml`, and `README.md` present and sound | pass |
| VERIFY-005 | REQ-005 | Run all tests | `pytest` | Baseline runs pass without warning errors | All tests pass without warnings or errors | pass |

## Skipped checks
*None*

# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Exposure Classification | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-002 | REQ-002 | Root .gitignore parsing (pathspec) | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-003 | REQ-003 | CorpusFile mappings and line maps | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-004 | REQ-004 | System Excluded mappings | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-005 | REQ-003 | Shifted line map coordinates | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-006 | REQ-001 | Ingestion determinism | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-007 | REQ-001 | Read failure classification | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-008 | REQ-001 | Prompt scope filter regression guard | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-009 | REQ-001 | Non-UTF-8 tolerant decoding (Latin-1) | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-010 | REQ-001 | Path collision prevention check | pytest tests/test_corpus.py | pass | pass | verified |
| VERIFY-011 | REQ-001 | Path conservation accounting check | pytest tests/test_corpus.py | pass | pass | verified |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| None | N/A | N/A |

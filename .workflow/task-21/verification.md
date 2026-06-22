# Verification Ledger - Task 21

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-21-01 | REQ-21-R1 | Survived candidate schema mapping | `pytest tests/test_debate_loop.py` | pass | pass | completed |
| VERIFY-21-02 | REQ-21-R2 | Secret absence in debate prompt | `pytest tests/test_debate_loop.py -k test_no_raw_secret_in_debate_prompt` | pass | pass | completed |
| VERIFY-21-03 | REQ-21-R3 | Graceful fallback on mid-debate failures | `pytest tests/test_debate_loop.py -k test_http_debate_fallback_on_failure` | pass | pass | completed |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Real-LLM (live API) smoke test | Deferred to Task 24 per user instruction. | Minimal. Covered by fake-LLM tests and unit tests mocking adapters. |

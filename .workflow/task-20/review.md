# Review - Task 20 (Remediation Pass & Coordinator Hardening)

## Code Quality & Safety Checks
- Verified that `inspect.iscoroutinefunction` and `inspect.iscoroutine` are utilized correctly in `orchestrator.py` to seamlessly handle both async and sync specialist functions.
- Confirmed that FastAPI `/review` route calls `await orch.run_specialist_async("security", ...)` successfully.
- Verified that all finding IDs generated for new proposals are derived using SHA-256 hashes of `citation + claim`, eliminating `uuid4` completely from finding ID generation.
- Ensured that exceptions caught during the debate loop in `agent.py` are logged at WARNING level with their exact type and message, avoiding swallowing the real errors.
- Verified that the `GeminiClient` dummy path properly constructs mapping responses for `response_schema` models like `CoordinatorOutput` and correctly propagates custom `fake_responses` list items across retries.
- Confirmed that `test_http_debate_path` is properly hardened to verify that the report has not fallen back to `terminal_fallback`, that logs contain no warnings, and that contested items are correctly populated.

## Self-Correction & Reflection during Task
1. **Preventing premature Round 1 termination in determinism test**: The new budget checks and empty proposals in mock functions meant that empty findings would immediately terminate in Round 1. We resolved this by making the mock defender return an initial proposal in Round 1, preventing early termination and verifying generative IDs.
2. **NoneType on contested findings closed reason**: Because `contested` findings do not have `closed_reason` (per Pydantic schema validation rules), we updated the existing `test_transcript_redaction` to set finding citation to `NONE` so it maps to `defeated` and successfully evaluates the redacted closed reasoning.
3. **Coordinate out of bounds in HTTP debate test**: We found that mock-seeding a finding on lines 1-2 while writing a 1-line file in the test zip caused a validation failure (out-of-bounds). We resolved this by writing a two-line mock file in the test setup.
4. **Reusing custom fake responses**: In unit tests checking JSON errors, a single malformed custom response caused subsequent retries to succeed on the default dummy schema path. We corrected this by reusing the last provided custom response in `GeminiClient` when the list index goes out of bounds.

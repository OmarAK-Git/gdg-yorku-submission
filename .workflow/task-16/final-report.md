# Final Report - Task 16 (Pinned Demo Sample)

## Summary
Successfully implemented the pinned demo repository `samples/driftstore/` and packaged it into `samples/driftstore.zip` to trigger all required review findings (tracked secret, gitignored secret, correctness divergence, and deterministic AST security issues), and verified them using automated tests under `tests/test_demo_sample.py`.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-16-1 | `samples/driftstore.zip` contains `SPEC.md`, `.gitignore`, `.env`, `src/app.py`, and `tests/test_dummy.py`. |
| REQ-16-2 | The tracked Google API key in `src/app.py` is correctly identified as `HIGH` severity. |
| REQ-16-3 | The gitignored database password in `.env` is correctly identified as `INFO` severity. |
| REQ-16-4 | AST security baseline pass detects SQLi, missing auth write route, verify=False, path traversal, shell_true, and unsafe_deserialize in `src/app.py`. |
| REQ-16-5 | Correctness review coordinates parsing+grounding verified; LLM-based detection deferred to Task 24. |
| REQ-16-6 | E2E integration tests compile clean reports on both InProcessOrchestrator and AdkOrchestrator without raw secret leakages. |

## Files changed
- `samples/driftstore/SPEC.md` [NEW]
- `samples/driftstore/.gitignore` [NEW]
- `samples/driftstore/.env` [NEW]
- `samples/driftstore/src/app.py` [NEW]
- `samples/driftstore/tests/test_dummy.py` [NEW]
- `samples/driftstore.zip` [NEW]
- `tests/test_demo_sample.py` [NEW]

## Verification performed
- Ran `pytest tests/test_demo_sample.py` (12 tests passed).
- Ran all 264 tests in the repository (264 passed).

## Known gaps
None. (All 6 AST rules are now fully triggered by the demo sample, demonstrating the full baseline surface).

## Follow-up tasks
- Task 17 — Frontend Report Viewer.

## Archive decision
- Accepted

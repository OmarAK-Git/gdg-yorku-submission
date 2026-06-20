# Final Report - Task 11

## Summary
Task 11 implements the deterministic Python AST security checkers (SQLi, shell=True, unsafe deserialization, missing-auth write route, path traversal, verify=False) as a baseline security perspective. 

We accomplished:
1. **Orchestrator Extension**: Enhanced `run_specialist` to unpack an optional `(findings, status, reason)` tuple from specialist functions, allowing custom perspective statuses (like `complete_limited`).
2. **Deterministic Baseline Checkers**: Created 6 high-precision checkers inside `src/gdg_yorku_submission/security/deterministic.py` using AST visitor classes. All checkers are warning-free under Python 3.13 deprecation constraints.
3. **Language Detection**: Classifies file extensions, mapping mixed/non-Python repositories to `complete_limited` status with a reason outlining the unsupported extensions and writing `unsupported_language_count` to the report run metadata.
4. **App Integration**: Replaced the stub security specialist with the real AST scanner.
5. **Testing Suite**: Authored 9 unit and E2E tests checking all checker rules, language detection, custom status overrides, and API integrations.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-001 (Baseline Checkers) | 6 checkers implemented in `deterministic.py` and validated by 6 corresponding positive/negative test cases in `test_security_deterministic.py`. |
| REQ-002 (Language Detection) | Language classification maps unsupported extensions to `complete_limited` status and records `unsupported_language_count` in metadata. Validated by `test_language_detection` and `test_custom_status_override`. |
| REQ-003 (Specialist Status) | Orchestrator supports status and reason overrides from specialists. Checked by `test_custom_status_override`. |
| REQ-004 (API Integration) | App FastAPI routes run the real AST baseline checker. Verified by `test_api_e2e_security` and updated `test_api_skeleton.py`. |

## Files changed
- `src/gdg_yorku_submission/orchestrator.py`
- `src/gdg_yorku_submission/app.py`
- `src/gdg_yorku_submission/security/__init__.py`
- `src/gdg_yorku_submission/security/deterministic.py`
- `pyproject.toml`
- `tests/test_api_skeleton.py`
- `tests/test_security_deterministic.py`
- `.workflow/task-11/plan.md`
- `.workflow/task-11/state.json`
- `.workflow/task-11/traceability.md`
- `.workflow/task-11/verification.md`
- `.workflow/task-11/review.md`

## Verification performed
- Ran `pytest tests/test_security_deterministic.py` (9/9 passed).
- Ran entire project test suite: `pytest` (172/172 passed).

## Known gaps
None.

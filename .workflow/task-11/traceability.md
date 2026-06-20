# Traceability Matrix - Task 11

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-002, TASK-004 | `src/gdg_yorku_submission/security/deterministic.py` | `tests/test_security_deterministic.py` | `review.md` | completed |
| REQ-002 | AC-002 | DEC-002 | TASK-002, TASK-004 | `src/gdg_yorku_submission/security/deterministic.py` | `tests/test_security_deterministic.py` | `review.md` | completed |
| REQ-003 | AC-003 | DEC-003 | TASK-001, TASK-004 | `src/gdg_yorku_submission/orchestrator.py` | `tests/test_security_deterministic.py` | `review.md` | completed |
| REQ-004 | AC-004 | DEC-004 | TASK-003, TASK-004 | `src/gdg_yorku_submission/app.py` | `tests/test_security_deterministic.py` | `review.md` | completed |

## Decision References
- **DEC-001**: Implement the 6 AST-based rules using a helper AST visitor class for high precision and code structure isolation.
- **DEC-002**: Parse corpus file paths to collect extensions; count distinct unsupported non-python extensions for `complete_limited` status reason and `unsupported_language_count` metadata.
- **DEC-003**: Check if specialist returns standard List or Tuple containing status/reason overrides to update status in the Orchestrator without breaking stubs.
- **DEC-004**: Replace the stub security specialist call with the real generator call in `app.py`.

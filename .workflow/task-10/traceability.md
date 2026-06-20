# Traceability Matrix - Task 10

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-001 | `src/gdg_yorku_submission/correctness/methodology.md` | `tests/test_correctness_methodology.py` | `review.md` | completed |
| REQ-002 | AC-002 | DEC-002 | TASK-001, TASK-002 | `src/gdg_yorku_submission/correctness/methodology.md` | `tests/test_correctness_methodology.py` | `review.md` | completed |
| REQ-003 | AC-003 | DEC-003 | TASK-001, TASK-002 | `src/gdg_yorku_submission/correctness/methodology.md` | `tests/test_correctness_methodology.py` | `review.md` | completed |
| REQ-004 | AC-004 | DEC-004 | TASK-001, TASK-002 | `src/gdg_yorku_submission/correctness/methodology.md` | `tests/test_correctness_methodology.py` | `review.md` | completed |
| REQ-005 | AC-005 | DEC-005 | TASK-001, TASK-002 | `src/gdg_yorku_submission/correctness/methodology.md` | `tests/test_correctness_methodology.py` | `review.md` | completed |

## Decision References
- **DEC-001**: Place the rubric file at `src/gdg_yorku_submission/correctness/methodology.md` to keep it structured and close to correctness logic.
- **DEC-002**: Strip legacy out-of-scope topics entirely from active rules to prevent correctness agent distraction.
- **DEC-003**: Focus the methodology explicitly on intent, neutral divergence statements, traceability, and logic consistency.
- **DEC-004**: Explicitly list all nine standard schema fields (including `status` and `metadata`) to avoid field drift.
- **DEC-005**: Cap findings in no-spec repositories at `medium` severity to prevent LLM hallucinations from escalating.

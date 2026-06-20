# Final Report

## Summary

Implemented the budget-aware Correctness Agent Adapter using Vertex AI Gemini. Discovers the specification, runs the grounded review using a nonced evidence plane, translates redacted line coordinates back to original coordinates, validates findings schema and coordinate bounds, handles JSON parsing errors with retries, and enforces budget lease and cost caps inside the LLM client wrapper.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 | [budget.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/budget.py) implements RunBudget, BudgetLease, cost checking, and checker functions, integrated into Orchestrator state and synced with run metadata. |
| REQ-002 | [agent.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/correctness/agent.py) discovers SoT, builds evidence prompt, and makes grounded Gemini content calls. |
| REQ-003 | [agent.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/correctness/agent.py) sets skipped status and `no_spec_found_conformance_skipped` reason when SoT is absent. |
| REQ-004 | [agent.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/correctness/agent.py) runs `validate_correctness_finding`, maps coordinates, checks grounding, and verifies location/evidence coordinate existence. |

## Files changed

- `src/gdg_yorku_submission/budget.py`
- `src/gdg_yorku_submission/llm/gemini.py`
- `src/gdg_yorku_submission/correctness/agent.py`
- `src/gdg_yorku_submission/orchestrator.py`
- `src/gdg_yorku_submission/app.py`
- `tests/test_correctness_agent.py`
- `tests/test_api_skeleton.py`
- `tests/conftest.py`

## Verification performed

- Created unit/integration tests in [test_correctness_agent.py](file:///c:/Users/oalan/gdg-yorku-submission/tests/test_correctness_agent.py).
- Ran all tests via `pytest` (all 200 tests passed successfully).

## Known gaps

- **REQ-004 cap at medium on no-spec fallback**: The agent is configured to skip correctness review entirely when no spec is found and return status `skipped` with reason `no_spec_found_conformance_skipped`. Therefore, the no-spec logic cap at `medium` is enforced at the methodology layer (`validate_correctness_finding`) but is not active in the correctness agent itself since it skips.

## Follow-up tasks

- TASK-13: Implement the Coordinator Compiler.

## Archive decision

- Accepted

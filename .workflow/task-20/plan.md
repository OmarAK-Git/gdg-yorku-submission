# Workflow Plan - Task 20 (Remediation Pass & Coordinator Hardening)

## Goal
Remediate the Task 20/21 debate loop to make it functional on the real-LLM/HTTP path, enforce score/grounding-driven resolution logic, ensure deterministic ID generation for generative findings, bring Round 1 under the budget checks and exception handling, and add robust integration and invariant tests. Additionally, fix the pre-existing coordinator fake-LLM JSON mapping bug and harden HTTP debate path validation.

## Scope

### In scope
- Enforce deterministic mapping of resolutions in `src/gdg_yorku_submission/security/debate.py` based on `{verdict, groundedness, severity}`.
- Import `ROUND_1_INSTRUCTIONS` in `debate.py` to fix the NameError on the real path.
- Support async execution in `src/gdg_yorku_submission/orchestrator.py` via `run_specialist_async`.
- Update `src/gdg_yorku_submission/security/agent.py` and `src/gdg_yorku_submission/app.py` to execute the debate loop asynchronously in the running event loop without invoking a nested `anyio.run`.
- Hash citation and claim deterministically for generative findings in `debate.py` rather than using `uuid.uuid4()`.
- Wrap Round 1 under the same budget checks and try/except handling as rounds 2+ in `debate.py`.
- Improve error logging in `agent.py` to print exception type + message on fallback warnings, and avoid catching `BaseException`.
- Write the four new required tests validating real-path smoke, HTTP path, groundedness resolution logic, and generative ID determinism in `tests/test_debate_loop.py`.
- Fix coordinator fake-LLM compilation fallback bug by returning a valid JSON object matching `CoordinatorOutput` instead of a list when `USE_FAKE_LLM` is active in `src/gdg_yorku_submission/llm/gemini.py`.
- Harden `src/gdg_yorku_submission/coordinator/compiler.py` to raise a clear `ValueError` if the parsed JSON is not a dictionary.
- Update `test_http_debate_path` to assert on `compilation_mode != "terminal_fallback"`, ensure no fallback warnings are in logs, and assert that the seeded finding was resolved to `"contested"`.

### Out of scope
- Changing the core role definition (Gemini = defender, Claude = challenger).
- Re-adding any OpenAI or GPT references.

## Requirements

| ID | Requirement | Description |
|---|---|---|
| REQ-20-R1 | Score/Grounding Resolution | Map `accept` -> `survived`; `reject` + ungrounded -> `defeated`; `reject` + grounded + below-floor -> `defeated`; `reject` + grounded + at-or-above-floor -> `contested`; modify/unresolved -> `contested`. |
| REQ-20-R2 | Import NameError Fix | Import `ROUND_1_INSTRUCTIONS` from `personas.py` into `debate.py`. |
| REQ-20-R3 | Async Specialist Seam | Implement `run_specialist_async` in `orchestrator.py` and call it in `app.py` so FastAPI's HTTP path doesn't crash on nested loops. |
| REQ-20-R4 | Deterministic Generative IDs | Hash `groundednessCitation` + `claim` to derive stable finding IDs instead of using `uuid.uuid4()`. |
| REQ-20-R5 | Round 1 Budget and Try-Except | Bring Round 1 execution under the intrinsic budget check and exception handling/logging. |
| REQ-20-R6 | Warning-level Logging | Log fallback exception type and message at WARNING level, avoiding catching `BaseException`. |
| REQ-20-R7 | Coordinator Fake-LLM Fix | Conforms fake GeminiClient generate_content to response_schema, returning a JSON mapping for CoordinatorOutput. |
| REQ-20-R8 | Harden HTTP Debate Path Test | Assert `compilation_mode != terminal_fallback`, assert no falling back log, and assert `status == contested` in final report. |

## Risks & Mitigation
- **Risk**: Introducing event loop deadlock or collision if sync and async paths are mixed incorrectly.
- **Mitigation**: Implement `run_specialist_async` as a pure async function that directly awaits coroutines, and update `run_specialist` to safely use `anyio.run` ONLY when there is no active event loop running.
- **Risk**: breaking existing tests or regression in AST baseline.
- **Mitigation**: Run all 302 tests continuously.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_debate_loop.py` to verify all new and old tests pass.
- Run `pytest` on the entire suite to verify zero regressions.

### Integration / Invariant Tests to Add
1. **REAL-PATH smoke**: Run debate with dummy adapters, validating turn responses adapt correctly and no NameError is raised.
2. **HTTP debate path**: Simulate async `/review` upload with `ENABLE_SECURITY_DEBATE=true`, ensuring it executes the debate loop and does not fall back.
3. **Groundedness resolution**: Verify that grounded vs ungrounded findings behave differently upon `reject`.
4. **Generative ID determinism**: Verify that identical generative findings produced in separate runs result in identical IDs.

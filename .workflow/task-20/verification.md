# Verification Ledger - Task 20 (Remediation Pass & Coordinator Hardening)

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-20-1 | REQ-20-R1 | Score/Grounding Resolution | pytest tests/test_debate_loop.py -k test_groundedness_resolution | pass | pass | pass |
| VERIFY-20-2 | REQ-20-R2 | Import NameError Fix | pytest tests/test_debate_loop.py -k test_real_path_smoke | pass | pass | pass |
| VERIFY-20-3 | REQ-20-R3 | Async Specialist Seam | pytest tests/test_debate_loop.py -k test_http_debate_path | pass | pass | pass |
| VERIFY-20-4 | REQ-20-R4 | Deterministic Generative IDs | pytest tests/test_debate_loop.py -k test_generative_id_determinism | pass | pass | pass |
| VERIFY-20-5 | REQ-20-R5 | Round 1 Budget check | pytest tests/test_debate_loop.py -k test_budget_graceful_termination | pass | pass | pass |
| VERIFY-20-6 | REQ-20-R6 | Catch exception type + message | pytest tests/test_debate_loop.py | pass | pass | pass |
| VERIFY-20-7 | REQ-20-R7 | Coordinator Fake-LLM response shape | pytest tests/test_coordinator.py | pass | pass | pass |
| VERIFY-20-8 | REQ-20-R8 | Hardened HTTP Debate Path Test | pytest tests/test_debate_loop.py -k test_http_debate_path | pass | pass | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| None | N/A | N/A |

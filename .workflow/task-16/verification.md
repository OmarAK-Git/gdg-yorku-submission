# Verification Ledger - Task 16

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-16-1 | REQ-16-1 | Zip package exists and contains correct paths | `pytest tests/test_demo_sample.py -k test_demo_zip_structure` | pass | pass | completed |
| VERIFY-16-2 | REQ-16-2 | Tracked secret maps to HIGH | `pytest tests/test_demo_sample.py -k test_demo_secrets_severity` | pass | pass | completed |
| VERIFY-16-3 | REQ-16-3 | Ignored secret maps to INFO | `pytest tests/test_demo_sample.py -k test_demo_secrets_severity` | pass | pass | completed |
| VERIFY-16-4 | REQ-16-4 | AST security rules (SQLi, missing auth, verify=False, path traversal, shell_true, unsafe deserialize) detected | `pytest tests/test_demo_sample.py -k test_demo_ast_rules` | pass | pass | completed |
| VERIFY-16-5 | REQ-16-5 | Correctness coordinates parsing+grounding validated (detection deferred to Task 24) | `pytest tests/test_demo_sample.py -k test_demo_correctness` | pass | pass | completed |
| VERIFY-16-6 | REQ-16-6 | End-to-end Orchestrator review flow compiles cleanly | `pytest tests/test_demo_sample.py -k test_demo_e2e_run` | pass | pass | completed |

## Skipped checks
None.

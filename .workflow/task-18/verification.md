# Verification Ledger - Task 18

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-18-1 | REQ-18-1 | Ingestion works out-of-band | `python -m gdg_yorku_submission.demo_hooks drop-high samples/driftstore.zip` | Baseline errors == `[]` and output prints "Generated 7 input findings." | Baseline verified clean, inputs generated successfully | completed |
| VERIFY-18-2 | REQ-18-2 | `drop-high` outputs exact omission error | `pytest tests/test_validator_demo_hook.py -k test_run_demo_drop_high_direct` | Exact validation error matches dropped finding ID and severity | Validation error matched exactly, exit code 1 | completed |
| VERIFY-18-3 | REQ-18-2 | `corrupt-location` coordinate bounds check | `pytest tests/test_validator_demo_hook.py -k test_run_demo_corrupt_location_direct` | Location out-of-bounds error matched exactly | validation error matched exactly, exit code 1 | completed |
| VERIFY-18-4 | REQ-18-2 | `corrupt-evidence-ref` coordinate bounds check | `pytest tests/test_validator_demo_hook.py -k test_run_demo_corrupt_evidence_ref_direct` | Evidence reference out-of-bounds error matched exactly | validation error matched exactly, exit code 1 | completed |
| VERIFY-18-5 | REQ-18-2 | `leak-secret` error redaction check | `pytest tests/test_validator_demo_hook.py -k test_run_demo_leak_secret_direct` | Raw secret is redacted in stdout and replaced with safe placeholder | Asserted raw secret absent and placeholder present | completed |
| VERIFY-18-6 | REQ-18-3 | HTTP/Router isolation test | `pytest tests/test_validator_demo_hook.py -k test_http_and_production_isolation` | All production modules parse correctly, no imports found, pyproject checked | Asserted 0 imports and pyproject.toml clean | completed |

## Skipped checks
* None

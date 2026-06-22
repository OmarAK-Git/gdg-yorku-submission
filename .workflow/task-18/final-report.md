# Final Report - Task 18 (Out-of-Band Validator-Rejection Demo Hook)

## Summary
Successfully implemented the out-of-band validator-rejection hook CLI tool under `src/gdg_yorku_submission/demo_hooks.py` and its corresponding test suite under `tests/test_validator_demo_hook.py`. The tool manual-corrupts reports using the `drop-high`, `corrupt-location`, and `corrupt-evidence-ref` actions, executing the report validator and printing the rejection errors. The `leak-secret` action validates the real secret redaction invariant on the serialized report. The test suite asserts HTTP/production route isolation.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-18-1 | CLI commands `python -m gdg_yorku_submission.demo_hooks <action> <zip_path>` run successfully out-of-band. |
| REQ-18-2 | Ingestion validated clean via negative control checks. Actions `drop-high`, `corrupt-location`, and `corrupt-evidence-ref` trigger expected report validation errors. The `leak-secret` action verifies that raw secrets are absent from both the redacted corpus text and the unmodified serialized report output, while only salted fingerprints are surfaced. |
| REQ-18-3 | Complete HTTP isolation: tests verify no production module imports `demo_hooks.py` and it is not registered as a console script in `pyproject.toml`. |

## Files changed
- `src/gdg_yorku_submission/demo_hooks.py` [NEW]
- `tests/test_validator_demo_hook.py` [NEW]
- `docs/demo-script.md` [NEW]

## Verification performed
- Ran manual test commands:
  - `python -m gdg_yorku_submission.demo_hooks drop-high samples/driftstore.zip` (exits 1, outputs omission error).
  - `python -m gdg_yorku_submission.demo_hooks corrupt-location samples/driftstore.zip` (exits 1, outputs location coordinate error).
  - `python -m gdg_yorku_submission.demo_hooks corrupt-evidence-ref samples/driftstore.zip` (exits 1, outputs evidence-ref coordinate error).
  - `python -m gdg_yorku_submission.demo_hooks leak-secret samples/driftstore.zip` (exits 0, asserts PASS and dynamic fingerprint is present).
- Ran automated test suite:
  - `pytest tests/test_validator_demo_hook.py` (9 tests passed, including unredacted failure check).
  - `pytest` (278 tests passed).

## Known Gaps & Framing Limitations
- **Upstream Prevention vs. Backstop Verification**: The `drop-high` scenario validates the report validator's backstop check. However, in the production coordinator, high/critical findings are prevented from being omitted by default schema constraints. Thus, this demo verifies a last-line-of-defense validator capability for an upstream-prevented state.
- **Demo Hard-Aborts vs. Production Fallback**: The demo CLI is framed as a hard gate (exiting with code `1`) to highlight validation detection on camera. In contrast, the production environment follows the "never-fails" contract, where validator failure triggers warnings and falls back to a valid zero-LLM terminal report rather than terminating the run.
- **Validator Warnings Raw Append Leak Gap**: Production validator warning logs are appended raw (`orchestrator.py:369–378`) and are not independently re-redacted if a raw secret ends up inside them. This demo does not cover that path (separate hardening path). Instead, the redaction safety holds on the compiled report surface because raw secrets are fully redacted from the corpus upstream during pre-flight.

## Follow-up tasks
- Upgrades or close-out integration tests.

## Archive decision
- Accepted

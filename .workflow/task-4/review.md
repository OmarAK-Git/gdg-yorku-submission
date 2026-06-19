# Review

## Spec compliance review
- The abstract `Orchestrator` base class is defined as the thin interface seam [R8].
- Both `InProcessOrchestrator` and `AdkOrchestrator` implement the seam, sharing core logic to avoid behavior drift, and behave identically across all state transitions.
- State is deep-copied at `read_state()` and `write_findings()` to guarantee data isolation and prevent memory aliasing.
- Specialist errors are caught inside `run_specialist` and logged as `failed` status in the perspective status without aborting the overall run.
- Perspectives are validated at the entry of `run_specialist` and `write_findings` to prevent validation errors during fail-status creation.
- Ingestion errors abort (invalid zip files or corrupt archives throw HTTP 400 immediately).
- ID finalization is executed correctly before compiling the report, mapping provisional findings to finalized deterministic stable IDs, and updating the perspective status `finding_ids`.
- Contested findings are correctly placed in the `omitted` ledger to satisfy conservation equations (`included U merged_inputs U omitted == total_inputs`).
- `high_critical_findings` is strictly a subset of `findings` (containing only active high/critical findings).
- The FastAPI `/review` endpoint accepts zip files and returns a schema-valid `ReviewReport` containing all statuses, severity counts, findings, and accounting ledger.
- Production HTTP route contains no fault-injection testing parameters; tests run failures via python monkeypatching.

## Code quality review
- Eliminated code duplication by centralizing execution logic in the base `Orchestrator` class.
- Avoided environment leaks in testing by auto-clearing the ADK store via a conftest fixture.
- Pruned dead imports from `orchestrator.py`.

## Risk review
- Completely mitigates ADK single-point-of-failure risk by ensuring a shared logic base and verified equivalence in differential test.
- Mitigates memory leak concerns in `AdkOrchestrator` by enforcing a 100-run size limit.

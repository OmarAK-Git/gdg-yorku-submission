# Traceability Matrix - Task 13

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-001, TASK-002 | `compiler.py:run_coordinator_compilation` | `test_coordinator.py:test_compile_report_successful_mock_gemini_call` | accepted | accepted |
| REQ-002 | AC-002 | DEC-002 | TASK-002 | `compiler.py:reconstruct_report_components` | `test_coordinator.py:test_validator_rejects_severity_downgrade_and_upgrade_on_merge`, `test_merged_id_stability_cross_run` | accepted | accepted |
| REQ-003 | AC-003 | DEC-003 | TASK-002, TASK-003 | `compiler.py:validate_report_invariants` | `test_coordinator.py:test_validator_detects_high_omission_direct`, `test_validator_detects_cross_perspective_merge_direct`, `test_validator_detects_holed_ledger`, `test_validator_detects_double_counted_ledger`, `test_validator_detects_unknown_id_in_ledger`, `test_validator_rejects_finding_out_of_bounds_location` | accepted | accepted |
| REQ-004 | AC-004 | DEC-004 | TASK-004 | `orchestrator.py:compile_terminal_report` | `test_coordinator.py:test_terminal_fallback_sanitizes_bad_coordinates`, `test_compile_report_budget_exhaustion_fallback`, `test_terminal_report_sanitizes_gate_findings_and_never_raises` | accepted | accepted |

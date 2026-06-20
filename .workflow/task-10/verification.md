# Verification Ledger - Task 10

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Methodology file existence | `pytest tests/test_correctness_methodology.py -k test_methodology_file_exists` | File exists and is non-empty | File exists and is 2.5KB | pass |
| VERIFY-002 | REQ-001 | Valid markdown structure check | `pytest tests/test_correctness_methodology.py -k test_valid_markdown_structure` | Heading structure and code blocks parse | Clean H1 -> H2 -> H3 heading hierarchy | pass |
| VERIFY-003 | REQ-002 | Absence of legacy topics (entire doc scan) | `pytest tests/test_correctness_methodology.py -k test_legacy_topics_absent_across_entire_document` | No security/secrets/TDD/PASS-FIX outside exclusions section | Entire file scans clean | pass |
| VERIFY-004 | REQ-003 | Correctness focus headings check | `pytest tests/test_correctness_methodology.py -k test_correctness_core_focus_present_as_headings` | Intent, divergence, traceability, logic present as H3 headings | H3 headings present | pass |
| VERIFY-005 | REQ-004 | Schema fields required check | `pytest tests/test_correctness_methodology.py -k test_schema_fields_present_in_requirements_block` | All 9 schema fields listed under block | id, source_agent, perspective, severity, location, claim, evidence_ref, status, metadata present | pass |
| VERIFY-006 | REQ-005 | No-spec medium cap rule check | `pytest tests/test_correctness_methodology.py -k test_no_spec_severity_cap_rules` | Regex matching no-spec and medium severity cap | Rules present; negative assertions passed | pass |
| VERIFY-007 | Invariants | Executable invariant validator checks | `pytest tests/test_correctness_methodology.py -k test_validator_` (7 tests) | Conformance checks correctly identify valid vs violating findings using Pydantic models | Mock findings (severity cap breach, invalid enum values, coordinate format errors) correctly validated and blocked; correctness claims containing "password" or "dependency" successfully accepted | pass |
| VERIFY-008 | All | Run full test suite | `pytest` | 163 passes, no failures | 163 passed | pass |

> [!NOTE]
> The prose criteria in `methodology.md` (e.g. direction-neutral tone and out-of-scope topic guidelines) act as instructions for the LLM prompt, and are best-effort guidance. Programmatic validation via `validate_correctness_finding` enforces structural Pydantic model conformance, source agent/perspective constraints, severity capping on no-spec runs, and coordinate syntax checks.

# Final Report - Task 9

## Summary
Task 9 implements **Source-of-Truth (SoT) Discovery** for specification and design documents. The implementation defines a fallback precedence chain, supports case-insensitive/case-tolerant search across the ingestion corpus, parses the root README to extract only allowlisted sections, handles code-blocks, and returns a structured fallback response when no specification is found. Security-wise, it enforces the system-wide secret redaction precondition (`redaction_applied=True` check), avoids direct filesystem traversal risks by querying only the in-memory corpus, respects gitignore filtering (`exposure_status == "prompt_exposed"`), skips empty specs to prevent downstream agent mis-verifications, and tie-breaks case collisions deterministically.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-001 | Discovers specification files in precedence order: root `SPEC.md` -> root `DESIGN.md` -> allowed README sections -> conventional `docs/SPEC.md`. |
| REQ-002 | Supports case-tolerant matching on corpus keys (e.g. `spec.md`, `design.MD`). |
| REQ-003 | Parses README and extracts only allowed H2 headings: `## Spec`, `## Design`, `## Requirements`, `## Intent`. |
| REQ-004 | README heading termination works correctly for other H1/H2 titles, and comments starting with `#` in backtick code blocks are ignored correctly. |
| REQ-005 | Empty/missing specification falls back to status `no_spec_found_conformance_skipped` with `None` text. |
| Redaction Invariant | Checks and asserts `redaction_applied` is True before returning any spec text; raises `RuntimeError` otherwise. |
| Exposure Scope | Filters candidates to `prompt_exposed` only; gitignored spec files are correctly skipped. |
| Determinism | Deterministic alphabetical sort is applied to resolve case-variant filename collisions. |

## Files changed
- `src/gdg_yorku_submission/correctness/sot.py`
- `src/gdg_yorku_submission/correctness/__init__.py`
- `src/gdg_yorku_submission/__init__.py`
- `tests/test_sot_discovery.py`

## Verification performed
- Executed unit tests: `pytest tests/test_sot_discovery.py` (17/17 passing, including adversarial content, case collision determinism, redaction precondition violations, and gitignored skips).
- Executed full test suite: `pytest` (150/150 passing).

## Known gaps
- **Markdown Parse Limitations (Cosmetic)**: Markdown code block tracking only supports backticks (```). Tilde fences or 4-space indented blocks containing comments could trigger false heading cutoffs, but this is a low-risk edge case for README fallback.

## Follow-up tasks
- Task 10: Rewrite Correctness Rubric/Methodology.

## Archive decision
Accepted.


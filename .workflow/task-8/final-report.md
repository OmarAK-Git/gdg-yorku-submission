# Final Report

## Summary
Task 8 implements the `Evidence-Plane Prompt Builder (Nonced)` which isolates untrusted repository source code and specifications from the trusted instruction channel using a per-run random nonce. Following a gate review, the implementation was hardened against path injection vulnerabilities, dynamic noncing was extended to file boundaries, structural assertions were made non-vacuous, negative breakout tests for unguessable nonces were added, and line conservation (R5) and output determinism checks were implemented.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-001 | Generates unique per-run cryptographically secure random nonces (32-character hex). |
| REQ-002 | Processes only prompt-exposed files and formats them using redacted content. |
| REQ-003 | Outer evidence plane wrapped inside nonced XML-style tags, and inner file boundaries nonced using `<file nonce="NONCE" path="PATH">` and `</file nonce="NONCE">`. |
| REQ-004 | Sanitizes untrusted paths and content to prevent quote breakout, newline injections, and delimiter breakout. |

## Files changed
- `src/gdg_yorku_submission/prompts/__init__.py`
- `src/gdg_yorku_submission/prompts/evidence_plane.py`
- `src/gdg_yorku_submission/__init__.py`
- `tests/test_evidence_plane.py`

## Verification performed
- Executed unit tests: `pytest tests/test_evidence_plane.py` (9/9 passing).
- Executed full test suite: `pytest` (125/125 passing).

## Known gaps
- The redaction precondition is currently a documented, unenforced contract in the builder. Verification that only redacted text is passed in the production request pipeline is deferred to the end-to-end integration tests in Task 23.

## Follow-up tasks
- Task 9: Source-of-Truth Discovery.

## Archive decision
Accepted.

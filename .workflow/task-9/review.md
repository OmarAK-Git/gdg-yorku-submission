# Review - Task 9

## Spec compliance review
- Ensure SoT Discovery order: root `SPEC.md` -> root `DESIGN.md` -> allowed README sections -> `docs/SPEC.md` -> no-spec fallback is implemented exactly.
- Verify allowlist headers are case-tolerant or exact as per design choice, but strictly matching allowlisted terms.
- Confirm README heading parsing doesn't over-extract or under-extract.
- Enforce the system-wide secret redaction invariant: SoT text is only matched and retrieved if it is in the corpus and has had secret scanning applied (`redaction_applied=True`).
- Filter selection to `prompt_exposed` files only so gitignored/system-excluded specs cannot steer prompt context.

## Code quality review
- Verify that `sot.py` uses proper typing (e.g. `Optional`, `Dict`, Pydantic types).
- Verify standard imports and normalized forward slashes for cross-platform robustness.
- Ensure case-insensitivity uses keys matched on memory dict, making it fully OS-independent and deterministic.

## Risk review
- Injection or traversal risk: Completely resolved filesystem traversal/leak risk by eliminating direct file system reads. All queries are resolved entirely from the in-memory ingestion `corpus`.
- Precondition validation: Raises `RuntimeError` if secret scan has not been completed first, closing potential credential leak vectors.
- Empty specs: Prevented downstream correctness agent errors by ensuring files containing only whitespace are skipped rather than returning empty specification text.
- Case collisions: Alphabetical sort deterministically tie-breaks case-variant name collisions.

## Human review notes
- Markdown parsing support for code blocks is backtick-only. Tilde or indented code blocks containing comments could still toggle the header parser, but these are out of scope for README-as-SoT fallback.


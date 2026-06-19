# Final Report

## Summary
Task 6 implements the exposure-model prompt corpus. It classifies files into the spec-mandated three-value trust boundary exposure status: `prompt_exposed`, `ignored_by_root_gitignore`, and `excluded_by_system`. It uses `pathspec` to parse the root `.gitignore` file with GitIgnore wildmatch semantics. It wraps files as `CorpusFile` models that track original/redacted text and map line counts to ensure findings resolve back to original developer coordinates. 

Additionally, we addressed the new refined issues N1-N4:
- **N1 & N3 (Exposure Triad Alignment)**: We confined `ExposureStatus` exactly to the three spec-defined trust boundary categories. We introduced `IngestStatus` (`"success"`, `"security_skip"`, `"read_failure"`) to track operational state separate from trust boundary classification. Missing/unreadable files and skipped files correctly map to `"excluded_by_system"` under the exposure triad to keep Task 14 conservation simple and robust.
- **N2 (Tolerant Decoding)**: We updated `build_corpus` to decode files tolerantly using `errors="replace"`. Added `test_non_utf8_tolerant_read` asserting that non-UTF-8 files (like Latin-1) are processed successfully with content preserved for scanning.
- **N4 (Conservation & Collisions)**: We added duplicate path checking in `build_corpus` to raise `ValueError` on collisions, and asserted conservation (`len(corpus) == len(extracted_files) + len(skipped_files)`) at compile time.

## Completed requirements
| Requirement | Evidence |
|---|---|
| REQ-001 | Handled via `classify_exposure` and verified in unit tests (including read failures and determinism). |
| REQ-002 | Implemented `.gitignore` wildmatch loading via `pathspec` in `load_root_gitignore` (including negation). |
| REQ-003 | Defined `CorpusFile` in `schemas.py` with `map_line` helper (including shifted line mapping test). |
| REQ-004 | Skips and labels system-excluded and security rejected files as `excluded_by_system` in terms of exposure, while tracking operational status in `ingest_status`. |

## Files changed
- [schemas.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/schemas.py)
- [corpus.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/corpus.py)
- [app.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/app.py)
- [__init__.py](file:///c:/Users/oalan/gdg-yorku-submission/src/gdg_yorku_submission/__init__.py)
- [test_corpus.py](file:///c:/Users/oalan/gdg-yorku-submission/tests/test_corpus.py)

## Verification performed
- Created full suite of unit tests in `tests/test_corpus.py`.
- Executed `pytest` running 100 tests in total, all passing successfully.

## Known gaps
- None (nested `.gitignore` is deferred to V1.1 as per spec).

## Follow-up tasks
- Task 7 (Secret Scanner + Redaction Invariant)

## Archive decision
- Accepted

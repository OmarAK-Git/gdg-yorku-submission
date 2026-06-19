# Workflow Plan - Task 6

## Goal
Implement the exposure-model prompt corpus. It classifies ingested files into `prompt_exposed`, `ignored_by_root_gitignore`, or `excluded_by_system`. It uses `pathspec` to parse the root `.gitignore` file with `GitWildMatch` semantics. It wraps files as `CorpusFile` models that track original/redacted text and map line counts to ensure findings can resolve to original coordinates.

## Scope

### In scope
- Parse root `.gitignore` using `pathspec.PathSpec` with `GitWildMatch` pattern matching.
- Read/classify files in workspace:
  - `prompt_exposed`: Included/extracted and not ignored.
  - `ignored_by_root_gitignore`: Extracted but matched by `.gitignore` (which might be in the root).
  - `excluded_by_system`: Skipped files in ingestion manifest with reason matching system excludes/binaries, or explicitly identified.
- Wrap all extracted files as `CorpusFile` structures:
  - `normalized_path`: Relative path.
  - `original_text`: Exact content.
  - `redacted_text`: Content to use (can be identical to original_text initially, or redacted via secret gate later).
  - `original_line_count`: Total line count of original file.
  - `redacted_to_original_line_map`: Mapping lines if line count changes (otherwise 1-to-1).
  - `evidence_ref`: Citation coordinate.
- Integrate gitignore matching into ingestion or a separate corpus module.

### Out of scope
- Parsing nested/sub `.gitignore` files (deferred to V1.1).
- Consulting the local Git index or CLI Git command.
- Doing secret scans or redaction (this is Task 7).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Classify files into exact exposure categories: `prompt_exposed`, `ignored_by_root_gitignore`, and `excluded_by_system`. |
| REQ-002 | Use `pathspec.PathSpec` with `GitWildMatch` patterns to parse root `.gitignore` (if present) for matching. |
| REQ-003 | Define `CorpusFile` schema to preserve original/redacted text, line counts, and line mappings. |
| REQ-004 | Exclude binary and system excluded files as `excluded_by_system` in the exposure model. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | A file is classified correctly depending on its status (extracted vs skipped, ignored vs not ignored). |
| AC-002 | REQ-002 | Root `.gitignore` is parsed, supports negations (using `!`), and matches paths correctly. |
| AC-003 | REQ-003 | `CorpusFile` model correctly captures fields and exposes a method to resolve redacted lines to original line coordinates. |
| AC-004 | REQ-004 | System-excluded and binary files are correctly flagged under the `excluded_by_system` category. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Define `CorpusFile` model in `schemas.py` | `src/gdg_yorku_submission/schemas.py` | pending |
| TASK-002 | Implement root `.gitignore` parsing and exposure-model classification in a new `corpus.py` or updated `ingestion.py` | `src/gdg_yorku_submission/corpus.py` | pending |
| TASK-003 | Create unit tests to verify exposure model, pathspec matching, and `CorpusFile` mapping | `tests/test_corpus.py` | pending |

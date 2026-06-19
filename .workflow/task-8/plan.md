# Workflow Plan - Task 8

## Goal
Delimit untrusted content using per-run random nonced separators to prevent prompt injection and secure the evidence plane.

## Scope

### In scope
- Implement prompt builder utility that structures untrusted workspace/spec files within nonced XML-style tags.
- Sanitize and escape potentially malicious delimiters or nonces within the corpus files.
- Ensure only prompt-exposed files are formatted using their redacted contents.
- Implement comprehensive unit tests confirming delimiters cannot be broken out of.

### Out of scope
- Implementing the correctness specialist agent (Task 12).
- Source-of-Truth discovery logic (Task 9).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Dynamic per-run random nonce generation for evidence plane delimiters. |
| REQ-002 | Prompt-exposed files wrapped inside `<file path="...">` tags, utilizing `redacted_text` only. |
| REQ-003 | Outer evidence plane wrapped inside `<evidence_plane nonce="NONCE">` tags. |
| REQ-004 | Neutralize occurrence of tag patterns or the nonce within the file content to prevent breakout. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Nonces are generated as cryptographically secure random values unique to each run. |
| AC-002 | REQ-002 | Only `prompt_exposed` files are formatted; `ignored_by_root_gitignore` / `excluded_by_system` files are excluded from the prompt. |
| AC-003 | REQ-003 | XML structure has nonced boundaries. |
| AC-004 | REQ-004 | An injection attempt (e.g. file content containing `</evidence_plane nonce="..."` or the literal closing tags) is sanitized so the XML parses as literal content and instructions inside the file cannot breakout. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Implement evidence plane prompt builder | `src/gdg_yorku_submission/prompts/evidence_plane.py` | pending |
| TASK-002 | Implement unit tests for breakout & formatting | `tests/test_evidence_plane.py` | pending |

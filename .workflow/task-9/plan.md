# Workflow Plan - Task 9

## Goal
Implement the Source-of-Truth (SoT) Discovery logic to find specification and design files in the repository corpus. If no spec is found, define a structured no-spec fallback representation.

## Scope

### In scope
- Define SoT Discovery ordering: root `SPEC.md` -> root `DESIGN.md` -> README intent sections (selected only via a fixed heading allowlist: `## Spec`, `## Design`, `## Requirements`, `## Intent`) -> conventional `docs/SPEC.md`.
- Implement case-tolerant and robust file discovery.
- Implement Markdown parsing logic to extract README intent sections, stopping at next heading of same or higher level (H1 or non-allowed H2) but continuing across consecutive/multiple allowed headings.
- Define a structured `SotDiscoveryResult` schema that holds the discovered text, source path, source type, and status.
- Implement a comprehensive unit test suite with fixtures covering all paths of the discovery chain, case-insensitivity, README parsing edge cases, and the no-spec fallback.

### Out of scope
- Correctness agent prompting and Vertex AI Gemini adapter integration (Task 10/12).
- Deterministic AST security scanning (Task 11).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Discovers SoT files in the exact precedence order: root `SPEC.md` -> root `DESIGN.md` -> allowed README sections -> `docs/SPEC.md`. |
| REQ-002 | Allows case-tolerant filename matching (e.g. `spec.md`, `DESIGN.MD`) for robustness on different filesystems. |
| REQ-003 | Parses root README file and extracts only allowlisted H2 sections: `## Spec`, `## Design`, `## Requirements`, `## Intent`. |
| REQ-004 | README extraction terminates at any H1 (`#`) or non-allowed H2 (`##`) heading, but includes subheadings (H3+) and supports multiple allowed sections. |
| REQ-005 | Emits a structured `no_spec_found_conformance_skipped` status with `None` text when no specification/design sources are found. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | If root `SPEC.md` exists, it is selected. Otherwise, if root `DESIGN.md` exists, it is selected. Otherwise, allowed README sections are extracted. Otherwise, `docs/SPEC.md` is selected. |
| AC-002 | REQ-002 | Filenames like `spec.md` or `design.md` are correctly matched during discovery even if the casing differs from `SPEC.md` or `DESIGN.md`. |
| AC-003 | REQ-003 | README sections NOT in the allowlist (e.g., `## Installation`, `## Usage`) are completely omitted from the extracted text. |
| AC-004 | REQ-004 | Subheadings (e.g., `### Details`) under allowed README headings are correctly included. |
| AC-005 | REQ-005 | If none of the spec options are found, `discover_sot` returns a result indicating no spec was found and status is `no_spec_found_conformance_skipped`. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Implement SoT discovery module | `src/gdg_yorku_submission/correctness/sot.py` | pending |
| TASK-002 | Implement unit tests for SoT discovery | `tests/test_sot_discovery.py` | pending |

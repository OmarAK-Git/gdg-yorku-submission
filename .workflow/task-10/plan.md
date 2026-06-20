# Workflow Plan - Task 10

## Goal
Author correctness-only review criteria (rubric/methodology) for the correctness agent, ensuring it is correctness-only, specifies required schema fields, and caps no-spec findings at `medium`.

## Scope

### In scope
- Create `src/gdg_yorku_submission/correctness/methodology.md` with the new correctness-only methodology.
- Ensure the methodology covers:
  - Intent extraction
  - Spec-code divergence (direction-neutral, e.g. "code and SPEC.md disagree at X")
  - Traceability
  - Logic-vs-spec consistency checking
- Remove legacy requirements: secret hygiene, security blockers, evidence/dependency handling, TDD/Antigravity-PASS/FIX sections.
- Specify requirements for emitting schema-valid findings.
- Specify that when no specification exists, findings are capped at `medium` severity.
- Create unit tests in `tests/test_correctness_methodology.py` to statically verify that the rubric conforms to these design constraints and that the rubric file itself contains the required rules.

### Out of scope
- Correctness agent prompting and LLM execution (Task 12).
- Security baseline checks (Task 11).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Create a correctness-only review methodology file in markdown format at `src/gdg_yorku_submission/correctness/methodology.md`. |
| REQ-002 | The methodology must strip out secret hygiene, security blockers, evidence/dependency handling, and TDD/Antigravity-PASS/FIX instructions. |
| REQ-003 | The methodology must focus on: intent extraction, spec-code divergence (direction-neutral), traceability, and logic-vs-spec. |
| REQ-004 | The methodology must specify required schema fields for findings. |
| REQ-005 | The methodology must enforce that no-spec findings (conformance skipped, logic-only consistency checks) are capped at `medium` severity. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | The file `src/gdg_yorku_submission/correctness/methodology.md` is present and formatted in valid Markdown. |
| AC-002 | REQ-002 | Static validation checks that terms like "secret", "password", "credential", "TDD", "Antigravity", "PASS/FIX", "dependency" (as code dependencies) do not exist in the methodology.md as primary criteria. |
| AC-003 | REQ-003 | The methodology contains explicit sections/rules for intent extraction, spec-code divergence (which must be direction-neutral), traceability, and logic-vs-spec. |
| AC-004 | REQ-004 | The methodology lists the schema fields: `id`, `source_agent`, `perspective`, `severity`, `location`, `claim`, `evidence_ref`. |
| AC-005 | REQ-005 | The methodology explicitly limits the severity of findings without a specification to at most `medium`. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Author `src/gdg_yorku_submission/correctness/methodology.md` | `src/gdg_yorku_submission/correctness/methodology.md` | pending |
| TASK-002 | Implement unit tests for methodology criteria | `tests/test_correctness_methodology.py` | pending |

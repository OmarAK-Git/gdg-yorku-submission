# Workflow Plan - Task 19 (Debate Data Model)

## Goal
Design and implement robust Pydantic schemas for the security debate loop, representing debate rounds, candidate findings, debate resolutions (survived, defeated, contested), and debate sessions.

## Scope

### In scope
- Create `src/gdg_yorku_submission/security/debate_schema.py` containing Pydantic models for the debate loop:
  - `DebateMessage`: Represents a message in a debate round.
  - `DebateRound`: Represents a debate round containing messages.
  - `DebateCandidate`: Represents a candidate finding under debate with a resolution status (`survived`, `defeated`, `contested`).
  - `DebateLedger`: Represents the debate outcome tracker, providing helpers to separate candidates into survived, defeated, and contested lists.
  - `DebateSession`: Represents a complete debate session containing the ledger, rounds, and metadata.
- Create `tests/test_debate_schema.py` to verify schema validation, edge cases, default values, and helper methods.
- Integrate the debate schema in `src/gdg_yorku_submission/security/__init__.py`.

### Out of scope
- Implementing the actual LLM-based debate loop or stop conditions (Task 20).
- Integrating debate outcomes with the Orchestrator or Coordinator runner (Task 21).

## Requirements
| ID | Requirement |
|---|---|
| REQ-19-1 | **Schema Definitions**: Define Pydantic models for debate round messages, rounds, candidates, ledger, and session, utilizing Pydantic V2 configuration (`extra="forbid"`). |
| REQ-19-2 | **Resolution Outcomes & Boundary Validation**: Every challenger candidate must resolve to `survived`, `defeated`, or `contested`. Unresolved candidates (resolution=None) raise a `ValueError` during boundary validation (`validate_completeness`). A defeated finding must require a non-empty `closed_reason` string. |
| REQ-19-3 | **At-or-Above Floor Preservation & K-Cap**: Provide helper logic to compile/partition debate ledger results. High/critical defeated findings and contested findings must remain visible as `contested` status (carrying `closed_reason` in `metadata` for promoted ones), while survived findings become `active` status. Apply K-cap checks to truncate excess below-floor contested findings. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-19-1 | REQ-19-1 | Debate schemas validate successfully using Pydantic V2. Invalid inputs raise `ValidationError`. |
| AC-19-2 | REQ-19-2 | `closed_reason` validation checks: `defeated` status requires `closed_reason`, while `survived` and `contested` must not have it. Boundary checks throw errors if any candidate is unresolved. |
| AC-19-3 | REQ-19-3 | Ledger helper functions correctly filter and categorize findings, preserving high/critical defeated/contested findings, carrying forward reason rationale, and enforcing contested K-cap rules. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-19-1 | Create `src/gdg_yorku_submission/security/debate_schema.py` | `src/gdg_yorku_submission/security/debate_schema.py` | completed |
| TASK-19-2 | Update `src/gdg_yorku_submission/security/__init__.py` | `src/gdg_yorku_submission/security/__init__.py` | completed |
| TASK-19-3 | Create `tests/test_debate_schema.py` | `tests/test_debate_schema.py` | completed |
| TASK-19-4 | Run verification and update memory bank / workflow reports | None | completed |

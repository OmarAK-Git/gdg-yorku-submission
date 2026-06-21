# Workflow Plan - Task 16 (Pinned Demo Sample)

## Goal
Build and verify the demo repository `samples/driftstore` (packaged as `samples/driftstore.zip`) to trigger the required review findings (tracked secret, gitignored secret, correctness divergence, and deterministic AST security issues), and write automated tests under `tests/test_demo_sample.py` verifying the LLM-free path.

## Scope

### In scope
- Create the demo project directory `samples/driftstore/` with the following files:
  - `SPEC.md`: Specification with correctness requirements.
  - `.gitignore`: Configured to ignore `.env` and `*.db`.
  - `.env`: Contains a synthetic database password.
  - `src/app.py`: Contains a tracked Google API key, path traversal, SQL injection, missing auth, and verify=False HTTP calls.
  - `tests/`: Dummy test directory/files to simulate a test suite.
- Create `samples/driftstore.zip` dynamically or statically.
- Implement `tests/test_demo_sample.py` asserting:
  - Ingestion and exposure classification.
  - Pre-flight secret scan split (HIGH for prompt_exposed, INFO for ignored).
  - Promoted secret finding is included in coordinator ledger.
  - Deterministic AST security rule triggers.
  - Correctness agent mock and/or actual output runs.
  - End-to-end Orchestrator run compiling a final accepted report.

### Out of scope
- Implementing the debate loop (Task 21) or Orbit blast-radius (Task 22).

## Requirements
| ID | Requirement |
|---|---|
| REQ-16-1 | **Demo Repository Structure**: Provide `samples/driftstore` with `SPEC.md`, `.gitignore`, `.env`, `src/app.py`, and `tests/`. |
| REQ-16-2 | **Tracked Secret finding**: Trigger a tracked secret mapped to `HIGH` severity. |
| REQ-16-3 | **Ignored Secret finding**: Trigger an ignored secret in `.env` mapped to `INFO` severity. |
| REQ-16-4 | **AST Security Violations**: Trigger `missing_auth`, `sqli`, `verify_false`, and `path_traversal` baseline findings. |
| REQ-16-5 | **Correctness Divergence**: Verify coordinate parsing+grounding of correctness findings, deferring LLM detection to Task 24. |
| REQ-16-6 | **E2E Compilation**: Run full pipeline to compile the report successfully. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-16-1 | REQ-16-1 | `samples/driftstore.zip` is built and contains all listed files. |
| AC-16-2 | REQ-16-2 | Tracked Google API Key is prompt-exposed and mapped to `HIGH` severity. |
| AC-16-3 | REQ-16-3 | Ignored DB password is gitignored and mapped to `INFO` severity. |
| AC-16-4 | REQ-16-4 | AST checkers identify SQLi, shell_true, unsafe_deserialize, missing auth, path traversal, and verify=False. |
| AC-16-5 | REQ-16-5 | Correctness agent validation successfully passes coordinates and cites `SPEC.md` (LLM detection deferred to Task 24). |
| AC-16-6 | REQ-16-6 | E2E integration test completes successfully on both in-process and ADK orchestrators. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-16-1 | Create `samples/driftstore/` source files | `samples/driftstore/*` | completed |
| TASK-16-2 | Build `samples/driftstore.zip` package | `samples/driftstore.zip` | completed |
| TASK-16-3 | Implement unit/integration tests in `tests/test_demo_sample.py` | `tests/test_demo_sample.py` | completed |

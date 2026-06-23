# Workflow Plan - Task 24: Real-LLM Smoke Script & Google ADK Integration

## Goal
Implement a live-run smoke script (`scripts/run_sample_review.py`) and corresponding unit tests (`tests/test_run_sample_script.py`) to execute a full repository review on a sample zip file. Integrate Google ADC-first authentication across Gemini and Claude, update default model versions, cap Claude's reasoning effort, close verification gaps, and integrate genuine Google ADK support for the ADK orchestrator.

## Scope

### In scope
- Creation of `scripts/run_sample_review.py` with all required flags and preflight credentials checks.
- Routing all real LLM calls through Google Cloud ADC / Vertex AI:
  - `llm/gemini.py` (GeminiClient) tries Vertex/ADC first, falls back to `genai` with `GEMINI_API_KEY`.
  - `security/gemini_adapter.py` (call_gemini_adversary) tries Vertex/ADC first, falls back to `genai`.
  - `security/claude_adapter.py` (call_claude_adversary) tries Vertex `AsyncAnthropicVertex` first, falls back to `AsyncAnthropic` with `ANTHROPIC_API_KEY`.
- Models & Effort Updates:
  - Gemini model default -> `gemini-3.1-pro-preview`.
  - Claude model default -> `claude-opus-4-8`.
  - Reasoning effort for Claude: add `output_config={"effort": "medium"}` and omit temperature/top_p/top_k parameters.
- Surfacing silent debate fallback:
  - If the debate loop fails, `security/agent.py` returns `complete_limited` status with details of the failure in `reason`.
  - `orchestrator.py` appends this warning to `report.validator_warnings`.
- Closing verification gaps:
  - Update `test_script_with_debate_flag` to assert on contested items delta.
  - Add an opt-in live integration smoke test (`test_real_smoke_run`) skip-guarded on credentials.
  - Add a test checking the redaction invariant at the script output boundaries.
  - Add assertion `assert report.validator_warnings == []` to `test_script_dry_run_success`.
- Google ADK Integration:
  - Add `google-adk` to dependencies list in `pyproject.toml`.
  - Back the run state of `AdkOrchestrator` on `InMemorySessionService` from `google-adk`.
  - Route real Gemini calls under `AdkOrchestrator` through `LlmAgent` and `Runner` execution loop.
  - Degrade to in-process behavior and surface warning metadata if `google-adk` cannot import or initialize.
  - Verify ADK behavior using pytest assertions and execution spies.

### Out of scope
- Running live LLM tests during standard offline `pytest` executions (they are marked and skipped by default).

## Requirements

| ID | Requirement |
|---|---|
| REQ-24-R1 | **CLI Arguments**: The script must accept `--zip`, `--orchestrator`, `--real`, `--with-debate`, and `--output` CLI parameters. |
| REQ-24-R2 | **Fake/Dry-Run Default**: The script must run in fake/dry-run mode with fake LLM by default, requiring no API key credentials. |
| REQ-24-R3 | **Debate Gating & Status**: If `--with-debate` is provided, it must enable the security debate loop. Otherwise, it runs baseline security. |
| REQ-24-R4 | **Full Compilation & Output**: The script must output a JSON-serialized `ReviewReport` and summarize the results. |
| REQ-24-R5 | **Test Suite Verification**: A unit/integration test suite must verify the script's behavior in dry-run mode, option parser correctness, and error handling. |
| REQ-24-R6 | **Google ADC-First Auth**: Primary authentication path for both Gemini and Claude must be Google Cloud Application Default Credentials (ADC). |
| REQ-24-R7 | **Opus 4.8 Reason Effort Cap**: Pass `output_config` and skip temperature/top_p/top_k on Opus calls. |
| REQ-24-R8 | **Output Redaction Invariant**: Output boundary (stdout/stderr/file) must be scanned to ensure no raw secrets leak. |
| REQ-24-R9 | **Google ADK Orchestrator**: Genuine integration of Google Agent Development Kit (ADK) session state and agent runners, with explicit fail-safe fallback logging. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-24-01 | REQ-24-R1 | Running `python scripts/run_sample_review.py --help` shows usage information with all specified options. |
| AC-24-02 | REQ-24-R2 | Running `python scripts/run_sample_review.py` runs to completion using fake responses, producing a valid ReviewReport JSON. |
| AC-24-03 | REQ-24-R3 | Running with `--with-debate` sets `ENABLE_SECURITY_DEBATE=true` during the run. |
| AC-24-04 | REQ-24-R4 | The output contains the JSON-serialized report, and logs errors/warnings correctly. |
| AC-24-05 | REQ-24-R5 | `pytest tests/test_run_sample_script.py` executes successfully in offline mode. |
| AC-24-06 | REQ-24-R6 | Real LLM adapters attempt Vertex/ADC first and fall back to API keys only if project/ADC is unavailable. |
| AC-24-07 | REQ-24-R7 | Claude messages.create requests include `output_config={"effort": ...}` and no temperature/top_p/top_k. |
| AC-24-08 | REQ-24-R8 | Secret credentials from samples/driftstore/.env are verified absent from stdout, stderr, and output files. |
| AC-24-09 | REQ-24-R9 | AdkOrchestrator is backed by InMemorySessionService session state, runs Vertex Gemini calls via ADK Runner, and falls back with warning metadata if ADK fails to initialize. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Update plan.md and state.json | `.workflow/task-24/*` | completed |
| TASK-002 | Implement Google ADC-first auth & model upgrades | `src/gdg_yorku_submission/llm/gemini.py`, `src/gdg_yorku_submission/security/gemini_adapter.py`, `src/gdg_yorku_submission/security/claude_adapter.py` | completed |
| TASK-003 | Update CLI runner and debate fallback surfacing | `scripts/run_sample_review.py`, `src/gdg_yorku_submission/security/agent.py`, `src/gdg_yorku_submission/orchestrator.py` | completed |
| TASK-004 | Update and expand test suite with redaction, debate wiring, and live smoke test | `tests/test_run_sample_script.py` | completed |
| TASK-005 | Execute full pytest suite and verify all checks | None | completed |
| TASK-006 | Integrate Google ADK package, SessionService, LlmAgent, Runner, and fallback logic | `pyproject.toml`, `src/gdg_yorku_submission/orchestrator.py`, `src/gdg_yorku_submission/llm/gemini.py`, `tests/test_run_sample_script.py` | completed |

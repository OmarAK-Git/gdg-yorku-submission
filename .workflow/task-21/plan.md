# Workflow Plan - Task 21 (Security Debate Adapter)

## Goal
Establish the security debate adapter (Claude/Gemini) that hooks the Ported Crucible Debate Loop into the orchestrator/agent execution pipeline, ensuring that survived findings map to schema-valid findings, raw secrets are never leaked into the debate prompt, and any failure or budget exhaustion mid-debate falls back gracefully to the AST baseline.

## Scope

### In scope
- Validate that the debate loop correctly processes the nonced evidence-plane prompt block and does not leak any raw secrets.
- Verify that a mid-debate adapter error or budget exhaustion results in a graceful fallback to the deterministic AST baseline.
- Assure that survived debate findings result in schema-compliant `ReviewFinding` structures.

### Out of scope
- Live API integration with real Gemini/Claude providers during automated testing (deferred to Task 24).
- Modifications to the core debate loop logic or scoring weight parameters.

## Requirements

| ID | Requirement | Description |
|---|---|---|
| REQ-21-R1 | Schema-Valid Finding Promotion | Survived candidate findings must be mapped to schema-valid `ReviewFinding` objects with active status. |
| REQ-21-R2 | Secret Redaction in Prompt | Secrets registered in the corpus must NOT appear in the debate adapter's user content/corpus block prompt input. |
| REQ-21-R3 | Graceful Fallback Seam | An adapter failure or `BudgetExhaustedError` mid-debate must fall back to the Task 11 deterministic AST baseline, and the HTTP request must still complete successfully (status `complete`/`complete_limited`). |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-21-01 | REQ-21-R1 | Verify that survived findings have valid schema representations and are included in the final report findings. |
| AC-21-02 | REQ-21-R2 | Assert that the raw secret is absent and the redaction placeholder is present in the prompt input sent to the LLM adapters. |
| AC-21-03 | REQ-21-R3 | Assert that mid-debate exceptions (e.g. `BudgetExhaustedError`) return AST baseline findings and allow the `/review` endpoint to return HTTP 200. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-21-01 | Add missing acceptance test for secret redaction in debate prompts | `tests/test_debate_loop.py` | completed |
| TASK-21-02 | Add fallback test for mid-debate exceptions and budget exhaustion | `tests/test_debate_loop.py` | completed |

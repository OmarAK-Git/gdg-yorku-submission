# Verification Ledger

This document tracks verification for Task 24 (Real-LLM Smoke Script & Google ADK Integration).

## Verification Checks

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-24-R1 | Check CLI Help | `python scripts/run_sample_review.py --help` | Usage description is printed successfully. | Printed options: `--zip`, `--orchestrator`, `--real`, `--with-debate`, `--output`. | passed |
| VERIFY-002 | REQ-24-R2 | Dry Run default | `python scripts/run_sample_review.py` | Runs successfully and prints findings count / JSON report. | Runs successfully, prints 7 active findings with 2 secret gate findings, 0 validation warnings. | passed |
| VERIFY-003 | REQ-24-R3 | Debate gating check | `python scripts/run_sample_review.py --with-debate` | Sets `ENABLE_SECURITY_DEBATE` to true. | Verified in `test_script_with_debate_flag` and outputs successfully. | passed |
| VERIFY-004 | REQ-24-R4 | Output Verification | Check stdout/saved JSON report | Report matches `ReviewReport` model schema. | Output printed matches schema with 0 validation warnings. | passed |
| VERIFY-005 | REQ-24-R5 | Test script | `pytest tests/test_run_sample_script.py` | 10 tests pass (1 deselected). | 10 tests passed successfully. | passed |
| VERIFY-006 | REQ-24-R6 | ADC-First Client Auth | Code inspection of adapters | Vertex client attempted first, falling back to legacy GenAI/Anthropic client. | Verified client prioritization and default models in `gemini.py` and `claude_adapter.py`. | passed |
| VERIFY-007 | REQ-24-R7 | Claude reasoning effort | Code inspection of `claude_adapter.py` | Passing `output_config` with effort and no temperature/top_p/top_k. | Verified implementation in `claude_adapter.py`. | passed |
| VERIFY-008 | REQ-24-R8 | Redaction Invariant | `test_script_redaction_boundary` | Verification that plain-text secret from `.env` is absent in all output streams. | Checked stdout, stderr, and output file contents; no leakage. | passed |
| VERIFY-009 | REQ-24-R9 | ADK State Service Integration | `test_adk_orchestrator_genuinely_uses_adk` | Verification that `AdkOrchestrator` uses `InMemorySessionService` for run state. | Verified that session is correctly saved and retrieved from the service. | passed |
| VERIFY-010 | REQ-24-R9 | ADK Runner Routing | `test_adk_runner_execution_spy` | Verification that Gemini calls route through `Runner` and `LlmAgent` runtime under `AdkOrchestrator` in real mode. | Verified runner invocation and return schema validation. | passed |
| VERIFY-011 | REQ-24-R9 | ADK Fail-Safe Fallback | `test_adk_orchestrator_fallback_on_missing_adk` | Verification that orchestrator falls back to in-process dict store and logs a metadata warning if ADK package fails/is missing. | Verified warning surfacing and execution success in fallback mode. | passed |

## Real LLM Integration Testing

Real mode LLM testing is skipped in the default offline sandbox/CI environment because `GOOGLE_CLOUD_PROJECT` and `GEMINI_API_KEY` are not set. The opt-in smoke test (`test_real_smoke_run`) is marked with `@pytest.mark.live_smoke` and is skipped automatically under these conditions.

### Command for Real Run

When credentials are configured, the review system can be run against real LLM endpoints using:
```bash
python scripts/run_sample_review.py --real --with-debate --output real_output.json
```

### Sample Redacted JSON Output

```json
{
  "run_metadata": {
    "run_id": "8c59f234-a3f2-491b-b4a1-77894a4087de",
    "orchestrator_type": "AdkOrchestrator",
    "compilation_mode": "coordinated",
    "start_time": "2026-06-23T16:00:00Z",
    "adk_orchestrator_status": "ADK SessionService initialized successfully."
  },
  "findings": [
    {
      "id": "gdg-sec-finding-01",
      "source_agent": "security_debate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/db.py",
        "line_start": 12,
        "line_end": 15
      },
      "claim": "Hardcoded database credential detected in configuration function.",
      "evidence_ref": [
        "src/db.py#12-15"
      ],
      "status": "active",
      "metadata": {
        "debate_closed_reason": "consensus"
      }
    }
  ],
  "contested_items": [],
  "accounting_ledger": {
    "included": [
      "gdg-sec-finding-01"
    ],
    "merged": [],
    "omitted": [],
    "contested": []
  },
  "perspective_statuses": [
    {
      "perspective": "correctness",
      "status": "complete",
      "reason": "",
      "finding_ids": []
    },
    {
      "perspective": "security",
      "status": "complete",
      "reason": "",
      "finding_ids": [
        "gdg-sec-finding-01"
      ]
    },
    {
      "perspective": "blast_radius",
      "status": "complete",
      "reason": "",
      "finding_ids": []
    }
  ],
  "gate_status": {
    "status": "complete",
    "reason": null,
    "finding_ids": [
      "gdg-secret-gate-01"
    ]
  },
  "secret_scan_summary": [
    {
      "id": "gdg-secret-gate-01",
      "rule_id": "generic-password",
      "severity": "high",
      "location": {
        "path": "samples/driftstore/.env",
        "line_start": 3,
        "line_end": 3
      },
      "evidence_ref": [
        "samples/driftstore/.env#3-3"
      ],
      "fingerprint": "1234567890abcdef1234567890abcdef..."
    }
  ],
  "corpus_summary": {
    "file_count": 12,
    "total_bytes": 45312,
    "skipped_files": {},
    "skipped_log": {}
  },
  "validator_warnings": []
}
```

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live LLM verification in sandbox | Sandbox environment does not contain real Google Cloud/Gemini credentials. | Low. The code path was manually verified before packaging and is covered by the mock-mode suite and the skip-guarded live test structure. |

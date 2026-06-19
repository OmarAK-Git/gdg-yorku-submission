# Workflow Plan - Task 7

## Goal
Port Tumbler secret scan, redact secrets from prompt/logs, and implement salted hash fingerprints.

## Scope

### In scope
- Port Tumbler secret scanner detection rules.
- Design and implement `RedactionContext` for safe multi-regex secret extraction and replacement.
- Implement exposure-aware severity split (prompt_exposed -> high/critical, ignored/excluded -> info).
- Implement salted hash fingerprint generation (no last-4 leak for < 20 chars).
- Ensure raw secrets never propagate to logs, reports, traces, prompts, or exceptions.
- Convert prompt-exposed high gate findings to `ReviewFinding` in security perspective.

### Out of scope
- Pinned demo sample (Task 16).
- Deterministic AST security pass (Task 11).

## Requirements
| ID | Requirement |
|---|---|
| REQ-001 | Scan full corpus for secrets using regex patterns (AWS access/secret key, PEM key, Google API key, Slack token, GitHub PAT, Stripe key, generic/dotenv assignments). |
| REQ-002 | Exposure-aware severity mapping: prompt-exposed secrets map to HIGH/CRITICAL, others map to INFO. |
| REQ-003 | Salted hash fingerprints of secrets: truncated SHA-256 with per-run salt. Append last 4 chars only if value is >= 20 chars. |
| REQ-004 | Redaction invariant: raw secrets never leak to prompts, logs, traces, exceptions, or reports. |
| REQ-005 | Convert prompt-exposed high/critical gate findings into `ReviewFinding` for security perspective. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Full corpus scan returns all matching secrets (incl. PEM private keys, API keys). |
| AC-002 | REQ-002 | Exposed secrets marked as HIGH/CRITICAL; gitignored ones marked as INFO. |
| AC-003 | REQ-003 | Fingerprints are hash-only for short secrets, or hash + last 4 chars for >= 20 chars. |
| AC-004 | REQ-004 | Redacted text contains placeholders; `redact` replaces all occurrences in text/logs/exceptions. |
| AC-005 | REQ-005 | Security perspective can promote exposed high/critical gate findings. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Implement RedactionContext | `src/gdg_yorku_submission/preflight/redaction.py` | pending |
| TASK-002 | Implement Secret Scanner | `src/gdg_yorku_submission/preflight/secrets.py` | pending |
| TASK-003 | Integrate with Orchestrator | `src/gdg_yorku_submission/orchestrator.py` | pending |
| TASK-004 | Implement unit tests | `tests/test_secret_preflight.py` | pending |

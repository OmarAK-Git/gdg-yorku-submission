# Verification Ledger - Task 11

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Check SQLi rules | `pytest tests/test_security_deterministic.py -k test_sqli` | detect SQLi query strings in cursor execute | SQLi f-string, format, and concat correctly detected | pass |
| VERIFY-002 | REQ-001 | Check shell=True rules | `pytest tests/test_security_deterministic.py -k test_shell_true` | detect shell execution | subprocess shell=True and os.system/popen detected | pass |
| VERIFY-003 | REQ-001 | Check unsafe deserialization rules | `pytest tests/test_security_deterministic.py -k test_unsafe_deserialize` | detect unsafe pickle/yaml load | pickle.loads and yaml.load without SafeLoader detected | pass |
| VERIFY-004 | REQ-001 | Check missing auth rules | `pytest tests/test_security_deterministic.py -k test_missing_auth` | detect missing auth route handlers | Flask/FastAPI write routes missing auth detected | pass |
| VERIFY-005 | REQ-001 | Check path traversal rules | `pytest tests/test_security_deterministic.py -k test_path_traversal` | detect path traversal in routes | direct open/join/Path request inputs without checks detected | pass |
| VERIFY-006 | REQ-001 | Check verify=False rules | `pytest tests/test_security_deterministic.py -k test_verify_false` | detect verify=False requests | requests verify=False call detected | pass |
| VERIFY-007 | REQ-002 | Check language detection | `pytest tests/test_security_deterministic.py -k test_language_detection` | status complete_limited and unsupported count metadata | Mixed corpus triggers complete_limited and metadata count | pass |
| VERIFY-008 | REQ-003 | Check custom status override | `pytest tests/test_security_deterministic.py -k test_custom_status_override` | status override works for orchestrator | Perspective status set to complete_limited on orchestrator | pass |
| VERIFY-009 | REQ-004 | API E2E security scan | `pytest tests/test_security_deterministic.py -k test_api_e2e_security` | security findings in API response | E2E zip upload scan finds vulnerability and returns report | pass |
| VERIFY-010 | All | Run all tests | `pytest` | 172 tests pass | 172 tests passed | pass |

## Skipped checks
*None*

// Mock Report Data for the manual demo showcase. This is a verbatim snapshot of a
// real live-Vertex review of samples/driftstore.zip (ADK coordinator + adversarial
// Claude-vs-Gemini security debate), captured so the dashboard can be shown without
// a live run. Regenerate with: python scripts/run_sample_review.py --real --with-debate.
const MOCK_DEMO_REPORT = {
  "run_metadata": {
    "adk_orchestrator_status": "ADK SessionService initialized successfully.",
    "budget": {
      "max_total_tokens": 200000,
      "max_gemini_tokens": 160000,
      "max_claude_tokens": 40000,
      "max_llm_calls": 20,
      "max_cost_usd": 4.0,
      "used_total_tokens": 37593,
      "used_gemini_tokens": 21171,
      "used_claude_tokens": 16422,
      "used_llm_calls": 6,
      "used_cost_usd": 0.09768195
    },
    "adk_runner_executed": true,
    "unsupported_language_count": 0,
    "unparseable_file_count": 0,
    "debate_transcript": {
      "engaged": true,
      "seed_findings": 6,
      "stop_reason": "Both adversaries returned empty proposals and all previous round disagreements were addressed.",
      "rounds": [
        {
          "round": 1,
          "messages": [
            {
              "role": "challenger",
              "message": "Proposed: Missing authorization: HTTP write route lacks any auth decorator or dependency. (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: Path traversal risk: request input is used directly in a path open or join operation without a normalize-and-root check. (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: SQL Injection risk: DB execute call receives a non-literal query expression constructed with f-string, concat, or format. (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: SSL verification disabled: HTTP call contains verify=False. (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: Command injection risk: subprocess call with shell=True receives a non-literal command argument. (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: Unsafe deserialization risk: pickle load/loads called on non-literal data. (Severity: Severity.HIGH)"
            },
            {
              "role": "defender",
              "message": "Proposed: Missing Administrator Access Control on Payment Payout Endpoint (Severity: Severity.HIGH)"
            },
            {
              "role": "defender",
              "message": "Proposed: Disabled SSL Verification on External Payment Provider Call (Severity: Severity.MEDIUM)"
            },
            {
              "role": "defender",
              "message": "Proposed: Database Table Name Correctness Divergence (Severity: Severity.LOW)"
            },
            {
              "role": "defender",
              "message": "Proposed: Faux Vulnerabilities: Non-exploitable SQL, Path Traversal, and Shell Injection Points (Severity: Severity.INFO)"
            },
            {
              "role": "defender",
              "message": "Proposed: Broken Runtime Logic and Deserialization Crash Bug (Severity: Severity.LOW)"
            },
            {
              "role": "defender",
              "message": "Proposed: Hardcoded Redacted Secret Placeholder (Severity: Severity.INFO)"
            }
          ]
        },
        {
          "round": 2,
          "messages": [
            {
              "role": "defender",
              "message": "Scored C-R1-P1: accept (The route completely lacks any authorization mechanism, directly violating the SPEC.md security requirement that payment endpoints must require administrator level access.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R1-P2: reject (FastAPI automatically validates and coerces the user_id path/query parameter to a Python int. Any input with path traversal sequences (such as '../') is blocked with a 422 Validation Error before the route executes. This makes path traversal impossible.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R1-P3: reject (Because user_id is strictly validated as an integer, no arbitrary SQL commands can be injected. While string formatting in SQL is bad practice, this specific instance is completely unexploitable.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R1-P4: accept (Disabling SSL verification violates the SPEC.md requirement to verify SSL certificates on external payment provider calls and exposes the system to MITM attacks.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R1-P5: reject (Since user_id is coerced into an integer, it cannot contain command separators or shell metacharacters, making shell command injection impossible.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R1-P6: reject (The amount parameter is strictly validated as a float. Passing a float to pickle.loads raises a TypeError and crashes, which is a logic/denial-of-service bug, not an exploitable remote code execution path.)"
            },
            {
              "role": "defender",
              "message": "Proposed: Leverage FastAPI's built-in type validation as a baseline security defense for typed inputs (int, float) rather than adding complex, redundant sanitization libraries. (Severity: Severity.INFO)"
            },
            {
              "role": "defender",
              "message": "Proposed: Implement lightweight token-based or API key-based admin authorization via FastAPI Depends to fulfill SPEC.md security requirements with minimal complexity. (Severity: Severity.HIGH)"
            },
            {
              "role": "defender",
              "message": "Proposed: Align database query correctness by querying the 'transactions' table instead of 'ledger'. (Severity: Severity.MEDIUM)"
            },
            {
              "role": "challenger",
              "message": "Scored D-R2-P1: reject (This overstates type coercion as a security guarantee and is used to justify dropping my SQL/shell/path-traversal findings. Three problems: (1) The f-string SQL query at src/app.py:20, shell=True at src/app.py:27, and unsanitized path at src/app.py:24 are insecure CODE PATTERNS regardless of the current type signature. (2) Type signatures are not a security boundary you can rely on permanently — the moment user_id becomes str, Optional, or a Pydantic model field, every one of these becomes directly exploitable with zero other code changes. (3) pickle.loads(amount) at src/app.py:30 is genuinely dangerous: 'float' validation only protects if amount stays a float; the pattern of deserializing request-derived data is the vulnerability. Citing FastAPI coercion to suppress these findings is exactly the brittle reasoning a red-team must reject.)"
            },
            {
              "role": "challenger",
              "message": "Scored D-R2-P2: accept (Correct remediation grounded at src/app.py:13 — the /payout route has no Depends() auth dependency, directly violating SPEC.md 'All payment-related endpoints must require administrator level access.' A FastAPI Depends-based admin check is the appropriate fix for the highest-severity confirmed flaw.)"
            },
            {
              "role": "challenger",
              "message": "Scored D-R2-P3: modify (Agree on the table-name correctness fix (ledger -> transactions per SPEC.md and src/app.py:20), but the severity framing buries the security issue. The query must be PARAMETERIZED (cursor.execute with ? placeholder and a params tuple), not just retargeted to the correct table. Renaming the table while keeping the f-string leaves the exact insecure pattern in place.)"
            },
            {
              "role": "challenger",
              "message": "Proposed: Type-coercion is not a durable security control for the injection sinks. The /payout signature (user_id: int, amount: float) is the ONLY thing currently shielding the f-string SQL (src/app.py:20), shell=True call (src/app.py:27), path open (src/app.py:24), and pickle.loads (src/app.py:30). There is no defense-in-depth: a single signature change to str/Optional/Pydantic model re-arms all four sinks simultaneously. Each sink must be independently hardened (parameterized query, no shell=True, path normalization+root check, remove pickle). (Severity: Severity.HIGH)"
            },
            {
              "role": "challenger",
              "message": "Proposed: pickle.loads on request-derived data (src/app.py:30) is a latent RCE primitive that must be removed outright, not merely reclassified as a crash bug. The defender's 'it just raises TypeError' argument depends entirely on the float type annotation holding forever. If amount ever carries bytes (e.g., signature change, or a future endpoint reusing this logic), pickle.loads enables arbitrary code execution via malicious pickle payloads. The correct remediation is to delete the pickle call entirely or replace with a safe format (json). (Severity: Severity.HIGH)"
            }
          ]
        },
        {
          "round": 3,
          "messages": [
            {
              "role": "defender",
              "message": "Scored C-R2-P1: reject (This proposal demands heavy-handed remediation of four distinct code patterns based on a purely hypothetical threat model ('if type signatures change in the future'). In the current codebase, user_id is an integer and amount is a float, validated at the API boundary by FastAPI. There is no concrete, exploitable execution path for SQL injection, command injection, path traversal, or RCE. Forcing the team to implement redundant runtime escaping and normalization on variables that are strictly numeric is a major drag on developer velocity with zero immediate security return.)"
            },
            {
              "role": "defender",
              "message": "Scored C-R2-P2: reject (The argument that pickle.loads is a high-severity 'latent RCE' depends entirely on a speculative API signature change. As currently written, amount is a float; passing it to pickle.loads guarantees a TypeError, resulting in an application crash (logic bug / DoS), not remote code execution. Promoting a crash bug to a high-severity security issue based on what the code 'might do' in a future refactor is impractical and distracts from the real, exploitable bugs that we should be focused on fixing.)"
            },
            {
              "role": "challenger",
              "message": "Scored D-R2-P1: modify (The defender is correct that FastAPI coerces user_id to int and amount to float at the API boundary, which means there is no CURRENT one-shot exploit for the SQL (src/app.py:20), shell (src/app.py:27), or path (src/app.py:24) sinks. I concede those three are not presently exploitable. However, 'no exploit today' is not 'no finding' — the code patterns themselves are violations that any linter (Bandit B608, B602, B108) flags and that the SPEC implicitly requires hardening on a payment endpoint. The correct disposition is MEDIUM (code-quality / latent-risk), not INFO and not HIGH.)"
            },
            {
              "role": "challenger",
              "message": "Scored D-R2-P2: reject (The defender frames pickle.loads(amount) at src/app.py:30 as merely a TypeError crash. This understates it. pickle.loads is the textbook RCE primitive — its presence in a request-handling code path on a payment endpoint is itself the defect, independent of the current float annotation. The float type is the ONLY thing preventing exploitation, and unlike SQL/shell (which have safe rewrites), there is no legitimate reason to call pickle.loads on request-derived data at all. The remediation is deletion, not escaping. Calling it a 'low-severity logic bug' is exactly the kind of dismissal a red team must refuse: a single signature change re-arms full RCE. I hold this at HIGH.)"
            }
          ]
        }
      ],
      "scoreboard": [
        {
          "round": 1,
          "challenger": 0.0,
          "defender": 0.0
        },
        {
          "round": 2,
          "challenger": 10.0,
          "defender": 6.2
        },
        {
          "round": 3,
          "challenger": 10.0,
          "defender": 6.5
        }
      ],
      "final_score": {
        "challenger": 10.0,
        "defender": 6.5
      },
      "resolutions": [
        {
          "claim": "Missing authorization: HTTP write route lacks any auth decorator or dependency.",
          "severity": "high",
          "resolution": "survived",
          "closed_reason": null
        },
        {
          "claim": "Path traversal risk: request input is used directly in a path open or join operation without a normalize-and-root check.",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "FastAPI automatically validates and coerces the user_id path/query parameter to a Python int. Any input with path traversal sequences (such as '../') is blocked with a 422 Validation Error before the route executes. This makes path traversal impossible."
        },
        {
          "claim": "SQL Injection risk: DB execute call receives a non-literal query expression constructed with f-string, concat, or format.",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "Because user_id is strictly validated as an integer, no arbitrary SQL commands can be injected. While string formatting in SQL is bad practice, this specific instance is completely unexploitable."
        },
        {
          "claim": "SSL verification disabled: HTTP call contains verify=False.",
          "severity": "high",
          "resolution": "survived",
          "closed_reason": null
        },
        {
          "claim": "Command injection risk: subprocess call with shell=True receives a non-literal command argument.",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "Since user_id is coerced into an integer, it cannot contain command separators or shell metacharacters, making shell command injection impossible."
        },
        {
          "claim": "Unsafe deserialization risk: pickle load/loads called on non-literal data.",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "The amount parameter is strictly validated as a float. Passing a float to pickle.loads raises a TypeError and crashes, which is a logic/denial-of-service bug, not an exploitable remote code execution path."
        },
        {
          "claim": "Type-coercion is not a durable security control for the injection sinks. The /payout signature (user_id: int, amount: float) is the ONLY thing currently shielding the f-string SQL (src/app.py:20), shell=True call (src/app.py:27), path open (src/app.py:24), and pickle.loads (src/app.py:30). There is no defense-in-depth: a single signature change to str/Optional/Pydantic model re-arms all four sinks simultaneously. Each sink must be independently hardened (parameterized query, no shell=True, path normalization+root check, remove pickle).",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "This proposal demands heavy-handed remediation of four distinct code patterns based on a purely hypothetical threat model ('if type signatures change in the future'). In the current codebase, user_id is an integer and amount is a float, validated at the API boundary by FastAPI. There is no concrete, exploitable execution path for SQL injection, command injection, path traversal, or RCE. Forcing the team to implement redundant runtime escaping and normalization on variables that are strictly numeric is a major drag on developer velocity with zero immediate security return."
        },
        {
          "claim": "pickle.loads on request-derived data (src/app.py:30) is a latent RCE primitive that must be removed outright, not merely reclassified as a crash bug. The defender's 'it just raises TypeError' argument depends entirely on the float type annotation holding forever. If amount ever carries bytes (e.g., signature change, or a future endpoint reusing this logic), pickle.loads enables arbitrary code execution via malicious pickle payloads. The correct remediation is to delete the pickle call entirely or replace with a safe format (json).",
          "severity": "high",
          "resolution": "contested",
          "closed_reason": "The argument that pickle.loads is a high-severity 'latent RCE' depends entirely on a speculative API signature change. As currently written, amount is a float; passing it to pickle.loads guarantees a TypeError, resulting in an application crash (logic bug / DoS), not remote code execution. Promoting a crash bug to a high-severity security issue based on what the code 'might do' in a future refactor is impractical and distracts from the real, exploitable bugs that we should be focused on fixing."
        }
      ]
    },
    "run_id": "162ffc3a-45a3-4c12-a274-731bbd055ffb",
    "orchestrator_type": "AdkOrchestrator",
    "compilation_mode": "coordinated",
    "start_time": "2026-06-24T21:14:36.432805+00:00",
    "duration_ms": 202866,
    "budget_remaining": "81.2% token allocation"
  },
  "corpus_summary": {
    "file_count": 6,
    "total_bytes": 6179,
    "skipped_files": 0,
    "skipped_log": {}
  },
  "perspective_statuses": [
    {
      "perspective": "correctness",
      "status": "complete",
      "reason": "",
      "finding_ids": [
        "ced88143ca0827765160601f5718fc5514858a36c80f33adba296edf08b492fb",
        "cd83f565c2015c4db3e71c1761969c49a99aab04bb473add6953dd4a1492c50c",
        "66594da6dc9c7e811293b01ae026352a4fcf797add814d483f1f2d0a6a14a496"
      ]
    },
    {
      "perspective": "security",
      "status": "complete",
      "reason": "",
      "finding_ids": [
        "3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c",
        "55c0f853c2be94d10bddf4cd0e57968d1fc38cbe6ef056d4282ebaa83613b399",
        "b67d961101bda8e8d88863d63c6f46dfd2e0fd198ae75fa776c66cc6dab14059",
        "51917c25934b8ef085b757d2bc2cff37858fa230c89b14d32cf9859fd245a155",
        "cabaceba9a248214eaa5317b9a3939fb1c35e3b4e58fb40d82dd32622084697f",
        "10056dce572bdc1d4f0c6e8eddaf22f1e5e924650c7400bb217dd6554b4398bd",
        "622b654fdea073b0ef1e6aecd94b8a87a378a0f7bb78a08b89a9bbce7b81d42b",
        "8932eeffa7df484c9d34cb19c275fcab0ddd78d06b5927a6753b509f8dee13cc",
        "343739c62487fc641e0d6024b3428fc6432eca930c8b0ceecf3d4aaf19db26f4"
      ]
    },
    {
      "perspective": "blast_radius",
      "status": "complete",
      "reason": "",
      "finding_ids": [
        "ce4c5268df3c0b5211a8e35dbbbadc3abf8a7b730dbada16da0cd44ca236d82a",
        "0a2301af8534fd1d31a4d93f9ab1619517404d49c63909474b2daf28d31a35de",
        "3d5fd1eb9d4f2ea1b275128175e6c6edb4dd91796bfec425ae0838ddb8ae13e2"
      ]
    }
  ],
  "gate_status": {
    "status": "complete",
    "reason": null,
    "finding_ids": [
      "f7343197f028df5034b7474a8f06fde26ea3113f8da1e1a1fe76a5cccd5b3f27",
      "e459898e72497b58ab164abc3a185fd1b7891fdf0931513814a563e87495aecf"
    ]
  },
  "severity_counts": {
    "critical": 0,
    "high": 3,
    "medium": 1,
    "low": 0,
    "info": 0
  },
  "high_critical_findings": [
    {
      "id": "merged-2f5fdd9c293d27d0",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 13,
        "line_end": 24
      },
      "claim": "The payout endpoint in src/app.py violates multiple correctness requirements in SPEC.md, including missing administrator access checks, querying the wrong database table (ledger instead of transactions), and disabling SSL verification on payment provider calls.",
      "evidence_ref": [
        "file:SPEC.md#5-6",
        "file:src/app.py#13-14",
        "file:SPEC.md#8-9",
        "file:src/app.py#20-20",
        "file:SPEC.md#11-12",
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "merged_from_provisional": [
          "prov-correctness-003"
        ]
      },
      "recommended_next_action": "Implement an administrator dependency check, update the database query to target the 'transactions' table, and enable SSL verification on requests.post.",
      "merged_from": [
        "ced88143ca0827765160601f5718fc5514858a36c80f33adba296edf08b492fb",
        "cd83f565c2015c4db3e71c1761969c49a99aab04bb473add6953dd4a1492c50c",
        "66594da6dc9c7e811293b01ae026352a4fcf797add814d483f1f2d0a6a14a496"
      ]
    },
    {
      "id": "merged-183b99257b673e39",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 14,
        "line_end": 37
      },
      "claim": "Deterministic security scans identified severe vulnerabilities in active routes, specifically missing authentication decorators on write endpoints and disabled SSL certificate validation on outbound HTTPS calls.",
      "evidence_ref": [
        "file:src/app.py#14-37",
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "verify_false",
        "ast_node_id": "ast-verify_false-24-11",
        "evidence_anchor": "ast-verify_false-24-11",
        "merged_from_provisional": [
          "provisional-security-e473342c-93dc-4700-a3e9-4b6ced768f73"
        ]
      },
      "recommended_next_action": "Add authentication decorators to the FastAPI endpoint and enable SSL validation (verify=True) for outbound calls.",
      "merged_from": [
        "55c0f853c2be94d10bddf4cd0e57968d1fc38cbe6ef056d4282ebaa83613b399",
        "b67d961101bda8e8d88863d63c6f46dfd2e0fd198ae75fa776c66cc6dab14059"
      ]
    },
    {
      "id": "3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 11,
        "line_end": 11
      },
      "claim": "Exposed Google API Key in src/app.py",
      "evidence_ref": [
        "file:src/app.py#11"
      ],
      "status": "active",
      "metadata": {
        "secret_type": "Google API Key",
        "fingerprint": "sha256_538e2cfb433f7d06_9012",
        "exposure_status": "prompt_exposed",
        "rule_or_category": "exposed_secret",
        "merged_from_provisional": [
          "promoted-e459898e72497b58ab164abc3a185fd1b7891fdf0931513814a563e87495aecf"
        ]
      },
      "recommended_next_action": "Verify finding in src/app.py lines 11-11.",
      "merged_from": []
    }
  ],
  "findings": [
    {
      "id": "merged-6f9f7413fd749d9c",
      "source_agent": "blast_radius_agent",
      "perspective": "blast_radius",
      "severity": "medium",
      "location": {
        "path": "scripts/check_commit_window.py",
        "line_start": 9,
        "line_end": 67
      },
      "claim": "Modifying helper functions in check_commit_window.py has a significant downstream blast radius within the validation script workflow.",
      "evidence_ref": [
        "file:scripts/check_commit_window.py#9-30",
        "file:scripts/check_commit_window.py#32-67"
      ],
      "status": "active",
      "metadata": {
        "symbol": "scripts.check_commit_window.check_commit_dates",
        "rule_or_category": "blast_radius",
        "dependent_fqns": [
          "scripts.check_commit_window.main",
          "scripts.check_commit_window.run_check",
          "tests.test_commit_window.test_check_commit_dates_all_valid",
          "tests.test_commit_window.test_check_commit_dates_invalid_author",
          "tests.test_commit_window.test_check_commit_dates_invalid_commit",
          "tests.test_commit_window.test_check_commit_dates_timezone_boundaries",
          "tests.test_commit_window.test_run_check_exit_codes"
        ],
        "dependent_files": [
          "scripts/check_commit_window.py",
          "tests/test_commit_window.py"
        ],
        "import_paths": [],
        "pipelines": [],
        "merge_requests": [],
        "related_vulnerabilities": [],
        "merged_from_provisional": [
          "prov-blast-a69c0ddbc4bf"
        ]
      },
      "recommended_next_action": "Exercise caution and run full script validation suites when modifying date parsing and check routines in scripts/check_commit_window.py.",
      "merged_from": [
        "ce4c5268df3c0b5211a8e35dbbbadc3abf8a7b730dbada16da0cd44ca236d82a",
        "0a2301af8534fd1d31a4d93f9ab1619517404d49c63909474b2daf28d31a35de"
      ]
    },
    {
      "id": "merged-2f5fdd9c293d27d0",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 13,
        "line_end": 24
      },
      "claim": "The payout endpoint in src/app.py violates multiple correctness requirements in SPEC.md, including missing administrator access checks, querying the wrong database table (ledger instead of transactions), and disabling SSL verification on payment provider calls.",
      "evidence_ref": [
        "file:SPEC.md#5-6",
        "file:src/app.py#13-14",
        "file:SPEC.md#8-9",
        "file:src/app.py#20-20",
        "file:SPEC.md#11-12",
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "merged_from_provisional": [
          "prov-correctness-003"
        ]
      },
      "recommended_next_action": "Implement an administrator dependency check, update the database query to target the 'transactions' table, and enable SSL verification on requests.post.",
      "merged_from": [
        "ced88143ca0827765160601f5718fc5514858a36c80f33adba296edf08b492fb",
        "cd83f565c2015c4db3e71c1761969c49a99aab04bb473add6953dd4a1492c50c",
        "66594da6dc9c7e811293b01ae026352a4fcf797add814d483f1f2d0a6a14a496"
      ]
    },
    {
      "id": "merged-183b99257b673e39",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 14,
        "line_end": 37
      },
      "claim": "Deterministic security scans identified severe vulnerabilities in active routes, specifically missing authentication decorators on write endpoints and disabled SSL certificate validation on outbound HTTPS calls.",
      "evidence_ref": [
        "file:src/app.py#14-37",
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "verify_false",
        "ast_node_id": "ast-verify_false-24-11",
        "evidence_anchor": "ast-verify_false-24-11",
        "merged_from_provisional": [
          "provisional-security-e473342c-93dc-4700-a3e9-4b6ced768f73"
        ]
      },
      "recommended_next_action": "Add authentication decorators to the FastAPI endpoint and enable SSL validation (verify=True) for outbound calls.",
      "merged_from": [
        "55c0f853c2be94d10bddf4cd0e57968d1fc38cbe6ef056d4282ebaa83613b399",
        "b67d961101bda8e8d88863d63c6f46dfd2e0fd198ae75fa776c66cc6dab14059"
      ]
    },
    {
      "id": "3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 11,
        "line_end": 11
      },
      "claim": "Exposed Google API Key in src/app.py",
      "evidence_ref": [
        "file:src/app.py#11"
      ],
      "status": "active",
      "metadata": {
        "secret_type": "Google API Key",
        "fingerprint": "sha256_538e2cfb433f7d06_9012",
        "exposure_status": "prompt_exposed",
        "rule_or_category": "exposed_secret",
        "merged_from_provisional": [
          "promoted-e459898e72497b58ab164abc3a185fd1b7891fdf0931513814a563e87495aecf"
        ]
      },
      "recommended_next_action": "Verify finding in src/app.py lines 11-11.",
      "merged_from": []
    }
  ],
  "contested_items": [
    {
      "id": "merged-7d9d527f5b0568a5",
      "source_agent": "security_debate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 1,
        "line_end": 37
      },
      "claim": "Security debate regarding reliance on type-coercion as a primary defense-in-depth control against injection sinks and unsafe deserialization (pickle).",
      "evidence_ref": [
        "file:src/app.py#1-37"
      ],
      "status": "contested",
      "metadata": {
        "debate_closed_reason": "This proposal demands heavy-handed remediation of four distinct code patterns based on a purely hypothetical threat model ('if type signatures change in the future'). In the current codebase, user_id is an integer and amount is a float, validated at the API boundary by FastAPI. There is no concrete, exploitable execution path for SQL injection, command injection, path traversal, or RCE. Forcing the team to implement redundant runtime escaping and normalization on variables that are strictly numeric is a major drag on developer velocity with zero immediate security return.",
        "merged_from_provisional": [
          "security-63bb72e35446"
        ]
      },
      "recommended_next_action": "Hardening of all input injection sinks independently (parameterized SQL queries, removing pickle entirely) is strongly recommended to avoid relying on fragile type constraints.",
      "merged_from": [
        "343739c62487fc641e0d6024b3428fc6432eca930c8b0ceecf3d4aaf19db26f4",
        "8932eeffa7df484c9d34cb19c275fcab0ddd78d06b5927a6753b509f8dee13cc"
      ]
    },
    {
      "id": "merged-23e09ea0f186f720",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 20,
        "line_end": 35
      },
      "claim": "Static analysis identified high-severity code injection and sanitization risks, including SQL injection, command injection via shell=True, path traversal, and unsafe pickle deserialization.",
      "evidence_ref": [
        "file:src/app.py#20-20",
        "file:src/app.py#28-28",
        "file:src/app.py#32-32",
        "file:src/app.py#35-35"
      ],
      "status": "contested",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "unsafe_deserialize",
        "ast_node_id": "ast-unsafe_deserialize-35-4",
        "evidence_anchor": "ast-unsafe_deserialize-35-4",
        "debate_closed_reason": "The amount parameter is strictly validated as a float. Passing a float to pickle.loads raises a TypeError and crashes, which is a logic/denial-of-service bug, not an exploitable remote code execution path.",
        "merged_from_provisional": [
          "provisional-security-610ec08d-ec2d-4fcd-8479-551b4028519f"
        ]
      },
      "recommended_next_action": "Address each sink independently: parameterize the SQL query, avoid using shell=True, normalize and check paths against a root directory, and remove or replace pickle.loads with a safer format like JSON.",
      "merged_from": [
        "cabaceba9a248214eaa5317b9a3939fb1c35e3b4e58fb40d82dd32622084697f",
        "51917c25934b8ef085b757d2bc2cff37858fa230c89b14d32cf9859fd245a155",
        "10056dce572bdc1d4f0c6e8eddaf22f1e5e924650c7400bb217dd6554b4398bd",
        "622b654fdea073b0ef1e6aecd94b8a87a378a0f7bb78a08b89a9bbce7b81d42b"
      ]
    }
  ],
  "omitted_findings": [
    {
      "id": "3d5fd1eb9d4f2ea1b275128175e6c6edb4dd91796bfec425ae0838ddb8ae13e2",
      "source_agent": "blast_radius_agent",
      "perspective": "blast_radius",
      "severity": "low",
      "location": {
        "path": "scripts/check_commit_window.py",
        "line_start": 69,
        "line_end": 93
      },
      "claim": "Changing `scripts.check_commit_window.run_check` impacts 2 definitions across 2 files (call-graph blast radius).",
      "evidence_ref": [
        "file:scripts/check_commit_window.py#69-93"
      ],
      "status": "active",
      "metadata": {
        "symbol": "scripts.check_commit_window.run_check",
        "rule_or_category": "blast_radius",
        "dependent_fqns": [
          "scripts.check_commit_window.main",
          "tests.test_commit_window.test_run_check_exit_codes"
        ],
        "dependent_files": [
          "scripts/check_commit_window.py",
          "tests/test_commit_window.py"
        ],
        "import_paths": [],
        "pipelines": [],
        "merge_requests": [],
        "related_vulnerabilities": [],
        "merged_from_provisional": [
          "prov-blast-63f03459a590"
        ],
        "ledger_disposition": "omitted",
        "omitted_reason": "Low-severity call graph dependency finding that is highly redundant and does not represent an actual vulnerability or code defect."
      },
      "recommended_next_action": null,
      "merged_from": []
    }
  ],
  "merged_constituents": [
    {
      "id": "ce4c5268df3c0b5211a8e35dbbbadc3abf8a7b730dbada16da0cd44ca236d82a",
      "source_agent": "blast_radius_agent",
      "perspective": "blast_radius",
      "severity": "medium",
      "location": {
        "path": "scripts/check_commit_window.py",
        "line_start": 9,
        "line_end": 30
      },
      "claim": "Changing `scripts.check_commit_window.parse_git_date` impacts 10 definitions across 2 files (call-graph blast radius).",
      "evidence_ref": [
        "file:scripts/check_commit_window.py#9-30"
      ],
      "status": "active",
      "metadata": {
        "symbol": "scripts.check_commit_window.parse_git_date",
        "rule_or_category": "blast_radius",
        "dependent_fqns": [
          "scripts.check_commit_window.check_commit_dates",
          "scripts.check_commit_window.main",
          "scripts.check_commit_window.run_check",
          "tests.test_commit_window.test_check_commit_dates_all_valid",
          "tests.test_commit_window.test_check_commit_dates_invalid_author",
          "tests.test_commit_window.test_check_commit_dates_invalid_commit",
          "tests.test_commit_window.test_check_commit_dates_timezone_boundaries",
          "tests.test_commit_window.test_parse_git_date_invalid",
          "tests.test_commit_window.test_parse_git_date_valid",
          "tests.test_commit_window.test_run_check_exit_codes"
        ],
        "dependent_files": [
          "scripts/check_commit_window.py",
          "tests/test_commit_window.py"
        ],
        "import_paths": [],
        "pipelines": [],
        "merge_requests": [],
        "related_vulnerabilities": [],
        "merged_from_provisional": [
          "prov-blast-2f9c6309c43d"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-6f9f7413fd749d9c"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "0a2301af8534fd1d31a4d93f9ab1619517404d49c63909474b2daf28d31a35de",
      "source_agent": "blast_radius_agent",
      "perspective": "blast_radius",
      "severity": "medium",
      "location": {
        "path": "scripts/check_commit_window.py",
        "line_start": 32,
        "line_end": 67
      },
      "claim": "Changing `scripts.check_commit_window.check_commit_dates` impacts 7 definitions across 2 files (call-graph blast radius).",
      "evidence_ref": [
        "file:scripts/check_commit_window.py#32-67"
      ],
      "status": "active",
      "metadata": {
        "symbol": "scripts.check_commit_window.check_commit_dates",
        "rule_or_category": "blast_radius",
        "dependent_fqns": [
          "scripts.check_commit_window.main",
          "scripts.check_commit_window.run_check",
          "tests.test_commit_window.test_check_commit_dates_all_valid",
          "tests.test_commit_window.test_check_commit_dates_invalid_author",
          "tests.test_commit_window.test_check_commit_dates_invalid_commit",
          "tests.test_commit_window.test_check_commit_dates_timezone_boundaries",
          "tests.test_commit_window.test_run_check_exit_codes"
        ],
        "dependent_files": [
          "scripts/check_commit_window.py",
          "tests/test_commit_window.py"
        ],
        "import_paths": [],
        "pipelines": [],
        "merge_requests": [],
        "related_vulnerabilities": [],
        "merged_from_provisional": [
          "prov-blast-a69c0ddbc4bf"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-6f9f7413fd749d9c"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "343739c62487fc641e0d6024b3428fc6432eca930c8b0ceecf3d4aaf19db26f4",
      "source_agent": "security_debate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 1,
        "line_end": 37
      },
      "claim": "pickle.loads on request-derived data (src/app.py:30) is a latent RCE primitive that must be removed outright, not merely reclassified as a crash bug. The defender's 'it just raises TypeError' argument depends entirely on the float type annotation holding forever. If amount ever carries bytes (e.g., signature change, or a future endpoint reusing this logic), pickle.loads enables arbitrary code execution via malicious pickle payloads. The correct remediation is to delete the pickle call entirely or replace with a safe format (json).",
      "evidence_ref": [
        "file:src/app.py#1-37"
      ],
      "status": "contested",
      "metadata": {
        "debate_closed_reason": "The argument that pickle.loads is a high-severity 'latent RCE' depends entirely on a speculative API signature change. As currently written, amount is a float; passing it to pickle.loads guarantees a TypeError, resulting in an application crash (logic bug / DoS), not remote code execution. Promoting a crash bug to a high-severity security issue based on what the code 'might do' in a future refactor is impractical and distracts from the real, exploitable bugs that we should be focused on fixing.",
        "merged_from_provisional": [
          "security-4f53519fea23"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-7d9d527f5b0568a5"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "8932eeffa7df484c9d34cb19c275fcab0ddd78d06b5927a6753b509f8dee13cc",
      "source_agent": "security_debate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 1,
        "line_end": 37
      },
      "claim": "Type-coercion is not a durable security control for the injection sinks. The /payout signature (user_id: int, amount: float) is the ONLY thing currently shielding the f-string SQL (src/app.py:20), shell=True call (src/app.py:27), path open (src/app.py:24), and pickle.loads (src/app.py:30). There is no defense-in-depth: a single signature change to str/Optional/Pydantic model re-arms all four sinks simultaneously. Each sink must be independently hardened (parameterized query, no shell=True, path normalization+root check, remove pickle).",
      "evidence_ref": [
        "file:src/app.py#1-37"
      ],
      "status": "contested",
      "metadata": {
        "debate_closed_reason": "This proposal demands heavy-handed remediation of four distinct code patterns based on a purely hypothetical threat model ('if type signatures change in the future'). In the current codebase, user_id is an integer and amount is a float, validated at the API boundary by FastAPI. There is no concrete, exploitable execution path for SQL injection, command injection, path traversal, or RCE. Forcing the team to implement redundant runtime escaping and normalization on variables that are strictly numeric is a major drag on developer velocity with zero immediate security return.",
        "merged_from_provisional": [
          "security-63bb72e35446"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-7d9d527f5b0568a5"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "ced88143ca0827765160601f5718fc5514858a36c80f33adba296edf08b492fb",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 13,
        "line_end": 14
      },
      "claim": "The payout endpoint at src/app.py does not implement or enforce any administrator level access control, whereas SPEC.md specifies that all payment-related endpoints must require administrator level access.",
      "evidence_ref": [
        "file:SPEC.md#5-6",
        "file:src/app.py#13-14"
      ],
      "status": "active",
      "metadata": {
        "merged_from_provisional": [
          "prov-correctness-001"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-2f5fdd9c293d27d0"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "cd83f565c2015c4db3e71c1761969c49a99aab04bb473add6953dd4a1492c50c",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 20,
        "line_end": 20
      },
      "claim": "The database query in src/app.py attempts to verify the user balance by querying the 'ledger' table, whereas SPEC.md specifies that the payout endpoint must verify the user account balance by querying the 'transactions' database table.",
      "evidence_ref": [
        "file:SPEC.md#8-9",
        "file:src/app.py#20-20"
      ],
      "status": "active",
      "metadata": {
        "merged_from_provisional": [
          "prov-correctness-002"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-2f5fdd9c293d27d0"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "66594da6dc9c7e811293b01ae026352a4fcf797add814d483f1f2d0a6a14a496",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 24,
        "line_end": 24
      },
      "claim": "The external payment provider request in src/app.py is executed with SSL certificate verification disabled via verify=False, whereas SPEC.md specifies that all external payment provider calls must verify the SSL certificates.",
      "evidence_ref": [
        "file:SPEC.md#11-12",
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "merged_from_provisional": [
          "prov-correctness-003"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-2f5fdd9c293d27d0"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "55c0f853c2be94d10bddf4cd0e57968d1fc38cbe6ef056d4282ebaa83613b399",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 14,
        "line_end": 37
      },
      "claim": "Missing authorization: HTTP write route lacks any auth decorator or dependency.",
      "evidence_ref": [
        "file:src/app.py#14-37"
      ],
      "status": "active",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "missing_auth",
        "ast_node_id": "ast-missing_auth-14-0",
        "evidence_anchor": "ast-missing_auth-14-0",
        "merged_from_provisional": [
          "provisional-security-a4482bd9-fbee-4de5-bafe-2c54d7c1978f"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-183b99257b673e39"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "b67d961101bda8e8d88863d63c6f46dfd2e0fd198ae75fa776c66cc6dab14059",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 24,
        "line_end": 24
      },
      "claim": "SSL verification disabled: HTTP call contains verify=False.",
      "evidence_ref": [
        "file:src/app.py#24-24"
      ],
      "status": "active",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "verify_false",
        "ast_node_id": "ast-verify_false-24-11",
        "evidence_anchor": "ast-verify_false-24-11",
        "merged_from_provisional": [
          "provisional-security-e473342c-93dc-4700-a3e9-4b6ced768f73"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-183b99257b673e39"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "cabaceba9a248214eaa5317b9a3939fb1c35e3b4e58fb40d82dd32622084697f",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 20,
        "line_end": 20
      },
      "claim": "SQL Injection risk: DB execute call receives a non-literal query expression constructed with f-string, concat, or format.",
      "evidence_ref": [
        "file:src/app.py#20-20"
      ],
      "status": "contested",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "sqli",
        "ast_node_id": "ast-sqli-20-4",
        "evidence_anchor": "ast-sqli-20-4",
        "debate_closed_reason": "Because user_id is strictly validated as an integer, no arbitrary SQL commands can be injected. While string formatting in SQL is bad practice, this specific instance is completely unexploitable.",
        "merged_from_provisional": [
          "provisional-security-59893a48-a211-4492-925f-9fdfc3905f45"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-23e09ea0f186f720"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "51917c25934b8ef085b757d2bc2cff37858fa230c89b14d32cf9859fd245a155",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 28,
        "line_end": 28
      },
      "claim": "Path traversal risk: request input is used directly in a path open or join operation without a normalize-and-root check.",
      "evidence_ref": [
        "file:src/app.py#28-28"
      ],
      "status": "contested",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "path_traversal",
        "ast_node_id": "ast-path_traversal-28-9",
        "evidence_anchor": "ast-path_traversal-28-9",
        "debate_closed_reason": "FastAPI automatically validates and coerces the user_id path/query parameter to a Python int. Any input with path traversal sequences (such as '../') is blocked with a 422 Validation Error before the route executes. This makes path traversal impossible.",
        "merged_from_provisional": [
          "provisional-security-8f5ecb30-ec64-4942-abb3-3c8224c6530a"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-23e09ea0f186f720"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "10056dce572bdc1d4f0c6e8eddaf22f1e5e924650c7400bb217dd6554b4398bd",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 32,
        "line_end": 32
      },
      "claim": "Command injection risk: subprocess call with shell=True receives a non-literal command argument.",
      "evidence_ref": [
        "file:src/app.py#32-32"
      ],
      "status": "contested",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "shell_true",
        "ast_node_id": "ast-shell_true-32-4",
        "evidence_anchor": "ast-shell_true-32-4",
        "debate_closed_reason": "Since user_id is coerced into an integer, it cannot contain command separators or shell metacharacters, making shell command injection impossible.",
        "merged_from_provisional": [
          "provisional-security-bc5379fa-53d1-4b95-adfb-d0b862d2126d"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-23e09ea0f186f720"
      },
      "recommended_next_action": null,
      "merged_from": []
    },
    {
      "id": "622b654fdea073b0ef1e6aecd94b8a87a378a0f7bb78a08b89a9bbce7b81d42b",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 35,
        "line_end": 35
      },
      "claim": "Unsafe deserialization risk: pickle load/loads called on non-literal data.",
      "evidence_ref": [
        "file:src/app.py#35-35"
      ],
      "status": "contested",
      "metadata": {
        "rule_or_category": "security_baseline",
        "sub_rule": "unsafe_deserialize",
        "ast_node_id": "ast-unsafe_deserialize-35-4",
        "evidence_anchor": "ast-unsafe_deserialize-35-4",
        "debate_closed_reason": "The amount parameter is strictly validated as a float. Passing a float to pickle.loads raises a TypeError and crashes, which is a logic/denial-of-service bug, not an exploitable remote code execution path.",
        "merged_from_provisional": [
          "provisional-security-610ec08d-ec2d-4fcd-8479-551b4028519f"
        ],
        "ledger_disposition": "merged",
        "merged_into": "merged-23e09ea0f186f720"
      },
      "recommended_next_action": null,
      "merged_from": []
    }
  ],
  "secret_scan_summary": [
    {
      "id": "f7343197f028df5034b7474a8f06fde26ea3113f8da1e1a1fe76a5cccd5b3f27",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "info",
      "location": {
        "path": ".env",
        "line_start": 2,
        "line_end": 2
      },
      "claim": "Exposed Database Password in .env",
      "evidence_ref": [
        "file:.env#2"
      ],
      "secret_type": "Database Password",
      "fingerprint": "sha256_9de672d8e47935a5_2345",
      "exposure_status": "ignored_by_root_gitignore"
    },
    {
      "id": "e459898e72497b58ab164abc3a185fd1b7891fdf0931513814a563e87495aecf",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 11,
        "line_end": 11
      },
      "claim": "Exposed Google API Key in src/app.py",
      "evidence_ref": [
        "file:src/app.py#11"
      ],
      "secret_type": "Google API Key",
      "fingerprint": "sha256_538e2cfb433f7d06_9012",
      "exposure_status": "prompt_exposed"
    }
  ],
  "accounting_ledger": {
    "included": [
      "merged-6f9f7413fd749d9c",
      "merged-2f5fdd9c293d27d0",
      "merged-183b99257b673e39",
      "3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c"
    ],
    "merged": [
      {
        "output_id": "merged-6f9f7413fd749d9c",
        "input_ids": [
          "ce4c5268df3c0b5211a8e35dbbbadc3abf8a7b730dbada16da0cd44ca236d82a",
          "0a2301af8534fd1d31a4d93f9ab1619517404d49c63909474b2daf28d31a35de"
        ]
      },
      {
        "output_id": "merged-7d9d527f5b0568a5",
        "input_ids": [
          "343739c62487fc641e0d6024b3428fc6432eca930c8b0ceecf3d4aaf19db26f4",
          "8932eeffa7df484c9d34cb19c275fcab0ddd78d06b5927a6753b509f8dee13cc"
        ]
      },
      {
        "output_id": "merged-2f5fdd9c293d27d0",
        "input_ids": [
          "ced88143ca0827765160601f5718fc5514858a36c80f33adba296edf08b492fb",
          "cd83f565c2015c4db3e71c1761969c49a99aab04bb473add6953dd4a1492c50c",
          "66594da6dc9c7e811293b01ae026352a4fcf797add814d483f1f2d0a6a14a496"
        ]
      },
      {
        "output_id": "merged-183b99257b673e39",
        "input_ids": [
          "55c0f853c2be94d10bddf4cd0e57968d1fc38cbe6ef056d4282ebaa83613b399",
          "b67d961101bda8e8d88863d63c6f46dfd2e0fd198ae75fa776c66cc6dab14059"
        ]
      },
      {
        "output_id": "merged-23e09ea0f186f720",
        "input_ids": [
          "cabaceba9a248214eaa5317b9a3939fb1c35e3b4e58fb40d82dd32622084697f",
          "51917c25934b8ef085b757d2bc2cff37858fa230c89b14d32cf9859fd245a155",
          "10056dce572bdc1d4f0c6e8eddaf22f1e5e924650c7400bb217dd6554b4398bd",
          "622b654fdea073b0ef1e6aecd94b8a87a378a0f7bb78a08b89a9bbce7b81d42b"
        ]
      }
    ],
    "omitted": [
      {
        "id": "3d5fd1eb9d4f2ea1b275128175e6c6edb4dd91796bfec425ae0838ddb8ae13e2",
        "reason": "Low-severity call graph dependency finding that is highly redundant and does not represent an actual vulnerability or code defect."
      }
    ],
    "contested": [
      "merged-7d9d527f5b0568a5",
      "merged-23e09ea0f186f720"
    ]
  },
  "validator_warnings": []
};

// State to store current report
let currentReport = null;
let activeTab = 'all';
let activePerspectives = new Set(['all']); // Perspective filter state

document.addEventListener('DOMContentLoaded', () => {
  initDragAndDrop();
  initTabs();
  initPerspectiveFilters();

  // Set up mock button handler
  const demoBtn = document.getElementById('demo-load-btn');
  demoBtn.addEventListener('click', () => {
    loadReportData(MOCK_DEMO_REPORT);
  });

  // Home button handler
  const homeBtn = document.getElementById('home-btn');
  homeBtn.addEventListener('click', () => {
    resetToUploadView();
  });

  // Download report handler
  const downloadBtn = document.getElementById('download-report-btn');
  downloadBtn.addEventListener('click', () => {
    downloadReport();
  });

  // Adversarial debate viewer handlers
  document.getElementById('view-debate-btn').addEventListener('click', openDebateModal);
  document.getElementById('debate-modal-close').addEventListener('click', closeDebateModal);
  document.getElementById('debate-modal').addEventListener('click', (e) => {
    // Click on the dimmed backdrop (not the dialog body) closes the modal.
    if (e.target.id === 'debate-modal') closeDebateModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDebateModal();
  });
});

/**
 * Pull the adversarial debate transcript out of a report, if one was recorded.
 * Real runs attach it at run_metadata.debate_transcript; returns null when the
 * debate never engaged (disabled, budget-skipped, or AST-only fallback).
 */
function getDebateTranscript(report) {
  const t = report && report.run_metadata && report.run_metadata.debate_transcript;
  if (!t || t.engaged === false) return null;
  if (!Array.isArray(t.rounds) || t.rounds.length === 0) return null;
  return t;
}

/**
 * Initialize Drag and Drop Upload System
 */
function initDragAndDrop() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  // Highlighting drag states
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleRepositoryUpload(files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleRepositoryUpload(fileInput.files[0]);
    }
  });
}

/**
 * Send zip archive to FastAPI backend for live, streamed analysis.
 * Consumes the Server-Sent Event stream from POST /review/stream so each pipeline
 * stage is shown as it happens, then renders the dashboard from the terminal report.
 * Falls back to the blocking POST /review if streaming is unavailable.
 * @param {File} file
 */
async function handleRepositoryUpload(file) {
  if (file.type !== 'application/zip' && !file.name.endsWith('.zip')) {
    alert('Invalid file format. Please upload a repository packaged as a .zip file.');
    return;
  }

  const dropzone = document.getElementById('dropzone');
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');

  // Transition UI to progress view and build the live step tracker.
  dropzone.classList.add('hidden');
  progressContainer.classList.remove('hidden');
  progressFill.style.width = '4%';
  statusText.textContent = 'Uploading repository archive...';
  buildStepTracker();

  try {
    const result = await streamReview(file);
    if (result.report) {
      finishWithReport(result.report);
    } else {
      // A pipeline-level error event was already surfaced to the user.
      resetUploadUI();
    }
  } catch (streamErr) {
    // Transport-level failure (endpoint missing, no streaming support, network).
    // Fall back to the blocking endpoint so the dashboard still renders.
    console.warn('Streaming unavailable, falling back to blocking /review:', streamErr);
    hideStepTracker();
    progressFill.style.width = '45%';
    statusText.textContent = 'Streaming unavailable - running analysis...';
    try {
      const report = await blockingReview(file);
      finishWithReport(report);
    } catch (error) {
      console.error('Analysis failed:', error);
      alert(`Orchestrator Error: ${error.message}`);
      resetUploadUI();
    }
  }
}

/**
 * Canonical ordered pipeline stages, mirroring the backend SSE step names.
 */
const PIPELINE_STEPS = [
  { key: 'ingestion', label: 'Extracting & hardening archive' },
  { key: 'secret_gate', label: 'Pre-flight secret scan' },
  { key: 'correctness', label: 'Correctness specialist' },
  { key: 'security', label: 'Security specialist (AST + debate)' },
  { key: 'blast_radius', label: 'Blast-radius specialist' },
  { key: 'compile', label: 'Compiling final report' },
];

/**
 * Stream POST /review/stream and drive the live step tracker.
 * @param {File} file
 * @returns {Promise<{report: Object|null}>} report on success, {report:null} if a
 *   pipeline error event was handled. Throws only on transport failure (triggers fallback).
 */
async function streamReview(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/review/stream', { method: 'POST', body: formData });
  const ctype = response.headers.get('content-type') || '';
  if (!response.ok || !response.body || !ctype.includes('text/event-stream')) {
    throw new Error('stream-unsupported');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalReport = null;
  let pipelineError = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex;
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawFrame = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const evt = parseSseFrame(rawFrame);
      if (!evt) continue;

      if (evt.event === 'step') {
        updateStepTracker(evt.data);
      } else if (evt.event === 'debate') {
        handleDebateEvent(evt.data);
      } else if (evt.event === 'report') {
        finalReport = evt.data;
      } else if (evt.event === 'error') {
        pipelineError = evt.data;
      }
    }
  }

  if (pipelineError) {
    markStepError(pipelineError);
    alert(`Orchestrator Error: ${pipelineError.message || 'Review pipeline failed.'}`);
    return { report: null };
  }
  if (!finalReport) {
    // Stream ended without a report and without an error frame  treat as a transport
    // failure so we fall back to the blocking endpoint.
    throw new Error('stream-ended-without-report');
  }
  return { report: finalReport };
}

/**
 * Blocking fallback: POST /review and return the parsed report.
 * @param {File} file
 */
async function blockingReview(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/review', { method: 'POST', body: formData });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Review run aborted or failed.');
  }
  return await response.json();
}

/**
 * Parse a single raw SSE frame into {event, data}. Returns null if it has no data line.
 * @param {string} rawFrame
 */
function parseSseFrame(rawFrame) {
  let eventName = 'message';
  const dataLines = [];
  rawFrame.split('\n').forEach(line => {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  });
  if (dataLines.length === 0) return null;
  try {
    return { event: eventName, data: JSON.parse(dataLines.join('\n')) };
  } catch (e) {
    return null;
  }
}

/**
 * Build the live step tracker rows inside the progress container.
 */
function buildStepTracker() {
  const container = document.getElementById('upload-progress-container');
  let tracker = document.getElementById('live-steps');
  if (tracker) tracker.remove();

  tracker = document.createElement('ul');
  tracker.id = 'live-steps';
  tracker.className = 'live-steps';

  PIPELINE_STEPS.forEach(step => {
    const li = document.createElement('li');
    li.className = 'live-step is-pending';
    li.id = `live-step-${step.key}`;

    // Icon glyph (pending ring / spinner / check / x) is rendered by CSS from the
    // row's state class, so the element is intentionally empty.
    const icon = document.createElement('span');
    icon.className = 'live-step-icon';

    const label = document.createElement('span');
    label.className = 'live-step-label';
    label.textContent = step.label;

    li.appendChild(icon);
    li.appendChild(label);
    tracker.appendChild(li);
  });

  container.appendChild(tracker);
  buildActivityConsole();
}

/**
 * Update a single step row + the progress bar from a `step` SSE event.
 * @param {Object} data {step, status, label, index, total}
 */
function updateStepTracker(data) {
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');
  const total = data.total || PIPELINE_STEPS.length;
  const index = data.index || 0;

  if (data.label) statusText.textContent = data.label;

  // Running: bar sits just before the step completes; Complete: bar reaches index/total.
  const fraction = data.status === 'complete'
    ? index / total
    : Math.max(0, (index - 1)) / total + (0.5 / total);
  progressFill.style.width = `${Math.min(100, Math.round(fraction * 100))}%`;

  const row = document.getElementById(`live-step-${data.step}`);
  if (!row) return;

  row.classList.remove('is-pending', 'is-running', 'is-complete', 'is-error');
  if (data.status === 'complete') {
    row.classList.add('is-complete');
    stopStepFlavor();
    appendActivity(`${data.label || data.step} — done`, 'good');
  } else {
    row.classList.add('is-running');
    appendActivity(`▸ ${data.label || data.step}`, 'accent');
    startStepFlavor(data.step);
  }
}

/**
 * Mark the step that failed (from a terminal `error` event).
 * @param {Object} data {step, message}
 */
function markStepError(data) {
  stopStepFlavor();
  const row = document.getElementById(`live-step-${data.step}`);
  if (row) {
    row.classList.remove('is-pending', 'is-running', 'is-complete');
    row.classList.add('is-error');
  }
  appendActivity(`✕ ${data.step} failed — ${data.message || 'pipeline error'}`, 'warn');
}

function hideStepTracker() {
  stopStepFlavor();
  const tracker = document.getElementById('live-steps');
  if (tracker) tracker.remove();
  const consoleEl = document.getElementById('activity-console');
  if (consoleEl) consoleEl.remove();
}

/* --------------------------------------------------------------------------- *
 * Live activity console — a "behind the scenes" debug feed that keeps the user
 * informed (and entertained) across the 2-3 min run. Real SSE step events drive
 * the headline lines; per-step flavor pools fill the quiet stretches, with the
 * security step getting a Crucible-style adversarial-debate scoreboard.
 * --------------------------------------------------------------------------- */
let activityTimer = null;
let activityStartTime = 0;
let debateState = null;
let realDebateActive = false; // true once authentic SSE debate events arrive

const STEP_FLAVOR = {
  ingestion: [
    'unzipping archive into hardened sandbox…',
    'rejecting path-traversal & zip-slip entries…',
    'normalizing line endings and encodings…',
    'computing per-file size & type manifest…',
  ],
  secret_gate: [
    'scanning for high-entropy strings…',
    'matching Google / AWS / private-key signatures…',
    'cross-checking .gitignore exposure status…',
    'salting + hashing matches (no raw secrets leave the box)…',
  ],
  correctness: [
    'reading SPEC.md intent vs. implemented behavior…',
    'diffing documented requirements against code paths…',
    'grounding each claim to exact file + line evidence…',
    'flagging divergences for the coordinator…',
  ],
  blast_radius: [
    'querying Orbit knowledge graph over GitLab…',
    'resolving call sites for changed symbols…',
    'walking import edges to estimate impact…',
    'ranking findings by reachability…',
  ],
  compile: [
    'merging overlapping findings…',
    'enforcing conservation ledger (nothing dropped silently)…',
    'validating evidence coordinates in-bounds…',
    'finalizing stable finding IDs…',
  ],
};

const DEBATE_CHALLENGER = [
  'probing auth surface on write routes…',
  'arguing the deserialize path is attacker-reachable…',
  'pushing on the SQL string concatenation…',
  'claiming the path join is exploitable via ../…',
  'questioning whether verify=False ships to prod…',
];
const DEBATE_DEFENDER = [
  'rebuts: route is guarded by Depends(get_current_user)…',
  'counters: input is schema-validated upstream…',
  'concedes the point — finding survives…',
  'argues out-of-scope for the correctness baseline…',
  'demands grounded evidence before scoring…',
];

function buildActivityConsole() {
  const container = document.getElementById('upload-progress-container');
  let consoleEl = document.getElementById('activity-console');
  if (consoleEl) consoleEl.remove();

  consoleEl = document.createElement('div');
  consoleEl.id = 'activity-console';
  consoleEl.className = 'activity-console';

  const header = document.createElement('div');
  header.className = 'activity-console-header';
  header.textContent = 'behind the scenes';
  consoleEl.appendChild(header);

  const body = document.createElement('div');
  body.id = 'activity-console-body';
  consoleEl.appendChild(body);

  container.appendChild(consoleEl);
  activityStartTime = Date.now();
  debateState = null;
  realDebateActive = false;
  appendActivity('analysis pipeline initialized', 'accent');
}

/**
 * Render a real debate event streamed from the backend (phase ∈
 * start|round|scoreboard|complete). The first real event silences the synthetic
 * security flavor so the authentic rounds/scores take over.
 */
function handleDebateEvent(d) {
  if (!realDebateActive) {
    realDebateActive = true;
    stopStepFlavor();
  }
  if (!d || !d.phase) return;

  if (d.phase === 'start') {
    appendActivity(
      `adversarial debate engaged · ${d.seed_findings} seed finding(s) · Claude vs Gemini`,
      'accent'
    );
  } else if (d.phase === 'round') {
    const actor = d.actor === 'defender' ? 'Gemini (defender)' : 'Claude (challenger)';
    const kind = d.actor === 'defender' ? 'defender' : 'challenger';
    const bits = [];
    if (d.scored) bits.push(`scored ${d.scored}`);
    if (d.proposed) bits.push(`proposed ${d.proposed}`);
    appendActivity(`round ${d.round} · ${actor}${bits.length ? ' — ' + bits.join(', ') : ''}`, kind);
  } else if (d.phase === 'scoreboard') {
    appendActivity(`scoreboard · challenger ${d.challenger} · defender ${d.defender}`, '');
  } else if (d.phase === 'complete') {
    const reason = d.stop_reason ? ` (${d.stop_reason})` : '';
    appendActivity(`debate resolved · ${d.survived} survived · ${d.contested} contested${reason}`, 'good');
  }
}

function elapsedStamp() {
  const s = Math.floor((Date.now() - activityStartTime) / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

/**
 * Append one timestamped line. `kind` ∈ accent|good|warn|challenger|defender|''.
 */
function appendActivity(msg, kind = '') {
  const body = document.getElementById('activity-console-body');
  const consoleEl = document.getElementById('activity-console');
  if (!body || !consoleEl) return;

  const line = document.createElement('div');
  line.className = 'activity-line' + (kind ? ` is-${kind}` : '');

  const time = document.createElement('span');
  time.className = 'activity-time';
  time.textContent = elapsedStamp();

  const text = document.createElement('span');
  text.className = 'activity-msg';
  text.textContent = msg;

  line.appendChild(time);
  line.appendChild(text);
  body.appendChild(line);

  // Keep the log bounded and pinned to the newest line.
  while (body.children.length > 80) body.removeChild(body.firstChild);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Start rotating flavor lines for the running step. The security step runs the
 * Crucible-style debate scoreboard (challenger vs defender, rounds, points).
 */
function startStepFlavor(stepKey) {
  stopStepFlavor();

  if (stepKey === 'security') {
    debateState = { round: 1, turn: 'challenger', challenger: 0, defender: 0 };
    appendActivity('adversarial debate engaged · Claude (challenger) vs Gemini (defender)', 'accent');
    activityTimer = setInterval(tickDebate, 2400);
    return;
  }

  const pool = STEP_FLAVOR[stepKey];
  if (!pool) return;
  activityTimer = setInterval(() => appendActivity(pick(pool)), 2600);
}

function tickDebate() {
  if (!debateState) return;
  const st = debateState;

  if (st.turn === 'challenger') {
    appendActivity(`round ${st.round} · Claude ${pick(DEBATE_CHALLENGER)}`, 'challenger');
    st.turn = 'defender';
  } else {
    const line = pick(DEBATE_DEFENDER);
    appendActivity(`round ${st.round} · Gemini ${line}`, 'defender');
    // Score the exchange: a concession favors the challenger's finding.
    if (line.includes('survives') || line.includes('concedes')) st.challenger += 1;
    else st.defender += 1;
    appendActivity(`scoreboard · challenger ${st.challenger} · defender ${st.defender}`, '');
    st.turn = 'challenger';
    st.round += 1;
  }
}

function stopStepFlavor() {
  if (activityTimer) {
    clearInterval(activityTimer);
    activityTimer = null;
  }
}

/**
 * Transition from the progress view to the rendered dashboard.
 * @param {Object} report
 */
function finishWithReport(report) {
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');

  progressFill.style.width = '100%';
  statusText.textContent = 'Analysis complete. Loading dashboard...';

  setTimeout(() => {
    progressContainer.classList.add('hidden');
    hideStepTracker();
    loadReportData(report);
  }, 500);
}

/**
 * Reset the upload view after a failed/aborted run.
 */
function resetUploadUI() {
  const dropzone = document.getElementById('dropzone');
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  progressContainer.classList.add('hidden');
  hideStepTracker();
  if (progressFill) progressFill.style.width = '0%';
  dropzone.classList.remove('hidden');
}

/**
 * Reset UI back to upload view
 */
function resetToUploadView() {
  currentReport = null;
  activeTab = 'all';
  activePerspectives = new Set(['all']);

  // Hide dashboard and header buttons
  document.getElementById('dashboard-content').classList.add('hidden');
  document.getElementById('home-btn').classList.add('hidden');
  document.getElementById('download-report-btn').classList.add('hidden');
  document.getElementById('view-debate-btn').classList.add('hidden');
  closeDebateModal();
  document.getElementById('demo-load-btn').classList.remove('hidden');

  // Show upload section
  const uploadSection = document.getElementById('upload-section');
  uploadSection.classList.remove('hidden');
  document.getElementById('dropzone').classList.remove('hidden');
  document.getElementById('upload-progress-container').classList.add('hidden');

  // Reset file input
  document.getElementById('file-input').value = '';

  // Reset perspective filters
  document.querySelectorAll('.perspective-toggle').forEach(btn => {
    btn.classList.remove('active');
  });
  document.getElementById('filter-all').classList.add('active');

  // Reset tab state
  document.querySelectorAll('.tab-btn').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  document.getElementById('tab-all').classList.add('active');
  document.getElementById('tab-all').setAttribute('aria-selected', 'true');
  document.querySelectorAll('.tab-panel-content').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-findings').classList.remove('hidden');
}

/**
 * Initialize Dashboard Tab Bar Actions
 */
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Deactivate other tabs
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });

      // Activate clicked tab
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      const targetPanelId = tab.getAttribute('aria-controls');

      // Hide all panels
      panels.forEach(p => p.classList.add('hidden'));

      // Show selected panel
      document.getElementById(targetPanelId).classList.remove('hidden');

      // Update state
      if (tab.id === 'tab-all') {
        activeTab = 'all';
        renderFindingsList();
      } else if (tab.id === 'tab-high') {
        activeTab = 'high';
        renderFindingsList();
      } else if (tab.id === 'tab-contested') {
        activeTab = 'contested';
      } else if (tab.id === 'tab-secrets') {
        activeTab = 'secrets';
      } else if (tab.id === 'tab-ledger') {
        activeTab = 'ledger';
      }
    });
  });
}

/**
 * Initialize Perspective Filter Toggle Buttons
 */
function initPerspectiveFilters() {
  const toggles = document.querySelectorAll('.perspective-toggle');

  toggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
      const perspective = toggle.dataset.perspective;

      if (perspective === 'all') {
        // "All" resets everything
        activePerspectives = new Set(['all']);
        toggles.forEach(t => t.classList.remove('active'));
        toggle.classList.add('active');
      } else {
        // Individual toggle  remove "all"
        activePerspectives.delete('all');
        document.getElementById('filter-all').classList.remove('active');

        if (activePerspectives.has(perspective)) {
          activePerspectives.delete(perspective);
          toggle.classList.remove('active');
        } else {
          activePerspectives.add(perspective);
          toggle.classList.add('active');
        }

        // If nothing selected, revert to "all"
        if (activePerspectives.size === 0) {
          activePerspectives = new Set(['all']);
          document.getElementById('filter-all').classList.add('active');
        }
      }

      renderFindingsList();
    });
  });
}

/**
 * Check if a finding matches the active perspective filters
 */
function matchesPerspectiveFilter(finding) {
  if (activePerspectives.has('all')) return true;

  // Map source_agent to filter perspective
  if (finding.source_agent === 'preflight_secret_gate') {
    return activePerspectives.has('preflight');
  }
  if (finding.perspective === 'blast_radius') {
    return activePerspectives.has('blast_radius');
  }
  // correctness and security map directly
  return activePerspectives.has(finding.perspective);
}

/**
 * Load complete report structure into dashboard memory and redraw
 * @param {Object} report
 */
function loadReportData(report) {
  currentReport = report;

  // Hide upload section, show dashboard
  document.getElementById('upload-section').classList.add('hidden');
  document.getElementById('dashboard-content').classList.remove('hidden');

  // Show header buttons
  document.getElementById('home-btn').classList.remove('hidden');
  document.getElementById('download-report-btn').classList.remove('hidden');
  document.getElementById('demo-load-btn').classList.add('hidden');

  // Reveal the debate replay button only when a transcript was actually recorded.
  const debateBtn = document.getElementById('view-debate-btn');
  debateBtn.classList.toggle('hidden', !getDebateTranscript(report));

  // 1. Populate Scan Info
  document.getElementById('meta-time').textContent = report.run_metadata.start_time ? formatTimestamp(report.run_metadata.start_time) : 'n/a';
  const compilationMode = report.run_metadata.compilation_mode || 'unknown';
  const compilationEl = document.getElementById('meta-compilation');
  // The "coordinated" path means the ADK-driven coordinator compiled the report;
  // surface that as "ADK" rather than the opaque internal mode name.
  compilationEl.textContent = compilationMode === 'coordinated' ? 'ADK' : compilationMode === 'terminal_fallback' ? 'Terminal Fallback' : compilationMode;
  compilationEl.className = 'meta-value' + (compilationMode === 'terminal_fallback' ? ' compilation-fallback' : ' compilation-ok');

  // 2. Populate Corpus Summary
  document.getElementById('stat-file-count').textContent = report.corpus_summary.file_count || 0;
  document.getElementById('stat-total-bytes').textContent = formatBytes(report.corpus_summary.total_bytes || 0);
  document.getElementById('stat-skipped-count').textContent = report.corpus_summary.skipped_files || 0;

  // Populate skipped logs list if detailed log is present
  const skippedCard = document.getElementById('skipped-files-list');
  const skippedUl = document.getElementById('skipped-list-ul');
  skippedUl.innerHTML = '';

  if (report.corpus_summary.skipped_log && Object.keys(report.corpus_summary.skipped_log).length > 0) {
    skippedCard.classList.remove('hidden');
    Object.entries(report.corpus_summary.skipped_log).forEach(([filepath, entry]) => {
      const li = document.createElement('li');
      li.textContent = `${filepath}: ${entry.skipped_reason}`;
      skippedUl.appendChild(li);
    });
  } else {
    skippedCard.classList.add('hidden');
  }

  // 3. System Perspectives & Gate Badges
  updatePerspectiveBadge('badge-gate-status', report.gate_status?.status || 'complete');

  const perspectives = {};
  if (report.perspective_statuses) {
    report.perspective_statuses.forEach(p => {
      perspectives[p.perspective] = p;
    });
  }

  updatePerspectiveBadge('badge-correctness-status', perspectives['correctness']?.status || 'skipped');
  updatePerspectiveBadge('badge-security-status', perspectives['security']?.status || 'skipped');
  updatePerspectiveBadge('badge-blast-radius-status', perspectives['blast_radius']?.status || 'disabled');

  // 4. Severity Counter Badges
  const counts = report.severity_counts || {};
  document.getElementById('count-critical').textContent = counts.critical || 0;
  document.getElementById('count-high').textContent = counts.high || 0;
  document.getElementById('count-medium').textContent = counts.medium || 0;
  document.getElementById('count-low').textContent = counts.low || 0;
  document.getElementById('count-info').textContent = counts.info || 0;

  // Render warnings if validator raised warnings
  const warningsBanner = document.getElementById('validator-warning-banner');
  const warningsUl = document.getElementById('warnings-list-ul');
  warningsUl.innerHTML = '';
  if (report.validator_warnings && report.validator_warnings.length > 0) {
    warningsBanner.classList.remove('hidden');
    report.validator_warnings.forEach(warn => {
      const li = document.createElement('li');
      li.textContent = warn;
      warningsUl.appendChild(li);
    });
  } else {
    warningsBanner.classList.add('hidden');
  }

  document.getElementById('tab-count-findings').textContent = (report.findings || []).length;

  const highCriticalCount = (report.high_critical_findings || []).length;
  document.getElementById('tab-count-high').textContent = highCriticalCount;

  document.getElementById('tab-count-contested').textContent = (report.contested_items || []).length;
  document.getElementById('tab-count-secrets').textContent = (report.secret_scan_summary || []).length;

  // 6. Draw main lists
  renderFindingsList();
  renderContestedList();
  renderSecretsList();
  renderLedgerList();
}

/**
 * Render standard findings list using DOM template builders
 */
function isHighOrCritical(severity) {
  return severity === 'high' || severity === 'critical';
}

function renderFindingsList() {
  const container = document.getElementById('findings-list');
  container.innerHTML = '';

  if (!currentReport || !currentReport.findings) return;

  // Filter findings based on active tab and perspective selection
  let filtered = currentReport.findings;

  if (activeTab === 'high') {
    filtered = currentReport.high_critical_findings || [];
  }

  // Apply perspective filter
  filtered = filtered.filter(f => matchesPerspectiveFilter(f));

  // Ledger provenance: omitted findings and merged constituents are parsed out of the
  // final report but kept as full-detail snapshots. Surface them here (badged, greyed)
  // so the ledger counters aren't dead ends — they live in their severity category and
  // can be deep-linked to from the ledger. They are NOT part of report.findings, so they
  // never affect severity counts or the conservation invariant.
  let provenance = [
    ...(currentReport.omitted_findings || []),
    ...(currentReport.merged_constituents || []),
  ].filter(f => matchesPerspectiveFilter(f));
  if (activeTab === 'high') {
    provenance = provenance.filter(f => isHighOrCritical(f.severity));
  }

  if (filtered.length === 0 && provenance.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No findings matching the current filters.</p>';
    return;
  }

  filtered.forEach(finding => {
    container.appendChild(createFindingCardDOM(finding));
  });

  if (provenance.length > 0) {
    const divider = document.createElement('div');
    divider.className = 'provenance-divider';
    divider.textContent = 'Parsed out of the final report (ledger provenance — not counted above)';
    container.appendChild(divider);

    provenance.forEach(finding => {
      container.appendChild(createFindingCardDOM(finding));
    });
  }
}

/**
 * Render contested findings list
 */
function renderContestedList() {
  const container = document.getElementById('contested-list');
  container.innerHTML = '';

  if (!currentReport || !currentReport.contested_items || currentReport.contested_items.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No contested items in this report.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'contested-table';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['Severity', 'Finding', 'Decision', "Why it's contested (rebuttal)"].forEach(label => {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  currentReport.contested_items.forEach(finding => {
    tbody.appendChild(createContestedRowDOM(finding));
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

/**
 * Build one <tr> for the contested table. Surfaces, explicitly, what decision the
 * pipeline made about a contested finding and the defender's rebuttal that put it here.
 *
 * Decision: contested findings are never silently dropped — they are retained pending a
 * human ruling. We distinguish a plain retention from one that also consolidated several
 * inputs (merged_from) so the column carries real signal.
 *
 * Rebuttal: the defender's reasoning is preserved at metadata.debate_closed_reason
 * (set in the debate loop). Coordinator-merged contested items may lack it, so we degrade
 * gracefully rather than show an empty cell.
 */
function createContestedRowDOM(finding) {
  const tr = document.createElement('tr');
  tr.className = 'contested-row';
  tr.id = `finding-node-${finding.id}`;

  // Severity
  const tdSev = document.createElement('td');
  const badge = document.createElement('span');
  badge.className = `finding-severity-badge ${finding.severity}`;
  badge.textContent = finding.severity;
  tdSev.appendChild(badge);
  tr.appendChild(tdSev);

  // Finding (claim + location)
  const tdClaim = document.createElement('td');
  const claim = document.createElement('div');
  claim.className = 'contested-claim';
  claim.textContent = finding.claim;
  tdClaim.appendChild(claim);
  const loc = document.createElement('div');
  loc.className = 'contested-loc';
  loc.textContent = `${finding.location.path} : Lines ${finding.location.line_start} - ${finding.location.line_end}`;
  tdClaim.appendChild(loc);
  tr.appendChild(tdClaim);

  // Decision
  const tdDecision = document.createElement('td');
  const decisionBadge = document.createElement('span');
  decisionBadge.className = 'contested-decision-badge';
  const wasMerged = finding.merged_from && finding.merged_from.length > 0;
  decisionBadge.textContent = wasMerged
    ? `Consolidated from ${finding.merged_from.length} — retained, awaiting your ruling`
    : 'Retained — awaiting your ruling';
  tdDecision.appendChild(decisionBadge);
  const decisionNote = document.createElement('div');
  decisionNote.className = 'contested-decision-note';
  decisionNote.textContent = 'Not dropped, not auto-included. You decide: accept it or dismiss it.';
  tdDecision.appendChild(decisionNote);
  tr.appendChild(tdDecision);

  // Rebuttal — defender's pushback that made it contested
  const tdRebuttal = document.createElement('td');
  tdRebuttal.className = 'contested-rebuttal';
  const rebuttal = (finding.metadata && finding.metadata.debate_closed_reason)
    || finding.recommended_next_action
    || 'No recorded rebuttal — unresolved disagreement (defender requested a change or never accepted it).';
  tdRebuttal.textContent = rebuttal;
  tr.appendChild(tdRebuttal);

  return tr;
}

/**
 * Render secret gate findings inside the table layout
 */
function renderSecretsList() {
  const tbody = document.getElementById('secrets-table-body');
  tbody.innerHTML = '';

  if (!currentReport || !currentReport.secret_scan_summary || currentReport.secret_scan_summary.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-placeholder">No credentials detected in the codebase.</td>
      </tr>`;
    return;
  }

  currentReport.secret_scan_summary.forEach(secret => {
    const tr = document.createElement('tr');

    // Type cell
    const tdType = document.createElement('td');
    tdType.innerHTML = `<strong>${escapeHtml(secret.secret_type)}</strong>`;
    tr.appendChild(tdType);

    // Location cell
    const tdLoc = document.createElement('td');
    tdLoc.className = 'loc-cell';
    tdLoc.textContent = `${secret.location.path} : Line ${secret.location.line_start}`;
    tr.appendChild(tdLoc);

    // Severity cell
    const tdSev = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `finding-severity-badge ${secret.severity}`;
    badge.textContent = secret.severity;
    tdSev.appendChild(badge);
    tr.appendChild(tdSev);

    // Exposure status
    const tdExposure = document.createElement('td');
    const exposureLabel = document.createElement('span');
    exposureLabel.className = secret.exposure_status === 'prompt_exposed' ? 'highlight-text' : 'muted-text';
    exposureLabel.textContent = secret.exposure_status;
    tdExposure.appendChild(exposureLabel);
    tr.appendChild(tdExposure);

    // Fingerprint (salted-hash only)
    const tdFingerprint = document.createElement('td');
    tdFingerprint.style.fontFamily = 'var(--font-mono)';
    tdFingerprint.style.fontSize = '0.75rem';
    tdFingerprint.textContent = secret.fingerprint;
    tr.appendChild(tdFingerprint);

    tbody.appendChild(tr);
  });
}

/**
 * Render the details of the conservation/accounting ledger
 */
function renderLedgerList() {
  if (!currentReport || !currentReport.accounting_ledger) return;

  const ledger = currentReport.accounting_ledger;

  document.getElementById('ledger-count-included').textContent = (ledger.included || []).length;
  document.getElementById('ledger-count-merged').textContent = (ledger.merged || []).length;
  document.getElementById('ledger-count-omitted').textContent = (ledger.omitted || []).length;
  document.getElementById('ledger-count-contested').textContent = (ledger.contested || []).length;

  populateLedgerUl('ledger-list-included', ledger.included || []);
  populateLedgerUl('ledger-list-contested', ledger.contested || []);

  // Custom renderer for Merged ledger entries showing parent-child maps
  const mergedUl = document.getElementById('ledger-list-merged');
  mergedUl.innerHTML = '';
  if (ledger.merged && ledger.merged.length > 0) {
    ledger.merged.forEach(entry => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div>
          <strong>Output:</strong> ${escapeHtml(shortId(entry.output_id))}
          <div style="font-size: 0.65rem; color: var(--text-secondary); margin-top: 0.25rem;">
            From inputs: ${escapeHtml(entry.input_ids.map(shortId).join(', '))}
          </div>
        </div>`;
      attachLedgerNav(li, entry.output_id);
      mergedUl.appendChild(li);
    });
  } else {
    mergedUl.innerHTML = '<li class="table-placeholder">No merged items.</li>';
  }

  // Custom renderer for Omitted ledger entries showing reasons
  const omittedUl = document.getElementById('ledger-list-omitted');
  omittedUl.innerHTML = '';
  if (ledger.omitted && ledger.omitted.length > 0) {
    ledger.omitted.forEach(entry => {
      const li = document.createElement('li');
      li.style.flexDirection = 'column';
      li.style.alignItems = 'flex-start';
      li.innerHTML = `
        <strong>${escapeHtml(shortId(entry.id))}</strong>
        <span class="ledger-omit-reason">${escapeHtml(entry.reason)}</span>`;
      attachLedgerNav(li, entry.id);
      omittedUl.appendChild(li);
    });
  } else {
    omittedUl.innerHTML = '<li class="table-placeholder">No omitted items.</li>';
  }
}

/**
 * Helper to populate basic list of IDs into ledger card ULs
 */
function populateLedgerUl(elementId, idList) {
  const ul = document.getElementById(elementId);
  ul.innerHTML = '';

  if (idList.length === 0) {
    ul.innerHTML = '<li class="table-placeholder">No items.</li>';
    return;
  }

  idList.forEach(id => {
    const li = document.createElement('li');
    li.textContent = shortId(id);
    attachLedgerNav(li, id);
    ul.appendChild(li);
  });
}

/**
 * Make a ledger entry deep-link to the finding it refers to: clicking switches to the
 * tab the card lives in (All Findings or Contested), clears the perspective filter so the
 * target isn't hidden, then scrolls to and flashes the card. Entries whose finding has no
 * card in the dashboard (e.g. omitted findings, pending the backend snapshot phase) are
 * left as plain text.
 */
function findingHasCard(id) {
  if (!currentReport) return false;
  const inFindings = (currentReport.findings || []).some(f => f.id === id);
  const inContested = (currentReport.contested_items || []).some(f => f.id === id);
  const inOmitted = (currentReport.omitted_findings || []).some(f => f.id === id);
  const inMerged = (currentReport.merged_constituents || []).some(f => f.id === id);
  return inFindings || inContested || inOmitted || inMerged;
}

function attachLedgerNav(el, id) {
  if (!findingHasCard(id)) return;
  el.classList.add('ledger-clickable');
  el.title = `Jump to ${id}`;
  el.addEventListener('click', () => focusFinding(id));
}

function focusFinding(id) {
  if (!currentReport) return;
  const inContested = (currentReport.contested_items || []).some(f => f.id === id);
  const tabBtnId = inContested ? 'tab-contested' : 'tab-all';

  if (!inContested) {
    // Reset perspective filter to "all" so the target card can't be filtered out.
    activePerspectives = new Set(['all']);
    document.querySelectorAll('.perspective-toggle').forEach(t => t.classList.remove('active'));
    const allBtn = document.getElementById('filter-all');
    if (allBtn) allBtn.classList.add('active');
  }

  const tabBtn = document.getElementById(tabBtnId);
  if (tabBtn && typeof tabBtn.click === 'function') tabBtn.click();

  // Defer the scroll/flash until the destination tab has rendered.
  setTimeout(() => {
    const node = document.getElementById(`finding-node-${id}`);
    if (!node) return;
    if (typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (node.classList) {
      node.classList.add('finding-flash');
      setTimeout(() => node.classList.remove('finding-flash'), 1600);
    }
  }, 60);
}

/**
 * Builder creating finding item cards dynamically with events
 * @param {Object} finding
 * @returns {HTMLElement}
 */
/**
 * Human-facing label for the agent that produced a finding.
 * Both deterministic and debate security findings come from one logical
 * "security_agent"; we disambiguate the technique in parentheses rather than
 * exposing the internal "security_deterministic"/"security_debate" source names.
 */
function sourceAgentLabel(sourceAgent) {
  switch (sourceAgent) {
    case 'security_deterministic': return 'security_agent (AST)';
    case 'security_debate':        return 'security_agent (Adversarial Debate)';
    default:                       return sourceAgent;
  }
}

function createFindingCardDOM(finding) {
  const card = document.createElement('div');
  card.className = 'finding-card';
  card.id = `finding-node-${finding.id}`;

  // Ledger-provenance findings (omitted / merged constituents) are visually distinct so
  // they're never mistaken for active findings that made the cut.
  const disposition = finding.metadata && finding.metadata.ledger_disposition;
  if (disposition === 'omitted') card.classList.add('finding-omitted');
  if (disposition === 'merged') card.classList.add('finding-merged-away');

  const summary = document.createElement('div');
  summary.className = 'finding-summary';

  const badge = document.createElement('span');
  badge.className = `finding-severity-badge ${finding.severity}`;
  badge.textContent = finding.severity;
  summary.appendChild(badge);

  if (disposition === 'omitted' || disposition === 'merged') {
    const dispBadge = document.createElement('span');
    dispBadge.className = 'finding-disposition-badge';
    dispBadge.textContent = disposition === 'omitted'
      ? 'OMITTED'
      : `MERGED → ${shortId(finding.metadata.merged_into || '')}`;
    summary.appendChild(dispBadge);
  }

  const meta = document.createElement('div');
  meta.className = 'finding-meta';

  const title = document.createElement('span');
  title.className = 'finding-title';
  title.textContent = finding.claim;
  meta.appendChild(title);

  const loc = document.createElement('span');
  loc.className = 'finding-loc';
  loc.textContent = `${finding.location.path} : Lines ${finding.location.line_start} - ${finding.location.line_end}`;
  meta.appendChild(loc);

  const src = document.createElement('span');
  src.className = 'finding-source';
  src.innerHTML = `Detected by: <span>${escapeHtml(sourceAgentLabel(finding.source_agent))}</span>`;
  meta.appendChild(src);

  summary.appendChild(meta);

  const expander = document.createElement('div');
  expander.className = 'finding-expand-indicator';
  expander.textContent = 'v';
  summary.appendChild(expander);

  card.appendChild(summary);

  // Hidden details container
  const details = document.createElement('div');
  details.className = 'finding-details hidden';

  // ID Section
  const idSec = document.createElement('div');
  idSec.className = 'detail-section';
  idSec.innerHTML = `<h4>Stable Finding ID</h4><p style="font-family: var(--font-mono); font-size: 0.75rem;">${escapeHtml(finding.id)}</p>`;
  details.appendChild(idSec);

  // Ledger disposition explainer for parsed-out findings.
  if (disposition === 'omitted' || disposition === 'merged') {
    const dispSec = document.createElement('div');
    dispSec.className = 'detail-section';
    if (disposition === 'omitted') {
      const reason = (finding.metadata && finding.metadata.omitted_reason) || 'No reason recorded.';
      dispSec.innerHTML = `<h4>Why this was omitted</h4><p>${escapeHtml(reason)}</p>`;
    } else {
      const into = (finding.metadata && finding.metadata.merged_into) || '';
      dispSec.innerHTML = `<h4>Merged into</h4><p>This finding was consolidated into <code>${escapeHtml(into)}</code> and is represented by that finding in the report.</p>`;
    }
    details.appendChild(dispSec);
  }

  // Next Actions Section
  if (finding.recommended_next_action) {
    const actionSec = document.createElement('div');
    actionSec.className = 'detail-section';
    actionSec.innerHTML = `<h4>Recommended Remediation</h4><p>${escapeHtml(finding.recommended_next_action)}</p>`;
    details.appendChild(actionSec);
  }

  // Evidence refs section
  if (finding.evidence_ref && finding.evidence_ref.length > 0) {
    const evidenceSec = document.createElement('div');
    evidenceSec.className = 'detail-section';
    evidenceSec.innerHTML = '<h4>Grounded Evidence references</h4>';

    const pillContainer = document.createElement('div');
    pillContainer.className = 'evidence-pill-container';
    finding.evidence_ref.forEach(ref => {
      const pill = document.createElement('span');
      pill.className = 'evidence-pill';
      pill.textContent = ref;
      pillContainer.appendChild(pill);
    });

    evidenceSec.appendChild(pillContainer);
    details.appendChild(evidenceSec);
  }

  // Merged constituents section
  if (finding.merged_from && finding.merged_from.length > 0) {
    const mergedSec = document.createElement('div');
    mergedSec.className = 'detail-section';
    mergedSec.innerHTML = '<h4>Merged Constituent findings</h4>';

    const tagContainer = document.createElement('div');
    tagContainer.className = 'merged-id-list';
    finding.merged_from.forEach(mId => {
      const tag = document.createElement('span');
      tag.className = 'merged-id-tag';
      tag.textContent = shortId(mId);
      tag.title = mId;
      tagContainer.appendChild(tag);
    });

    mergedSec.appendChild(tagContainer);
    details.appendChild(mergedSec);
  }

  card.appendChild(details);

  // Toggle expand event
  summary.addEventListener('click', () => {
    const isExpanded = card.classList.toggle('expanded');
    details.classList.toggle('hidden');
    expander.textContent = isExpanded ? '^' : 'v';
  });

  return card;
}

/* --------------------------------------------------------------------------- *
 * Adversarial debate viewer — replays the redaction-safe back-and-forth between
 * Claude (challenger) and Gemini (defender) that decided each security finding.
 * --------------------------------------------------------------------------- */

function openDebateModal() {
  const transcript = getDebateTranscript(currentReport);
  if (!transcript) return;
  renderDebateTranscript(transcript);
  const modal = document.getElementById('debate-modal');
  modal.classList.remove('hidden');
  document.body.classList.add('modal-open');
}

function closeDebateModal() {
  const modal = document.getElementById('debate-modal');
  if (modal) modal.classList.add('hidden');
  document.body.classList.remove('modal-open');
}

const RESOLUTION_META = {
  survived: { label: 'KEPT', cls: 'res-survived' },
  contested: { label: 'CONTESTED', cls: 'res-contested' },
  defeated: { label: 'DROPPED', cls: 'res-defeated' },
};

/**
 * Render the transcript (meta strip + per-round exchange + final resolutions)
 * into the modal. All text is treated as untrusted and HTML-escaped.
 */
function renderDebateTranscript(t) {
  const meta = document.getElementById('debate-modal-meta');
  const fs = t.final_score || {};
  const metaBits = [
    `<span class="debate-meta-pill">${t.seed_findings || 0} seed finding(s)</span>`,
    `<span class="debate-meta-pill">${(t.rounds || []).length} round(s)</span>`,
    `<span class="debate-meta-pill">final score — challenger ${fs.challenger ?? '0'} · defender ${fs.defender ?? '0'}</span>`,
  ];
  if (t.stop_reason) {
    metaBits.push(`<span class="debate-meta-pill">stop: ${escapeHtml(String(t.stop_reason))}</span>`);
  }
  meta.innerHTML = metaBits.join('');

  const body = document.getElementById('debate-modal-body');
  body.innerHTML = '';

  (t.rounds || []).forEach(round => {
    const roundEl = document.createElement('div');
    roundEl.className = 'debate-round';

    const head = document.createElement('div');
    head.className = 'debate-round-head';
    let scoreLine = '';
    const sb = (t.scoreboard || []).find(s => s.round === round.round);
    if (sb) scoreLine = ` <span class="debate-round-score">challenger ${sb.challenger} · defender ${sb.defender}</span>`;
    head.innerHTML = `Round ${round.round}${scoreLine}`;
    roundEl.appendChild(head);

    (round.messages || []).forEach(msg => {
      const isDefender = msg.role === 'defender';
      const isSystem = msg.role === 'system';
      const row = document.createElement('div');
      row.className = 'debate-msg ' + (isSystem ? 'is-system' : isDefender ? 'is-defender' : 'is-challenger');

      const who = document.createElement('span');
      who.className = 'debate-msg-actor';
      who.textContent = isSystem ? 'system' : isDefender ? 'Gemini · defender' : 'Claude · challenger';

      const text = document.createElement('span');
      text.className = 'debate-msg-text';
      text.textContent = msg.message;

      row.appendChild(who);
      row.appendChild(text);
      roundEl.appendChild(row);
    });

    body.appendChild(roundEl);
  });

  // Final resolutions block — how each finding ended up.
  if (t.resolutions && t.resolutions.length > 0) {
    const resWrap = document.createElement('div');
    resWrap.className = 'debate-resolutions';
    const h = document.createElement('h3');
    h.textContent = 'How each finding was resolved';
    resWrap.appendChild(h);

    t.resolutions.forEach(r => {
      const rm = RESOLUTION_META[r.resolution] || { label: (r.resolution || '').toUpperCase(), cls: '' };
      const item = document.createElement('div');
      item.className = 'debate-resolution-item';

      const badge = document.createElement('span');
      badge.className = `debate-res-badge ${rm.cls}`;
      badge.textContent = rm.label;

      const claim = document.createElement('div');
      claim.className = 'debate-res-claim';
      claim.innerHTML = `<span class="debate-res-sev sev-${escapeHtml(r.severity || 'info')}">${escapeHtml(r.severity || 'info')}</span> ${escapeHtml(r.claim || '')}`;

      item.appendChild(badge);
      item.appendChild(claim);

      if (r.closed_reason) {
        const reason = document.createElement('div');
        reason.className = 'debate-res-reason';
        reason.textContent = r.closed_reason;
        claim.appendChild(reason);
      }

      resWrap.appendChild(item);
    });

    body.appendChild(resWrap);
  }
}

/**
 * Generate and download a clean portable Markdown report
 */
function downloadReport() {
  if (!currentReport) return;

  const report = currentReport;
  const timestamp = report.run_metadata.start_time
    ? new Date(report.run_metadata.start_time).toLocaleString()
    : 'Unknown';
  const compilationMode = report.run_metadata.compilation_mode || 'unknown';
  const counts = report.severity_counts || {};

  let md = '';

  // Header
  md += '# Code Review Report\n\n';
  const coordinatorLabel = compilationMode === 'coordinated' ? 'ADK' : compilationMode === 'terminal_fallback' ? 'Terminal Fallback' : compilationMode;
  md += `**Generated:** ${timestamp}  \n`;
  md += `**Coordinator:** ${coordinatorLabel}  \n`;
  md += `**Run ID:** ${report.run_metadata.run_id || 'N/A'}  \n\n`;

  // Executive Summary
  md += '---\n\n';
  md += '## Executive Summary\n\n';

  const totalFindings = (report.findings || []).length;
  const totalContested = (report.contested_items || []).length;
  const totalSecrets = (report.secret_scan_summary || []).length;

  md += `| Metric | Count |\n`;
  md += `|--------|-------|\n`;
  md += `| Active Findings | ${totalFindings} |\n`;
  md += `| Contested Items | ${totalContested} |\n`;
  md += `| Secrets Detected | ${totalSecrets} |\n\n`;

  md += `### Severity Breakdown\n\n`;
  md += `| Severity | Count |\n`;
  md += `|----------|-------|\n`;
  md += `|  Critical | ${counts.critical || 0} |\n`;
  md += `|  High | ${counts.high || 0} |\n`;
  md += `|  Medium | ${counts.medium || 0} |\n`;
  md += `|  Low | ${counts.low || 0} |\n`;
  md += `|  Info | ${counts.info || 0} |\n\n`;

  // Agent Statuses
  md += '### Agent Perspective Statuses\n\n';
  md += '| Agent | Status | Details |\n';
  md += '|-------|--------|--------|\n';
  md += `| Pre-Flight Gate | ${report.gate_status?.status || 'N/A'} | ${report.gate_status?.reason || ''} |\n`;
  if (report.perspective_statuses) {
    report.perspective_statuses.forEach(p => {
      const name = p.perspective === 'correctness' ? 'Correctness Agent'
                 : p.perspective === 'security' ? 'Security Agent'
                 : p.perspective === 'blast_radius' ? 'Blast-Radius (Orbit)'
                 : p.perspective;
      md += `| ${name} | ${p.status} | ${p.reason || ''} |\n`;
    });
  }
  md += '\n';

  // Findings
  md += '---\n\n';
  md += '## Active Findings\n\n';

  if (report.findings && report.findings.length > 0) {
    // Group by perspective
    const grouped = {};
    report.findings.forEach(f => {
      const key = f.source_agent === 'preflight_secret_gate' ? 'Pre-Flight Gate'
                : f.perspective === 'correctness' ? 'Correctness'
                : f.perspective === 'security' ? 'Security'
                : f.perspective === 'blast_radius' ? 'Blast-Radius (Orbit)'
                : f.perspective;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(f);
    });

    for (const [group, findings] of Object.entries(grouped)) {
      md += `### ${group}\n\n`;
      findings.forEach(f => {
        md += `#### \\[${f.severity.toUpperCase()}\\] ${f.claim}\n\n`;
        md += `- **Location:** \`${f.location.path}\` lines ${f.location.line_start}-${f.location.line_end}\n`;
        md += `- **Source Agent:** ${sourceAgentLabel(f.source_agent)}\n`;
        md += `- **Finding ID:** \`${f.id}\`\n`;
        if (f.evidence_ref && f.evidence_ref.length > 0) {
          md += `- **Evidence:** ${f.evidence_ref.map(r => '`' + r + '`').join(', ')}\n`;
        }
        if (f.recommended_next_action) {
          md += `- **Recommended Action:** ${f.recommended_next_action}\n`;
        }
        if (f.merged_from && f.merged_from.length > 0) {
          md += `- **Merged From:** ${f.merged_from.map(id => '`' + id + '`').join(', ')}\n`;
        }
        md += '\n';
      });
    }
  } else {
    md += '*No active findings.*\n\n';
  }

  // Contested
  if (report.contested_items && report.contested_items.length > 0) {
    md += '---\n\n';
    md += '## Contested Items\n\n';
    report.contested_items.forEach(f => {
      md += `#### \\[${f.severity.toUpperCase()}\\] ${f.claim}\n\n`;
      md += `- **Location:** \`${f.location.path}\` lines ${f.location.line_start}-${f.location.line_end}\n`;
      md += `- **Source Agent:** ${sourceAgentLabel(f.source_agent)}\n`;
      if (f.recommended_next_action) {
        md += `- **Note:** ${f.recommended_next_action}\n`;
      }
      md += '\n';
    });
  }

  // Secret Scan
  if (report.secret_scan_summary && report.secret_scan_summary.length > 0) {
    md += '---\n\n';
    md += '## Secret Scan Summary\n\n';
    md += '| Type | Location | Severity | Exposure | Fingerprint |\n';
    md += '|------|----------|----------|----------|-------------|\n';
    report.secret_scan_summary.forEach(s => {
      md += `| ${s.secret_type} | ${s.location.path}:${s.location.line_start} | ${s.severity} | ${s.exposure_status} | \`${s.fingerprint}\` |\n`;
    });
    md += '\n';
  }

  // Conservation Ledger
  if (report.accounting_ledger) {
    md += '---\n\n';
    md += '## Conservation Ledger\n\n';
    const l = report.accounting_ledger;
    md += `- **Included:** ${(l.included || []).length} findings\n`;
    md += `- **Merged:** ${(l.merged || []).length} consolidations\n`;
    md += `- **Omitted:** ${(l.omitted || []).length} suppressions\n`;
    md += `- **Contested:** ${(l.contested || []).length} items\n\n`;

    md += `*Integrity: Inputs == Included U Merged U Omitted U Contested (validator enforced)*\n\n`;
  }

  // Adversarial Security Debate
  const transcript = getDebateTranscript(report);
  if (transcript) {
    md += '---\n\n';
    md += '## Adversarial Security Debate\n\n';
    md += 'Claude (challenger / security hawk) vs Gemini (defender / ship-it advocate). ';
    md += 'This is the redaction-safe back-and-forth that decided each security finding below.\n\n';

    const fs = transcript.final_score || {};
    md += `- **Seed findings:** ${transcript.seed_findings || 0}\n`;
    md += `- **Rounds:** ${(transcript.rounds || []).length}\n`;
    md += `- **Final score:** challenger ${fs.challenger ?? 0} · defender ${fs.defender ?? 0}\n`;
    if (transcript.stop_reason) md += `- **Stop reason:** ${transcript.stop_reason}\n`;
    md += '\n';

    (transcript.rounds || []).forEach(round => {
      const sb = (transcript.scoreboard || []).find(s => s.round === round.round);
      const scoreNote = sb ? ` _(challenger ${sb.challenger} · defender ${sb.defender})_` : '';
      md += `### Round ${round.round}${scoreNote}\n\n`;
      (round.messages || []).forEach(msg => {
        const actor = msg.role === 'defender' ? 'Gemini (defender)'
                    : msg.role === 'challenger' ? 'Claude (challenger)'
                    : 'system';
        md += `- **${actor}:** ${msg.message}\n`;
      });
      md += '\n';
    });

    if (transcript.resolutions && transcript.resolutions.length > 0) {
      md += '### Resolutions\n\n';
      md += '| Outcome | Severity | Finding | Reasoning |\n';
      md += '|---------|----------|---------|-----------|\n';
      transcript.resolutions.forEach(r => {
        const outcome = r.resolution === 'survived' ? 'KEPT'
                      : r.resolution === 'contested' ? 'CONTESTED'
                      : r.resolution === 'defeated' ? 'DROPPED'
                      : (r.resolution || '');
        const reason = (r.closed_reason || '').replace(/\|/g, '\\|');
        const claim = (r.claim || '').replace(/\|/g, '\\|');
        md += `| ${outcome} | ${r.severity || 'info'} | ${claim} | ${reason} |\n`;
      });
      md += '\n';
    }
  }

  // Validator Warnings
  if (report.validator_warnings && report.validator_warnings.length > 0) {
    md += '---\n\n';
    md += '## Validator Warnings\n\n';
    report.validator_warnings.forEach(w => {
      md += `-  ${w}\n`;
    });
    md += '\n';
  }

  md += '---\n\n';
  md += '*Report generated by GDG-YorkU Code Review Tool - Automated Multi-Agent Integrity Suite*\n';

  // Download
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `code-review-report-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Helpers
 */
function updatePerspectiveBadge(badgeId, statusValue) {
  const badge = document.getElementById(badgeId);
  if (!badge) return;

  badge.className = 'status-badge';
  badge.textContent = statusValue.toUpperCase();

  switch(statusValue.toLowerCase()) {
    case 'complete':
    case 'success':
      badge.classList.add('status-complete');
      break;
    case 'failed':
      badge.classList.add('status-failed');
      break;
    case 'skipped':
    case 'complete_limited':
      badge.classList.add('status-skipped');
      break;
    case 'disabled':
    case 'unavailable':
      badge.classList.add('status-disabled');
      break;
    default:
      badge.classList.add('status-pending');
  }
}

function formatTimestamp(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString();
  } catch(e) {
    return isoStr;
  }
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function shortId(id) {
  if (id.length <= 16) return id;
  return id.substring(0, 8) + '...' + id.substring(id.length - 8);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

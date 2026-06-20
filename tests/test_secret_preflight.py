import os
import pytest
import tempfile
from gdg_yorku_submission.schemas import Location, CorpusFile, GateFinding, IngestionManifest
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.corpus import build_corpus
from gdg_yorku_submission.preflight import (
    RedactionContext,
    sanitize_value,
    scan_file_for_secrets,
    run_secret_scan,
    promote_gate_findings,
)

def test_fingerprint_generation():
    # Salted hash rules:
    # >= 20 chars -> hash + last 4 chars
    # < 20 chars -> hash only
    ctx = RedactionContext(salt=b"test_salt")
    
    short_secret = "short_sec" # 9 chars (< 20)
    fp_short = ctx.get_fingerprint(short_secret)
    assert "sha256_" in fp_short
    assert not fp_short.endswith(short_secret[-4:])
    
    long_secret = "super_long_secret_value_12345" # 29 chars (>= 20)
    fp_long = ctx.get_fingerprint(long_secret)
    assert "sha256_" in fp_long
    assert fp_long.endswith("2345") # ends with last 4 chars
    parts = fp_long.split("_")
    assert len(parts) == 3
    assert parts[0] == "sha256"
    assert len(parts[1]) == 16
    assert parts[2] == "12345"[-4:]


def test_fingerprint_boundary_check():
    # BUG-012: Check 19 and 20 char boundary edge cases
    ctx = RedactionContext(salt=b"test_salt")
    
    secret_19 = "1234567890123456789"
    fp_19 = ctx.get_fingerprint(secret_19)
    assert fp_19.count("_") == 1 # sha256_<hash>
    
    secret_20 = "12345678901234567890"
    fp_20 = ctx.get_fingerprint(secret_20)
    assert fp_20.count("_") == 2 # sha256_<hash>_<last4>
    assert fp_20.endswith("7890")


def test_redaction_invariant_and_placeholder():
    ctx = RedactionContext(salt=b"test_salt")
    secret = "my_api_key_12345"
    
    placeholder = ctx.register_secret(secret, "Google API Key")
    assert secret not in placeholder
    assert "GOOGLE_API_KEY" in placeholder
    
    log_line = f"Connecting using api_key: {secret} to database."
    redacted_line = ctx.redact(log_line)
    
    assert secret not in redacted_line
    assert placeholder in redacted_line


def test_substring_redaction_ordering():
    ctx = RedactionContext(salt=b"test_salt")
    secret_short = "secret"
    secret_long = "secret_longer"
    
    ph_short = ctx.register_secret(secret_short, "Short")
    ph_long = ctx.register_secret(secret_long, "Long")
    
    text = f"Both values: {secret_long} and {secret_short}."
    redacted = ctx.redact(text)
    
    assert secret_long not in redacted
    assert secret_short not in redacted
    assert ph_long in redacted
    assert ph_short in redacted


def test_exception_redaction():
    ctx = RedactionContext(salt=b"test_salt")
    secret = "super_secret_auth_token"
    ctx.register_secret(secret, "Auth Token")
    
    raw_error = ValueError(f"Failed authentication with token: {secret}")
    redacted_error = ctx.redact_exception(raw_error)
    
    assert isinstance(redacted_error, ValueError)
    assert secret not in str(redacted_error)
    assert "[REDACTED_AUTH_TOKEN" in str(redacted_error)


def test_recursive_value_sanitization():
    ctx = RedactionContext(salt=b"test_salt")
    secret = "secret_value_to_hide"
    ph = ctx.register_secret(secret, "Secret")
    
    nested_data = {
        "user": "admin",
        "auth": {
            "token": secret,
            "history": [
                f"Failed token: {secret}",
                "Success"
            ]
        },
        "error": ValueError(f"Invalid secret: {secret}")
    }
    
    sanitized = sanitize_value(nested_data, ctx)
    
    assert sanitized["user"] == "admin"
    assert sanitized["auth"]["token"] == ph
    assert sanitized["auth"]["history"][0] == f"Failed token: {ph}"
    assert sanitized["auth"]["history"][1] == "Success"
    assert secret not in str(sanitized["error"])
    assert ph in str(sanitized["error"])


def test_secret_scan_severity_split_and_findings():
    ctx = RedactionContext(salt=b"test_salt")
    
    exposed_file = CorpusFile(
        normalized_path="src/app.py",
        original_text="AWS_KEY = 'AKIA1234567890123456'\naws_secret_access_key = 'abcdefjhjklmnopqrstwxyz0123456789012345A'\n",
        redacted_text="",
        original_line_count=2,
        redacted_to_original_line_map={1: 1, 2: 2},
        evidence_ref="file:src/app.py",
        exposure_status="prompt_exposed",
        ingest_status="success"
    )
    
    ignored_file = CorpusFile(
        normalized_path="config/.env",
        original_text="DB_PASSWORD = 'my_super_secret_db_pass_123'\n",
        redacted_text="",
        original_line_count=1,
        redacted_to_original_line_map={1: 1},
        evidence_ref="file:config/.env",
        exposure_status="ignored_by_root_gitignore",
        ingest_status="success"
    )
    
    corpus = {
        "src/app.py": exposed_file,
        "config/.env": ignored_file
    }
    
    findings = run_secret_scan(corpus, ctx)
    
    assert exposed_file.redacted_text != exposed_file.original_text
    assert "AKIA" not in exposed_file.redacted_text
    assert "aws_secret_access_key" in exposed_file.redacted_text
    assert "abcdefjhj" not in exposed_file.redacted_text
    
    assert ignored_file.redacted_text != ignored_file.original_text
    assert "my_super_secret" not in ignored_file.redacted_text
    
    assert len(findings) == 3
    
    exposed_findings = [f for f in findings if f.location.path == "src/app.py"]
    assert len(exposed_findings) == 2
    
    severities = {f.secret_type: f.severity for f in exposed_findings}
    assert severities["AWS Access Key ID"] == Severity.HIGH
    assert severities["AWS Secret Access Key"] == Severity.CRITICAL
    
    ignored_findings = [f for f in findings if f.location.path == "config/.env"]
    assert len(ignored_findings) == 1
    assert ignored_findings[0].severity == Severity.INFO
    assert ignored_findings[0].secret_type == "Database Password" # Refined!


def test_gate_finding_promotion():
    loc1 = Location(path="src/app.py", line_start=1, line_end=1)
    loc2 = Location(path="config/.env", line_start=1, line_end=1)
    
    f1 = GateFinding(
        id="f1",
        severity=Severity.CRITICAL,
        location=loc1,
        claim="Exposed AWS secret",
        secret_type="AWS Secret Access Key",
        fingerprint="fp1",
        exposure_status="prompt_exposed"
    )
    
    f2 = GateFinding(
        id="f2",
        severity=Severity.HIGH,
        location=loc1,
        claim="Exposed AWS key ID",
        secret_type="AWS Access Key ID",
        fingerprint="fp2",
        exposure_status="prompt_exposed"
    )
    
    f3 = GateFinding(
        id="f3",
        severity=Severity.INFO,
        location=loc2,
        claim="Gitignored dotenv secret",
        secret_type="Dotenv Assignment",
        fingerprint="fp3",
        exposure_status="ignored_by_root_gitignore"
    )
    
    gate_findings = [f1, f2, f3]
    promoted = promote_gate_findings(gate_findings)
    
    assert len(promoted) == 2
    
    rf1 = promoted[0]
    assert rf1.id == "promoted-f1"
    assert rf1.source_agent == "preflight_secret_gate"
    assert rf1.perspective == "security"
    assert rf1.severity == Severity.CRITICAL
    assert rf1.location.path == "src/app.py"
    assert rf1.metadata["fingerprint"] == "fp1"
    
    rf2 = promoted[1]
    assert rf2.id == "promoted-f2"
    assert rf2.severity == Severity.HIGH


def test_crlf_pem_redaction_and_line_preservation():
    # BUG-001 & BUG-002: Re-scan and replace multi-line PEM on CRLF lines
    ctx = RedactionContext(salt=b"test_salt")
    crlf_text = (
        "# config file\r\n"
        "-----BEGIN RSA PRIVATE KEY-----\r\n"
        "MIIEowIBAAKCAQEA1234567890\r\n"
        "-----END RSA PRIVATE KEY-----\r\n"
        "# end config\r\n"
    )
    findings = scan_file_for_secrets("config.py", crlf_text, "prompt_exposed", ctx)
    assert len(findings) == 1
    
    redacted = ctx.redact(crlf_text)
    assert "MIIEowIBA" not in redacted
    assert "PEM_PRIVATE_KEY" in redacted
    
    # Assert line preservation
    assert crlf_text.count("\r\n") == redacted.count("\r\n")
    assert len(crlf_text.splitlines()) == len(redacted.splitlines())


def test_gate_finding_ids_stable():
    # BUG-011: Secret-gate finding IDs must be stable across runs and independent of salt
    ctx1 = RedactionContext(salt=b"salt_one")
    ctx2 = RedactionContext(salt=b"salt_two")
    text = "AWS_KEY = 'AKIA1234567890123456'\n"
    
    f1 = scan_file_for_secrets("app.py", text, "prompt_exposed", ctx1)
    f2 = scan_file_for_secrets("app.py", text, "prompt_exposed", ctx2)
    
    assert len(f1) == 1
    assert len(f2) == 1
    assert f1[0].id == f2[0].id # Stable finding IDs!


def test_salt_randomness():
    # BUG-004: Salt randomness invariant
    # Default salts must differ, leading to different fingerprints for same secret
    ctx1 = RedactionContext()
    ctx2 = RedactionContext()
    secret = "secret_to_fingerprint_value"
    
    assert ctx1.get_fingerprint(secret) != ctx2.get_fingerprint(secret)


def test_synthetic_secrets_leak_assertion():
    # BUG-005: Raw secrets absent from report and GateFinding serialization
    ctx = RedactionContext(salt=b"test_salt")
    secret = "AIzaSyA12345678901234567890123456789012" # 42 chars
    findings = scan_file_for_secrets("keys.py", f"api_key = '{secret}'", "prompt_exposed", ctx)
    
    assert len(findings) == 1
    gf = findings[0]
    
    # Assert secret never leaks into serialized representations
    serialized_gf = gf.model_dump_json()
    assert secret not in serialized_gf
    
    corpus = {
        "keys.py": CorpusFile(
            normalized_path="keys.py",
            original_text=f"api_key = '{secret}'",
            redacted_text=f"api_key = '{secret}'",
            original_line_count=1,
            redacted_to_original_line_map={1: 1},
            evidence_ref="file:keys.py",
            exposure_status="prompt_exposed",
            ingest_status="success"
        )
    }
    
    # Check InProcessOrchestrator compilation output
    orch = InProcessOrchestrator()
    orch.start_run()
    orch.set_corpus(corpus)
    orch.set_corpus_summary({"file_count": 1, "total_bytes": 10})
    orch.run_secret_gate(findings)
    
    report = orch.compile_report()
    serialized_report = report.model_dump_json()
    assert secret not in serialized_report


def test_cross_file_redaction():
    # BUG-006: A secret registered from one file is redacted from another file
    ctx = RedactionContext(salt=b"test_salt")
    
    # Detected in file A
    scan_file_for_secrets("file_a.py", "API_KEY = 'AIzaSyA_key_from_file_a_123456'", "prompt_exposed", ctx)
    
    # Text in file B contains same secret
    file_b_text = "Logging failure with key: AIzaSyA_key_from_file_a_123456 in file B"
    redacted_b = ctx.redact(file_b_text)
    
    assert "AIzaSyA_key_from_file_a_123456" not in redacted_b
    assert "[REDACTED_API_KEY" in redacted_b


def test_orchestrator_integration_real():
    # BUG-007: Integration test with real corpus scan -> Orchestrator -> compile_report()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src/secrets.py"), "w", encoding="utf-8") as f:
            f.write("AWS_KEY = 'AKIA1234567890123456'\naws_secret = 'abcdefjhjklmnopqrstwxyz0123456789012345A'\n")
            
        manifest = IngestionManifest(
            extracted_files=["src/secrets.py"],
            skipped_files={},
            total_extracted_bytes=100,
            total_extracted_count=1
        )
        
        orch = InProcessOrchestrator()
        orch.start_run()
        ctx = orch.get_redaction_context()

        # Real scanner path
        corpus = build_corpus(tmpdir, manifest)
        gate_findings = run_secret_scan(corpus, ctx)
        
        assert len(gate_findings) == 2
        
        orch.set_corpus(corpus)
        orch.set_corpus_summary({"file_count": 1, "total_bytes": 100})
        orch.run_secret_gate(gate_findings)
        
        # Run the security specialist, which should now claim all security findings (stub + promoted)
        def security_specialist_stub():
            return []
        orch.run_specialist("security", security_specialist_stub)

        report = orch.compile_report()
        
        # Verify findings count in summary
        assert len(report.secret_scan_summary) == 2
        
        # Verify promoted findings flow into report.findings and accounting_ledger.included (BUG-003)
        assert len(report.findings) == 2
        assert len(report.accounting_ledger.included) == 2
        assert any("promoted-" in pid for pid in report.findings[0].metadata.get("merged_from_provisional", []))

        security_status = next(s for s in report.perspective_statuses if s.perspective == "security")
        # The perspective status claims the 2 promoted IDs!
        assert len(security_status.finding_ids) == 2
        assert report.findings[0].id in security_status.finding_ids
        assert report.findings[1].id in security_status.finding_ids


def test_exception_redaction_nested():
    # BUG-008: redact_exception recursively redacts cause, context, and args list
    ctx = RedactionContext(salt=b"test_salt")
    secret_a = "secret_aaa_value"
    secret_b = "secret_bbb_value"
    
    ph_a = ctx.register_secret(secret_a, "SecretA")
    ph_b = ctx.register_secret(secret_b, "SecretB")
    
    # Chain: context_exc -> cause_exc -> root_exc
    context_exc = ValueError(f"Context error: {secret_a}", 123)
    cause_exc = RuntimeError(f"Cause error: {secret_b}")
    cause_exc.__context__ = context_exc
    
    root_exc = Exception("Root error", cause_exc)
    root_exc.__cause__ = cause_exc
    
    redacted = ctx.redact_exception(root_exc)
    
    # Assert root exception args
    assert redacted.args[0] == "Root error"
    
    # Assert cause exception
    assert redacted.__cause__ is not None
    assert secret_b not in redacted.__cause__.args[0]
    assert ph_b in redacted.__cause__.args[0]
    
    # Assert context exception
    assert redacted.__cause__.__context__ is not None
    assert secret_a not in redacted.__cause__.__context__.args[0]
    assert ph_a in redacted.__cause__.__context__.args[0]
    assert redacted.__cause__.__context__.args[1] == 123


def test_dotenv_url_false_positive():
    # BUG-009: DATABASE_URL should not be flagged as a secret when it does not contain credentials
    ctx = RedactionContext(salt=b"test_salt")
    text_bare = "DATABASE_URL=postgres://localhost:5432/mydb\n"
    findings_bare = scan_file_for_secrets("config.env", text_bare, "prompt_exposed", ctx)
    assert len(findings_bare) == 0

    # But DATABASE_URL with credentials should be flagged as a critical secret
    text_cred = "DATABASE_URL=postgres://admin:SuperSecretPw123@host/db\n"
    findings_cred = scan_file_for_secrets("config.env", text_cred, "prompt_exposed", ctx)
    assert len(findings_cred) == 1
    assert findings_cred[0].severity == Severity.CRITICAL
    assert findings_cred[0].secret_type == "Database Connection String"

    redacted = ctx.redact(text_cred)
    assert "SuperSecretPw123" not in redacted
    assert "[REDACTED_DATABASE_CONNECTION_STRING" in redacted

import sys
import subprocess
import ast
import re
import json
from pathlib import Path
import pytest

from gdg_yorku_submission.demo_hooks import run_demo_logic, run_demo

ZIP_PATH = Path("samples/driftstore.zip")

def test_run_demo_drop_high_direct():
    """Asserts that direct invocation of run_demo_logic for 'drop-high' passes negative control and matches error delta exactly."""
    assert ZIP_PATH.exists()
    result = run_demo_logic("drop-high", ZIP_PATH)

    # 1. Negative control check
    assert result.baseline_errors == [], f"Baseline report had unexpected errors: {result.baseline_errors}"

    # 2. Assert a high finding was actually identified and dropped
    assert result.target_finding_id is not None

    # 3. Assert the post-corruption result equals exactly the expected error delta
    expected = [f"Forbidden omission of high/critical finding '{result.target_finding_id}' (severity: high)"]
    assert result.corrupted_errors == expected, f"Expected errors: {expected}, got: {result.corrupted_errors}"

def test_run_demo_corrupt_location_direct():
    """Asserts that direct invocation for 'corrupt-location' passes negative control and matches location coordinate check exactly."""
    assert ZIP_PATH.exists()
    result = run_demo_logic("corrupt-location", ZIP_PATH)

    # 1. Negative control check
    assert result.baseline_errors == []
    assert result.target_finding_id is not None

    # 2. Assert location out-of-bounds coordinate check fails exactly
    expected = [f"Finding '{result.target_finding_id}' location lines 9999-10000 are out of bounds for 'src/app.py' (original line count: 37)"]
    assert result.corrupted_errors == expected

def test_run_demo_corrupt_evidence_ref_direct():
    """Asserts that direct invocation for 'corrupt-evidence-ref' passes negative control and matches evidence-ref check exactly."""
    assert ZIP_PATH.exists()
    result = run_demo_logic("corrupt-evidence-ref", ZIP_PATH)

    # 1. Negative control check
    assert result.baseline_errors == []
    assert result.target_finding_id is not None

    # 2. Assert evidence_ref out-of-bounds check fails exactly
    expected = [f"Finding '{result.target_finding_id}' evidence_ref lines 9999-10000 are out of bounds for 'src/app.py' (original line count: 37) in ref 'file:src/app.py#9999-10000'"]
    assert result.corrupted_errors == expected

def test_run_demo_leak_secret_direct():
    """Asserts that the real pipeline never emits raw secrets onto the report/frontend surface."""
    assert ZIP_PATH.exists()
    result = run_demo_logic("leak-secret", ZIP_PATH)

    # 1. Negative control check
    assert result.baseline_errors == []
    
    raw_secret_value = result.secret_value
    placeholder_value = result.secret_placeholder
    fingerprint_value = result.secret_fingerprint

    assert raw_secret_value is not None
    assert placeholder_value is not None
    assert fingerprint_value is not None

    # Assertion A: The raw secret value does appear in the secret-bearing file's original text
    assert raw_secret_value in result.source_file_original, "Raw secret was not present in original text"

    # Assertion B: Redaction holds at the corpus layer (redacted_text has placeholder, not raw secret)
    assert raw_secret_value not in result.source_file_redacted, "Raw secret leaked into corpus redacted_text"
    assert placeholder_value in result.source_file_redacted, "Redaction placeholder missing from corpus redacted_text"

    # Assertion C: Redaction holds on the production surface (serialized JSON)
    assert raw_secret_value not in result.serialized_report, "Raw secret leaked into serialized report JSON!"
    
    # Assert that the placeholder is naturally absent from the production report JSON (no metadata injection)
    assert placeholder_value not in result.serialized_report, "Redaction placeholder was unexpectedly present in report JSON!"

    # Assertion D: Salted fingerprint is present in the report JSON's secret_scan_summary
    report_data = json.loads(result.serialized_report)
    summary = report_data.get("secret_scan_summary", [])
    assert len(summary) > 0, "No gate findings present in secret scan summary"
    
    fp_found = False
    for gf in summary:
        assert raw_secret_value not in gf.get("claim", "")
        assert raw_secret_value not in gf.get("fingerprint", "")
        assert raw_secret_value not in gf.get("secret_type", "")
        if gf.get("fingerprint") == fingerprint_value:
            fp_found = True
            
    assert fp_found, f"Expected fingerprint '{fingerprint_value}' not found in secret scan summary"

def test_cli_subprocess_drop_high():
    """Asserts that running demo_hooks as a subprocess script with 'drop-high' exits with 1 and prints the rejection message."""
    result = subprocess.run(
        [sys.executable, "-m", "gdg_yorku_submission.demo_hooks", "drop-high", str(ZIP_PATH)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 1
    assert "=== VALIDATOR REJECTED REPORT ===" in result.stdout
    assert "Forbidden omission of high/critical finding" in result.stdout

def test_cli_subprocess_corrupt_location():
    """Asserts that running demo_hooks as a subprocess script with 'corrupt-location' exits with 1 and prints location coordinate bounds error."""
    result = subprocess.run(
        [sys.executable, "-m", "gdg_yorku_submission.demo_hooks", "corrupt-location", str(ZIP_PATH)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 1
    assert "=== VALIDATOR REJECTED REPORT ===" in result.stdout
    assert "location lines 9999-10000 are out of bounds for" in result.stdout

def test_cli_subprocess_corrupt_evidence_ref():
    """Asserts that running demo_hooks as a subprocess script with 'corrupt-evidence-ref' exits with 1 and prints evidence_ref bounds error."""
    result = subprocess.run(
        [sys.executable, "-m", "gdg_yorku_submission.demo_hooks", "corrupt-evidence-ref", str(ZIP_PATH)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 1
    assert "=== VALIDATOR REJECTED REPORT ===" in result.stdout
    assert "evidence_ref lines 9999-10000 are out of bounds for" in result.stdout

def test_cli_subprocess_leak_secret():
    """Asserts that running demo_hooks as a subprocess script with 'leak-secret' exits with 0 and validates the redaction invariant."""
    result = subprocess.run(
        [sys.executable, "-m", "gdg_yorku_submission.demo_hooks", "leak-secret", str(ZIP_PATH)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "=== PASS: REDACTION INVARIANT VALIDATED ===" in result.stdout
    
    # Assert neither raw secret is in stdout
    assert "AIzaSyA12345678901234567890123456789012" not in result.stdout, "Raw Google API Key leaked!"
    assert "super_secret_db_password_12345" not in result.stdout, "Raw DB password leaked!"
    
    # Assert the fingerprint pattern is present in stdout
    fingerprint_pattern = re.compile(r"sha256_[0-9a-f]{16}_[0-9]{4}")
    assert fingerprint_pattern.search(result.stdout) is not None, "Redaction fingerprint missing from stdout"

def test_http_and_production_isolation():
    """
    Asserts that gdg_yorku_submission.demo_hooks is isolated from production routes.
    Must fail loudly if any production module has syntax errors.
    """
    src_dir = Path(__file__).parent.parent / "src" / "gdg_yorku_submission"
    assert src_dir.exists()

    for path in src_dir.rglob("*.py"):
        if path.name == "demo_hooks.py":
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse AST without catching SyntaxError to fail loudly if syntax is invalid
        tree = ast.parse(content, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    assert "demo_hooks" not in name.name, f"Forbidden import of demo_hooks found in {path.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "demo_hooks" not in node.module, f"Forbidden import of demo_hooks found in {path.name}"
                    for name in node.names:
                        assert "demo_hooks" not in name.name, f"Forbidden import of demo_hooks found in {path.name}"

    # Verify that demo_hooks is not registered as a console script / entry point in pyproject.toml
    pyproject_path = src_dir.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "demo_hooks" not in content, "demo_hooks must not be registered in pyproject.toml"

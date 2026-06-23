import io
import os
import json
import sys
import zipfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from gdg_yorku_submission.app import app
from gdg_yorku_submission.orchestrator import InProcessOrchestrator, AdkOrchestrator
from gdg_yorku_submission.llm.gemini import GeminiClient
from gdg_yorku_submission.schemas import ReviewReport, Severity

client = TestClient(app)

# The Google API Key regex requires AIza + 35 characters = exactly 39 characters.
# AIzaSyA_exposed_google_key_987654321012 has length 39.
RAW_SECRET_GOOGLE = "AIzaSyA_exposed_google_key_987654321012"
RAW_SECRET_DB = "super_secret_db_password_12345"


def create_e2e_zip() -> bytes:
    """Helper to create a zip buffer with known structure and secrets."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "SPEC.md",
            "# Specification\n"
            "## Intent\n"
            "Requirement 1: The application must use safe deserialize patterns.\n"
            "Requirement 2: Line 5 of SPEC.\n"
            "Requirement 3: Line 6 of SPEC.\n"
            "Requirement 4: Line 7 of SPEC.\n"
        )
        z.writestr(
            "src/payout.py",
            "import pickle\n"
            "def process_payout(payload):\n"
            "    # This triggers unsafe deserialize in AST rules\n"
            "    data = pickle.loads(payload)\n"
            f"    # Exposed Google API Key\n"
            f"    key = '{RAW_SECRET_GOOGLE}'\n"
            "    return data\n"
        )
        z.writestr(
            ".gitignore",
            "secrets/\n"
        )
        z.writestr(
            "secrets/credentials.env",
            f"DATABASE_PASSWORD = '{RAW_SECRET_DB}'\n"
        )
    return buf.getvalue()


def test_e2e_offline_guarantee():
    """
    REQ-23-R5 / AC-23-05: Offline Guarantee.
    Assert that the suite runs in a completely isolated offline mode,
    verifying that GeminiClient uses fake models and does not make live API calls.
    """
    # 1. Assert that the environment flag for fake LLM is set to true
    assert os.environ.get("USE_FAKE_LLM") == "true", (
        "USE_FAKE_LLM environment variable must be set to 'true' for offline test safety."
    )

    # 2. Assert that GeminiClient initializes with use_fake=True by default under this env
    client_instance = GeminiClient()
    assert client_instance.use_fake is True, (
        "GeminiClient must be operating in fake/mock mode under test environment."
    )

    # 3. Assert that calling generate_content does not attempt live Google Vertex init
    # We mock google.generativeai and vertexai in sys.modules to trace configure/init calls
    mock_genai = MagicMock()
    mock_vertex = MagicMock()
    
    with patch.dict(sys.modules, {"google.generativeai": mock_genai, "vertexai": mock_vertex}):
        orch = InProcessOrchestrator()
        orch.start_run()
        
        response = client_instance.generate_content(
            orch=orch,
            prompt="Hello from offline tests",
            component="correctness_agent"
        )
        
        # Verify response is returned successfully from dummy path without hitting configure or init
        assert response is not None
        mock_genai.configure.assert_not_called()
        mock_vertex.init.assert_not_called()


@pytest.mark.parametrize("orch_type", ["adk", "in_process"])
def test_e2e_full_run(orch_type, monkeypatch):
    """
    REQ-23-R1 / AC-23-01: Verify a complete run from upload to validated final report
    across both InProcess and ADK orchestrators.
    """
    fake_correctness = [
        {
            "id": "prov-correctness-e2e-1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "high",
            "location": {
                "path": "src/payout.py",
                "line_start": 2,
                "line_end": 4
            },
            "claim": "Implemented behavior uses unsafe pickle deserialize mismatching Requirement 1.",
            "evidence_ref": ["file:SPEC.md#3-4", "file:src/payout.py#2-4"]
        }
    ]

    # Mock GeminiClient responses
    captured_prompts = []

    def mock_generate(self, orch, prompt, response_schema=None, **kwargs):
        captured_prompts.append(prompt)
        if kwargs.get("component") == "coordinator":
            # Return valid coordinator output
            coord_out = {
                "merges": [],
                "omissions": [],
                "recommended_actions": {
                    "prov-correctness-e2e-1": "Refactor process_payout to use safe JSON schema validation.",
                    "security-deterministic-unsafe_deserialize-1": "Verify deserialization safety.",
                }
            }
            return json.dumps(coord_out)
        else:
            return json.dumps(fake_correctness)

    monkeypatch.setattr(GeminiClient, "generate_content", mock_generate)

    # Execute review upload via test client
    zip_bytes = create_e2e_zip()
    files = {"file": ("test_e2e.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": orch_type})
    assert response.status_code == 200, f"Response: {response.text}"
    
    report_data = response.json()
    
    # Assert output conforms to ReviewReport Pydantic schema
    report = ReviewReport(**report_data)
    
    assert report.run_metadata["compilation_mode"] == "coordinated"
    assert report.run_metadata["orchestrator_type"] in ("InProcessOrchestrator", "AdkOrchestrator")
    
    # Assert correctness and security specialist statuses
    statuses = {s.perspective: s.status for s in report.perspective_statuses}
    assert statuses.get("correctness") == "complete"
    assert statuses.get("security") == "complete"
    
    # Assert secret scanning occurred
    assert len(report.secret_scan_summary) == 2
    secret_paths = {s.location.path for s in report.secret_scan_summary}
    assert "src/payout.py" in secret_paths
    assert "secrets/credentials.env" in secret_paths
    
    # Exposed Google key is promoted (severity: high)
    promoted = [s for s in report.secret_scan_summary if s.severity == Severity.HIGH]
    assert len(promoted) == 1
    assert promoted[0].location.path == "src/payout.py"
    
    # Ignored secret in gitignored dir remains INFO/advisory
    ignored = [s for s in report.secret_scan_summary if s.severity == Severity.INFO]
    assert len(ignored) == 1
    assert ignored[0].location.path == "secrets/credentials.env"

    # Confirm AST rules found the pickle.loads vulnerability
    security_findings = [f for f in report.findings if f.perspective == "security" and f.source_agent == "security_deterministic"]
    assert len(security_findings) == 1
    assert security_findings[0].metadata.get("sub_rule") == "unsafe_deserialize"
    
    # Confirm ledger lists all active findings
    assert len(report.findings) == 3  # Correctness + AST security + Promoted secret
    assert len(report.accounting_ledger.included) == 3
    assert len(report.accounting_ledger.merged) == 0
    assert len(report.accounting_ledger.omitted) == 0


def test_e2e_secret_redactions(monkeypatch):
    """
    REQ-23-R2 / AC-23-02: Secret Redaction Invariants.
    Ensure raw secrets never leak in the prompt, serialized report JSON, or warnings.
    """
    fake_correctness = []
    captured_prompts = []

    def mock_generate(self, orch, prompt, response_schema=None, **kwargs):
        captured_prompts.append(prompt)
        if kwargs.get("component") == "coordinator":
            return json.dumps({"merges": [], "omissions": [], "recommended_actions": {}})
        else:
            return json.dumps(fake_correctness)

    monkeypatch.setattr(GeminiClient, "generate_content", mock_generate)

    # Upload zip containing sensitive strings
    zip_bytes = create_e2e_zip()
    files = {"file": ("test_e2e.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    assert response.status_code == 200
    
    # 1. Assert raw secrets NEVER leak in the serialized JSON report
    report_json_str = response.text
    
    assert RAW_SECRET_GOOGLE not in report_json_str, "Exposed Google API key leaked in final report JSON"
    assert RAW_SECRET_DB not in report_json_str, "Exposed DB password leaked in final report JSON"
    
    # 2. Assert raw secrets NEVER leak in generated specialist prompts
    assert len(captured_prompts) > 0
    for prompt in captured_prompts:
        assert RAW_SECRET_GOOGLE not in prompt, "Exposed Google API key leaked in LLM prompt context"
        assert RAW_SECRET_DB not in prompt, "Exposed DB password leaked in LLM prompt context"
        
    # Verify that at least one prompt (the correctness prompt) contains the redaction placeholder
    placeholders_found = any(
        "[REDACTED_GOOGLE_API_KEY_" in p or "[REDACTED_DATABASE_PASSWORD_" in p
        for p in captured_prompts
    )
    assert placeholders_found, "Redaction placeholder missing from all generated prompts"


def test_e2e_fallback_on_coordinator_failure(monkeypatch):
    """
    REQ-23-R3 / AC-23-03: Fallback Guarantee.
    Mocking a failing coordinator (JSON decode error) causes compilation fallback to terminal report.
    """
    # Return malformed JSON to force failure in compilation
    monkeypatch.setattr(
        GeminiClient,
        "generate_content",
        lambda *args, **kwargs: "{invalid coordinator JSON response"
    )

    zip_bytes = create_e2e_zip()
    files = {"file": ("test_e2e.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    assert response.status_code == 200
    
    report_data = response.json()
    report = ReviewReport(**report_data)
    
    # Mode must fallback to terminal_fallback
    assert report.run_metadata["compilation_mode"] == "terminal_fallback"
    
    # Zero merges, omissions. All input findings must be included verbatim.
    assert len(report.findings) == 2  # AST security + Promoted secret
    assert report.accounting_ledger.included == [f.id for f in report.findings]
    assert len(report.accounting_ledger.merged) == 0
    assert len(report.accounting_ledger.omitted) == 0
    assert any("Coordinator compilation failed or was bypassed" in w for w in report.validator_warnings)


def test_e2e_coordinate_validation(monkeypatch):
    """
    REQ-23-R4 / AC-23-04: Coordinate Validity & Invariant Rejection.
    If the coordinator returns findings citing out-of-bounds line numbers,
    the validator must reject the coordinated report and fallback to the terminal report.
    """
    fake_correctness = [
        {
            "id": "prov-correctness-e2e-valid",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "high",
            "location": {
                "path": "src/payout.py",
                "line_start": 2,
                "line_end": 4
            },
            "claim": "Valid correctness claim.",
            "evidence_ref": ["file:SPEC.md#3-4", "file:src/payout.py#2-4"]
        }
    ]

    # Let's mock `run_coordinator_compilation` directly to return an out-of-bounds finding location
    from gdg_yorku_submission.schemas import ReportFinding, Location, AccountingLedger
    
    def mock_corrupt_compilation(*args, **kwargs):
        # Return a report finding with line_start=9999, line_end=10000 (out of bounds for src/payout.py which has 7 lines)
        corrupted_finding = ReportFinding(
            id="prov-correctness-e2e-valid",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=Location(path="src/payout.py", line_start=9999, line_end=10000),
            claim="Valid correctness claim.",
            evidence_ref=["file:SPEC.md#3-4"],
            status="active",
            recommended_next_action="Action",
            merged_from=[]
        )
        return [corrupted_finding], [], AccountingLedger(included=["prov-correctness-e2e-valid"], merged=[], omitted=[], contested=[])

    monkeypatch.setattr(GeminiClient, "generate_content", lambda *args, **kwargs: json.dumps(fake_correctness))
    monkeypatch.setattr("gdg_yorku_submission.coordinator.run_coordinator_compilation", mock_corrupt_compilation)

    zip_bytes = create_e2e_zip()
    files = {"file": ("test_e2e.zip", zip_bytes, "application/zip")}
    
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    assert response.status_code == 200
    
    report_data = response.json()
    report = ReviewReport(**report_data)
    
    # Must fallback to terminal report because of coordinate validation failure
    assert report.run_metadata["compilation_mode"] == "terminal_fallback"
    assert any("out of bounds" in w for w in report.validator_warnings)

import os
import sys
import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src/ to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_sample_review import main, run_review
from gdg_yorku_submission.schemas import ReviewReport

@pytest.fixture(autouse=True)
def clean_env():
    old_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(old_env)

def test_script_help(monkeypatch):
    """Verifies that the script CLI help compiles and parses correctly."""
    monkeypatch.setattr(sys, "argv", ["run_sample_review.py", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

def test_script_missing_zip(monkeypatch):
    """Verifies that the script exits with code 1 if the zip file does not exist."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_sample_review.py", "--zip", "non_existent_file_12345.zip"]
    )
    assert main() == 1

def test_script_real_llm_without_credentials(monkeypatch):
    """Verifies that real LLM mode fails if no credentials are in env."""
    # Ensure no credentials in the env
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_sample_review.py", "--zip", "samples/driftstore.zip", "--real"]
    )
    assert main() == 1

@pytest.mark.parametrize("orchestrator", ["adk", "in_process"])
def test_script_dry_run_success(orchestrator, monkeypatch, tmp_path):
    """Verifies a full successful run in dry-run/fake mode using adk and in_process orchestrators."""
    # Ensure fake LLM env var is not overriding our flags
    monkeypatch.delenv("USE_FAKE_LLM", raising=False)
    
    output_json_file = tmp_path / "report.json"
    
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--orchestrator", orchestrator,
            "--output", str(output_json_file)
        ]
    )
    
    assert main() == 0
    assert os.path.exists(output_json_file)
    
    # Read the file and parse it as ReviewReport
    report_data = json.loads(output_json_file.read_text(encoding="utf-8"))
    report = ReviewReport(**report_data)
    
    assert report.run_metadata["orchestrator_type"] in ("AdkOrchestrator", "InProcessOrchestrator")
    assert report.run_metadata["compilation_mode"] == "coordinated"
    
    # Check that we found findings (correctness finding + security AST baseline findings + promoted secrets)
    assert len(report.findings) > 0
    assert len(report.secret_scan_summary) >= 2
    
    # B4: test_script_dry_run_success locks the "0 validation warnings" claim
    assert report.validator_warnings == []

def test_script_with_debate_flag(monkeypatch, tmp_path):
    """Verifies that --with-debate runs debate and produces debate artifacts."""
    output_no_debate = tmp_path / "report_nodebate.json"
    output_debate = tmp_path / "report_debate.json"
    
    # Run 1: without debate
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--output", str(output_no_debate)
        ]
    )
    assert main() == 0
    report_no_debate = ReviewReport(**json.loads(output_no_debate.read_text(encoding="utf-8")))
    
    # Run 2: with debate
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--with-debate",
            "--output", str(output_debate)
        ]
    )
    assert main() == 0
    report_debate = ReviewReport(**json.loads(output_debate.read_text(encoding="utf-8")))
    
    # B1: Assert debate wiring artifact.
    # In fake/dry-run debate mode, findings are mapped as contested.
    # So contested_items list is non-empty, whereas in non-debate path it is empty.
    assert len(report_no_debate.contested_items) == 0
    assert len(report_debate.contested_items) > 0
    assert os.getenv("ENABLE_SECURITY_DEBATE") == "true"
    assert os.getenv("USE_FAKE_LLM") == "true"

def test_script_redaction_boundary(monkeypatch, tmp_path, capsys):
    """B3: Verifies that the plaintext secret from samples/driftstore/.env does not leak in outputs."""
    output_json_file = tmp_path / "report_redacted.json"
    
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--output", str(output_json_file)
        ]
    )
    
    assert main() == 0
    
    captured = capsys.readouterr()
    stdout_content = captured.out
    stderr_content = captured.err
    file_content = output_json_file.read_text(encoding="utf-8")
    
    # Plaintext secret is "super_secret_db_password_12345"
    plaintext_secret = "super_secret_db_password_12345"
    
    assert plaintext_secret not in stdout_content, "Plaintext secret leaked in stdout!"
    assert plaintext_secret not in stderr_content, "Plaintext secret leaked in stderr!"
    assert plaintext_secret not in file_content, "Plaintext secret leaked in output JSON file!"

@pytest.mark.live_smoke
@pytest.mark.skipif(
    not (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GEMINI_API_KEY")),
    reason="Missing credentials for live integration test"
)
def test_real_smoke_run(monkeypatch, tmp_path):
    """B2: Opt-in live integration smoke test using real LLM and debate."""
    output_json_file = tmp_path / "live_report.json"
    
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--real",
            "--orchestrator", "adk",
            "--with-debate",
            "--output", str(output_json_file)
        ]
    )
    
    assert main() == 0
    assert os.path.exists(output_json_file)
    
    report_data = json.loads(output_json_file.read_text(encoding="utf-8"))
    report = ReviewReport(**report_data)
    
    assert report.run_metadata["compilation_mode"] == "coordinated"
    assert len(report.findings) > 0 or len(report.contested_items) > 0
    assert report.run_metadata.get("adk_runner_executed") is True



def test_adk_orchestrator_genuinely_uses_adk(monkeypatch):
    """C4: Verifies that AdkOrchestrator genuinely uses InMemorySessionService from google-adk."""
    try:
        from google.adk.sessions import InMemorySessionService
        adk_installed = True
    except ImportError:
        adk_installed = False

    if not adk_installed:
        pytest.skip("google-adk is not installed")

    from gdg_yorku_submission.orchestrator import AdkOrchestrator
    orch = AdkOrchestrator()
    run_id = orch.start_run()

    assert orch._fallback_mode is False
    assert isinstance(orch._session_service, InMemorySessionService)

    session = orch._session_service._get_session_impl(
        app_name="gdg-yorku-submission",
        user_id="system",
        session_id=run_id
    )
    assert session is not None
    assert session.id == run_id
    session_state_clean = {k: v for k, v in session.state.items() if k != "redaction_context"}
    orch_state_clean = {k: v for k, v in orch.read_state().items() if k != "redaction_context"}
    assert session_state_clean == orch_state_clean


def test_adk_runner_execution_spy(monkeypatch):
    """C4: Verifies that real LLM calls route through google.adk.Runner when AdkOrchestrator is used."""
    try:
        from google.adk import Runner
        adk_installed = True
    except ImportError:
        adk_installed = False

    if not adk_installed:
        pytest.skip("google-adk is not installed")

    from gdg_yorku_submission.orchestrator import AdkOrchestrator
    from gdg_yorku_submission.llm.gemini import GeminiClient

    orch = AdkOrchestrator()
    orch.start_run()

    monkeypatch.setenv("USE_FAKE_LLM", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")

    runner_run_called = []

    async def mock_runner_run_async(self, *args, **kwargs):
        runner_run_called.append((args, kwargs))
        from google.adk import Event
        yield Event(output="{'mock_findings': []}")

    monkeypatch.setattr(Runner, "run_async", mock_runner_run_async)

    client = GeminiClient(use_fake=False)
    
    response = client.generate_content(
        orch=orch,
        prompt="run safety check",
        response_schema=None
    )

    assert len(runner_run_called) == 1
    assert response == "{'mock_findings': []}"
    
    state = orch.read_state()
    assert state["run_metadata"].get("adk_runner_executed") is True


def test_adk_runner_executes_from_running_event_loop(monkeypatch):
    """C4 regression guard: generate_content() is invoked from inside a running
    event loop (the CLI wraps the pipeline in asyncio.run(); FastAPI handlers are
    async). The ADK path must offload to a worker thread rather than call
    asyncio.run() in that context, otherwise it raises 'asyncio.run() cannot be
    called from a running event loop' and silently falls back to direct Vertex."""
    try:
        from google.adk import Runner
    except ImportError:
        pytest.skip("google-adk is not installed")

    from gdg_yorku_submission.orchestrator import AdkOrchestrator
    from gdg_yorku_submission.llm.gemini import GeminiClient

    orch = AdkOrchestrator()
    orch.start_run()

    monkeypatch.setenv("USE_FAKE_LLM", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")

    async def mock_runner_run_async(self, *args, **kwargs):
        from google.adk import Event
        yield Event(output="{'mock_findings': []}")

    monkeypatch.setattr(Runner, "run_async", mock_runner_run_async)

    client = GeminiClient(use_fake=False)

    async def _call_from_within_loop():
        # Mirror orch.run_specialist("correctness", ...) being called from inside
        # the asyncio.run(run_review(...)) loop: a synchronous generate_content()
        # invocation while an event loop is already running on this thread.
        return client.generate_content(
            orch=orch,
            prompt="run safety check",
            response_schema=None
        )

    response = asyncio.run(_call_from_within_loop())

    assert response == "{'mock_findings': []}"
    assert orch.read_state()["run_metadata"].get("adk_runner_executed") is True


def test_adk_orchestrator_fallback_on_missing_adk(monkeypatch):
    """C3: Verifies that AdkOrchestrator degrades to in-process behavior and surfaces a warning if ADK is missing."""
    from gdg_yorku_submission import orchestrator
    monkeypatch.setattr(orchestrator, "_ADK_AVAILABLE", False)
    monkeypatch.setattr(orchestrator.AdkOrchestrator, "_session_service", None)
    
    from gdg_yorku_submission.orchestrator import AdkOrchestrator
    
    orch = AdkOrchestrator()
    run_id = orch.start_run()
    
    assert orch._fallback_mode is True
    
    state = orch.read_state()
    assert "adk_warning" in state["run_metadata"]
    assert "Fell back to in-process orchestrator" in state["run_metadata"]["adk_warning"]


def test_adk_internal_apis_durability_guard():
    """D6: Asserts that private session service methods and attributes used by AdkOrchestrator exist
    and conform to their expected signatures, guarding against ADK version mismatches/breakages."""
    try:
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        pytest.fail("google-adk package is not installed, which is required for durability guard")

    import inspect
    
    # 1. Verify InMemorySessionService has '_get_session_impl'
    assert hasattr(InMemorySessionService, "_get_session_impl"), (
        "InMemorySessionService missing private method '_get_session_impl'. "
        "AdkOrchestrator depends on google-adk internal session APIs."
    )
    sig_get = inspect.signature(InMemorySessionService._get_session_impl)
    for param in ["app_name", "user_id", "session_id"]:
        assert param in sig_get.parameters, f"'_get_session_impl' signature changed: missing parameter '{param}'"

    # 2. Verify InMemorySessionService has '_create_session_impl'
    assert hasattr(InMemorySessionService, "_create_session_impl"), (
        "InMemorySessionService missing private method '_create_session_impl'. "
        "AdkOrchestrator depends on google-adk internal session APIs."
    )
    sig_create = inspect.signature(InMemorySessionService._create_session_impl)
    for param in ["app_name", "user_id", "state", "session_id"]:
        assert param in sig_create.parameters, f"'_create_session_impl' signature changed: missing parameter '{param}'"

    # 3. Verify InMemorySessionService has 'sessions' dictionary attribute
    s = InMemorySessionService()
    assert hasattr(s, "sessions"), "InMemorySessionService is missing 'sessions' attribute"
    assert isinstance(s.sessions, dict), f"InMemorySessionService.sessions is type {type(s.sessions)}, expected dict"


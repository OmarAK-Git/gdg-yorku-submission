"""Offline regression guards for the real (non-fake) LLM call paths.

These cover gaps the live_smoke test cannot, because it is skipped without
credentials: client precedence (Vertex/ADC first), the Opus 4.8 effort cap, the
absence of banned sampling params, and the debate-fallback visibility guarantee.
All real clients are mocked — no network calls.
"""
import os
import sys
import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.security.claude_adapter import call_claude_adversary
from gdg_yorku_submission.security.gemini_adapter import call_gemini_adversary
from gdg_yorku_submission.security.debate_schema import AdversaryResponse


@pytest.fixture(autouse=True)
def clean_env():
    old_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(old_env)


def _started_orch():
    orch = InProcessOrchestrator()
    orch.start_run()
    return orch


def _mock_claude_response():
    payload = {
        "proposals": [
            {
                "text": "x",
                "severity": "high",
                "groundednessCitation": "src/app.py#20-30",
                "reasoning": "y",
            }
        ],
        "questions_for_human": [],
    }
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(payload))]
    resp.usage = MagicMock(input_tokens=10, output_tokens=20)
    return resp


def test_claude_real_path_uses_vertex_and_caps_effort(monkeypatch):
    """Gap #1: real Claude path prefers Vertex/ADC and caps effort; no banned params."""
    monkeypatch.setenv("USE_FAKE_LLM", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-proj")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-east5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "should-not-be-used")
    monkeypatch.setenv("CRUCIBLE_CLAUDE_EFFORT", "low")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_claude_response())

    with patch("anthropic.AsyncAnthropicVertex", return_value=mock_client) as vertex_ctor, \
         patch("anthropic.AsyncAnthropic") as api_key_ctor:
        result = asyncio.run(
            call_claude_adversary(_started_orch(), "sys", "user", response_model=AdversaryResponse)
        )

    # Vertex/ADC chosen over the API-key client even though ANTHROPIC_API_KEY is set
    vertex_ctor.assert_called_once()
    assert vertex_ctor.call_args.kwargs.get("project_id") == "test-proj"
    assert vertex_ctor.call_args.kwargs.get("region") == "us-east5"
    api_key_ctor.assert_not_called()

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["output_config"]["effort"] == "low"
    for banned in ("temperature", "top_p", "top_k", "thinking", "budget_tokens"):
        assert banned not in kwargs, f"{banned} must not be sent to Opus 4.8"

    assert isinstance(result, AdversaryResponse)


def test_claude_real_path_falls_back_to_api_key(monkeypatch):
    """Gap #1: with no GOOGLE_CLOUD_PROJECT, the API-key client is used (and effort still capped)."""
    monkeypatch.setenv("USE_FAKE_LLM", "false")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CRUCIBLE_CLAUDE_EFFORT", "medium")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_claude_response())

    with patch("anthropic.AsyncAnthropic", return_value=mock_client) as api_key_ctor, \
         patch("anthropic.AsyncAnthropicVertex") as vertex_ctor:
        asyncio.run(
            call_claude_adversary(_started_orch(), "sys", "user", response_model=AdversaryResponse)
        )

    api_key_ctor.assert_called_once()
    vertex_ctor.assert_not_called()
    assert mock_client.messages.create.call_args.kwargs["output_config"]["effort"] == "medium"


def test_gemini_defender_real_path_uses_vertex(monkeypatch):
    """Gap #1: real Gemini defender prefers Vertex/ADC and honors GEMINI_MODEL."""
    monkeypatch.setenv("USE_FAKE_LLM", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-proj")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("GEMINI_MODEL", "my-test-model")

    resp = MagicMock()
    resp.text = json.dumps({"proposals": [], "questions_for_human": []})
    resp.usage_metadata = MagicMock(prompt_token_count=5, candidates_token_count=7)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = resp

    with patch("google.genai.Client", return_value=mock_client) as client_ctor:
        result = asyncio.run(
            call_gemini_adversary(_started_orch(), "sys", "user", response_model=AdversaryResponse)
        )

    client_ctor.assert_called_once()
    assert client_ctor.call_args.kwargs.get("vertexai") is True
    assert client_ctor.call_args.kwargs.get("project") == "test-proj"
    assert client_ctor.call_args.kwargs.get("location") == "us-central1"
    
    mock_client.models.generate_content.assert_called_once()
    assert mock_client.models.generate_content.call_args.kwargs.get("model") == "my-test-model"
    assert isinstance(result, AdversaryResponse)



def test_debate_failure_surfaces_validator_warning(monkeypatch, tmp_path):
    """Gap #2: when the debate loop raises, the fall back to the AST baseline is surfaced
    in report.validator_warnings (never silently dropping the primary security perspective)."""
    from scripts.run_sample_review import main
    from gdg_yorku_submission.schemas import ReviewReport

    async def _boom(*args, **kwargs):
        raise RuntimeError("debate exploded")

    monkeypatch.setattr("gdg_yorku_submission.security.debate.run_debate_loop", _boom)

    output_json = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_sample_review.py",
            "--zip", "samples/driftstore.zip",
            "--with-debate",
            "--output", str(output_json),
        ],
    )

    assert main() == 0
    report = ReviewReport(**json.loads(output_json.read_text(encoding="utf-8")))
    assert any("debate failed" in w.lower() for w in report.validator_warnings), (
        f"debate fallback not surfaced; warnings={report.validator_warnings}"
    )

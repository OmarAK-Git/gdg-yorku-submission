import json
import pytest
from gdg_yorku_submission.schemas import CorpusFile, Location, Severity, ReviewFinding
from gdg_yorku_submission.orchestrator import InProcessOrchestrator
from gdg_yorku_submission.budget import RunBudget, BudgetLease, acquire_budget_lease, record_llm_usage, BudgetExhaustedError
from gdg_yorku_submission.llm.gemini import GeminiClient
from gdg_yorku_submission.correctness.agent import run_correctness_review, make_correctness_specialist, CorrectnessAgentException

def create_corpus_entry(
    path: str,
    text: str,
    exposure: str = "prompt_exposed",
    redaction_applied: bool = True,
    ingest_status: str = "success"
) -> CorpusFile:
    """Helper to create a mock CorpusFile with standard defaults for testing."""
    return CorpusFile(
        normalized_path=path,
        original_text=text,
        redacted_text=text,
        original_line_count=len(text.splitlines()) if text else 0,
        redacted_to_original_line_map={i: i for i in range(1, len(text.splitlines()) + 1)} if text else {},
        evidence_ref=f"file:{path}",
        exposure_status=exposure,
        ingest_status=ingest_status,
        redaction_applied=redaction_applied
    )

# --- Budget & Lease Tests ---

def test_budget_initialization():
    orch = InProcessOrchestrator()
    orch.start_run()
    state = orch.read_state()
    
    assert "budget" in state
    budget = RunBudget(**state["budget"])
    assert budget.used_llm_calls == 0
    assert budget.max_total_tokens == 100000

def test_acquire_lease_success():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    lease = BudgetLease(component="test", estimated_tokens=1000, provider="gemini")
    acquire_budget_lease(orch, lease)
    
    state = orch.read_state()
    budget = RunBudget(**state["budget"])
    assert budget.used_llm_calls == 1

def test_acquire_lease_max_calls_exhausted():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Manually update max calls to 1
    state = orch._get_state()
    state["budget"]["max_llm_calls"] = 1
    orch._save_state(state)
    
    lease1 = BudgetLease(component="test", estimated_tokens=1000, provider="gemini")
    acquire_budget_lease(orch, lease1)
    
    lease2 = BudgetLease(component="test", estimated_tokens=1000, provider="gemini")
    with pytest.raises(BudgetExhaustedError, match="maximum LLM calls cap reached"):
        acquire_budget_lease(orch, lease2)

def test_acquire_lease_tokens_exhausted():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Manually update max total tokens
    state = orch._get_state()
    state["budget"]["max_total_tokens"] = 5000
    orch._save_state(state)
    
    lease = BudgetLease(component="test", estimated_tokens=6000, provider="gemini")
    with pytest.raises(BudgetExhaustedError, match="exceed max_total_tokens cap"):
        acquire_budget_lease(orch, lease)

def test_acquire_lease_provider_tokens_exhausted():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Manually update max gemini tokens
    state = orch._get_state()
    state["budget"]["max_gemini_tokens"] = 2000
    orch._save_state(state)
    
    lease = BudgetLease(component="test", estimated_tokens=3000, provider="gemini")
    with pytest.raises(BudgetExhaustedError, match="exceed max_gemini_tokens cap"):
        acquire_budget_lease(orch, lease)

def test_record_usage():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    record_llm_usage(orch, "gemini", tokens_used=1200, cost_usd=0.005)
    
    state = orch.read_state()
    budget = RunBudget(**state["budget"])
    assert budget.used_total_tokens == 1200
    assert budget.used_gemini_tokens == 1200
    assert budget.used_cost_usd == 0.005
    assert state["run_metadata"]["budget"]["used_total_tokens"] == 1200

# --- Correctness Agent Adapter Tests ---

def test_run_correctness_review_no_spec():
    orch = InProcessOrchestrator()
    orch.start_run()
    # Empty corpus -> no specification
    orch.set_corpus({})
    
    findings, status, reason = run_correctness_review(orch)
    assert findings == []
    assert status == "skipped"
    assert reason == "no_spec_found_conformance_skipped"

def test_run_correctness_review_success():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "This is SPEC content.\nRequirement 1 is documented here.\nLine 3 of spec."),
        "src/app.py": create_corpus_entry("src/app.py", "def my_func():\n    pass\n# another line\n")
    }
    orch.set_corpus(corpus)
    
    valid_findings_json = json.dumps([
        {
            "id": "prov-correctness-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "high",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 2
            },
            "claim": "Implemented behavior diverges from Requirement 1 in SPEC.md.",
            "evidence_ref": ["file:SPEC.md#2-2", "file:src/app.py#1-2"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[valid_findings_json])
    
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    
    assert status == "complete"
    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "prov-correctness-f1"
    assert finding.severity == Severity.HIGH
    assert finding.location.path == "src/app.py"
    assert finding.location.line_start == 1
    assert finding.location.line_end == 2
    assert finding.evidence_ref == ["file:SPEC.md#2-2", "file:src/app.py#1-2"]

def test_run_correctness_review_malformed_json_retries():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec content"),
        "src/app.py": create_corpus_entry("src/app.py", "App content")
    }
    orch.set_corpus(corpus)
    
    # First response is malformed, second is valid
    valid_json = json.dumps([
        {
            "id": "prov-correctness-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 1
            },
            "claim": "Claim text",
            "evidence_ref": ["file:SPEC.md#1-1"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=["{invalid JSON text", valid_json])
    
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    assert status == "complete"
    assert len(findings) == 1
    assert findings[0].id == "prov-correctness-f1"

def test_run_correctness_review_malformed_json_exhausted():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec content"),
        "src/app.py": create_corpus_entry("src/app.py", "App content")
    }
    orch.set_corpus(corpus)
    
    # Both responses are malformed
    gemini = GeminiClient(use_fake=True, fake_responses=["{invalid JSON text", "{still bad json"])
    
    with pytest.raises(CorrectnessAgentException, match="returned invalid JSON after 2 attempts"):
        run_correctness_review(orch, gemini_client=gemini)

def test_run_correctness_coordinate_checks():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Line 1\nLine 2"),
        "src/app.py": create_corpus_entry("src/app.py", "Line 1\nLine 2\nLine 3")
    }
    orch.set_corpus(corpus)
    
    findings_json = json.dumps([
        # 1. Non-existent location path -> skipped
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/non_existent.py",
                "line_start": 1,
                "line_end": 1
            },
            "claim": "Non-existent file cited",
            "evidence_ref": ["file:SPEC.md#1-1"]
        },
        # 2. Location lines out of bounds -> skipped
        {
            "id": "prov-f2",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 10  # max lines is 3
            },
            "claim": "Out of bounds lines cited",
            "evidence_ref": ["file:SPEC.md#1-1"]
        },
        # 3. Evidence ref non-existent path -> skipped
        {
            "id": "prov-f3",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 1
            },
            "claim": "Non-existent evidence file cited",
            "evidence_ref": ["file:non_existent_sot.md#1-1"]
        },
        # 4. Evidence ref lines out of bounds -> skipped
        {
            "id": "prov-f4",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 1
            },
            "claim": "Out of bounds evidence lines cited",
            "evidence_ref": ["file:SPEC.md#1-10"] # max lines is 2
        },
        # 5. Fully valid -> kept
        {
            "id": "prov-f5",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 2
            },
            "claim": "Valid claim",
            "evidence_ref": ["file:SPEC.md#1-2"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[findings_json])
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    
    assert status == "complete"
    assert len(findings) == 1
    assert findings[0].id == "prov-f5"

def test_make_specialist_integration():
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec content"),
        "src/app.py": create_corpus_entry("src/app.py", "App content")
    }
    orch.set_corpus(corpus)
    
    findings_json = json.dumps([
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "low",
            "location": {
                "path": "src/app.py",
                "line_start": 1,
                "line_end": 1
            },
            "claim": "Valid claim",
            "evidence_ref": ["file:SPEC.md#1-1"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[findings_json])
    specialist_func = make_correctness_specialist(orch, gemini_client=gemini)
    
    orch.run_specialist("correctness", specialist_func)
    
    state = orch.read_state()
    p_status = state["perspective_statuses"]["correctness"]
    assert p_status.status == "complete"
    assert len(p_status.finding_ids) == 1
    assert len(state["findings"]) == 1
    assert state["findings"][0].id == "prov-f1"

# --- Issue-Specific Regression and Attack Tests ---

def test_retry_loop_budget_lease_and_calls_counting():
    """
    Issue 1: Test that on a retry, the budget lease is acquired for EACH attempt,
    and used_llm_calls correctly tracks the actual call count including retries.
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec content"),
        "src/app.py": create_corpus_entry("src/app.py", "App content")
    }
    orch.set_corpus(corpus)
    
    # We trigger two attempts: first attempt returns malformed JSON, second is valid
    valid_json = json.dumps([
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Mock claim",
            "evidence_ref": ["file:SPEC.md#1-1"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=["{malformed JSON", valid_json])
    
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    assert status == "complete"
    assert len(findings) == 1
    
    # Verify lease calls was incremented twice (1 for initial attempt, 1 for retry)
    state = orch.read_state()
    budget = RunBudget(**state["budget"])
    assert budget.used_llm_calls == 2

def test_max_cost_usd_limit_enforced():
    """
    Issue 2: Test that projected cost checking is enforced in acquire_budget_lease
    and results in BudgetExhaustedError when exceeded.
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Set max cost limit to $0.0001 (very low)
    state = orch._get_state()
    state["budget"]["max_cost_usd"] = 0.0001
    orch._save_state(state)
    
    # Estimate tokens so that projected cost is high:
    # lease.estimated_tokens = 10000 -> projected cost = 10000 * 0.30 / 1M = $0.003 (exceeds $0.0001)
    lease = BudgetLease(component="correctness_agent", estimated_tokens=10000, provider="gemini")
    
    with pytest.raises(BudgetExhaustedError, match="exceed max_cost_usd cap"):
        acquire_budget_lease(orch, lease)

def test_budget_exhausted_integration_status():
    """
    Issue 3: Test that run_specialist under budget exhaustion results in
    perspective_statuses["correctness"].status == "failed" and reason == "budget_exhausted".
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec content"),
        "src/app.py": create_corpus_entry("src/app.py", "App content")
    }
    orch.set_corpus(corpus)
    
    # Force max calls to 0 to trigger immediate budget exhaustion
    state = orch._get_state()
    state["budget"]["max_llm_calls"] = 0
    orch._save_state(state)
    
    specialist_func = make_correctness_specialist(orch)
    orch.run_specialist("correctness", specialist_func)
    
    state = orch.read_state()
    p_status = state["perspective_statuses"]["correctness"]
    assert p_status.status == "failed"
    assert p_status.reason == "budget_exhausted"

def test_grounding_checks_require_spec_cite():
    """
    Issue 4: Test that correctness agent rejects findings that do not cite the discovered SoT path,
    or have an empty evidence_ref list.
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Spec line 1\nSpec line 2"),
        "src/app.py": create_corpus_entry("src/app.py", "App line 1\nApp line 2")
    }
    orch.set_corpus(corpus)
    
    findings_json = json.dumps([
        # 1. Empty evidence_ref -> rejected
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "No evidence cited",
            "evidence_ref": []
        },
        # 2. Cites code only, no SoT -> rejected
        {
            "id": "prov-f2",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Only code cited",
            "evidence_ref": ["file:src/app.py#1-1"]
        },
        # 3. Fully grounded -> kept
        {
            "id": "prov-f3",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Correctly grounded",
            "evidence_ref": ["file:SPEC.md#1-2", "file:src/app.py#1-1"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[findings_json])
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    
    assert status == "complete"
    assert len(findings) == 1
    assert findings[0].id == "prov-f3"

def test_coordinate_translation_mapping():
    """
    Issue 5: Test that redacted line citations are translated back to original lines using map_line.
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # We construct a mock CorpusFile where line mappings are shifted.
    # Original has 5 lines, Redacted has 3 lines:
    # Redacted Line 1 -> Original Line 1
    # Redacted Line 2 -> Original Line 3
    # Redacted Line 3 -> Original Line 5
    spec_entry = CorpusFile(
        normalized_path="SPEC.md",
        original_text="orig1\norig2\norig3\norig4\norig5",
        redacted_text="orig1\norig3\norig5",
        original_line_count=5,
        redacted_to_original_line_map={1: 1, 2: 3, 3: 5},
        evidence_ref="file:SPEC.md",
        exposure_status="prompt_exposed",
        ingest_status="success",
        redaction_applied=True
    )
    
    app_entry = CorpusFile(
        normalized_path="src/app.py",
        original_text="line1\nline2\nline3\nline4\nline5",
        redacted_text="line1\nline3\nline5",
        original_line_count=5,
        redacted_to_original_line_map={1: 1, 2: 3, 3: 5},
        evidence_ref="file:src/app.py",
        exposure_status="prompt_exposed",
        ingest_status="success",
        redaction_applied=True
    )
    
    corpus = {
        "SPEC.md": spec_entry,
        "src/app.py": app_entry
    }
    orch.set_corpus(corpus)
    
    # LLM returns coordinates in terms of redacted lines (1, 2, 3)
    findings_json = json.dumps([
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {
                "path": "src/app.py",
                "line_start": 2, # Redacted Line 2 -> Original Line 3
                "line_end": 2
            },
            "claim": "Claim text",
            "evidence_ref": ["file:SPEC.md#3-3"] # Redacted Line 3 -> Original Line 5
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[findings_json])
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    
    assert status == "complete"
    assert len(findings) == 1
    f = findings[0]
    
    # Assert coordinates are correctly translated to original coordinates
    assert f.location.line_start == 3
    assert f.location.line_end == 3
    assert f.evidence_ref == ["file:SPEC.md#5-5"]

def test_evidence_ref_ordering_and_lower_bound_checks():
    """
    Issue 6: Test that evidence_ref existence checks enforce lower bounds (>=1)
    and ordering (start <= end).
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    corpus = {
        "SPEC.md": create_corpus_entry("SPEC.md", "Line 1\nLine 2"),
        "src/app.py": create_corpus_entry("src/app.py", "Line 1\nLine 2\nLine 3")
    }
    orch.set_corpus(corpus)
    
    findings_json = json.dumps([
        # 1. Zero line start -> rejected
        {
            "id": "prov-f1",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Zero index cited",
            "evidence_ref": ["file:SPEC.md#0-2"]
        },
        # 2. Inverted line range -> rejected
        {
            "id": "prov-f2",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Inverted range cited",
            "evidence_ref": ["file:SPEC.md#2-1"]
        },
        # 3. Valid range -> kept
        {
            "id": "prov-f3",
            "source_agent": "correctness_agent",
            "perspective": "correctness",
            "severity": "medium",
            "location": {"path": "src/app.py", "line_start": 1, "line_end": 1},
            "claim": "Valid range",
            "evidence_ref": ["file:SPEC.md#1-2"]
        }
    ])
    
    gemini = GeminiClient(use_fake=True, fake_responses=[findings_json])
    findings, status, reason = run_correctness_review(orch, gemini_client=gemini)
    
    assert status == "complete"
    assert len(findings) == 1
    assert findings[0].id == "prov-f3"

def test_gemini_client_production_loud_failure_when_missing_creds():
    """
    Issue 7: Test that the GeminiClient raises a RuntimeError in real/production mode
    if credentials are missing from the environment.
    """
    import os
    # Temporarily strip all environment variables that count as credentials
    old_env = {}
    for key in ["GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "USE_FAKE_LLM"]:
        if key in os.environ:
            old_env[key] = os.environ[key]
            del os.environ[key]
            
    try:
        with pytest.raises(RuntimeError, match="no credentials .* were detected"):
            # Set use_fake to False explicitly to force production checks
            GeminiClient(use_fake=False)
    finally:
        # Restore environment variables
        for key, val in old_env.items():
            os.environ[key] = val


def test_coordinator_budget_reserve():
    """
    Test that non-coordinator budget leases account for the coordinator reserve,
    while coordinator budget leases do not.
    """
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Configure budget: max 2 calls, max 5000 tokens
    state = orch._get_state()
    state["budget"]["max_llm_calls"] = 2
    state["budget"]["max_total_tokens"] = 5000
    orch._save_state(state)
    
    # Reserve is 1 call, 4000 tokens.
    # Non-coordinator lease of 500 tokens:
    # check_total_tokens = used (0) + lease (500) + reserve (4000) = 4500 <= 5000. Success.
    # check_llm_calls = used (0) + 1 + reserve (1) = 2 <= 2. Success.
    lease1 = BudgetLease(component="correctness_agent", estimated_tokens=500, provider="gemini")
    acquire_budget_lease(orch, lease1)
    
    # A second non-coordinator lease of 500 tokens:
    # check_total_tokens = used (500) + lease (500) + reserve (4000) = 5000 <= 5000.
    # check_llm_calls = used (1) + 1 + reserve (1) = 3 > 2. Raises!
    lease2 = BudgetLease(component="correctness_agent", estimated_tokens=500, provider="gemini")
    with pytest.raises(BudgetExhaustedError, match="maximum LLM calls cap reached"):
        acquire_budget_lease(orch, lease2)
        
    # A coordinator lease of 500 tokens:
    # check_total_tokens = used (500) + lease (500) = 1000 <= 5000.
    # check_llm_calls = used (1) + 1 = 2 <= 2. Success. (exempt from reserve check)
    lease_coord = BudgetLease(component="coordinator", estimated_tokens=500, provider="gemini")
    acquire_budget_lease(orch, lease_coord)
    
    state = orch.read_state()
    budget = RunBudget(**state["budget"])
    assert budget.used_llm_calls == 2



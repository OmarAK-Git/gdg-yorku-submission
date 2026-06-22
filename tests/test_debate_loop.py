import pytest
import os
import sys
from pydantic import ValidationError
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.schemas import Location, Finding
from gdg_yorku_submission.security.debate import run_debate_loop
from gdg_yorku_submission.security.debate_schema import (
    DebateMessage,
    DebateCandidate,
    DebateLedger,
    DebateSession,
    DebateRound,
    Proposal,
    OpponentScore,
    TurnResponse,
    AdversaryResponse,
)
from gdg_yorku_submission.security.debate_scoring import score_proposal, score_round, SEVERITY_WEIGHTS
from gdg_yorku_submission.security.stop_condition import should_terminate, get_proposal_max_score
from gdg_yorku_submission.budget import BudgetExhaustedError
from gdg_yorku_submission.preflight.redaction import RedactionContext

@pytest.fixture
def anyio_backend():
    return 'asyncio'

def make_test_finding(fid: str, severity: Severity, line: int = 10) -> Finding:
    return Finding(
        id=fid,
        source_agent="security_debate",
        perspective="security",
        severity=severity,
        location=Location(path="app.py", line_start=line, line_end=line),
        claim=f"Potential vulnerability under debate {fid}",
        evidence_ref=[f"file:app.py#{line}-{line}"],
        status="active"
    )

class MockOrchestrator:
    def __init__(self, budget_dict=None):
        self.state = {
            "budget": budget_dict or {
                "max_total_tokens": 100000,
                "max_gemini_tokens": 80000,
                "max_claude_tokens": 20000,
                "max_llm_calls": 20,
                "max_cost_usd": 2.0,
                "used_total_tokens": 0,
                "used_gemini_tokens": 0,
                "used_claude_tokens": 0,
                "used_llm_calls": 0,
                "used_cost_usd": 0.0,
            },
            "redaction_context": RedactionContext(),
            "corpus": {}
        }
        
    def read_state(self):
        return self.state
        
    def _get_state(self):
        return self.state
        
    def _save_state(self, state):
        self.state = state

    def get_redaction_context(self):
        return self.state.get("redaction_context")

    def get_corpus(self):
        return self.state.get("corpus")

# 1. Determinism: identical transcript+scores -> identical resolution across two runs.
@pytest.mark.anyio
async def test_determinism():
    orch1 = MockOrchestrator()
    orch2 = MockOrchestrator()
    f1 = make_test_finding("f1", Severity.HIGH)

    def mock_defender(orch, findings, history):
        return TurnResponse(
            summary="Defender Turn",
            opponent_scores=[OpponentScore(proposal_id="C-R1-P1", verdict="accept", reasoning="grounded issue")],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    def mock_challenger(orch, findings, history):
        return TurnResponse(
            summary="Challenger Turn",
            opponent_scores=[],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    session1 = await run_debate_loop(
        orch=orch1,
        findings=[f1],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2
    )

    session2 = await run_debate_loop(
        orch=orch2,
        findings=[f1],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2,
        session_id=session1.session_id
    )

    assert session1.model_dump() == session2.model_dump()

# 2. Self-scoring guard: a side scoring its own proposal raises AssertionError.
def test_self_scoring_guard():
    p_def = Proposal(
        id="D-R2-P1",
        adversary="defender",
        text="usability issue",
        severity=Severity.INFO,
        groundednessCitation="src/app.py",
        reasoning="reasoning"
    )
    p_chal = Proposal(
        id="C-R1-P1",
        adversary="challenger",
        text="security flaw",
        severity=Severity.HIGH,
        groundednessCitation="src/app.py",
        reasoning="reasoning"
    )

    # Scorer is Defender, tries to score a Defender proposal -> Assert raises
    round_data_def_violates = DebateRound(
        round_number=2,
        defender_turn=TurnResponse(
            summary="Violating turn",
            opponent_scores=[OpponentScore(proposal_id="D-R2-P1", verdict="accept", reasoning="self-score")],
            new_proposals=[]
        ),
        scores_this_round={}
    )

    with pytest.raises(AssertionError) as excinfo:
        score_round(round_data_def_violates, {"D-R2-P1": p_def})
    assert "scorer" in str(excinfo.value)

    # Scorer is Challenger, tries to score a Challenger proposal -> Assert raises
    round_data_chal_violates = DebateRound(
        round_number=2,
        challenger_turn=TurnResponse(
            summary="Violating turn",
            opponent_scores=[OpponentScore(proposal_id="C-R1-P1", verdict="accept", reasoning="self-score")],
            new_proposals=[]
        ),
        scores_this_round={}
    )

    with pytest.raises(AssertionError) as excinfo:
        score_round(round_data_chal_violates, {"C-R1-P1": p_chal})
    assert "scorer" in str(excinfo.value)

# 3. Groundedness: an ungrounded "over-hardening" proposal is scored x0.2 and loses to a grounded one.
def test_groundedness_penalty():
    # Grounded: citation is >= 3 chars, not "NONE"
    p_grounded = Proposal(
        id="C-R1-P1",
        adversary="challenger",
        text="Grounded flaw",
        severity=Severity.CRITICAL,
        groundednessCitation="src/app.py#5-10",
        reasoning="reason"
    )
    # Ungrounded: citation is "NONE"
    p_ungrounded = Proposal(
        id="C-R1-P2",
        adversary="challenger",
        text="Ungrounded flaw",
        severity=Severity.CRITICAL,
        groundednessCitation="NONE",
        reasoning="reason"
    )

    # Weight of critical is 10.0. Acceptance factor of accept is 1.0.
    # Grounded: 10.0 * 1.0 * 1.0 = 10.0
    # Ungrounded: 10.0 * 0.2 * 1.0 = 2.0
    score_g = score_proposal(p_grounded, "accept")
    score_ug = score_proposal(p_ungrounded, "accept")

    assert score_g == 10.0
    assert score_ug == 2.0
    assert score_g > score_ug

# 4. Convergence: relative-5% FIRES when delta < 5% of max; does NOT fire when delta exceeds it.
def test_convergence_math():
    p_g = Proposal(
        id="C-R1-P1",
        adversary="challenger",
        text="Grounded",
        severity=Severity.CRITICAL,
        groundednessCitation="src/app.py",
        reasoning="reason"
    )
    proposals_by_id = {"C-R1-P1": p_g}

    # Round 1: Setup scores
    r1 = DebateRound(
        round_number=1,
        defender_turn=TurnResponse(summary="summary", new_proposals=[]),
        challenger_turn=TurnResponse(summary="summary", new_proposals=[p_g]),
        scores_this_round={"defender": 0.0, "challenger": 0.0}
    )

    # Case A: actual_delta >= 5% of max_possible_delta (Does NOT fire)
    r2_high_delta = DebateRound(
        round_number=2,
        defender_turn=TurnResponse(
            summary="Defender turn",
            opponent_scores=[OpponentScore(proposal_id="C-R1-P1", verdict="accept", reasoning="accept")],
            new_proposals=[]
        ),
        scores_this_round={"defender": 0.0, "challenger": 10.0} # Challenger gets 10.0 points
    )
    
    rounds_no_fire = [r1, r2_high_delta]
    # Max possible delta is max(r1_max=0.0, r2_max=10.0) = 10.0
    # actual_delta = abs(10.0 - 0.0) = 10.0
    # 5% threshold = 0.5
    # actual_delta (10.0) > 5% of max (0.5) -> should not terminate
    terminated, reason = should_terminate(rounds_no_fire)
    assert not terminated

    # Case B: actual_delta < 5% of max_possible_delta (FIRES)
    # Let's say in Round 2, challenger got 10.0 points.
    # In Round 3, challenger gets 10.1 points (delta = 0.1).
    # Since evaluated proposals in both rounds are same (e.g. C-R1-P1 evaluated in both), max_possible_delta = 10.0.
    # 5% threshold = 0.5.
    # actual_delta (0.1) < 5% threshold (0.5) -> terminates!
    r3_low_delta = DebateRound(
        round_number=3,
        defender_turn=TurnResponse(
            summary="Defender turn",
            opponent_scores=[OpponentScore(proposal_id="C-R1-P1", verdict="accept", reasoning="accept")],
            new_proposals=[]
        ),
        scores_this_round={"defender": 0.0, "challenger": 10.1}
    )
    
    rounds_fire = [r1, r2_high_delta, r3_low_delta]
    terminated, reason = should_terminate(rounds_fire)
    assert terminated
    assert "Score convergence" in reason

# 5. No-floor-severity-for-2-rounds stop condition.
def test_no_floor_severity_stop_condition():
    # Only low/info proposals (below floor) in rounds 2 and 3
    p_low = Proposal(
        id="C-R2-P1",
        adversary="challenger",
        text="Low vulnerability",
        severity=Severity.LOW,
        groundednessCitation="src/app.py",
        reasoning="reason"
    )

    r1 = DebateRound(
        round_number=1,
        defender_turn=TurnResponse(summary="summary", new_proposals=[]),
        challenger_turn=TurnResponse(summary="summary", new_proposals=[]),
        scores_this_round={}
    )
    r2 = DebateRound(
        round_number=2,
        defender_turn=TurnResponse(summary="summary", new_proposals=[]),
        challenger_turn=TurnResponse(summary="summary", new_proposals=[p_low]),
        scores_this_round={"C-R2-P1": 1.0}
    )
    r3 = DebateRound(
        round_number=3,
        defender_turn=TurnResponse(summary="summary", new_proposals=[]),
        challenger_turn=TurnResponse(summary="summary", new_proposals=[p_low]),
        scores_this_round={"C-R2-P1": 0.0}
    )

    terminated, reason = should_terminate([r1, r2, r3])
    assert terminated
    assert "No critical or important proposals" in reason

# 6. High/critical defeated -> contested promotion safety
@pytest.mark.anyio
async def test_high_severity_defeated_promotion_safety():
    orch = MockOrchestrator()
    f_high = make_test_finding("f_high", Severity.HIGH, line=10)
    f_crit = make_test_finding("f_crit", Severity.CRITICAL, line=11)
    f_med = make_test_finding("f_med", Severity.MEDIUM, line=12)

    def mock_defender(orch, findings, history):
        return TurnResponse(
            summary="Defender turn",
            opponent_scores=[
                OpponentScore(proposal_id="C-R1-P1", verdict="reject", reasoning="false positive claim"),
                OpponentScore(proposal_id="C-R1-P2", verdict="reject", reasoning="false positive claim"),
                OpponentScore(proposal_id="C-R1-P3", verdict="reject", reasoning="false positive claim"),
            ],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    def mock_challenger(orch, findings, history):
        return TurnResponse(
            summary="Challenger turn",
            opponent_scores=[],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    session = await run_debate_loop(
        orch=orch,
        findings=[f_high, f_crit, f_med],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2
    )

    ledger = session.ledger
    contested = ledger.get_contested()
    # f_high and f_crit must be promoted to contested because they are high/critical severity
    assert len(contested) == 2
    assert {c.id for c in contested} == {"f_high", "f_crit"}
    for f in contested:
        assert f.status == "contested"
        assert f.metadata.get("debate_closed_reason") == "false positive claim"

    # f_med is below floor, so it remains omitted
    omitted = ledger.get_omitted()
    assert len(omitted) == 1
    assert omitted[0]["id"] == "f_med"
    assert omitted[0]["reason"] == "false positive claim"

# 7. Redaction: a secret inside a generated proposal/argument is gone from transcript + closed_reason.
@pytest.mark.anyio
async def test_transcript_redaction():
    orch = MockOrchestrator()
    secret = "SUPER_SECRET_TOKEN_XYZ"
    placeholder = orch.get_redaction_context().register_secret(secret, "API_KEY")

    f = make_test_finding("f1", Severity.HIGH)
    f.evidence_ref = ["NONE"]

    def mock_defender(orch, findings, history):
        return TurnResponse(
            summary=f"Defender turn with {secret}",
            opponent_scores=[OpponentScore(proposal_id="C-R1-P1", verdict="reject", reasoning=f"Rejecting {secret}")],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    def mock_challenger(orch, findings, history):
        return TurnResponse(
            summary=f"Challenger turn with {secret}",
            opponent_scores=[],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )

    session = await run_debate_loop(
        orch=orch,
        findings=[f],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2
    )

    # Verify secret is not in the round messages
    for rd in session.rounds:
        for msg in rd.messages:
            assert secret not in msg.message
    # Verify that the placeholder is present in at least one message (confirming redaction happened)
    assert any(placeholder in msg.message for rd in session.rounds for msg in rd.messages)

    # Verify secret is not in the closed reason
    candidate = session.ledger.candidates[0]
    assert secret not in candidate.closed_reason
    assert placeholder in candidate.closed_reason

# 8. Budget: graceful termination + intrinsic guard.
@pytest.mark.anyio
async def test_budget_graceful_termination():
    # Setup exhausted budget dict
    budget_dict = {
        "max_total_tokens": 100,
        "max_gemini_tokens": 80,
        "max_claude_tokens": 20,
        "max_llm_calls": 2,
        "max_cost_usd": 2.0,
        "used_total_tokens": 0,
        "used_gemini_tokens": 0,
        "used_claude_tokens": 0,
        "used_llm_calls": 2, # Exhausted!
        "used_cost_usd": 0.0,
    }
    orch = MockOrchestrator(budget_dict)
    f = make_test_finding("f1", Severity.HIGH)

    def mock_defender(orch, findings, history):
        return TurnResponse(summary="Defender", opponent_scores=[])

    def mock_challenger(orch, findings, history):
        return TurnResponse(summary="Challenger", opponent_scores=[])

    # Run debate loop - should stop intrinsically before round 2 due to budget exhaustion
    session = await run_debate_loop(
        orch=orch,
        findings=[f],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=3
    )

    assert len(session.rounds) == 0 # Round 1 budget check now blocks execution
    assert session.metadata["stop_reason"] == "budget_exhausted"

# 9. Severity remap correctness (each level -> expected weight).
def test_severity_remap_correctness():
    expected_weights = {
        "critical": 10.0,
        "high": 5.0,
        "medium": 2.0,
        "low": 1.0,
        "info": 0.5
    }
    for level, weight in expected_weights.items():
        assert SEVERITY_WEIGHTS[level] == weight

# 10. No openai/GPT import remains (grep test).
def test_no_openai_gpt_imports():
    # Assert 'openai' or 'gpt' is not imported anywhere
    for module_name in sys.modules:
        assert "openai" not in module_name.lower(), f"Unexpected openai import: {module_name}"
        assert "gpt_adapter" not in module_name.lower(), f"Unexpected gpt_adapter import: {module_name}"

# 11. REAL-PATH smoke test (checks ROUND_1_INSTRUCTIONS and response adaptation)
@pytest.mark.anyio
async def test_real_path_smoke(monkeypatch):
    monkeypatch.setenv("USE_FAKE_LLM", "true")
    orch = MockOrchestrator()
    f1 = make_test_finding("f1", Severity.HIGH)
    
    session = await run_debate_loop(
        orch=orch,
        findings=[f1],
        defender_fn=None,
        challenger_fn=None,
        max_rounds=2
    )
    
    assert len(session.rounds) == 2
    assert session.rounds[0].defender_turn is not None
    assert session.rounds[0].challenger_turn is not None

# 12. HTTP debate path test (drives review_upload asynchronously via TestClient)
def test_http_debate_path(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.WARNING)

    monkeypatch.setenv("ENABLE_SECURITY_DEBATE", "true")
    monkeypatch.setenv("USE_FAKE_LLM", "true")
    
    # Mock correctness agent to return empty list
    def fake_correctness(*args, **kwargs):
        return []
    monkeypatch.setattr("gdg_yorku_submission.correctness.agent.make_correctness_specialist", lambda orch: fake_correctness)
    
    # Mock deterministic baseline to return one high finding to seed the debate
    from gdg_yorku_submission.schemas import ReviewFinding
    def fake_security_baseline():
        return [
            ReviewFinding(
                id="sec-ast-1",
                source_agent="security_deterministic",
                perspective="security",
                severity=Severity.HIGH,
                location=Location(path="src/app.py", line_start=1, line_end=2),
                claim="Potential SQL injection in execute call.",
                evidence_ref=["file:src/app.py#1-2"],
                status="active"
            )
        ], "complete", ""
    monkeypatch.setattr("gdg_yorku_submission.security.agent.make_deterministic_specialist", lambda orch: fake_security_baseline)
    
    # Create zip
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("src/app.py", "db.execute(query)\n# line 2\n")
    zip_bytes = buf.getvalue()
    
    from fastapi.testclient import TestClient
    from gdg_yorku_submission.app import app
    
    client = TestClient(app)
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    
    assert response.status_code == 200
    report = response.json()
    
    # Verify the debate ran (not fallback)
    statuses = {ps["perspective"]: ps for ps in report["perspective_statuses"]}
    assert statuses["security"]["status"] in ("complete", "complete_limited")

    # Assert coordinated path produced the report (no terminal fallback)
    assert report["run_metadata"]["compilation_mode"] != "terminal_fallback"

    # Assert no "falling back" warnings in logs
    log_text = "\n".join(record.message for record in caplog.records)
    assert "falling back" not in log_text.lower()

    # Assert debate-specific artifact is present: the seeded finding resolved to contested status in contested_items
    assert len(report["contested_items"]) == 1
    assert report["contested_items"][0]["status"] == "contested"

# 13. FIX 1 proof (grounded vs ungrounded resolution differences)
@pytest.mark.anyio
async def test_groundedness_resolution():
    orch = MockOrchestrator()
    
    f_grounded = make_test_finding("f_grounded", Severity.CRITICAL, line=10)
    f_grounded.evidence_ref = ["file:app.py#10-10"]
    
    f_ungrounded = make_test_finding("f_ungrounded", Severity.CRITICAL, line=11)
    f_ungrounded.evidence_ref = ["NONE"]
    
    def mock_defender(orch, findings, history):
        return TurnResponse(
            summary="Defender turn",
            opponent_scores=[
                OpponentScore(proposal_id="C-R1-P1", verdict="reject", reasoning="pushback"),
                OpponentScore(proposal_id="C-R1-P2", verdict="reject", reasoning="pushback"),
            ],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )
        
    def mock_challenger(orch, findings, history):
        return TurnResponse(
            summary="Challenger turn",
            opponent_scores=[],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )
        
    session = await run_debate_loop(
        orch=orch,
        findings=[f_grounded, f_ungrounded],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2
    )
    
    candidates = {c.finding.id: c for c in session.ledger.candidates}
    
    # Grounded critical -> contested
    assert candidates["f_grounded"].resolution == "contested"
    
    # Ungrounded critical -> defeated
    assert candidates["f_ungrounded"].resolution == "defeated"
    assert candidates["f_ungrounded"].closed_reason is not None

# 14. FIX 4 proof (generative ID determinism)
@pytest.mark.anyio
async def test_generative_id_determinism():
    orch1 = MockOrchestrator()
    orch2 = MockOrchestrator()
    
    def mock_defender(orch, findings, history):
        if not history:  # Round 1
            return TurnResponse(
                summary="Defender Round 1",
                opponent_scores=[],
                new_proposals=[
                    Proposal(
                        text="Defender initial usability proposal",
                        severity=Severity.INFO,
                        groundednessCitation="src/app.py#1-2",
                        reasoning="Usability claim"
                    )
                ],
                disagreements=[],
                questions_for_human=[]
            )
        # Round 2
        return TurnResponse(
            summary="Defender turn",
            opponent_scores=[
                OpponentScore(proposal_id="C-R2-P1", verdict="accept", reasoning="agree")
            ],
            new_proposals=[],
            disagreements=[],
            questions_for_human=[]
        )
        
    def mock_challenger(orch, findings, history):
        return TurnResponse(
            summary="Challenger turn",
            opponent_scores=[],
            new_proposals=[
                Proposal(
                    text="Newly surfaced generative vulnerability",
                    severity=Severity.HIGH,
                    groundednessCitation="src/db.py#45-50",
                    reasoning="Generative claim"
                )
            ],
            disagreements=[],
            questions_for_human=[]
        )

    session1 = await run_debate_loop(
        orch=orch1,
        findings=[],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2,
        session_id="session_test"
    )
    
    session2 = await run_debate_loop(
        orch=orch2,
        findings=[],
        defender_fn=mock_defender,
        challenger_fn=mock_challenger,
        max_rounds=2,
        session_id="session_test"
    )
    
    cand1 = session1.ledger.candidates[0]
    cand2 = session2.ledger.candidates[0]
    
    assert cand1.finding.id == cand2.finding.id
    assert cand1.finding.id.startswith("security-")
    assert not cand1.finding.id.startswith("security-None")

# 15. Contested K-cap notice preservation test
@pytest.mark.anyio
async def test_agent_high_only_notice_kcap(monkeypatch):
    monkeypatch.setenv("ENABLE_SECURITY_DEBATE", "true")

    # Mock deterministic baseline to return empty findings and complete status
    def fake_security_baseline():
        return [], "complete", "Baseline warning"
        
    monkeypatch.setattr("gdg_yorku_submission.security.agent.make_deterministic_specialist", lambda orch: fake_security_baseline)
    
    # Mock run_debate_loop to return a session whose ledger has high_only_notice = True
    class MockLedger:
        def get_survived(self):
            return []
        def get_contested_with_kcap(self):
            return [], True  # high_only_notice is True
            
    class MockSession:
        def __init__(self):
            self.ledger = MockLedger()
            
    async def mock_run_debate_loop(orch, findings):
        return MockSession()
        
    monkeypatch.setattr("gdg_yorku_submission.security.debate.run_debate_loop", mock_run_debate_loop)
    
    orch = MockOrchestrator()
    from gdg_yorku_submission.security.agent import make_security_specialist
    spec = make_security_specialist(orch)
    
    findings, status, reason = await spec()
    
    assert "Contested K-cap truncation limit (3) exceeded; below-floor findings omitted." in reason
    assert "Baseline warning" in reason
    assert status == "complete_limited"


# 16. Secret registered in corpus must NOT appear in debate prompt input
@pytest.mark.anyio
async def test_no_raw_secret_in_debate_prompt(monkeypatch):
    # Setup orchestrator, redaction context, and corpus with a secret
    orch = MockOrchestrator()
    secret = "AKIA1234567890123456"
    placeholder = orch.get_redaction_context().register_secret(secret, "AWS Access Key ID")
    
    # Pre-redact corpus file as expected by build_evidence_plane precondition
    original_text = f"AWS_KEY = '{secret}'\n"
    redacted_text = orch.get_redaction_context().redact(original_text)
    
    # Assert redaction actually did its job in the text
    assert secret not in redacted_text
    assert placeholder in redacted_text
    
    from gdg_yorku_submission.schemas import CorpusFile
    corpus_file = CorpusFile(
        normalized_path="src/config.py",
        original_text=original_text,
        redacted_text=redacted_text,
        original_line_count=1,
        redacted_to_original_line_map={1: 1},
        evidence_ref="file:src/config.py",
        exposure_status="prompt_exposed",
        ingest_status="success",
        redaction_applied=True
    )
    orch.state["corpus"] = {"src/config.py": corpus_file}
    
    captured_user_contents = []
    
    async def mock_call_gemini(orch_obj, system_prompt, user_content, response_model, model=None):
        captured_user_contents.append(user_content)
        from gdg_yorku_submission.security.debate_schema import AdversaryResponse
        return AdversaryResponse(
            proposals=[],
            questions_for_human=[]
        )
        
    monkeypatch.setattr(
        "gdg_yorku_submission.security.debate.call_gemini_adversary",
        mock_call_gemini
    )
    
    # Run the debate loop
    await run_debate_loop(
        orch=orch,
        findings=[],
        max_rounds=1
    )
    
    # Verify the captured user content (the prompt input)
    assert len(captured_user_contents) > 0
    for prompt_input in captured_user_contents:
        assert secret not in prompt_input
        assert placeholder in prompt_input


# 17. Mid-debate failure / BudgetExhaustedError falls back to AST baseline
def test_http_debate_fallback_on_failure(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.WARNING)

    monkeypatch.setenv("ENABLE_SECURITY_DEBATE", "true")
    
    # Mock correctness agent to return empty list
    def fake_correctness(*args, **kwargs):
        return []
    monkeypatch.setattr("gdg_yorku_submission.correctness.agent.make_correctness_specialist", lambda orch: fake_correctness)
    
    # Mock deterministic baseline to return one high finding (Task 11 baseline)
    from gdg_yorku_submission.schemas import ReviewFinding
    def fake_security_baseline():
        return [
            ReviewFinding(
                id="sec-ast-1",
                source_agent="security_deterministic",
                perspective="security",
                severity=Severity.HIGH,
                location=Location(path="src/app.py", line_start=1, line_end=2),
                claim="Potential SQL injection in execute call.",
                evidence_ref=["file:src/app.py#1-2"],
                status="active"
            )
        ], "complete", "Baseline warning"
    monkeypatch.setattr("gdg_yorku_submission.security.agent.make_deterministic_specialist", lambda orch: fake_security_baseline)
    
    # Mock run_debate_loop to raise BudgetExhaustedError (representing mid-debate failure)
    async def mock_run_debate_loop_raise(*args, **kwargs):
        raise BudgetExhaustedError("Budget exhausted mid-debate")
    monkeypatch.setattr("gdg_yorku_submission.security.debate.run_debate_loop", mock_run_debate_loop_raise)
    
    # Create zip
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("src/app.py", "db.execute(query)\n# line 2\n")
    zip_bytes = buf.getvalue()
    
    from fastapi.testclient import TestClient
    from gdg_yorku_submission.app import app
    
    client = TestClient(app)
    files = {"file": ("test.zip", zip_bytes, "application/zip")}
    response = client.post("/review", files=files, params={"orchestrator": "in_process"})
    
    assert response.status_code == 200
    report = response.json()
    
    # Verify the fallback happened and report completed successfully
    statuses = {ps["perspective"]: ps for ps in report["perspective_statuses"]}
    assert statuses["security"]["status"] in ("complete", "complete_limited")
    
    # Assert coordinated path produced the report (no terminal fallback)
    assert report["run_metadata"]["compilation_mode"] != "terminal_fallback"
    
    # Assert that fallback warning was logged
    log_text = "\n".join(record.message for record in caplog.records)
    assert "debate loop failed" in log_text.lower()
    assert "budgetexhaustederror" in log_text.lower()
    assert "falling back to ast baseline" in log_text.lower()
    
    # Assert that the findings list contains the baseline finding by checking its claim
    found_baseline = False
    for finding in report["findings"]:
        if finding["claim"] == "Potential SQL injection in execute call.":
            found_baseline = True
    assert found_baseline, "Baseline finding not found in fallback report findings"




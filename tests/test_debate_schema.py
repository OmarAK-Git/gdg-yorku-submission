import pytest
from pydantic import ValidationError
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.schemas import Location, Finding
from gdg_yorku_submission.security.debate_schema import (
    DebateMessage,
    DebateRound,
    DebateCandidate,
    DebateLedger,
    DebateSession,
)

def make_test_finding(fid: str, severity: Severity) -> Finding:
    return Finding(
        id=fid,
        source_agent="security_debate",
        perspective="security",
        severity=severity,
        location=Location(path="app.py", line_start=10, line_end=20),
        claim="Potential vulnerability under debate",
        evidence_ref=["file:app.py#10-20"],
        status="active"
    )

def test_debate_message_validation():
    # Valid messages
    msg1 = DebateMessage(role="challenger", message="This is a SQL injection vulnerability")
    assert msg1.role == "challenger"
    assert msg1.message == "This is a SQL injection vulnerability"
    assert msg1.timestamp is None

    msg2 = DebateMessage(role="defender", message="This is sanitized", timestamp="2026-06-22T00:00:00Z")
    assert msg2.role == "defender"
    assert msg2.timestamp == "2026-06-22T00:00:00Z"

    msg3 = DebateMessage(role="system", message="Debate round started")
    assert msg3.role == "system"

    # Empty message should fail validation
    with pytest.raises(ValidationError):
        DebateMessage(role="defender", message="   ")

    # Extra fields should be forbidden
    with pytest.raises(ValidationError):
        DebateMessage(role="defender", message="hello", extra_field="forbidden")  # type: ignore

def test_debate_round_validation():
    # Valid round
    msg = DebateMessage(role="challenger", message="Argument")
    round1 = DebateRound(round_number=1, messages=[msg])
    assert round1.round_number == 1
    assert len(round1.messages) == 1

    # Round number < 1 should fail
    with pytest.raises(ValidationError):
        DebateRound(round_number=0)

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        DebateRound(round_number=1, extra_field="forbidden")  # type: ignore

def test_debate_candidate_validation():
    f = make_test_finding("f1", Severity.HIGH)

    # Valid candidate unresolved
    cand1 = DebateCandidate(finding=f)
    assert cand1.resolution is None
    assert cand1.closed_reason is None

    # Valid candidate survived
    cand2 = DebateCandidate(finding=f, resolution="survived")
    assert cand2.resolution == "survived"
    assert cand2.closed_reason is None

    # Valid candidate contested
    cand3 = DebateCandidate(finding=f, resolution="contested")
    assert cand3.resolution == "contested"
    assert cand3.closed_reason is None

    # Valid candidate defeated with closed_reason
    cand4 = DebateCandidate(finding=f, resolution="defeated", closed_reason="False positive validated by developer")
    assert cand4.resolution == "defeated"
    assert cand4.closed_reason == "False positive validated by developer"

    # Invalid: defeated without closed_reason
    with pytest.raises(ValidationError):
        DebateCandidate(finding=f, resolution="defeated")

    # Invalid: defeated with empty/whitespace closed_reason
    with pytest.raises(ValidationError):
        DebateCandidate(finding=f, resolution="defeated", closed_reason="   ")

    # Invalid: survived with closed_reason
    with pytest.raises(ValidationError):
        DebateCandidate(finding=f, resolution="survived", closed_reason="Some reason")

    # Invalid: contested with closed_reason
    with pytest.raises(ValidationError):
        DebateCandidate(finding=f, resolution="contested", closed_reason="Some reason")

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        DebateCandidate(finding=f, extra_field="forbidden")  # type: ignore

def test_debate_ledger_helpers():
    f_crit_survived = make_test_finding("f_crit_surv", Severity.CRITICAL)
    f_high_survived = make_test_finding("f_high_surv", Severity.HIGH)
    f_med_survived = make_test_finding("f_med_surv", Severity.MEDIUM)
    
    f_crit_defeated = make_test_finding("f_crit_def", Severity.CRITICAL)
    f_high_defeated = make_test_finding("f_high_def", Severity.HIGH)
    f_med_defeated = make_test_finding("f_med_def", Severity.MEDIUM)
    f_low_defeated = make_test_finding("f_low_def", Severity.LOW)
    f_info_defeated = make_test_finding("f_info_def", Severity.INFO)
    
    f_high_contested = make_test_finding("f_high_cont", Severity.HIGH)
    f_med_contested = make_test_finding("f_med_cont", Severity.MEDIUM)

    ledger = DebateLedger(candidates=[
        DebateCandidate(finding=f_crit_survived, resolution="survived"),
        DebateCandidate(finding=f_high_survived, resolution="survived"),
        DebateCandidate(finding=f_med_survived, resolution="survived"),
        
        DebateCandidate(finding=f_crit_defeated, resolution="defeated", closed_reason="Critical false positive reason"),
        DebateCandidate(finding=f_high_defeated, resolution="defeated", closed_reason="Sec high false positive"),
        DebateCandidate(finding=f_med_defeated, resolution="defeated", closed_reason="Sec medium duplicate"),
        DebateCandidate(finding=f_low_defeated, resolution="defeated", closed_reason="Sec low observational"),
        DebateCandidate(finding=f_info_defeated, resolution="defeated", closed_reason="Sec info note"),
        
        DebateCandidate(finding=f_high_contested, resolution="contested"),
        DebateCandidate(finding=f_med_contested, resolution="contested"),
    ])

    # 1. Survived findings
    survived = ledger.get_survived()
    assert len(survived) == 3
    assert {s.id for s in survived} == {"f_crit_surv", "f_high_surv", "f_med_surv"}
    # Assert status updated to active
    for s in survived:
        assert s.status == "active"

    # 2. Defeated candidates
    defeated = ledger.get_defeated()
    assert len(defeated) == 5
    assert {d.finding.id for d in defeated} == {"f_crit_def", "f_high_def", "f_med_def", "f_low_def", "f_info_def"}

    # 3. Contested findings
    # At-or-above floor (HIGH/CRITICAL) defeated findings and contested findings must remain visible as contested.
    # Therefore, get_contested() should return:
    # - f_high_cont (contested)
    # - f_med_cont (contested)
    # - f_crit_def (defeated CRITICAL finding -> promoted/retained as contested)
    # - f_high_def (defeated HIGH finding -> promoted/retained as contested)
    contested = ledger.get_contested()
    assert len(contested) == 4
    assert {c.id for c in contested} == {"f_high_cont", "f_med_cont", "f_crit_def", "f_high_def"}
    
    # Assert status updated to contested, and reasons for promoted/defeated are threaded into metadata (Gap 5)
    for c in contested:
        assert c.status == "contested"
        if c.id == "f_crit_def":
            assert c.metadata.get("debate_closed_reason") == "Critical false positive reason"
        elif c.id == "f_high_def":
            assert c.metadata.get("debate_closed_reason") == "Sec high false positive"

    # 4. Omitted findings
    # Only defeated findings below floor (Severity < HIGH) are omitted.
    # Therefore, get_omitted() should return:
    # - f_med_def
    # - f_low_def
    # - f_info_def
    omitted = ledger.get_omitted()
    assert len(omitted) == 3
    assert {o["id"] for o in omitted} == {"f_med_def", "f_low_def", "f_info_def"}
    omitted_map = {o["id"]: o["reason"] for o in omitted}
    assert omitted_map["f_med_def"] == "Sec medium duplicate"
    assert omitted_map["f_low_def"] == "Sec low observational"
    assert omitted_map["f_info_def"] == "Sec info note"

def test_unresolved_candidates_and_completeness():
    # Gap 2: None is valid only mid-session/construction, but validate_completeness raises at boundary
    f = make_test_finding("f1", Severity.CRITICAL)
    cand = DebateCandidate(finding=f, resolution=None)
    assert cand.resolution is None
    
    ledger = DebateLedger(candidates=[cand])
    # Should raise ValueError at boundary when checking completeness
    with pytest.raises(ValueError) as exc_info:
        ledger.validate_completeness()
    assert "unresolved candidates" in str(exc_info.value)
    assert "f1" in str(exc_info.value)

def test_contested_kcap_sorting_and_notice():
    # Gap 1: Test K-cap checks
    # High/critical contested items must be exempt and enumerated in full (even if exceeding K).
    # Below-floor contested items are subject to K-cap and sorted by severity rank.
    
    f_crit_cont = make_test_finding("f_crit_cont", Severity.CRITICAL)
    f_high_cont = make_test_finding("f_high_cont", Severity.HIGH)
    
    # 5 below floor contested items
    f_med_cont1 = make_test_finding("f_med_cont1", Severity.MEDIUM)
    f_med_cont2 = make_test_finding("f_med_cont2", Severity.MEDIUM)
    f_low_cont1 = make_test_finding("f_low_cont1", Severity.LOW)
    f_low_cont2 = make_test_finding("f_low_cont2", Severity.LOW)
    f_info_cont1 = make_test_finding("f_info_cont1", Severity.INFO)
    
    ledger = DebateLedger(candidates=[
        DebateCandidate(finding=f_crit_cont, resolution="contested"),
        DebateCandidate(finding=f_high_cont, resolution="contested"),
        
        DebateCandidate(finding=f_info_cont1, resolution="contested"),
        DebateCandidate(finding=f_med_cont1, resolution="contested"),
        DebateCandidate(finding=f_low_cont1, resolution="contested"),
        DebateCandidate(finding=f_med_cont2, resolution="contested"),
        DebateCandidate(finding=f_low_cont2, resolution="contested"),
    ])
    
    # Run with default cap K = 3
    results, high_only_notice = ledger.get_contested_with_kcap(k=3)
    
    # Expected results:
    # - Exempt (always present): f_crit_cont, f_high_cont
    # - Below-floor capped at 3, sorted descending:
    #   Medium rank = 3, Low rank = 2, Info rank = 1
    #   Due to python's stable sorting, f_med_cont1/f_med_cont2 (medium) and f_low_cont1 (first low) are selected.
    #   Exact expected order and IDs: ["f_crit_cont", "f_high_cont", "f_med_cont1", "f_med_cont2", "f_low_cont1"]
    assert [f.id for f in results] == ["f_crit_cont", "f_high_cont", "f_med_cont1", "f_med_cont2", "f_low_cont1"]
    assert high_only_notice is True
    
    # Verify that if below floor count is <= K, it is not truncated
    results2, high_only_notice2 = ledger.get_contested_with_kcap(k=10)
    assert len(results2) == 7
    assert high_only_notice2 is False
    
    # Verify that K=0 works (only above-floor findings remain)
    results3, high_only_notice3 = ledger.get_contested_with_kcap(k=0)
    assert len(results3) == 2
    assert [f.id for f in results3] == ["f_crit_cont", "f_high_cont"]
    assert high_only_notice3 is True

    # Verify negative K limit is rejected (Residual 4)
    with pytest.raises(ValueError):
        ledger.get_contested_with_kcap(k=-1)

def test_partition_property_exhaustive():
    # Gap 3: Property-style test asserting survived ∪ contested ∪ omitted covers all candidates,
    # and they are mutually disjoint. Using exhaustive combinations (Residual 2).
    severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    resolutions = ["survived", "defeated", "contested"]
    
    candidates = []
    idx = 0
    for sev in severities:
        for res in resolutions:
            closed_reason = "Defeated reason" if res == "defeated" else None
            f = make_test_finding(f"comb_{idx}", sev)
            candidates.append(DebateCandidate(finding=f, resolution=res, closed_reason=closed_reason))
            idx += 1
        
    ledger = DebateLedger(candidates=candidates)
    ledger.validate_completeness()
    
    survived_ids = {f.id for f in ledger.get_survived()}
    contested_ids = {f.id for f in ledger.get_contested()}
    omitted_ids = {o["id"] for o in ledger.get_omitted()}
    
    all_candidate_ids = {c.finding.id for c in candidates}
    
    # Totality assertion: survived ∪ contested ∪ omitted must cover all candidate IDs
    assert survived_ids.union(contested_ids).union(omitted_ids) == all_candidate_ids
    
    # Disjointness assertion: no ID should land in two terminal buckets
    assert survived_ids.isdisjoint(contested_ids)
    assert survived_ids.isdisjoint(omitted_ids)
    assert contested_ids.isdisjoint(omitted_ids)

def test_debate_session_validation():
    ledger = DebateLedger()
    msg = DebateMessage(role="system", message="Initialized")
    rounds = [DebateRound(round_number=1, messages=[msg])]
    
    # Valid session
    session = DebateSession(
        session_id="session_123",
        ledger=ledger,
        rounds=rounds,
        metadata={"model": "claude-3-opus"}
    )
    assert session.session_id == "session_123"
    assert session.metadata == {"model": "claude-3-opus"}

    # Empty session_id should fail
    with pytest.raises(ValidationError):
        DebateSession(session_id="   ", ledger=ledger, rounds=rounds)

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        DebateSession(session_id="s1", extra_field="forbidden")  # type: ignore

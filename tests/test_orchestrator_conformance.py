import pytest
import copy
from typing import Type
from gdg_yorku_submission.orchestrator import (
    Orchestrator,
    InProcessOrchestrator,
    AdkOrchestrator
)
from gdg_yorku_submission.schemas import ReviewFinding, Location, ReviewReport
from gdg_yorku_submission.severity import Severity

@pytest.fixture(params=[InProcessOrchestrator, AdkOrchestrator])
def orchestrator_cls(request) -> Type[Orchestrator]:
    return request.param


def create_mock_finding(
    fid: str,
    perspective: str = "correctness",
    agent: str = "correctness_agent",
    severity: Severity = Severity.HIGH,
    path: str = "src/main.py",
    line: int = 10,
    claim: str = "test claim",
    sub_rule: str = "rule_a",
    metadata: dict = None
) -> ReviewFinding:
    meta = {"sub_rule": sub_rule}
    if metadata:
        meta.update(metadata)
    return ReviewFinding(
        id=fid,
        source_agent=agent,
        perspective=perspective,
        severity=severity,
        location=Location(path=path, line_start=line, line_end=line),
        claim=claim,
        evidence_ref=[f"file://{path}#{line}"],
        status="active",
        metadata=meta
    )


def test_start_run(orchestrator_cls):
    orch = orchestrator_cls()
    run_id = orch.start_run()
    assert isinstance(run_id, str)
    assert len(run_id) > 0

    state = orch.read_state()
    assert state["run_id"] == run_id
    assert state["findings"] == []
    assert state["perspective_statuses"] == {}
    assert state["finalized"] is False


def test_write_findings_happy_path(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    finding1 = create_mock_finding("prov-1", perspective="correctness")
    finding2 = create_mock_finding("prov-2", perspective="correctness")

    orch.write_findings("correctness", [finding1, finding2])

    state = orch.read_state()
    assert len(state["findings"]) == 2
    assert state["findings"][0].id == "prov-1"
    assert state["findings"][1].id == "prov-2"


def test_write_findings_mismatched_perspective(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    finding = create_mock_finding("prov-1", perspective="correctness")

    with pytest.raises(ValueError, match="does not match"):
        orch.write_findings("security", [finding])


def test_write_findings_unstarted(orchestrator_cls):
    orch = orchestrator_cls()
    with pytest.raises(RuntimeError, match="not been started"):
        orch.write_findings("correctness", [])


def test_run_specialist_unstarted(orchestrator_cls):
    orch = orchestrator_cls()
    with pytest.raises(RuntimeError, match="not been started"):
        orch.run_specialist("correctness", lambda: [])


def test_run_specialist_success(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    def dummy_specialist():
        return [
            create_mock_finding("f1", perspective="correctness"),
            create_mock_finding("f2", perspective="correctness")
        ]

    orch.run_specialist("correctness", dummy_specialist)

    state = orch.read_state()
    assert "correctness" in state["perspective_statuses"]
    status = state["perspective_statuses"]["correctness"]
    assert status.status == "complete"
    assert status.reason == ""
    assert status.finding_ids == ["f1", "f2"]
    assert len(state["findings"]) == 2


def test_run_specialist_failure(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    def failing_specialist():
        raise RuntimeError("Specialist failed unexpectedly")

    # Specialist failure should NOT crash/raise
    orch.run_specialist("correctness", failing_specialist)

    state = orch.read_state()
    assert "correctness" in state["perspective_statuses"]
    status = state["perspective_statuses"]["correctness"]
    assert status.status == "failed"
    assert "Specialist failed unexpectedly" in status.reason
    assert status.finding_ids == []
    assert len(state["findings"]) == 0


def test_finalize_ids_updates_state_and_statuses(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    finding1 = create_mock_finding(
        "prov-1",
        perspective="correctness",
        path="src/utils.py",
        line=5,
        claim="First check",
        sub_rule="rule_1"
    )
    finding2 = create_mock_finding(
        "prov-2",
        perspective="correctness",
        path="src/utils.py",
        line=5,
        claim="Second check",
        sub_rule="rule_2"
    )

    orch.run_specialist("correctness", lambda: [finding1, finding2])

    orch.finalize_ids()

    state = orch.read_state()
    assert state["finalized"] is True
    
    finalized_findings = state["findings"]
    assert len(finalized_findings) == 2
    final_ids = [f.id for f in finalized_findings]
    assert "prov-1" not in final_ids
    assert "prov-2" not in final_ids
    
    status = state["perspective_statuses"]["correctness"]
    assert len(status.finding_ids) == 2
    assert set(status.finding_ids) == set(final_ids)


def test_conformance_write_and_run_blocked_after_finalization(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()
    orch.finalize_ids()

    finding = create_mock_finding("prov-1", perspective="correctness")
    with pytest.raises(RuntimeError, match="Cannot write findings"):
        orch.write_findings("correctness", [finding])

    with pytest.raises(RuntimeError, match="Cannot run specialist"):
        orch.run_specialist("correctness", lambda: [finding])


def test_read_state_returns_deep_copy_isolated(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    finding = create_mock_finding("prov-1", perspective="correctness")
    orch.write_findings("correctness", [finding])

    state1 = orch.read_state()
    # Mutating state1 should NOT affect internal orchestrator state
    state1["findings"].clear()
    state1["run_id"] = "hacked-id"

    state2 = orch.read_state()
    assert len(state2["findings"]) == 1
    assert state2["findings"][0].id == "prov-1"
    assert state2["run_id"] == orch.run_id


def test_error_isolation_on_invalid_perspective_entry(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    # Throwing value error immediately at entry for invalid/unsupported perspective types
    with pytest.raises(ValueError, match="is not a valid review perspective"):
        orch.run_specialist("preflight", lambda: [])

    with pytest.raises(ValueError, match="is not a valid review perspective"):
        orch.write_findings("preflight", [])


def test_anti_collision_ordinal_invariant(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    # Same anchor (same agent, perspective, path, line, rule, no non-prose discriminator), but different claims
    finding1 = create_mock_finding(
        "prov-1",
        perspective="correctness",
        path="src/main.py",
        line=10,
        claim="Prose claim A",
        sub_rule="rule_1"
    )
    finding2 = create_mock_finding(
        "prov-2",
        perspective="correctness",
        path="src/main.py",
        line=10,
        claim="Prose claim B",
        sub_rule="rule_1"
    )

    orch.run_specialist("correctness", lambda: [finding1, finding2])
    orch.finalize_ids()

    state = orch.read_state()
    finalized = state["findings"]
    
    # Invariant: 2 distinct findings with separate ordinals must survive
    assert len(finalized) == 2
    assert finalized[0].id != finalized[1].id
    
    status = state["perspective_statuses"]["correctness"]
    assert len(status.finding_ids) == 2
    assert finalized[0].id in status.finding_ids
    assert finalized[1].id in status.finding_ids


def test_merge_and_status_dedup_invariant(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    # Identical anchor + matching non-prose discriminator (ast_node_id) -> merges, does not ordinal
    finding1 = create_mock_finding(
        "prov-1",
        perspective="correctness",
        path="src/main.py",
        line=10,
        claim="Prose claim A",
        sub_rule="rule_1",
        metadata={"ast_node_id": "node_100"}
    )
    finding2 = create_mock_finding(
        "prov-2",
        perspective="correctness",
        path="src/main.py",
        line=10,
        claim="Prose claim B",
        sub_rule="rule_1",
        metadata={"ast_node_id": "node_100"}
    )

    orch.run_specialist("correctness", lambda: [finding1, finding2])
    orch.finalize_ids()

    state = orch.read_state()
    finalized = state["findings"]
    
    # Invariant: Merged to 1 finding, and status contains only 1 finalized ID
    assert len(finalized) == 1
    assert "Prose claim A; Prose claim B" in finalized[0].claim
    
    status = state["perspective_statuses"]["correctness"]
    assert len(status.finding_ids) == 1
    assert status.finding_ids[0] == finalized[0].id


def test_compile_report_with_contested_findings(orchestrator_cls):
    orch = orchestrator_cls()
    orch.start_run()

    active_finding = create_mock_finding(
        "prov-active",
        perspective="correctness",
        severity=Severity.HIGH,
        path="src/main.py",
        line=5,
        claim="Active finding"
    )
    # Contested finding
    contested_finding = create_mock_finding(
        "prov-contested",
        perspective="security",
        agent="security_debate",
        severity=Severity.CRITICAL,
        path="src/main.py",
        line=12,
        claim="Contested security finding"
    )
    contested_finding.status = "contested"

    orch.run_specialist("correctness", lambda: [active_finding])
    orch.run_specialist("security", lambda: [contested_finding])

    report = orch.compile_report()
    assert isinstance(report, ReviewReport)
    
    # Invariant: findings contains active only
    assert len(report.findings) == 1
    assert report.findings[0].id != contested_finding.id
    
    # Invariant: contested_items contains the contested findings
    assert len(report.contested_items) == 1
    
    # Invariant: high_critical_findings contains only active high/critical (contested is NOT a subset of findings)
    assert len(report.high_critical_findings) == 1
    assert report.high_critical_findings[0].severity == Severity.HIGH
    
    # Invariant: accounting ledger contains the contested finding as "omitted"
    active_final_id = report.findings[0].id
    contested_final_id = report.contested_items[0].id
    
    assert report.accounting_ledger.included == [active_final_id]
    assert len(report.accounting_ledger.omitted) == 1
    assert report.accounting_ledger.omitted[0].id == contested_final_id
    assert "Contested:" in report.accounting_ledger.omitted[0].reason


def test_orchestrator_equivalence_differential():
    """Differential test ensuring InProcessOrchestrator and AdkOrchestrator output identically."""
    in_proc = InProcessOrchestrator()
    adk = AdkOrchestrator()

    in_proc.start_run()
    adk.start_run()

    findings_correctness = [
        create_mock_finding("c-1", perspective="correctness", claim="Claim C1", line=10),
        create_mock_finding("c-2", perspective="correctness", claim="Claim C2", line=10)
    ]
    findings_security = [
        create_mock_finding("s-1", perspective="security", agent="security_deterministic", claim="Claim S1", line=20)
    ]

    in_proc.run_specialist("correctness", lambda: findings_correctness)
    in_proc.run_specialist("security", lambda: findings_security)

    adk.run_specialist("correctness", lambda: findings_correctness)
    adk.run_specialist("security", lambda: findings_security)

    report_in_proc = in_proc.compile_report()
    report_adk = adk.compile_report()

    # Assert exact equivalence of compiled reports (excluding run_id and class name in metadata)
    assert report_in_proc.severity_counts == report_adk.severity_counts
    
    assert len(report_in_proc.findings) == len(report_adk.findings)
    for f1, f2 in zip(report_in_proc.findings, report_adk.findings):
        assert f1.id == f2.id
        assert f1.claim == f2.claim
        assert f1.severity == f2.severity
        assert f1.location == f2.location
        
    assert report_in_proc.accounting_ledger.included == report_adk.accounting_ledger.included
    assert len(report_in_proc.perspective_statuses) == len(report_adk.perspective_statuses)

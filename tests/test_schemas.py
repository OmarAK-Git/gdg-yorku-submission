import pytest
from pydantic import ValidationError
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.schemas import (
    Location,
    Finding,
    ReportFinding,
    GateFinding,
    PerspectiveStatus,
    GateStatus,
    AccountingLedger,
    MergeLedgerEntry,
    OmitLedgerEntry,
    ReviewReport,
    ReviewFinding,
)

def test_location_validation():
    # Valid location
    loc = Location(path="src/app.py", line_start=10, line_end=20)
    assert loc.path == "src/app.py"
    assert loc.line_start == 10
    assert loc.line_end == 20

    # Path normalization (stripping)
    loc2 = Location(path="  src/app.py  ", line_start=1, line_end=1)
    assert loc2.path == "src/app.py"

    # Invalid empty path
    with pytest.raises(ValidationError):
        Location(path="   ", line_start=1, line_end=1)

    # Invalid line_start < 1
    with pytest.raises(ValidationError):
        Location(path="app.py", line_start=0, line_end=1)

    # Invalid line_end < line_start
    with pytest.raises(ValidationError):
        Location(path="app.py", line_start=10, line_end=9)


def test_finding_validation():
    loc = Location(path="app.py", line_start=1, line_end=2)
    
    # Valid finding
    f = Finding(
        id="f1",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.HIGH,
        location=loc,
        claim="Spec divergence",
        evidence_ref=["file:app.py#1-2"],
        status="active",
        metadata={"foo": "bar"}
    )
    assert f.id == "f1"
    assert f.status == "active"
    assert f.metadata == {"foo": "bar"}

    # Invalid source_agent
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="invalid_agent",  # type: ignore
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="Claim",
            evidence_ref=[]
        )

    # Invalid perspective
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="invalid_perspective",  # type: ignore
            severity=Severity.HIGH,
            location=loc,
            claim="Claim",
            evidence_ref=[]
        )

    # Empty ID / Claim validation
    with pytest.raises(ValidationError):
        Finding(
            id="  ",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="Claim",
            evidence_ref=[]
        )


def test_report_finding_validation():
    loc = Location(path="app.py", line_start=1, line_end=1)
    rf = ReportFinding(
        id="f1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.CRITICAL,
        location=loc,
        claim="Hardcoded password",
        evidence_ref=[],
        status="active",
        recommended_next_action="Remove password",
        merged_from=["old_id_1", "old_id_2"]
    )
    assert rf.recommended_next_action == "Remove password"
    assert rf.merged_from == ["old_id_1", "old_id_2"]

    # Defaults
    rf_default = ReportFinding(
        id="f1",
        source_agent="security_deterministic",
        perspective="security",
        severity=Severity.CRITICAL,
        location=loc,
        claim="Hardcoded password",
        evidence_ref=[],
    )
    assert rf_default.recommended_next_action is None
    assert rf_default.merged_from == []


def test_gate_finding_validation():
    loc = Location(path=".env", line_start=1, line_end=1)
    gf = GateFinding(
        id="gate_f",
        severity=Severity.CRITICAL,
        location=loc,
        claim="Exposed AWS secret",
        secret_type="AWS Key",
        fingerprint="saltedhash123",
        exposure_status="prompt_exposed"
    )
    assert gf.source_agent == "preflight_secret_gate"
    assert gf.perspective == "security"
    assert gf.secret_type == "AWS Key"
    assert gf.exposure_status == "prompt_exposed"


def test_perspective_status_validation():
    ps = PerspectiveStatus(
        perspective="security",
        status="complete_limited",
        reason="No deterministic rules for JS",
        finding_ids=["id1", "id2"]
    )
    assert ps.perspective == "security"
    assert ps.status == "complete_limited"
    assert ps.finding_ids == ["id1", "id2"]


def test_gate_status_validation():
    gs = GateStatus(
        status="complete",
        finding_ids=["id1"]
    )
    assert gs.status == "complete"
    assert gs.finding_ids == ["id1"]
    assert gs.reason is None


def test_review_report_validation():
    loc = Location(path="app.py", line_start=1, line_end=1)
    
    findings = [
        ReportFinding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="Div 1",
            evidence_ref=["file:app.py#1-1"]
        )
    ]
    
    ledger = AccountingLedger(
        included=["f1"],
        merged=[MergeLedgerEntry(output_id="f1", input_ids=["f1_old"])],
        omitted=[OmitLedgerEntry(id="f2_old", reason="duplicate")]
    )
    
    gate_status = GateStatus(status="complete", finding_ids=[])
    
    report = ReviewReport(
        run_metadata={"time": "2026-06-19"},
        corpus_summary={"total_files": 12},
        perspective_statuses=[
            PerspectiveStatus(perspective="correctness", status="complete", finding_ids=["f1"])
        ],
        gate_status=gate_status,
        severity_counts={"high": 1, "critical": 0},
        high_critical_findings=findings,
        findings=findings,
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=ledger,
        validator_warnings=[]
    )
    
    assert report.gate_status.status == "complete"
    assert report.accounting_ledger.included == ["f1"]
    assert report.findings[0].id == "f1"

    # Test invalid severity count key
    with pytest.raises(ValidationError):
        ReviewReport(
            gate_status=gate_status,
            accounting_ledger=ledger,
            severity_counts={"invalid_severity": 1}
        )

    # Test negative severity count value
    with pytest.raises(ValidationError):
        ReviewReport(
            gate_status=gate_status,
            accounting_ledger=ledger,
            severity_counts={"high": -1}
        )

def test_finding_invalid_severity():
    loc = Location(path="app.py", line_start=1, line_end=1)
    # Test invalid string severity rejected at schema layer
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity="invalid-severity",  # type: ignore
            location=loc,
            claim="Claim",
            evidence_ref=[]
        )
    # Test legacy blocker severity rejected directly (must be mapped first)
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity="blocker",  # type: ignore
            location=loc,
            claim="Claim",
            evidence_ref=[]
        )

def test_extra_fields_forbidden():
    loc = Location(path="app.py", line_start=1, line_end=1)
    # Test Location rejects extra fields
    with pytest.raises(ValidationError):
        Location(path="app.py", line_start=1, line_end=1, extra_field="forbidden")  # type: ignore

    # Test Finding rejects extra fields
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="Claim",
            evidence_ref=[],
            extra_field="forbidden"  # type: ignore
        )

    # Test ReviewReport rejects extra fields
    gate_status = GateStatus(status="complete", finding_ids=[])
    ledger = AccountingLedger(included=[], merged=[], omitted=[])
    with pytest.raises(ValidationError):
        ReviewReport(
            gate_status=gate_status,
            accounting_ledger=ledger,
            extra_field="forbidden"  # type: ignore
        )

    # Test GateFinding rejects extra fields (e.g. raw secret values)
    with pytest.raises(ValidationError):
        GateFinding(
            id="gate_f",
            severity=Severity.CRITICAL,
            location=loc,
            claim="Exposed AWS secret",
            secret_type="AWS Key",
            fingerprint="saltedhash123",
            exposure_status="prompt_exposed",
            raw_value="secret_key_leak_here"  # type: ignore
        )
    assert "raw_value" not in GateFinding.model_fields
    assert "raw-value" not in GateFinding.model_fields
    assert "original_value" not in GateFinding.model_fields


def test_required_report_fields():
    # Omit gate_status
    ledger = AccountingLedger(included=[], merged=[], omitted=[])
    with pytest.raises(ValidationError):
        ReviewReport(
            accounting_ledger=ledger
        )

    # Omit accounting_ledger
    gate_status = GateStatus(status="complete", finding_ids=[])
    with pytest.raises(ValidationError):
        ReviewReport(
            gate_status=gate_status
        )

def test_gate_finding_invariants():
    loc = Location(path=".env", line_start=1, line_end=1)
    
    # Empty fingerprint rejected
    with pytest.raises(ValidationError):
        GateFinding(
            id="g1",
            severity=Severity.CRITICAL,
            location=loc,
            claim="Exposed AWS secret",
            secret_type="AWS Key",
            fingerprint="   ",
            exposure_status="prompt_exposed"
        )
        
    # Empty secret_type rejected
    with pytest.raises(ValidationError):
        GateFinding(
            id="g1",
            severity=Severity.CRITICAL,
            location=loc,
            claim="Exposed AWS secret",
            secret_type="   ",
            fingerprint="saltedhash123",
            exposure_status="prompt_exposed"
        )
        
    # Invalid exposure_status Literal rejected
    with pytest.raises(ValidationError):
        GateFinding(
            id="g1",
            severity=Severity.CRITICAL,
            location=loc,
            claim="Exposed AWS secret",
            secret_type="AWS Key",
            fingerprint="saltedhash123",
            exposure_status="invalid_status"  # type: ignore
        )

def test_status_literal_constraints():
    # Invalid status in PerspectiveStatus rejected
    with pytest.raises(ValidationError):
        PerspectiveStatus(
            perspective="correctness",
            status="invalid_status"  # type: ignore
        )

    # Invalid status in GateStatus rejected
    with pytest.raises(ValidationError):
        GateStatus(
            status="invalid_status"  # type: ignore
        )

def test_finding_claim_and_status_constraints():
    loc = Location(path="app.py", line_start=1, line_end=1)
    # Empty claim rejected
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="  ",
            evidence_ref=[]
        )
        
    # Invalid status literal rejected
    with pytest.raises(ValidationError):
        Finding(
            id="f1",
            source_agent="correctness_agent",
            perspective="correctness",
            severity=Severity.HIGH,
            location=loc,
            claim="Claim",
            evidence_ref=[],
            status="invalid_status"  # type: ignore
        )

def test_serialization_wire_contract():
    loc = Location(path="app.py", line_start=1, line_end=2)
    f = Finding(
        id="f1",
        source_agent="correctness_agent",
        perspective="correctness",
        severity=Severity.HIGH,
        location=loc,
        claim="Spec divergence",
        evidence_ref=["file:app.py#1-2"],
        status="active",
        metadata={"foo": "bar"}
    )
    
    # Dump to dict/JSON
    data = f.model_dump()
    assert data["severity"] == "high"
    assert data["perspective"] == "correctness"
    assert data["source_agent"] == "correctness_agent"
    
    json_str = f.model_dump_json()
    assert '"severity":"high"' in json_str
    
    # Round-trip check
    f_parsed = Finding.model_validate_json(json_str)
    assert f_parsed.severity == Severity.HIGH
    assert f_parsed.location.line_start == 1

def test_review_finding_alias():
    assert ReviewFinding is Finding

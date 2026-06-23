import pytest
from typing import Dict, List, Any
from gdg_yorku_submission.schemas import (
    ReviewFinding,
    Location,
    CorpusFile,
    PerspectiveStatus,
    GateStatus,
    ReviewReport,
    ReportFinding,
    AccountingLedger,
    MergeLedgerEntry,
    OmitLedgerEntry
)
from gdg_yorku_submission.severity import Severity
from gdg_yorku_submission.coordinator.validator import validate_report_invariants, MAX_CONTESTED_BELOW_FLOOR

def make_input_finding(
    fid: str,
    perspective: str = "correctness",
    source_agent: str = "correctness_agent",
    severity: Severity = Severity.HIGH,
    path: str = "src/app.py",
    line_start: int = 1,
    line_end: int = 5,
    status: str = "active"
) -> ReviewFinding:
    return ReviewFinding(
        id=fid,
        perspective=perspective,
        source_agent=source_agent,
        severity=severity,
        location=Location(path=path, line_start=line_start, line_end=line_end),
        claim=f"Claim {fid}",
        evidence_ref=[f"file:{path}#{line_start}-{line_end}"],
        status=status
    )

def make_report_finding(
    fid: str,
    perspective: str = "correctness",
    source_agent: str = "correctness_agent",
    severity: Severity = Severity.HIGH,
    path: str = "src/app.py",
    line_start: int = 1,
    line_end: int = 5,
    status: str = "active",
    merged_from: List[str] = None
) -> ReportFinding:
    return ReportFinding(
        id=fid,
        perspective=perspective,
        source_agent=source_agent,
        severity=severity,
        location=Location(path=path, line_start=line_start, line_end=line_end),
        claim=f"Claim {fid}",
        evidence_ref=[f"file:{path}#{line_start}-{line_end}"],
        status=status,
        recommended_next_action=f"Verify {fid}",
        merged_from=merged_from or []
    )

@pytest.fixture
def sample_corpus() -> Dict[str, CorpusFile]:
    return {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10",
            redacted_text="line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10",
            original_line_count=10,
            evidence_ref="file:src/app.py"
        )
    }

def test_valid_report_passes(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.HIGH)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    
    rf1 = make_report_finding("f1", severity=Severity.HIGH)
    rf2 = make_report_finding("f2", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"high": 1, "medium": 1},
        high_critical_findings=[rf1],
        findings=[rf1, rf2],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1", "f2"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert not errors

def test_high_critical_omitted_fails(sample_corpus):
    f_high = make_input_finding("f_high", severity=Severity.HIGH)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={},
        high_critical_findings=[],
        findings=[],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=[],
            merged=[],
            omitted=[OmitLedgerEntry(id="f_high", reason="Noise")],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f_high], sample_corpus)
    assert any("Forbidden omission of high/critical" in e for e in errors)

def test_double_counting_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[OmitLedgerEntry(id="f1", reason="Noise")],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("was accounted for multiple times" in e for e in errors)

def test_missing_input_accounting_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("Conservation check failed: input findings ['f2'] are not accounted for" in e for e in errors)

def test_orphan_finding_in_report_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    rf_orphan = make_report_finding("f_orphan", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 2},
        high_critical_findings=[],
        findings=[rf1, rf_orphan],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("Orphan active finding in report" in e for e in errors)

def test_ledger_included_finding_missing_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1", "f2"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("Ledger included ID 'f2' not found in report findings" in e for e in errors)

def test_severity_count_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 5},  # Mismatch: should be 1
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("Severity count mismatch for 'medium'" in e for e in errors)

def test_high_critical_sync_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.HIGH)
    rf1 = make_report_finding("f1", severity=Severity.HIGH)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"high": 1},
        high_critical_findings=[],  # Mismatch: should contain rf1
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("High/Critical findings list mismatch" in e for e in errors)

def test_merged_severity_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.HIGH)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    
    rf_merged = make_report_finding("merged-1", severity=Severity.MEDIUM, merged_from=["f1", "f2"])  # Should be HIGH
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf_merged],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["merged-1"],
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("does not exactly equal the max constituent severity" in e for e in errors)

def test_out_of_bounds_location_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM, line_start=15, line_end=20) # Out of bounds (corpus has 10 lines)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("location lines 15-20 are out of bounds for 'src/app.py'" in e for e in errors)

def test_out_of_bounds_evidence_ref_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    rf1.evidence_ref = ["file:src/app.py#99-100"]  # Out of bounds
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("evidence_ref lines 99-100 are out of bounds for 'src/app.py'" in e for e in errors)

def test_contested_k_cap_violation_fails(sample_corpus):
    input_findings = []
    contested_findings = []
    contested_ids = []
    
    # Create 4 contested findings below floor (medium)
    for i in range(1, 5):
        fid = f"f{i}"
        input_findings.append(make_input_finding(fid, severity=Severity.MEDIUM, status="contested"))
        contested_findings.append(make_report_finding(fid, severity=Severity.MEDIUM, status="contested"))
        contested_ids.append(fid)
        
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={},
        high_critical_findings=[],
        findings=[],
        contested_items=contested_findings,
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=[],
            merged=[],
            omitted=[],
            contested=contested_ids
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, input_findings, sample_corpus)
    # MAX_CONTESTED_BELOW_FLOOR is 3. We have 4.
    assert any(f"Contested findings below high floor count (4) exceeds the maximum cap of {MAX_CONTESTED_BELOW_FLOOR}" in e for e in errors)

def test_merged_constituent_perspective_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", perspective="correctness", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", perspective="security", severity=Severity.MEDIUM)
    
    rf_merged = make_report_finding("merged-1", severity=Severity.MEDIUM, merged_from=["f1", "f2"])
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf_merged],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["merged-1"],
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("belong to the same perspective and source agent" in e for e in errors)

def test_merged_constituent_source_agent_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", source_agent="correctness_agent", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", source_agent="security_debate", severity=Severity.MEDIUM)
    
    rf_merged = make_report_finding("merged-1", severity=Severity.MEDIUM, merged_from=["f1", "f2"])
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf_merged],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["merged-1"],
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("belong to the same perspective and source agent" in e for e in errors)

def test_merged_routing_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    
    # Finding is active, but NOT in ledger included
    rf_merged = make_report_finding("merged-1", severity=Severity.MEDIUM, merged_from=["f1", "f2"])
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf_merged],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=[],  # Missing merged-1!
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("Merged active finding 'merged-1' is not in ledger included list" in e for e in errors)

def test_contested_k_cap_boundary_and_exemption(sample_corpus):
    # (a) exactly 3 below-floor contested pass validation
    input_findings = []
    contested_findings = []
    contested_ids = []
    for i in range(1, 4):
        fid = f"f_below_{i}"
        input_findings.append(make_input_finding(fid, severity=Severity.MEDIUM, status="contested"))
        contested_findings.append(make_report_finding(fid, severity=Severity.MEDIUM, status="contested"))
        contested_ids.append(fid)
    
    # (b) >3 high/critical contested pass (exempt)
    for i in range(1, 6):
        fid = f"f_above_{i}"
        input_findings.append(make_input_finding(fid, severity=Severity.HIGH, status="contested"))
        contested_findings.append(make_report_finding(fid, severity=Severity.HIGH, status="contested"))
        contested_ids.append(fid)

    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={},
        high_critical_findings=[],
        findings=[],
        contested_items=contested_findings,
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=[],
            merged=[],
            omitted=[],
            contested=contested_ids
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, input_findings, sample_corpus)
    assert errors == []

def test_case_sensitive_path_rejected(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    # Use mismatched casing SRC/APP.PY instead of src/app.py
    rf1.location = Location(path="SRC/APP.PY", line_start=1, line_end=5)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("location cites unknown path 'SRC/APP.PY'" in e for e in errors)

def test_merge_unknown_constituents_does_not_raise(sample_corpus):
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[make_report_finding("merged-out", severity=Severity.MEDIUM, merged_from=["unknown-1", "unknown-2"])],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["merged-out"],
            merged=[MergeLedgerEntry(output_id="merged-out", input_ids=["unknown-1", "unknown-2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    # This should not raise ValueError from max() and instead return validation errors
    errors = validate_report_invariants(report, [], sample_corpus)
    assert any("Merge entry for 'merged-out' has no known constituents" in e for e in errors)

def test_contested_orphan_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM, status="contested")
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM, status="contested")
    rf_orphan = make_report_finding("f_orphan", severity=Severity.MEDIUM, status="contested")
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 2},
        high_critical_findings=[],
        findings=[],
        contested_items=[rf1, rf_orphan],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=[],
            merged=[],
            omitted=[],
            contested=["f1"]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("Orphan contested finding in report: 'f_orphan'" in e for e in errors)

def test_misrouted_buckets_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM, status="active")
    f2 = make_input_finding("f2", severity=Severity.MEDIUM, status="contested")
    
    # f1 is listed in included ledger, but physically in contested_items
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM, status="active")
    # f2 is listed in contested ledger, but physically in findings
    rf2 = make_report_finding("f2", severity=Severity.MEDIUM, status="contested")
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf2],
        contested_items=[rf1],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=["f2"]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("Finding 'f1' is listed under ledger included, but routed to contested_items" in e for e in errors) or \
           any("Finding 'f2' is listed under ledger contested, but routed to findings" in e for e in errors)

def test_misrouted_status_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM, status="active")
    f2 = make_input_finding("f2", severity=Severity.MEDIUM, status="contested")
    
    # f1 reported as contested
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM, status="contested")
    # f2 reported as active
    rf2 = make_report_finding("f2", severity=Severity.MEDIUM, status="active")
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf2],
        contested_items=[rf1],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f2"],
            merged=[],
            omitted=[],
            contested=["f1"]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("Included finding 'f2' status 'active' does not match input status 'contested'" in e for e in errors)
    assert any("Contested finding 'f1' status 'contested' does not match input status 'active'" in e for e in errors)

def test_merged_from_ledger_mismatch_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    f2 = make_input_finding("f2", severity=Severity.MEDIUM)
    
    # merged_from has different constituents than listed in ledger.merged
    rf_merged = make_report_finding("merged-1", severity=Severity.MEDIUM, merged_from=["f1"])
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf_merged],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["merged-1"],
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2], sample_corpus)
    assert any("field 'merged_from' ['f1'] does not match ledger constituents" in e for e in errors)

def test_rich_valid_report_passes_clean():
    corpus = {
        "src/app.py": CorpusFile(
            normalized_path="src/app.py",
            original_text="line 1\nline 2\nline 3\nline 4\nline 5",
            redacted_text="line 1\nline 2\nline 3\nline 4\nline 5",
            original_line_count=5,
            evidence_ref="file:src/app.py"
        ),
        "src/utils.py": CorpusFile(
            normalized_path="src/utils.py",
            original_text="line 1\nline 2",
            redacted_text="line 1\nline 2",
            original_line_count=2,
            evidence_ref="file:src/utils.py"
        )
    }
    
    f1 = make_input_finding("f1", severity=Severity.HIGH, path="src/app.py")
    f2 = make_input_finding("f2", severity=Severity.MEDIUM, path="src/app.py")
    f3 = make_input_finding("f3", severity=Severity.LOW, path="src/utils.py", status="contested", line_start=1, line_end=2)
    
    from gdg_yorku_submission.schemas import GateFinding
    gf = GateFinding(
        id="gate-sec",
        source_agent="preflight_secret_gate",
        perspective="security",
        severity=Severity.HIGH,
        location=Location(path="src/utils.py", line_start=1, line_end=2),
        claim="Synthetic secret",
        evidence_ref=["file:src/utils.py#1-2"],
        secret_type="AWS Access Key",
        fingerprint="fp1",
        exposure_status="prompt_exposed"
    )
    
    # Merged finding of f1 and f2
    rf_merged = make_report_finding("merged-1", severity=Severity.HIGH, path="src/app.py", merged_from=["f1", "f2"])
    # Contested finding f3
    rf_contested = make_report_finding("f3", severity=Severity.LOW, path="src/utils.py", status="contested", line_start=1, line_end=2)
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        # Counts: 1 active HIGH merged finding (contested LOW finding f3 is excluded from severity_counts)
        severity_counts={"high": 1},
        high_critical_findings=[rf_merged],
        findings=[rf_merged],
        contested_items=[rf_contested],
        secret_scan_summary=[gf],
        accounting_ledger=AccountingLedger(
            included=["merged-1"],
            merged=[MergeLedgerEntry(output_id="merged-1", input_ids=["f1", "f2"])],
            omitted=[],
            contested=["f3"]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1, f2, f3], corpus)
    assert errors == []

def test_claim_altered_fails(sample_corpus):
    f1 = make_input_finding("f1", severity=Severity.MEDIUM)
    rf1 = make_report_finding("f1", severity=Severity.MEDIUM)
    rf1.claim = "Altered claim!"
    
    report = ReviewReport(
        run_metadata={},
        corpus_summary={},
        perspective_statuses=[],
        gate_status=GateStatus(status="complete", finding_ids=[]),
        severity_counts={"medium": 1},
        high_critical_findings=[],
        findings=[rf1],
        contested_items=[],
        secret_scan_summary=[],
        accounting_ledger=AccountingLedger(
            included=["f1"],
            merged=[],
            omitted=[],
            contested=[]
        ),
        validator_warnings=[]
    )
    
    errors = validate_report_invariants(report, [f1], sample_corpus)
    assert any("Included finding 'f1' claim was altered" in e for e in errors)


def test_validator_warnings_secret_redaction():
    """
    Test that registered secret values present in validator warnings are redacted
    when compiling the report.
    """
    from gdg_yorku_submission.orchestrator import InProcessOrchestrator
    from gdg_yorku_submission.schemas import PerspectiveStatus, GateStatus
    
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Register a secret in the orchestrator's redaction context
    secret_val = "SUPER_SECRET_TOKEN_XYZ"
    redaction_ctx = orch.get_redaction_context()
    placeholder = redaction_ctx.register_secret(secret_val, "TOKEN")
    
    # Set up empty corpus and findings
    orch.set_corpus({})
    orch.finalize_ids()
    
    # Manually append a warning with the secret value to the state (or force it via fallback)
    # The terminal fallback warnings will receive any string we pass to fallback_warnings
    report = orch.compile_terminal_report(fallback_warnings=[f"Warning containing secret: {secret_val}"])
    
    # Assert secret is redacted and placeholder is present in the final report warnings
    assert any(placeholder in w for w in report.validator_warnings)
    assert all(secret_val not in w for w in report.validator_warnings)


def test_validator_warnings_secret_redaction_coordinated(monkeypatch):
    """
    Test that registered secret values present in validator warnings are redacted
    under the coordinated compile path (compile_report).
    """
    from gdg_yorku_submission.orchestrator import InProcessOrchestrator
    from gdg_yorku_submission.schemas import PerspectiveStatus, GateStatus
    import gdg_yorku_submission.coordinator.validator as coord_val
    
    orch = InProcessOrchestrator()
    orch.start_run()
    
    # Register a secret in the orchestrator's redaction context
    secret_val = "SUPER_SECRET_COORDINATED_XYZ"
    redaction_ctx = orch.get_redaction_context()
    placeholder = redaction_ctx.register_secret(secret_val, "TOKEN")
    
    # Set up empty corpus and findings
    orch.set_corpus({})
    orch.finalize_ids()
    
    # Mock run_coordinator_compilation to return empty lists/ledger successfully
    # so we proceed through the coordinated compile path
    from gdg_yorku_submission.schemas import AccountingLedger
    def mock_run_coordinator_compilation(*args, **kwargs):
        return [], [], AccountingLedger(included=[], merged=[], omitted=[], contested=[])
        
    monkeypatch.setattr(
        "gdg_yorku_submission.coordinator.run_coordinator_compilation",
        mock_run_coordinator_compilation
    )
    
    # Monkeypatch build_review_report to inject a warning with the secret value
    original_build = coord_val.build_review_report
    def mock_build_review_report(*args, **kwargs):
        report = original_build(*args, **kwargs)
        report.validator_warnings = [f"Coordinated warning containing secret: {secret_val}"]
        return report
        
    monkeypatch.setattr(coord_val, "build_review_report", mock_build_review_report)
    
    # Compile the report via coordinated path
    report = orch.compile_report()
    
    # Verify compile was coordinated and the warning was redacted
    assert report.run_metadata["compilation_mode"] == "coordinated"
    assert any(placeholder in w for w in report.validator_warnings)
    assert all(secret_val not in w for w in report.validator_warnings)



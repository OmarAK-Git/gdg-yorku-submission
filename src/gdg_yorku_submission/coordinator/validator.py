import logging
import re
from typing import List, Tuple, Dict, Any, Optional, Set
from gdg_yorku_submission.schemas import (
    ReviewFinding,
    ReportFinding,
    Location,
    PerspectiveStatus,
    GateStatus,
    AccountingLedger,
    MergeLedgerEntry,
    OmitLedgerEntry,
    ReviewReport,
    FindingStatus
)
from gdg_yorku_submission.severity import Severity, is_at_or_above_floor

logger = logging.getLogger(__name__)

# K-cap limit on contested findings below high severity floor
MAX_CONTESTED_BELOW_FLOOR = 3

class ReportValidationError(ValueError):
    """Raised when report validation fails due to invariant violations."""
    pass

def parse_evidence_ref(ref: str) -> Tuple[str, int, int]:
    """Parses evidence ref of form file:path#start-end or file:path#line."""
    if not ref.startswith("file:"):
        raise ValueError(f"Evidence reference '{ref}' does not start with 'file:'")
    parts = ref[5:].split("#")
    path = parts[0]
    if len(parts) < 2:
        raise ValueError(f"Evidence reference '{ref}' is missing line coordinates after '#' separator")
    coord = parts[1]
    if "-" in coord:
        line_parts = coord.split("-")
        return path, int(line_parts[0]), int(line_parts[1])
    else:
        line = int(coord)
        return path, line, line

def validate_report_invariants(
    report: ReviewReport,
    input_findings: List[ReviewFinding],
    corpus: Dict[str, Any]
) -> List[str]:
    """
    Validates report invariants (conformance checks).
    Returns a list of validation error message strings. If empty, the report is valid.
    """
    errors: List[str] = []
    input_map = {f.id: f for f in input_findings}
    input_ids = set(input_map.keys())

    # Map findings in report
    report_findings_map = {rf.id: rf for rf in report.findings}
    report_contested_map = {rf.id: rf for rf in report.contested_items}
    all_report_findings_map = {**report_findings_map, **report_contested_map}

    # 1. Conservation Accounting & Double Counting
    accounted_input_ids: Set[str] = set()

    # Process merges in ledger
    merged_output_ids = set()
    for merge_entry in report.accounting_ledger.merged:
        out_id = merge_entry.output_id
        if out_id not in all_report_findings_map:
            errors.append(f"Merge output ID '{out_id}' not found in report findings")
            continue
        merged_output_ids.add(out_id)

        output_finding = all_report_findings_map[out_id]
        
        # Verify constituents
        constituents = merge_entry.input_ids
        if not constituents:
            errors.append(f"Merge entry for '{out_id}' is empty")
            continue
            
        for cid in constituents:
            if cid not in input_ids:
                errors.append(f"Merge entry for '{out_id}' cites unknown input ID '{cid}'")
                continue
            if cid in accounted_input_ids:
                errors.append(f"Input ID '{cid}' was accounted for multiple times")
            accounted_input_ids.add(cid)
            
        # Verify merged_from is populated and matches ledger input_ids exactly
        if sorted(output_finding.merged_from) != sorted(constituents):
            errors.append(
                f"Merged finding '{out_id}' field 'merged_from' {sorted(output_finding.merged_from)} "
                f"does not match ledger constituents {sorted(constituents)}"
            )

        # Check severity exact equality (Spec 25/169 require merged = max of constituents)
        known_constituents = [input_map[cid] for cid in constituents if cid in input_map]
        if not known_constituents:
            errors.append(f"Merge entry for '{out_id}' has no known constituents, cannot compute severity")
            continue
        max_constituent_sev = max(c.severity for c in known_constituents)
        if output_finding.severity != max_constituent_sev:
            errors.append(
                f"Merged finding '{out_id}' has severity '{output_finding.severity.value}' "
                f"which does not exactly equal the max constituent severity '{max_constituent_sev.value}'"
            )
            
        # Check merge perspective/agent isolation
        first_const = input_map[constituents[0]] if constituents[0] in input_map else None
        if first_const:
            expected_p = first_const.perspective
            expected_a = first_const.source_agent
            for cid in constituents:
                if cid in input_map:
                    c = input_map[cid]
                    if c.perspective != expected_p or c.source_agent != expected_a:
                        errors.append(
                            f"Merged findings must belong to the same perspective and source agent. "
                            f"Cannot merge '{cid}' ({c.perspective}/{c.source_agent}) with "
                            f"'{constituents[0]}' ({expected_p}/{expected_a})"
                        )
                        break

        # Check merge output routing to included/contested lists
        if output_finding.status == "contested":
            if out_id not in report.accounting_ledger.contested:
                errors.append(f"Merged contested finding '{out_id}' is not in ledger contested list")
        else:
            if out_id not in report.accounting_ledger.included:
                errors.append(f"Merged active finding '{out_id}' is not in ledger included list")

    # Process omissions in ledger
    for omit_entry in report.accounting_ledger.omitted:
        oid = omit_entry.id
        if oid not in input_ids:
            errors.append(f"Omission entry cites unknown input ID '{oid}'")
            continue
            
        if oid in accounted_input_ids:
            errors.append(f"Input ID '{oid}' was accounted for multiple times")
        accounted_input_ids.add(oid)
        
        # High/critical non-omission check
        input_f = input_map[oid]
        if is_at_or_above_floor(input_f.severity):
            errors.append(f"Forbidden omission of high/critical finding '{oid}' (severity: {input_f.severity.value})")

    # Process verbatim included active findings
    for fid in report.accounting_ledger.included:
        if fid not in input_ids:
            # It could be a merged output ID
            if fid in merged_output_ids:
                continue
            errors.append(f"Ledger included list cites unknown ID '{fid}'")
            continue
            
        if fid in accounted_input_ids:
            errors.append(f"Input ID '{fid}' was accounted for multiple times")
        accounted_input_ids.add(fid)
        
        # Included finding severity must match input severity exactly
        if fid in input_map:
            report_f = report_findings_map.get(fid)
            if not report_f:
                if fid in report_contested_map:
                    errors.append(f"Finding '{fid}' is listed under ledger included, but routed to contested_items")
                else:
                    errors.append(f"Ledger included ID '{fid}' not found in report findings")
            elif report_f.severity != input_map[fid].severity:
                errors.append(
                    f"Included finding '{fid}' severity '{report_f.severity.value}' "
                    f"does not match input finding severity '{input_map[fid].severity.value}'"
                )
            if report_f and report_f.status != input_map[fid].status:
                errors.append(
                    f"Included finding '{fid}' status '{report_f.status}' "
                    f"does not match input status '{input_map[fid].status}'"
                )
            if report_f and report_f.claim != input_map[fid].claim:
                errors.append(
                    f"Included finding '{fid}' claim was altered: "
                    f"expected '{input_map[fid].claim}', got '{report_f.claim}'"
                )

    # Process contested findings
    for fid in report.accounting_ledger.contested:
        if fid not in input_ids:
            if fid in merged_output_ids:
                continue
            errors.append(f"Ledger contested list cites unknown ID '{fid}'")
            continue
            
        if fid in accounted_input_ids:
            errors.append(f"Input ID '{fid}' was accounted for multiple times")
        accounted_input_ids.add(fid)
        
        # Contested finding severity must match input severity exactly
        if fid in input_map:
            report_f = report_contested_map.get(fid)
            if not report_f:
                if fid in report_findings_map:
                    errors.append(f"Finding '{fid}' is listed under ledger contested, but routed to findings")
                else:
                    errors.append(f"Ledger contested ID '{fid}' not found in report contested items")
            elif report_f.severity != input_map[fid].severity:
                errors.append(
                    f"Contested finding '{fid}' severity '{report_f.severity.value}' "
                    f"does not match input finding severity '{input_map[fid].severity.value}'"
                )
            if report_f and report_f.status != input_map[fid].status:
                errors.append(
                    f"Contested finding '{fid}' status '{report_f.status}' "
                    f"does not match input status '{input_map[fid].status}'"
                )
            if report_f and report_f.claim != input_map[fid].claim:
                errors.append(
                    f"Contested finding '{fid}' claim was altered: "
                    f"expected '{input_map[fid].claim}', got '{report_f.claim}'"
                )

    # Verify every input ID is accounted for
    missing_ids = input_ids - accounted_input_ids
    if missing_ids:
        errors.append(f"Conservation check failed: input findings {sorted(list(missing_ids))} are not accounted for in ledger")

    # 2. Bidirectional Ledger vs Findings list consistency (Orphan Finding Checks)
    # Check that every active report finding is accounted for in ledger included
    for rf in report.findings:
        if rf.id not in report.accounting_ledger.included:
            errors.append(f"Orphan active finding in report: '{rf.id}' is not in ledger included list")

    # Check that every contested report finding is accounted for in ledger contested
    for rf in report.contested_items:
        if rf.id not in report.accounting_ledger.contested:
            errors.append(f"Orphan contested finding in report: '{rf.id}' is not in ledger contested list")

    # 3. Exact Severity Counts
    expected_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for rf in report.findings:
        expected_counts[rf.severity.value] += 1
    
    for sev in expected_counts:
        actual_val = report.severity_counts.get(sev, 0)
        expected_val = expected_counts[sev]
        if actual_val != expected_val:
            errors.append(
                f"Severity count mismatch for '{sev}': report lists {actual_val} but findings count is {expected_val}"
            )

    # 4. High/Critical list synchronization check
    expected_high_critical_ids = {rf.id for rf in report.findings if is_at_or_above_floor(rf.severity)}
    actual_high_critical_ids = {rf.id for rf in report.high_critical_findings}
    if expected_high_critical_ids != actual_high_critical_ids:
        errors.append(
            f"High/Critical findings list mismatch: "
            f"expected IDs {sorted(list(expected_high_critical_ids))}, "
            f"got {sorted(list(actual_high_critical_ids))}"
        )

    # 5. Contested K-cap
    contested_below_floor_count = sum(
        1 for rf in report.contested_items if not is_at_or_above_floor(rf.severity)
    )
    if contested_below_floor_count > MAX_CONTESTED_BELOW_FLOOR:
        errors.append(
            f"Contested findings below high floor count ({contested_below_floor_count}) "
            f"exceeds the maximum cap of {MAX_CONTESTED_BELOW_FLOOR}"
        )

    # 6. Evidence-coordinate existence validation
    # Check both active findings, contested findings, and secret_scan_summary gate findings
    all_findings_to_check: List[Any] = []
    all_findings_to_check.extend(report.findings)
    all_findings_to_check.extend(report.contested_items)
    all_findings_to_check.extend(report.secret_scan_summary)

    for f in all_findings_to_check:
        # Check location coordinate ranges (R2a)
        loc = getattr(f, "location", None)
        if loc:
            try:
                ref_path = loc.path
                ref_start = loc.line_start
                ref_end = loc.line_end
                
                # Check path case-sensitively in corpus (Windows -> Linux case-sensitive deployment)
                normalized_ref_path = ref_path.replace("\\", "/")
                corpus_key = None
                if normalized_ref_path in corpus:
                    corpus_key = normalized_ref_path
                if corpus_key is None:
                    errors.append(f"Finding '{f.id}' location cites unknown path '{ref_path}'")
                else:
                    corpus_file = corpus[corpus_key]
                    if ref_start < 1 or ref_end > corpus_file.original_line_count or ref_start > ref_end:
                        errors.append(
                            f"Finding '{f.id}' location lines {ref_start}-{ref_end} "
                            f"are out of bounds for '{ref_path}' (original line count: {corpus_file.original_line_count})"
                        )
            except Exception as e:
                errors.append(f"Finding '{f.id}' contains invalid location: {str(e)}")

        # Check evidence_refs
        evidence_refs = getattr(f, "evidence_ref", [])
        for ref in evidence_refs:
            try:
                ref_path, ref_start, ref_end = parse_evidence_ref(ref)
                
                # Check path case-sensitively in corpus (Windows -> Linux case-sensitive deployment)
                normalized_ref_path = ref_path.replace("\\", "/")
                corpus_key = None
                if normalized_ref_path in corpus:
                    corpus_key = normalized_ref_path
                if corpus_key is None:
                    errors.append(f"Finding '{f.id}' evidence_ref cites unknown path '{ref_path}' in ref '{ref}'")
                else:
                    corpus_file = corpus[corpus_key]
                    if ref_start < 1 or ref_end > corpus_file.original_line_count or ref_start > ref_end:
                        errors.append(
                            f"Finding '{f.id}' evidence_ref lines {ref_start}-{ref_end} "
                            f"are out of bounds for '{ref_path}' (original line count: {corpus_file.original_line_count}) in ref '{ref}'"
                        )
            except Exception as e:
                errors.append(f"Finding '{f.id}' contains malformed evidence_ref '{ref}': {str(e)}")

    return errors

import json
import logging
import hashlib
import secrets
import re
from typing import List, Tuple, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
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
from gdg_yorku_submission.llm.gemini import GeminiClient
from gdg_yorku_submission.budget import BudgetExhaustedError
import copy
from gdg_yorku_submission.coordinator.validator import (
    parse_evidence_ref,
    validate_report_invariants,
    remediate_contested_kcap,
    build_review_report
)

logger = logging.getLogger(__name__)

def sanitize_untrusted_input(content: str, nonce: str) -> str:
    """Sanitizes untrusted coordinator findings input to prevent delimiter breakout."""
    if nonce:
        content = content.replace(nonce, "[NONCE_REDACTED]")
    content = re.sub(r'</?evidence_plane\b', lambda m: m.group(0).replace('<', '&lt;'), content, flags=re.IGNORECASE)
    return content


class CoordinatorMergeGroup(BaseModel):
    merged_ids: List[str] = Field(
        ...,
        description="IDs of input findings to merge. Must be at least 2 findings from the same perspective and source agent."
    )
    consolidated_claim: str = Field(
        ...,
        description="A clear, consolidated claim description summarizing all the merged findings."
    )
    recommended_next_action: str = Field(
        ...,
        description="Recommended action for the developer to address the merged findings."
    )

class CoordinatorOmission(BaseModel):
    id: str = Field(..., description="Provisional or finalized finding ID to omit.")
    reason: str = Field(..., description="Justification/reason why this finding is omitted from the report.")

class CoordinatorOutput(BaseModel):
    merges: List[CoordinatorMergeGroup] = Field(
        default_factory=list,
        description="Proposed merges of redundant/overlapping findings."
    )
    omissions: List[CoordinatorOmission] = Field(
        default_factory=list,
        description="Proposed omissions of low-severity findings. High/critical findings CANNOT be omitted."
    )
    recommended_actions: Dict[str, str] = Field(
        default_factory=dict,
        description="Recommended next actions for individual (unmerged, included) findings, mapping ID to action text."
    )



def is_remediable_error(err: str) -> bool:
    """
    Classifies errors as coordinator-remediable or not.
    Errors regarding location out-of-bounds, invalid evidence_ref format/paths,
    or verbatim field mismatches (where the coordinator cannot change the properties of
    the input findings) are non-remediable.
    """
    non_remediable_keywords = [
        "out of bounds",
        "cites unknown path",
        "does not match input finding severity",
        "does not match input status",
        "claim was altered",
        "contains invalid location",
        "contains malformed evidence_ref"
    ]
    for kw in non_remediable_keywords:
        if kw.lower() in err.lower():
            return False
    return True


def run_coordinator_compilation(
    orch,
    input_findings: List[ReviewFinding],
    statuses: List[PerspectiveStatus],
    gate_status: GateStatus,
    gemini_client: Optional[GeminiClient] = None
) -> Tuple[List[ReportFinding], List[ReportFinding], AccountingLedger]:
    """
    Runs the coordinator agent using Gemini to group and merge findings.
    If LLM fails, budget runs out, or validation fails after R=2 retries,
    raises ValueError (which lets compile_report fallback to terminal report).
    """
    if gemini_client is None:
        gemini_client = GeminiClient()

    corpus = orch.get_corpus()
    input_map = {f.id: f for f in input_findings}

    # Build prompt
    findings_list = []
    for f in input_findings:
        findings_list.append({
            "id": f.id,
            "source_agent": f.source_agent,
            "perspective": f.perspective,
            "severity": f.severity.value,
            "location": {
                "path": f.location.path,
                "line_start": f.location.line_start,
                "line_end": f.location.line_end
            },
            "claim": f.claim,
            "evidence_ref": f.evidence_ref,
            "status": f.status
        })

    nonce = secrets.token_hex(16)
    findings_json = json.dumps(findings_list, indent=2)
    sanitized_findings = sanitize_untrusted_input(findings_json, nonce)

    prompt = (
        "You are the coordinator agent. Your job is to compile, group, and merge findings from various "
        "specialist perspectives into a consolidated, clean review report.\n\n"
        "Here is the nonced evidence plane containing the input findings:\n"
        f'<evidence_plane nonce="{nonce}">\n'
        f"{sanitized_findings}\n"
        f'</evidence_plane nonce="{nonce}">\n\n'
        "Strict Rules:\n"
        "1. Merging:\n"
        "   - You can only merge findings that belong to the SAME perspective AND the SAME source_agent.\n"
        "   - For any merged group, you must specify all their original IDs in `merged_ids`.\n"
        "   - You must write a consolidated claim summarizing the merged findings in `consolidated_claim`.\n"
        "   - You must write a recommended next action for the merged finding in `recommended_next_action`.\n"
        "2. Omissions:\n"
        "   - You may omit minor/low-severity findings that are noise or redundant (list their IDs in `omissions` with a brief reason).\n"
        "   - WARNING: You are STRICTLY FORBIDDEN from omitting any HIGH or CRITICAL severity findings.\n"
        "3. Individual Findings:\n"
        "   - For findings that you do not merge or omit, you should provide a recommended next action in `recommended_actions` "
        "(mapping the finding's ID to a recommended action string).\n\n"
        "Please return a JSON object conforming strictly to the requested schema."
    )

    max_retries = 2
    raw_response = ""
    parsed_output = None
    validation_errors = []

    # Bounded retry loop (R=2 attempts total)
    for attempt in range(max_retries):
        current_prompt = prompt
        if validation_errors:
            error_details = "\n".join(validation_errors)
            # Sanitize feedback errors to prevent prompt-injection delimiter breakout (Point 1)
            sanitized_errors = sanitize_untrusted_input(error_details, nonce)
            current_prompt += (
                f"\n\nYOUR PREVIOUS RESPONSE FAILED VALIDATION with the following errors:\n{sanitized_errors}\n"
                "Please fix these errors and regenerate conforming to all rules."
            )

        try:
            raw_response = gemini_client.generate_content(
                orch,
                prompt=current_prompt,
                response_schema=CoordinatorOutput,
                estimated_input_tokens=len(current_prompt) // 4 + 1000,
                estimated_output_tokens=1000,
                component="coordinator"
            )

            cleaned_text = raw_response.strip()
            if cleaned_text.startswith("```"):
                lines = cleaned_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines).strip()

            parsed_json = json.loads(cleaned_text)
            parsed_output = CoordinatorOutput(**parsed_json)

            # Reconstruct and pre-validate selections locally
            findings, contested, ledger, errors = reconstruct_report_components(
                parsed_output, input_findings, corpus
            )
            if not errors:
                draft_findings = copy.deepcopy(findings)
                draft_contested = copy.deepcopy(contested)
                draft_ledger = copy.deepcopy(ledger)
                
                # Apply contested K-cap remediation logic inside the compiler loop
                draft_contested, draft_ledger = remediate_contested_kcap(draft_contested, draft_ledger)
                
                state = orch.read_state()
                draft_report = build_review_report(
                    orch,
                    state,
                    draft_findings,
                    draft_contested,
                    draft_ledger,
                    statuses,
                    gate_status,
                    compilation_mode="coordinated"
                )
                
                errors = validate_report_invariants(draft_report, input_findings, corpus)
                if not errors:
                    return draft_findings, draft_contested, draft_ledger
                
                # Classify errors as coordinator-remediable or not; bypass retries if all are non-remediable (Point 4)
                remediable_errors = [e for e in errors if is_remediable_error(e)]
                if not remediable_errors:
                    logger.warning(f"All validation errors are non-remediable. Bypassing retries to conserve budget. Errors: {errors}")
                    raise ValueError(f"Coordinator compilation failed with non-remediable errors: {errors}")
                
            validation_errors = errors
            logger.warning(f"Coordinator attempt {attempt + 1} validation failed: {validation_errors}")
        except BudgetExhaustedError as e:
            logger.error(f"Budget exhausted during coordinator compilation: {e}")
            raise ValueError("Coordinator compilation failed due to budget exhaustion") from e
        except Exception as e:
            # Propagate non-remediable compiler errors directly
            if isinstance(e, ValueError) and "non-remediable errors" in str(e):
                raise e
            # A validator internal crash (like RuntimeError) should immediately raise to fall back (Point 5)
            if not isinstance(e, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
                raise e
            logger.warning(f"Error parsing coordinator response on attempt {attempt + 1}: {e}")
            validation_errors = [f"JSON parsing or structure error: {str(e)}"]

    raise ValueError(f"Coordinator failed to produce a valid report after {max_retries} attempts: {validation_errors}")

def reconstruct_report_components(
    output: CoordinatorOutput,
    input_findings: List[ReviewFinding],
    corpus: Dict[str, Any]
) -> Tuple[List[ReportFinding], List[ReportFinding], AccountingLedger, List[str]]:
    """
    Reconstructs ReportFinding list, contested findings list, and AccountingLedger from LLM suggestion.
    Performs validation on merges and omissions, returning any validation errors.
    """
    errors: List[str] = []
    input_map = {f.id: f for f in input_findings}
    processed_ids: Set[str] = set()

    findings: List[ReportFinding] = []
    contested_items: List[ReportFinding] = []

    ledger_included: List[str] = []
    ledger_merged: List[MergeLedgerEntry] = []
    ledger_omitted: List[OmitLedgerEntry] = []
    ledger_contested: List[str] = []

    # 1. Process merges
    for m_group in output.merges:
        # Validate constituent IDs
        valid_constituents = []
        for fid in m_group.merged_ids:
            if fid not in input_map:
                errors.append(f"Merge group cites unknown finding ID '{fid}'")
                continue
            if fid in processed_ids:
                errors.append(f"Merge group cites already-processed ID '{fid}'")
                continue
            valid_constituents.append(fid)

        if len(valid_constituents) < 2:
            continue

        constituents = [input_map[fid] for fid in valid_constituents]
        
        # Verify perspective and source agent isolation
        expected_p = constituents[0].perspective
        expected_a = constituents[0].source_agent
        mismatched = False
        for c in constituents:
            if c.perspective != expected_p or c.source_agent != expected_a:
                errors.append(
                    f"Cannot merge finding '{c.id}' ({c.perspective}/{c.source_agent}) with "
                    f"'{constituents[0].id}' ({expected_p}/{expected_a}) - mismatched isolation boundary"
                )
                mismatched = True
                break
        if mismatched:
            continue

        # Mark processed
        for fid in valid_constituents:
            processed_ids.add(fid)

        # Determine severity (max)
        merged_severity = max(c.severity for c in constituents)
        
        # Determine location
        first_c = constituents[0]
        # Same path grouping
        same_path = all(c.location.path == first_c.location.path for c in constituents)
        if same_path:
            line_start = min(c.location.line_start for c in constituents)
            line_end = max(c.location.line_end for c in constituents)
            merged_location = Location(path=first_c.location.path, line_start=line_start, line_end=line_end)
        else:
            # Fallback: take coordinate of highest severity constituent (or first tiebreaker)
            primary_c = max(constituents, key=lambda c: (c.severity, c.id))
            merged_location = primary_c.location

        # Determine evidence_refs (union)
        evidence_refs: List[str] = []
        for c in constituents:
            for ref in c.evidence_ref:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)

        # Precedence for status: active > contested > advisory
        status_ranks = {"active": 3, "contested": 2, "advisory": 1}
        merged_status = max(constituents, key=lambda c: status_ranks.get(c.status, 0)).status

        # Merge metadata
        merged_metadata = {}
        for c in constituents:
            if c.metadata:
                merged_metadata.update(c.metadata)

        # Stable merged ID
        sorted_ids_str = ",".join(sorted(valid_constituents))
        merged_id = f"merged-{hashlib.sha256(sorted_ids_str.encode('utf-8')).hexdigest()[:16]}"

        rf = ReportFinding(
            id=merged_id,
            source_agent=expected_a,
            perspective=expected_p,
            severity=merged_severity,
            location=merged_location,
            claim=m_group.consolidated_claim,
            evidence_ref=evidence_refs,
            status=merged_status,
            metadata=merged_metadata,
            recommended_next_action=m_group.recommended_next_action,
            merged_from=valid_constituents
        )

        if merged_status == "contested":
            contested_items.append(rf)
            ledger_contested.append(merged_id)
        else:
            findings.append(rf)
            ledger_included.append(merged_id)

        ledger_merged.append(MergeLedgerEntry(output_id=merged_id, input_ids=valid_constituents))

    # 2. Process omissions
    for o in output.omissions:
        fid = o.id
        if fid not in input_map:
            errors.append(f"Omission cites unknown finding ID '{fid}'")
            continue
        if fid in processed_ids:
            errors.append(f"Omission cites already-processed ID '{fid}'")
            continue

        # Check high/critical non-omission
        input_f = input_map[fid]
        if is_at_or_above_floor(input_f.severity):
            errors.append(f"Cannot omit high/critical severity finding '{fid}'")
            continue

        processed_ids.add(fid)
        ledger_omitted.append(OmitLedgerEntry(id=fid, reason=o.reason))

    # 3. Process remaining unmerged findings
    for f in input_findings:
        if f.id in processed_ids:
            continue

        processed_ids.add(f.id)
        
        # Get recommended action
        rec_action = output.recommended_actions.get(f.id)
        if not rec_action:
            rec_action = f"Verify finding in {f.location.path} lines {f.location.line_start}-{f.location.line_end}."

        rf = ReportFinding(
            id=f.id,
            source_agent=f.source_agent,
            perspective=f.perspective,
            severity=f.severity,
            location=f.location,
            claim=f.claim,
            evidence_ref=f.evidence_ref,
            status=f.status,
            metadata=f.metadata,
            recommended_next_action=rec_action,
            merged_from=[]
        )

        if f.status == "contested":
            contested_items.append(rf)
            ledger_contested.append(f.id)
        else:
            findings.append(rf)
            ledger_included.append(f.id)

    ledger = AccountingLedger(
        included=ledger_included,
        merged=ledger_merged,
        omitted=ledger_omitted,
        contested=ledger_contested
    )

    return findings, contested_items, ledger, errors

import hashlib
import os
from typing import List, Dict, Tuple, Optional, Any

from gdg_yorku_submission.schemas import Finding, Location
from gdg_yorku_submission.severity import Severity

# Metadata key contract for finding_ids.py (Gap 11)
# -------------------------------------------------
# - Rule/Category: used to group findings by the general category of the check.
#   Checked keys: "rule_or_category", "rule", "category", fallback to "sub_rule", "sub_category", "rule_id".
# - Sub-Rule: used for sorting/tiebreaking.
#   Checked keys: "sub_rule", "sub_category", "rule_id".
# - Non-prose Discriminator: used to distinguish co-located findings (e.g. offset, node ID).
#   Checked keys: "token_offset", "ast_node_id", "evidence_anchor", "offset".
# - Stable Symbol: used to anchor finding to code symbol if available.
#   Checked keys: "stable_symbol", "symbol".

METADATA_KEYS_RULE = [
    "rule_or_category",
    "rule",
    "category",
    "sub_rule",
    "sub_category",
    "rule_id",
]
METADATA_KEYS_SUB_RULE = ["sub_rule", "sub_category", "rule_id"]
METADATA_KEYS_DISCRIMINATOR = ["token_offset", "ast_node_id", "evidence_anchor", "offset"]
METADATA_KEYS_SYMBOL = ["stable_symbol", "symbol"]


def get_metadata_value(metadata: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    """Helper to check for key presence and return its value if not None (Gap 3)."""
    for key in keys:
        if key in metadata:
            val = metadata[key]
            if val is not None:
                return val
    return None


def normalize_path(path: str) -> str:
    """Normalizes file path for cross-platform consistency."""
    return os.path.normpath(path).replace('\\', '/')


def compute_anchor(finding: Finding) -> str:
    """
    Computes a deterministic anchor hash for a finding.
    
    Anchor is the SHA-256 hash of:
    source_agent + perspective + normalized_path + line_start + rule_or_category + stable_symbol
    """
    metadata = finding.metadata or {}
    source_agent = finding.source_agent
    perspective = finding.perspective  # Added perspective to anchor (Gap 2)
    normalized_path = normalize_path(finding.location.path)
    line_start = finding.location.line_start
    
    rule_or_category = get_metadata_value(metadata, METADATA_KEYS_RULE)
    rule_or_category = "" if rule_or_category is None else str(rule_or_category).strip()
    
    stable_symbol = get_metadata_value(metadata, METADATA_KEYS_SYMBOL)
    stable_symbol = "" if stable_symbol is None else str(stable_symbol).strip()
    
    anchor_str = f"{source_agent}:{perspective}:{normalized_path}:{line_start}:{rule_or_category}:{stable_symbol}"
    return hashlib.sha256(anchor_str.encode("utf-8")).hexdigest()


def get_sub_rule(finding: Finding) -> str:
    """Extracts sub-rule/sub-category enum if emitted using the aligned key set (Gap 11)."""
    metadata = finding.metadata or {}
    val = get_metadata_value(metadata, METADATA_KEYS_SUB_RULE)
    return "" if val is None else str(val).strip()


def get_non_prose_discriminator(finding: Finding) -> Optional[str]:
    """
    Extracts normalized non-prose evidence anchor (offset, token_offset, ast_node_id)
    with strict None checks to handle 0 values (Gap 3).
    """
    metadata = finding.metadata or {}
    val = get_metadata_value(metadata, METADATA_KEYS_DISCRIMINATOR)
    if val is not None:
        return str(val).strip()
    return None


def merge_finding_objects(findings: List[Finding]) -> Finding:
    """
    Merges multiple findings into a single finding.
    
    - severity: maximum rank among findings
    - location: same path & line_start, line_end is max of all
    - claim: joined with '; '
    - evidence_ref: union of all, order-preserved, deduplicated
    - status: highest priority (active > contested > advisory) (Gap 5)
    - metadata: merged dictionaries
    """
    if not findings:
        raise ValueError("Cannot merge an empty list of findings")
    if len(findings) == 1:
        return findings[0]
        
    base = findings[0]
    cls = base.__class__
    
    # Refuse cross-perspective and cross-source_agent merges (Gap 2)
    for f in findings[1:]:
        if f.perspective != base.perspective:
            raise ValueError(
                f"Cannot merge findings with different perspectives: "
                f"'{f.perspective}' vs '{base.perspective}'"
            )
        if f.source_agent != base.source_agent:
            raise ValueError(
                f"Cannot merge findings with different source agents: "
                f"'{f.source_agent}' vs '{base.source_agent}'"
            )
            
    # Merge severity
    max_severity = base.severity
    for f in findings[1:]:
        if f.severity > max_severity:
            max_severity = f.severity
            
    # Merge location
    max_line_end = max(f.location.line_end for f in findings)
    merged_location = Location(
        path=base.location.path,
        line_start=base.location.line_start,
        line_end=max_line_end
    )
    
    # Merge claims (deduplicated)
    claims = []
    for f in findings:
        if f.claim not in claims:
            claims.append(f.claim)
    merged_claim = "; ".join(claims)
    
    # Merge evidence_ref
    evidence_refs = []
    for f in findings:
        for ref in f.evidence_ref:
            if ref not in evidence_refs:
                evidence_refs.append(ref)
                
    # Merge status (Gap 5): active > contested > advisory
    merged_status = "advisory"
    statuses = {f.status for f in findings}
    if "active" in statuses:
        merged_status = "active"
    elif "contested" in statuses:
        merged_status = "contested"
        
    # Merge metadata
    merged_metadata = {}
    merged_from_provisional = []
    for f in findings:
        merged_metadata.update(f.metadata or {})
        existing_merged = f.metadata.get("merged_from_provisional") if f.metadata else None
        if existing_merged:
            if isinstance(existing_merged, list):
                merged_from_provisional.extend(existing_merged)
            else:
                merged_from_provisional.append(existing_merged)
        if f.id not in merged_from_provisional:
            merged_from_provisional.append(f.id)
            
    # Deduplicate merged_from_provisional
    deduped_merged = []
    for p_id in merged_from_provisional:
        if p_id not in deduped_merged:
            deduped_merged.append(p_id)
            
    merged_metadata["merged_from_provisional"] = deduped_merged
    
    # Support optional ReportFinding properties if base is a ReportFinding subclass
    extra_kwargs = {}
    if hasattr(base, "recommended_next_action"):
        recommended_actions = []
        for f in findings:
            action = getattr(f, "recommended_next_action", None)
            if action and action not in recommended_actions:
                recommended_actions.append(action)
        extra_kwargs["recommended_next_action"] = "; ".join(recommended_actions) if recommended_actions else None
        
    if hasattr(base, "merged_from"):
        merged_from_ids = []
        for f in findings:
            m_from = getattr(f, "merged_from", None)
            if m_from:
                for m_id in m_from:
                    if m_id not in merged_from_ids:
                        merged_from_ids.append(m_id)
            if f.id not in merged_from_ids:
                merged_from_ids.append(f.id)
        extra_kwargs["merged_from"] = merged_from_ids

    return cls(
        id=base.id,  # Placeholder, will be replaced by finalize_finding_ids
        source_agent=base.source_agent,
        perspective=base.perspective,
        severity=max_severity,
        location=merged_location,
        claim=merged_claim,
        evidence_ref=evidence_refs,
        status=merged_status,
        metadata=merged_metadata,
        **extra_kwargs
    )


def parse_discriminator_for_sorting(val: Optional[str]) -> Tuple[int, Any]:
    """
    Parses a discriminator string into a tuple (type_priority, value) for sorting.
    Type priority:
    - 0: None / empty (comes first)
    - 1: Numeric (sorted numerically)
    - 2: Non-numeric String (sorted lexicographically)
    
    This ensures type-safe sorting and correct numeric order for negative values and floats.
    """
    if val is None:
        return (0, 0)
    val_str = str(val).strip()
    if not val_str:
        return (0, 0)
        
    try:
        return (1, int(val_str))
    except ValueError:
        try:
            return (1, float(val_str))
        except ValueError:
            return (2, val_str)


def get_sort_key_for_indexed_finding(item: Tuple[int, Finding]) -> Tuple[str, Tuple[int, Any], str, int]:
    """Returns stable sorting key tuple (sub_rule, parsed_non_prose, claim_sha, input_index) (Gaps 7, 10)."""
    idx, f = item
    sub_rule = get_sub_rule(f)
    non_prose = get_non_prose_discriminator(f)
    parsed_non_prose = parse_discriminator_for_sorting(non_prose)
    claim_sha = hashlib.sha256(f.claim.encode("utf-8")).hexdigest()
    return (sub_rule, parsed_non_prose, claim_sha, idx)


def get_finalized_finding_sort_key(f: Finding) -> Tuple[str, int, str, str, str, Tuple[int, Any], str, str]:
    """Returns a stable sorting key for a finalized finding based on its semantic attributes."""
    path = normalize_path(f.location.path)
    line_start = f.location.line_start
    source_agent = f.source_agent
    perspective = f.perspective
    sub_rule = get_sub_rule(f)
    non_prose = get_non_prose_discriminator(f)
    parsed_non_prose = parse_discriminator_for_sorting(non_prose)
    claim_sha = hashlib.sha256(f.claim.encode("utf-8")).hexdigest()
    return (path, line_start, source_agent, perspective, sub_rule, parsed_non_prose, claim_sha, f.id)


def finalize_finding_ids(findings: List[Finding]) -> Tuple[List[Finding], Dict[str, List[str]]]:
    """
    Groups provisional findings, merges co-located findings with identical non-prose keys,
    sorts by tiebreakers, assigns ordinals, and freezes stable final IDs.
    
    Returns:
        Tuple[finalized_findings, id_mapping]
        - finalized_findings: list of Finding (or subclass) with frozen IDs.
        - id_mapping: dictionary mapping finalized_id -> list of original provisional_ids.
    """
    if not findings:
        return [], {}
        
    # Group findings by their anchor hash (assigning input index to preserve original emission order)
    anchor_groups: Dict[str, List[Tuple[int, Finding]]] = {}
    for idx, f in enumerate(findings):
        anchor = compute_anchor(f)
        anchor_groups.setdefault(anchor, []).append((idx, f))
        
    finalized_findings: List[Finding] = []
    id_mapping: Dict[str, List[str]] = {}
    
    for anchor, group in anchor_groups.items():
        # Separate findings into detector-backed (having non-prose discriminator) and LLM-authored (lacking it)
        detector_groups: Dict[Tuple[str, str], List[Tuple[int, Finding]]] = {}
        llm_findings: List[Tuple[int, Finding]] = []
        
        for idx, f in group:
            non_prose_disc = get_non_prose_discriminator(f)
            if non_prose_disc is not None:
                sub_rule = get_sub_rule(f)
                detector_groups.setdefault((sub_rule, non_prose_disc), []).append((idx, f))
            else:
                llm_findings.append((idx, f))
                
        # Merge detector-backed findings with identical non-prose keys
        unique_indexed_findings: List[Tuple[int, Finding]] = []
        for (sub_rule, non_prose_disc), f_list in detector_groups.items():
            min_idx = min(idx for idx, _ in f_list)
            merged = merge_finding_objects([f for _, f in f_list])
            unique_indexed_findings.append((min_idx, merged))
            
        # LLM findings are NOT merged/collapsed by claim (Gap 4).
        # They remain distinct and are simply appended to unique findings.
        for idx, f in llm_findings:
            unique_indexed_findings.append((idx, f))
            
        # Sort remaining findings in the anchor group by the tiebreaker key
        unique_indexed_findings.sort(key=get_sort_key_for_indexed_finding)
        
        # Assign per-anchor occurrence ordinals and freeze final IDs
        for ordinal, (idx, f) in enumerate(unique_indexed_findings):
            final_id = hashlib.sha256(f"{anchor}:{ordinal}".encode("utf-8")).hexdigest()
            
            # Map finalized_id to the provisional ID(s) it represents
            provisional_ids = f.metadata.get("merged_from_provisional")
            if not provisional_ids:
                provisional_ids = [f.id]
            else:
                flat_ids = []
                for item in provisional_ids:
                    if isinstance(item, list):
                        flat_ids.extend(item)
                    else:
                        flat_ids.append(item)
                provisional_ids = flat_ids
                
            # Make sure finalized finding preserves merged_from_provisional in metadata (Gap 6)
            cleaned_metadata = dict(f.metadata or {})
            cleaned_metadata["merged_from_provisional"] = provisional_ids
            
            finalized_f = f.model_copy(update={
                "id": final_id,
                "metadata": cleaned_metadata
            })
            
            finalized_findings.append(finalized_f)
            id_mapping[final_id] = provisional_ids
            
    # Ensure stable output list order across all runs (Gap 10)
    finalized_findings.sort(key=get_finalized_finding_sort_key)
    
    return finalized_findings, id_mapping

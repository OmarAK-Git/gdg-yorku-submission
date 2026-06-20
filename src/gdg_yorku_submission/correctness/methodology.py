import re
from pathlib import Path
from typing import Dict, List, Any

from gdg_yorku_submission.schemas import Finding
from gdg_yorku_submission.severity import Severity

METHODOLOGY_PATH = Path(__file__).parent / "methodology.md"

def load_methodology() -> str:
    """Reads and returns the correctness review methodology markdown content."""
    if not METHODOLOGY_PATH.exists():
        raise FileNotFoundError(f"Methodology file not found at {METHODOLOGY_PATH}")
    return METHODOLOGY_PATH.read_text(encoding="utf-8")

COORDINATE_PATTERN = re.compile(r"^file:[^#]+#\d+-\d+$")

def validate_correctness_finding(finding: Dict[str, Any], has_spec: bool) -> List[str]:
    """
    Validates a correctness finding against the rules defined in the methodology.
    Returns a list of error messages (empty if valid).
    """
    errors = []

    # 1. Structural and Schema Validation using Pydantic Finding model
    try:
        finding_model = Finding(**finding)
    except Exception as e:
        errors.append(f"Schema validation failed: {e}")
        return errors

    # 2. Source Agent and Perspective Constraints
    if finding_model.source_agent != "correctness_agent":
        errors.append(f"Invalid source_agent: {finding_model.source_agent}. Must be 'correctness_agent'.")
    if finding_model.perspective != "correctness":
        errors.append(f"Invalid perspective: {finding_model.perspective}. Must be 'correctness'.")

    # 3. Severity constraints (Capped at medium when has_spec is False)
    if not has_spec:
        if finding_model.severity in [Severity.HIGH, Severity.CRITICAL]:
            errors.append(f"Severity must be capped at medium (got '{finding_model.severity.value}') when no specification exists.")

    # 4. Syntactic Coordinate Format Checks for evidence_refs
    for ref in finding_model.evidence_ref:
        if not COORDINATE_PATTERN.match(ref):
            errors.append(f"Invalid evidence_ref format: '{ref}'. Must match 'file:path#line_start-line_end'.")

    return errors

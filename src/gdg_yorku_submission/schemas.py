from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Literal, Optional, Any, List, Dict
from gdg_yorku_submission.severity import Severity

class SkippedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    skipped_reason: str = Field(..., description="Reason why the file was skipped")

class IngestionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    extracted_files: List[str] = Field(default_factory=list)
    skipped_files: Dict[str, SkippedEntry] = Field(default_factory=dict)
    total_extracted_bytes: int = Field(0)
    total_extracted_count: int = Field(0)

class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Normalized relative path to the file")
    line_start: int = Field(..., description="1-indexed starting line number")
    line_end: int = Field(..., description="1-indexed ending line number (inclusive)")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("path must be a non-empty string")
        return v.strip()

    @field_validator("line_start")
    @classmethod
    def validate_line_start(cls, v: int) -> int:
        if v < 1:
            raise ValueError("line_start must be >= 1")
        return v

    @model_validator(mode="after")
    def validate_lines(self) -> "Location":
        if self.line_end < self.line_start:
            raise ValueError("line_end must be >= line_start")
        return self


SourceAgent = Literal[
    "preflight_secret_gate",
    "correctness_agent",
    "security_debate",
    "security_deterministic",
    "blast_radius_agent",
]

Perspective = Literal["preflight", "correctness", "security", "blast_radius"]

FindingStatus = Literal["active", "contested", "advisory"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Deterministic, collision-safe ID")
    source_agent: SourceAgent = Field(..., description="Agent that produced the finding")
    perspective: Perspective = Field(..., description="Review perspective")
    severity: Severity = Field(..., description="Standardized severity enum")
    location: Location = Field(..., description="Location of the finding in the source code")
    claim: str = Field(..., description="Summary of the issue or claim")
    evidence_ref: List[str] = Field(
        default_factory=list,
        description="Coordinates citing Source-of-Truth or codebase lines"
    )
    status: FindingStatus = Field("active", description="Status of the finding")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional metadata"
    )

    @field_validator("id", "claim")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Value must be a non-empty string")
        return v.strip()


class ReportFinding(Finding):
    model_config = ConfigDict(extra="forbid")

    recommended_next_action: Optional[str] = Field(
        None,
        description="Recommended next steps for the developer"
    )
    merged_from: List[str] = Field(
        default_factory=list,
        description="IDs of input findings merged into this consolidated finding"
    )


class GateFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Deterministic, collision-safe ID")
    source_agent: Literal["preflight_secret_gate"] = "preflight_secret_gate"
    perspective: Literal["security", "preflight"] = "security"
    severity: Severity = Field(..., description="Severity of secret exposure")
    location: Location = Field(..., description="Location of the secret")
    claim: str = Field(..., description="Summary of secret exposure claim")
    evidence_ref: List[str] = Field(default_factory=list)
    secret_type: str = Field(..., description="Type of secret (e.g. AWS Key, PEM)")
    fingerprint: str = Field(..., description="Salted hash fingerprint of the secret")
    exposure_status: Literal["prompt_exposed", "ignored_by_root_gitignore", "excluded_by_system"] = Field(
        ...,
        description="Exposure category from the ingestion exposure model"
    )

    @field_validator("id", "claim", "secret_type", "fingerprint")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Value must be a non-empty string")
        return v.strip()


class PerspectiveStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    perspective: Literal["correctness", "security", "blast_radius"]
    status: Literal["complete", "complete_limited", "skipped", "disabled", "unavailable", "failed"]
    reason: str = Field("", description="Reason for the status (especially if failed/skipped)")
    finding_ids: List[str] = Field(
        default_factory=list,
        description="IDs of findings emitted by this perspective"
    )


class GateStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "failed"]
    reason: Optional[str] = Field(None, description="Reason for the gate failure")
    finding_ids: List[str] = Field(
        default_factory=list,
        description="IDs of findings emitted by the gate"
    )


class MergeLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_id: str = Field(..., description="ID of the consolidated output finding")
    input_ids: List[str] = Field(
        ...,
        description="IDs of constituent input findings that were merged"
    )


class OmitLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="ID of the omitted finding")
    reason: str = Field(..., description="Reason why the finding was omitted")


class AccountingLedger(BaseModel):
    """
    Conservation ledger tracking every finding.
    
    NOTE: Conservation checks (e.g. that included U merged U omitted U contested covers all inputs)
    are logically enforced by the report validator in Task 14, not by this schema itself.
    """
    model_config = ConfigDict(extra="forbid")

    included: List[str] = Field(
        default_factory=list,
        description="IDs of findings included directly/verbatim"
    )
    merged: List[MergeLedgerEntry] = Field(
        default_factory=list,
        description="Consolidated findings mapping"
    )
    omitted: List[OmitLedgerEntry] = Field(
        default_factory=list,
        description="Omitted findings with justifications"
    )
    contested: List[str] = Field(
        default_factory=list,
        description="IDs of findings marked as contested"
    )


class ReviewReport(BaseModel):
    """
    Final review report containing all findings and metadata.
    
    NOTE: Structural conservation invariants (e.g. high_critical_findings subset of findings,
    severity_counts matches actual findings, and ledger completeness) are enforced
    programmatically by the validator in Task 14, not statically by this schema.
    """
    model_config = ConfigDict(extra="forbid")

    run_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the review execution run"
    )
    corpus_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics of the analyzed corpus"
    )
    perspective_statuses: List[PerspectiveStatus] = Field(
        default_factory=list,
        description="Execution status for each perspective"
    )
    gate_status: GateStatus = Field(..., description="Status of the secret gate scan")
    severity_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of findings grouped by standardized severity level"
    )
    high_critical_findings: List[ReportFinding] = Field(
        default_factory=list,
        description="List of high and critical severity findings"
    )
    findings: List[ReportFinding] = Field(
        default_factory=list,
        description="All findings included in the report"
    )
    contested_items: List[ReportFinding] = Field(
        default_factory=list,
        description="Debated findings marked as contested"
    )
    secret_scan_summary: List[GateFinding] = Field(
        default_factory=list,
        description="Summary of secret findings"
    )
    accounting_ledger: AccountingLedger = Field(
        ...,
        description="Conservation ledger tracking every finding"
    )
    validator_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings emitted during report validation"
    )

    @field_validator("severity_counts")
    @classmethod
    def validate_severity_counts(cls, v: Dict[str, int]) -> Dict[str, int]:
        valid_keys = {sev.value for sev in Severity}
        for key, val in v.items():
            if key not in valid_keys:
                raise ValueError(f"Invalid severity count key: {key}")
            if val < 0:
                raise ValueError(f"Count for {key} cannot be negative")
        return v


# Alias representing pre-coordinator / Specialist Finding written to shared state
# (referred to as ReviewFinding in specification document §2)
ReviewFinding = Finding

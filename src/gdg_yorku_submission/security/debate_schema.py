from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Literal, Optional, List, Dict, Any, Tuple
from gdg_yorku_submission.schemas import Finding
from gdg_yorku_submission.severity import Severity, is_at_or_above_floor

DebateResolution = Literal["survived", "defeated", "contested"]

class DebateMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["defender", "challenger", "system"] = Field(..., description="Role of the debater or system message")
    message: str = Field(..., description="Argument text / content")
    timestamp: Optional[str] = Field(None, description="Optional timestamp or reference")

    @field_validator("message")
    @classmethod
    def validate_non_empty_msg(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must be a non-empty string")
        return v

class DebateRound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(..., description="1-indexed round number")
    messages: List[DebateMessage] = Field(default_factory=list, description="Messages exchanged during this round")

    @field_validator("round_number")
    @classmethod
    def validate_round_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("round_number must be >= 1")
        return v

class DebateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding: Finding = Field(..., description="The finding being debated")
    resolution: Optional[DebateResolution] = Field(None, description="Outcome of the debate for this finding")
    closed_reason: Optional[str] = Field(None, description="Reason for closure/defeat (required if resolution is defeated)")

    @model_validator(mode="after")
    def validate_resolution_and_reason(self) -> "DebateCandidate":
        if self.resolution == "defeated":
            if not self.closed_reason or not self.closed_reason.strip():
                raise ValueError("closed_reason is required when finding is defeated")
        else:
            if self.closed_reason is not None:
                raise ValueError("closed_reason should only be provided when finding is defeated")
        return self

class DebateLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: List[DebateCandidate] = Field(default_factory=list, description="All debate candidates and their status")

    def validate_completeness(self) -> None:
        """
        Verifies that every candidate has a resolution.
        Raises ValueError if any candidate is unresolved (resolution is None).
        """
        unresolved = [c for c in self.candidates if c.resolution is None]
        if unresolved:
            unresolved_ids = [c.finding.id for c in unresolved]
            raise ValueError(f"Debate ledger has unresolved candidates: {unresolved_ids}")

    def get_survived(self) -> List[Finding]:
        """Returns findings that survived the debate (resolution == survived)."""
        survived_findings = []
        for c in self.candidates:
            if c.resolution == "survived":
                # Ensure status is active
                f = c.finding.model_copy(update={"status": "active"})
                survived_findings.append(f)
        return survived_findings

    def get_defeated(self) -> List[DebateCandidate]:
        """Returns candidates that were defeated."""
        return [c for c in self.candidates if c.resolution == "defeated"]

    def get_contested(self) -> List[Finding]:
        """
        Returns findings that are contested.
        These are findings with resolution == 'contested'.
        Also, high/critical findings that were defeated must be retained as contested.
        Defeat reasons for promoted findings are threaded into metadata.debate_closed_reason.
        """
        contested_findings = []
        for c in self.candidates:
            is_high_or_critical = is_at_or_above_floor(c.finding.severity)
            if c.resolution == "contested" or (c.resolution == "defeated" and is_high_or_critical):
                # Update finding status to contested
                meta = dict(c.finding.metadata or {})
                if c.resolution == "defeated" and c.closed_reason:
                    meta["debate_closed_reason"] = c.closed_reason
                f = c.finding.model_copy(update={"status": "contested", "metadata": meta})
                contested_findings.append(f)
        return contested_findings

    def get_contested_with_kcap(self, k: int = 3) -> Tuple[List[Finding], bool]:
        """
        Applies K-cap to below-floor contested items.
        Raises ValueError if k is negative.
        Returns:
            Tuple[List[Finding], bool]: (list of findings, high_only_notice flag)
            where high_only_notice is True if any below-floor findings were truncated.
        """
        if k < 0:
            raise ValueError("K-cap limit must be non-negative")
            
        all_contested = self.get_contested()
        
        above_floor = [f for f in all_contested if is_at_or_above_floor(f.severity)]
        below_floor = [f for f in all_contested if not is_at_or_above_floor(f.severity)]
        
        # Sort below-floor descending by severity rank
        below_floor.sort(key=lambda x: -x.severity.rank)
        
        high_only_notice = len(below_floor) > k
        allowed_below_floor = below_floor[:k]
        
        return above_floor + allowed_below_floor, high_only_notice

    def get_omitted(self) -> List[Dict[str, str]]:
        """
        Returns a list of dictionaries with 'id' and 'reason' for findings that are omitted.
        These are findings with resolution == 'defeated' that are NOT high/critical (i.e. below floor).
        """
        omitted_list = []
        for c in self.candidates:
            is_high_or_critical = is_at_or_above_floor(c.finding.severity)
            if c.resolution == "defeated" and not is_high_or_critical:
                omitted_list.append({
                    "id": c.finding.id,
                    "reason": c.closed_reason or "Defeated in debate"
                })
        return omitted_list

class DebateSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Unique ID for the debate session")
    ledger: DebateLedger = Field(default_factory=DebateLedger, description="Structured outcome ledger")
    rounds: List[DebateRound] = Field(default_factory=list, description="Rounds of arguments exchanged")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session-level metadata")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("session_id must be a non-empty string")
        return v.strip()

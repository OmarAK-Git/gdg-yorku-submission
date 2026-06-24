from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Literal, Optional, List, Dict, Any, Tuple
from gdg_yorku_submission.schemas import Finding
from gdg_yorku_submission.severity import Severity, is_at_or_above_floor

DebateResolution = Literal["survived", "defeated", "contested"]

class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    question: str = Field(..., description="The question in plain English")
    why_it_matters: str = Field(..., description="Why this question matters (one sentence)")
    recommended_default: str = Field(..., description="The recommended default answer")
    default_reasoning: str = Field(..., description="Reasoning for the recommended default")

class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: Optional[str] = Field(default=None, description="Deterministic ID, e.g. C-R1-P1")
    adversary: Optional[Literal["defender", "challenger"]] = Field(default=None, description="The proposer ('defender' or 'challenger')")
    text: str = Field(..., description="The proposed change or finding detail")
    severity: Severity = Field(..., description="The severity level of the proposal")
    groundednessCitation: str = Field(..., description="Where this is grounded, as a corpus path with a line anchor: 'path/to/file.py#START-END' (e.g. 'src/app.py#14-37'). The path must be a real corpus file and the lines must exist in it. Free-text forms like 'line 23' are tolerated, but the clean 'path#start-end' anchor is strongly preferred. Do not add prose after the line range.")
    reasoning: str = Field(..., description="The reasoning behind the proposal")

class OpponentScore(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    proposal_id: str = Field(..., description="The ID of the opponent's proposal being scored")
    verdict: Literal["accept", "modify", "reject"] = Field(..., description="Score verdict")
    reasoning: str = Field(..., description="Reasoning for the score")
    modification: Optional[str] = Field(default=None, description="Suggested modification text, required if verdict is modify")

    @model_validator(mode="after")
    def validate_modification_on_modify(self) -> "OpponentScore":
        if self.verdict == "modify":
            if not self.modification or not self.modification.strip():
                raise ValueError("modification is required when verdict is modify")
        return self

class TurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    summary: str = Field(..., description="Text summary of the turn analysis")
    opponent_scores: List[OpponentScore] = Field(default_factory=list, description="Scores for the opponent's previous proposals")
    new_proposals: List[Proposal] = Field(default_factory=list, description="New proposals from this turn")
    disagreements: List[str] = Field(default_factory=list, description="List of open/counter-arg disagreements that proposer has addressed")
    questions_for_human: List[Question] = Field(default_factory=list, description="Questions for the human if any")

class DebateMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    round_number: int = Field(..., description="1-indexed round number")
    messages: List[DebateMessage] = Field(default_factory=list, description="Messages exchanged during this round")
    
    # Sequential turns and Crucible metrics metadata
    defender_turn: Optional[TurnResponse] = Field(default=None, description="Defender's turn response")
    challenger_turn: Optional[TurnResponse] = Field(default=None, description="Challenger's turn response")
    working_prompt_after: Optional[str] = Field(default=None, description="Working prompt/guidelines state after this round")
    scores_this_round: Dict[str, float] = Field(default_factory=dict, description="Defender and challenger scores gained in this round")

    @field_validator("round_number")
    @classmethod
    def validate_round_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("round_number must be >= 1")
        return v

class DebateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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

class AdversaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    proposals: List[Proposal] = Field(default_factory=list, description="List of proposals from the adversary")
    questions_for_human: List[Question] = Field(default_factory=list, description="Questions for the human if any")


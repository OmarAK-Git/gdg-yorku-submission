import uuid
import logging
import hashlib
import secrets
from typing import List, Dict, Any, Callable, Tuple, Optional
from gdg_yorku_submission.schemas import Finding, Location
from gdg_yorku_submission.severity import Severity, is_at_or_above_floor
from gdg_yorku_submission.security.debate_schema import (
    DebateSession,
    DebateRound,
    DebateMessage,
    DebateCandidate,
    DebateLedger,
    AdversaryResponse,
    TurnResponse,
    Proposal,
    OpponentScore
)
from gdg_yorku_submission.security.debate_scoring import score_round, score_proposal
from gdg_yorku_submission.security.stop_condition import should_terminate
from gdg_yorku_submission.security.personas import DEFENDER_PERSONA, CHALLENGER_PERSONA, ANTI_SYCOPHANCY, ROUND_1_INSTRUCTIONS
from gdg_yorku_submission.security.gemini_adapter import call_gemini_adversary
from gdg_yorku_submission.security.claude_adapter import call_claude_adversary
from gdg_yorku_submission.budget import BudgetExhaustedError

logger = logging.getLogger(__name__)

SEQUENTIAL_INSTRUCTIONS = """
PHASE: SEQUENTIAL DEBATE TURN
You have seen your opponent's previous-turn proposals. Your job is to:

SCORE each opponent proposal as one of:
- "accept": this proposal is correct, grounded in the corpus, and represents a valid perspective.
- "modify": this has merit but needs adjustment. Provide the adjustment.
- "reject": this is incorrect, ungrounded, cosmetic, redundant, or not on an exploitable path. Explain why.

Do NOT silently drop any opponent proposal. Score every one.

PROPOSE new findings (if you are the Challenger) or usability/implementation constraints/assumptions (if you are the Defender). Same rules as round 1.
If you have NO new proposals AND zero open disagreements with the opponent, return an empty proposals array and an empty disagreements array. The orchestrator uses this signal to terminate.

Your output must be a valid JSON object matching this schema:
{
  "summary": "Brief summary of your turn",
  "opponent_scores": [
    {
      "proposal_id": "ID of opponent proposal being evaluated",
      "verdict": "accept" | "modify" | "reject",
      "reasoning": "Reasoning for the score",
      "modification": "Modification string (only required if verdict is modify)"
    }
  ],
  "new_proposals": [
    {
      "text": "The proposed change or finding detail",
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "groundednessCitation": "File path, function, or line number in the corpus, or 'original spec'",
      "reasoning": "Reasoning for the proposal"
    }
  ],
  "disagreements": [
    "Any addressed disagreements or counter-arguments resolving previous modify/reject feedback on your own proposals"
  ],
  "questions_for_human": [
    {
      "question": "The question in plain English",
      "why_it_matters": "Why it matters (one sentence)",
      "recommended_default": "Your recommended default answer",
      "default_reasoning": "The reasoning behind that default"
    }
  ]
}
Output ONLY the JSON object — no markdown fences.
"""

def get_system_prompt(role: str, persona: str, round_num: int) -> str:
    return f"Role: {role}\n\n{persona}\n\n{ANTI_SYCOPHANCY}\n\nROUND {round_num}\n{SEQUENTIAL_INSTRUCTIONS}"

def parse_location_from_citation(citation: str) -> Location:
    parts = citation.split("#")
    path = parts[0].strip() if parts[0].strip() else "unknown"
    line_start = 1
    line_end = 1
    if len(parts) > 1:
        line_parts = parts[1].split("-")
        try:
            line_start = int(line_parts[0])
            if len(line_parts) > 1:
                line_end = int(line_parts[1])
            else:
                line_end = line_start
        except ValueError:
            pass
    return Location(path=path, line_start=line_start, line_end=line_end)

async def run_debate_loop(
    orch,
    findings: List[Finding],
    defender_fn: Optional[Callable] = None,
    challenger_fn: Optional[Callable] = None,
    max_rounds: int = 5,
    session_id: Optional[str] = None
) -> DebateSession:
    """
    Executes the generative, AST-seeded Crucible debate loop for a list of candidate findings.
    Gemini is the defender (usability/ship-it advocate), Claude is the challenger (security hawk).
    """
    if not session_id:
        if findings:
            sorted_fids = sorted(f.id for f in findings)
            fid_hash = hashlib.sha256("".join(sorted_fids).encode()).hexdigest()[:8]
            session_id = f"session_{fid_hash}"
        else:
            session_id = f"session_{uuid.uuid4().hex[:8]}"

    # Fetch RedactionContext from the orchestrator for transcript/reason redaction
    redaction_ctx = orch.get_redaction_context() if hasattr(orch, "get_redaction_context") else None

    def redact_text(text: str) -> str:
        if redaction_ctx and isinstance(text, str):
            return redaction_ctx.redact(text)
        return text

    # Map deterministic AST findings to challenger's Round 1 proposals
    challenger_r1_proposals = []
    proposals_by_id: Dict[str, Proposal] = {}
    for idx, f in enumerate(findings, 1):
        citation = f.evidence_ref[0] if f.evidence_ref else "NONE"
        sev_str = f.severity.value if isinstance(f.severity, Severity) else str(f.severity)
        
        # Enforce severity validation / coercion
        try:
            sev_enum = Severity(sev_str)
        except ValueError:
            sev_enum = Severity.HIGH

        p = Proposal(
            id=f"C-R1-P{idx}",
            adversary="challenger",
            text=f.claim,
            severity=sev_enum,
            groundednessCitation=citation,
            reasoning=f.claim
        )
        challenger_r1_proposals.append(p)
        proposals_by_id[p.id] = p

    # Challenger turn response for Round 1
    challenger_r1_turn = TurnResponse(
        summary="Round 1 deterministic seed proposals",
        opponent_scores=[],
        new_proposals=challenger_r1_proposals,
        disagreements=[],
        questions_for_human=[]
    )

    # Let's get the codebase corpus text for prompts
    corpus = orch.get_corpus()
    from gdg_yorku_submission.prompts.evidence_plane import build_evidence_plane
    nonce = secrets.token_hex(16)
    corpus_block = build_evidence_plane(corpus, nonce)

    session = DebateSession(
        session_id=session_id,
        ledger=DebateLedger(candidates=[]),
        rounds=[],
        metadata={
            "max_rounds": max_rounds,
            "stop_reason": "max_rounds"
        }
    )

    try:
        # Intrinsic budget guard check before Round 1
        state = orch.read_state()
        budget_dict = state.get("budget")
        if budget_dict:
            from gdg_yorku_submission.budget import RunBudget
            budget = RunBudget(**budget_dict)
            if (
                budget.used_llm_calls >= budget.max_llm_calls or
                budget.used_cost_usd >= budget.max_cost_usd or
                budget.used_total_tokens >= budget.max_total_tokens
            ):
                session.metadata["stop_reason"] = "budget_exhausted"
                raise BudgetExhaustedError("Budget exhausted before Round 1")

        # Execute Defender Round 1 turn
        if defender_fn:
            # If callable is provided (for mock tests)
            res = defender_fn(orch, findings, [])
            if isinstance(res, str):
                defender_turn_resp = TurnResponse(
                    summary="Defender turn response",
                    opponent_scores=[],
                    new_proposals=[
                        Proposal(
                            id="D-R1-P1",
                            adversary="defender",
                            text=res,
                            severity=Severity.INFO,
                            groundednessCitation="NONE",
                            reasoning=res
                        )
                    ],
                    disagreements=[],
                    questions_for_human=[]
                )
            else:
                defender_turn_resp = res
        else:
            system_prompt = f"Role: Defender\n\n{DEFENDER_PERSONA}\n\n{ANTI_SYCOPHANCY}\n\nROUND 1\n{ROUND_1_INSTRUCTIONS}"
            user_content = (
                f"Here is the codebase corpus and initial security findings:\n\n"
                f"{corpus_block}\n\n"
                f"Please review and propose usability or implementation counter-arguments or assumptions."
            )
            defender_turn_resp = await call_gemini_adversary(
                orch, system_prompt, user_content, response_model=AdversaryResponse
            )
            # Adapt AdversaryResponse to TurnResponse
            defender_turn_resp = TurnResponse(
                summary="Round 1 initial proposals",
                opponent_scores=[],
                new_proposals=defender_turn_resp.proposals,
                disagreements=[],
                questions_for_human=defender_turn_resp.questions_for_human
            )

        # Set Defender proposal IDs and adversaries
        for i, p in enumerate(defender_turn_resp.new_proposals, 1):
            p.id = f"D-R1-P{i}"
            p.adversary = "defender"
            proposals_by_id[p.id] = p

        # Round 1 setup
        round_1_obj = DebateRound(
            round_number=1,
            defender_turn=defender_turn_resp,
            challenger_turn=challenger_r1_turn,
            scores_this_round={"defender": 0.0, "challenger": 0.0}
        )

        # Log/redact round 1 messages
        for p in challenger_r1_proposals:
            round_1_obj.messages.append(
                DebateMessage(role="challenger", message=redact_text(f"Proposed: {p.text} (Severity: {p.severity})"))
            )
        for p in defender_turn_resp.new_proposals:
            round_1_obj.messages.append(
                DebateMessage(role="defender", message=redact_text(f"Proposed: {p.text} (Severity: {p.severity})"))
            )

        session.rounds.append(round_1_obj)

    except BudgetExhaustedError as e:
        logger.warning(f"Debate loop hit budget limit at round 1: {e}")
        session.metadata["stop_reason"] = "budget_exhausted"
    except Exception as e:
        logger.error(f"Error during debate round 1: {e}", exc_info=True)
        session.metadata["stop_reason"] = f"error: {str(e)}"
        raise e

    # Check if Round 1 terminates early
    terminated, reason = should_terminate(session.rounds)
    if terminated:
        session.metadata["stop_reason"] = reason
    else:
        # Run sequential rounds 2 to 5
        for r in range(2, max_rounds + 1):
            # Intrinsic budget guard check before each round
            state = orch.read_state()
            budget_dict = state.get("budget")
            if budget_dict:
                from gdg_yorku_submission.budget import RunBudget
                budget = RunBudget(**budget_dict)
                if (
                    budget.used_llm_calls >= budget.max_llm_calls or
                    budget.used_cost_usd >= budget.max_cost_usd or
                    budget.used_total_tokens >= budget.max_total_tokens
                ):
                    session.metadata["stop_reason"] = "budget_exhausted"
                    break

            round_obj = DebateRound(round_number=r)

            # Format prior messages transcript
            messages_text = ""
            for prev_round in session.rounds:
                for msg in prev_round.messages:
                    messages_text += f"{msg.role}: {msg.message}\n"

            # 1. Defender Turn (Gemini)
            prev_round = session.rounds[-1]
            opp_proposals = prev_round.challenger_turn.new_proposals if prev_round.challenger_turn else []

            opp_content = "Opponent's previous-turn proposals to score:\n"
            for p in opp_proposals:
                opp_content += (
                    f"- ID: {p.id}\n"
                    f"  Text: {p.text}\n"
                    f"  Citation: {p.groundednessCitation}\n"
                    f"  Severity: {p.severity}\n"
                    f"  Reasoning: {p.reasoning}\n\n"
                )

            user_content = (
                f"{corpus_block}\n\n"
                f"Please review the following opponent proposals and context:\n"
                f'<opponent_context nonce="{nonce}">\n'
                f"{opp_content}\n"
                f"Prior Messages/Transcript:\n{messages_text}\n"
                f'</opponent_context nonce="{nonce}">\n'
            )

            try:
                if defender_fn:
                    defender_turn_resp = defender_fn(orch, findings, round_obj.messages)
                    if not isinstance(defender_turn_resp, TurnResponse):
                        defender_turn_resp = TurnResponse(
                            summary="Defender Turn",
                            opponent_scores=[OpponentScore(proposal_id=p.id, verdict="accept", reasoning="mock accept") for p in opp_proposals],
                            new_proposals=[],
                            disagreements=[],
                            questions_for_human=[]
                        )
                else:
                    system_prompt = get_system_prompt("Defender", DEFENDER_PERSONA, r)
                    defender_turn_resp = await call_gemini_adversary(
                        orch, system_prompt, user_content, response_model=TurnResponse
                    )

                # Set proposal IDs and adversaries
                for idx, p in enumerate(defender_turn_resp.new_proposals, 1):
                    p.id = f"D-R{r}-P{idx}"
                    p.adversary = "defender"
                    proposals_by_id[p.id] = p

                # Log to transcript
                for sc in defender_turn_resp.opponent_scores:
                    round_obj.messages.append(
                        DebateMessage(role="defender", message=redact_text(f"Scored {sc.proposal_id}: {sc.verdict} ({sc.reasoning})"))
                    )
                for p in defender_turn_resp.new_proposals:
                    round_obj.messages.append(
                        DebateMessage(role="defender", message=redact_text(f"Proposed: {p.text} (Severity: {p.severity})"))
                    )
                round_obj.defender_turn = defender_turn_resp

                # 2. Challenger Turn (Claude)
                opp_proposals = defender_turn_resp.new_proposals

                opp_content = "Opponent's previous-turn proposals to score:\n"
                for p in opp_proposals:
                    opp_content += (
                        f"- ID: {p.id}\n"
                        f"  Text: {p.text}\n"
                        f"  Citation: {p.groundednessCitation}\n"
                        f"  Severity: {p.severity}\n"
                        f"  Reasoning: {p.reasoning}\n\n"
                    )

                # Recalculate transcript with current round's defender messages included
                messages_text_with_def = messages_text
                for msg in round_obj.messages:
                    if msg.role == "defender":
                        messages_text_with_def += f"{msg.role}: {msg.message}\n"

                user_content = (
                    f"{corpus_block}\n\n"
                    f"Please review the following opponent proposals and context:\n"
                    f'<opponent_context nonce="{nonce}">\n'
                    f"{opp_content}\n"
                    f"Prior Messages/Transcript:\n{messages_text_with_def}\n"
                    f'</opponent_context nonce="{nonce}">\n'
                )

                if challenger_fn:
                    challenger_turn_resp = challenger_fn(orch, findings, round_obj.messages)
                    if not isinstance(challenger_turn_resp, TurnResponse):
                        challenger_turn_resp = TurnResponse(
                            summary="Challenger Turn",
                            opponent_scores=[OpponentScore(proposal_id=p.id, verdict="reject", reasoning="mock reject") for p in opp_proposals],
                            new_proposals=[],
                            disagreements=[],
                            questions_for_human=[]
                        )
                else:
                    system_prompt = get_system_prompt("Challenger", CHALLENGER_PERSONA, r)
                    challenger_turn_resp = await call_claude_adversary(
                        orch, system_prompt, user_content, response_model=TurnResponse
                    )

                # Set proposal IDs and adversaries
                for idx, p in enumerate(challenger_turn_resp.new_proposals, 1):
                    p.id = f"C-R{r}-P{idx}"
                    p.adversary = "challenger"
                    proposals_by_id[p.id] = p

                # Log to transcript
                for sc in challenger_turn_resp.opponent_scores:
                    round_obj.messages.append(
                        DebateMessage(role="challenger", message=redact_text(f"Scored {sc.proposal_id}: {sc.verdict} ({sc.reasoning})"))
                    )
                for p in challenger_turn_resp.new_proposals:
                    round_obj.messages.append(
                        DebateMessage(role="challenger", message=redact_text(f"Proposed: {p.text} (Severity: {p.severity})"))
                    )
                round_obj.challenger_turn = challenger_turn_resp

                # 3. Score this Round
                scores_gained = score_round(round_obj, proposals_by_id)
                round_obj.scores_this_round = scores_gained

                session.rounds.append(round_obj)

                # Check termination
                terminated, reason = should_terminate(session.rounds)
                if terminated:
                    session.metadata["stop_reason"] = reason
                    break

            except BudgetExhaustedError as e:
                logger.warning(f"Debate loop hit budget limit at round {r}: {e}")
                session.metadata["stop_reason"] = "budget_exhausted"
                break
            except Exception as e:
                logger.error(f"Error during debate round {r}: {e}", exc_info=True)
                session.metadata["stop_reason"] = f"error: {str(e)}"
                raise e

    # Post-Loop Resolution Mapping
    # Find all Challenger proposals across all rounds
    challenger_proposals = []
    for r_data in session.rounds:
        if r_data.challenger_turn:
            challenger_proposals.extend(r_data.challenger_turn.new_proposals)

    # Determine final verdict on each Challenger proposal
    candidates = []
    for p in challenger_proposals:
        # Search for the final verdict from Defender
        final_verdict = None
        final_reasoning = None

        for r_data in reversed(session.rounds):
            if r_data.defender_turn:
                for score_item in r_data.defender_turn.opponent_scores:
                    if score_item.proposal_id == p.id:
                        final_verdict = score_item.verdict
                        final_reasoning = score_item.reasoning
                        break
            if final_verdict:
                break

        # Check groundedness
        is_grounded = p.groundednessCitation not in (None, "", "NONE")
        is_above_floor = is_at_or_above_floor(p.severity)

        # Map verdict to resolution deterministically
        if final_verdict == "accept":
            res = "survived"
            closed_reason = None
        elif final_verdict == "reject":
            if not is_grounded:
                res = "defeated"
                closed_reason = redact_text(final_reasoning) if final_reasoning else "Defeated in debate (ungrounded)"
            else:
                if is_above_floor:
                    res = "contested"
                    closed_reason = None
                else:
                    res = "defeated"
                    closed_reason = redact_text(final_reasoning) if final_reasoning else "Defeated in debate (below floor)"
        else:
            # modify, unresolved or no verdict (None)
            res = "contested"
            closed_reason = None

        # Map Proposal to Finding
        # Check if it was seeded from a deterministic baseline finding
        original_finding = None
        for f in findings:
            citation = f.evidence_ref[0] if f.evidence_ref else "NONE"
            if p.text == f.claim and p.groundednessCitation == citation:
                original_finding = f
                break

        if original_finding:
            # Preserve original finding properties, update status and metadata
            finding = original_finding.model_copy()
        else:
            # Generative finding: derive provisional ID deterministically from stable anchor (citation + claim hash)
            citation_str = p.groundednessCitation if p.groundednessCitation else "NONE"
            
            evidence_refs = []
            loc_path = "unknown"
            loc_start = 1
            loc_end = 1
            resolved_valid = False
            
            if citation_str != "NONE":
                raw_citation = citation_str
                if raw_citation.startswith("file:"):
                    raw_citation = raw_citation[5:]
                parts = raw_citation.split("#")
                raw_path = parts[0].strip()
                
                # Normalize path
                normalized_raw_path = raw_path.replace("\\", "/").lower()
                
                # Check corpus
                corpus = orch.get_corpus() if hasattr(orch, "get_corpus") else {}
                matched_key = None
                for k in corpus.keys():
                    if k.lower() == normalized_raw_path:
                        matched_key = k
                        break
                        
                if matched_key:
                    corpus_file = corpus[matched_key]
                    line_start = 1
                    line_end = 1
                    if len(parts) > 1:
                        line_parts = parts[1].split("-")
                        try:
                            line_start = int(line_parts[0])
                            if len(line_parts) > 1:
                                line_end = int(line_parts[1])
                            else:
                                line_end = line_start
                        except ValueError:
                            pass
                            
                    # Bounds check
                    if 1 <= line_start <= line_end <= corpus_file.original_line_count:
                        loc_path = matched_key
                        loc_start = line_start
                        loc_end = line_end
                        evidence_refs = [f"file:{matched_key}#{line_start}-{line_end}"]
                        resolved_valid = True

            if not resolved_valid:
                logger.warning(
                    f"Dropping ungrounded/invalid generative finding proposal: claim={p.text}, citation={citation_str}"
                )
                continue

            stable_hash = hashlib.sha256(f"{citation_str}:{p.text}".encode("utf-8")).hexdigest()
            finding_id = f"security-{stable_hash[:12]}"
            
            # Coerce severity to standard enum
            try:
                sev_enum = Severity(p.severity)
            except ValueError:
                sev_enum = Severity.HIGH
                
            loc = Location(path=loc_path, line_start=loc_start, line_end=loc_end)
            
            finding = Finding(
                id=finding_id,
                source_agent="security_debate",
                perspective="security",
                severity=sev_enum,
                location=loc,
                claim=p.text,
                evidence_ref=evidence_refs,
                status="active"
            )

        # Preserve defender's pushback reasoning in finding metadata if rejected/modified
        if final_verdict in ("reject", "modify") and final_reasoning:
            meta = dict(finding.metadata or {})
            meta["debate_closed_reason"] = redact_text(final_reasoning)
            finding.metadata = meta

        candidate = DebateCandidate(
            finding=finding,
            resolution=res,
            closed_reason=closed_reason
        )
        candidates.append(candidate)

    # Set candidates in ledger
    session.ledger.candidates = candidates

    # Run validations
    session.ledger.validate_completeness()
    session = DebateSession.model_validate(session.model_dump())

    return session

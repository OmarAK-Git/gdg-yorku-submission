import logging
from typing import Dict, Any
from gdg_yorku_submission.security.debate_schema import Proposal, DebateRound
from gdg_yorku_submission.severity import Severity

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "critical": 10.0,
    "high": 5.0,
    "medium": 2.0,
    "low": 1.0,
    "info": 0.5
}

ACCEPTANCE_FACTORS = {
    "accept": 1.0,
    "modify": 0.6,
    "reject": 0.0
}

def score_proposal(proposal: Proposal, opponent_verdict: str) -> float:
    """
    Computes the score for a single proposal based on severity, groundedness, and opponent verdict.
    Formula: score = severity_weight * groundedness_multiplier * acceptance_factor
    """
    severity_val = proposal.severity
    if isinstance(severity_val, Severity):
        severity = severity_val.value.lower()
    else:
        severity = str(severity_val).lower()
        
    sev_weight = SEVERITY_WEIGHTS.get(severity, 2.0)
    
    # Groundedness multiplier: 1.0 if not "NONE" and >= 3 characters of non-whitespace; 0.2 otherwise.
    citation = (proposal.groundednessCitation or "").strip()
    is_grounded = len(citation) >= 3 and citation.upper() != "NONE"
    ground_mult = 1.0 if is_grounded else 0.2
    
    # Acceptance factor
    verdict = (opponent_verdict or "reject").lower()
    accept_factor = ACCEPTANCE_FACTORS.get(verdict, 0.0)
    
    return sev_weight * ground_mult * accept_factor

def score_round(round_data: DebateRound, proposals_by_id: dict) -> dict:
    """
    Calculates the scores gained by defender and challenger in this round.

    Enforces the no-self-scoring guarantee: a scorer never earns points for its
    own proposals. Real LLMs occasionally violate the scoring convention (e.g.
    the defender returning a score for one of its own ``D-`` proposals), so such
    invalid scores are skipped with a warning rather than crashing the whole
    debate loop into the AST fallback.
    """
    defender_gain = 0.0
    challenger_gain = 0.0

    # Defender's turn scores Challenger's proposals -> Challenger gets the points
    if round_data.defender_turn:
        for score_item in round_data.defender_turn.opponent_scores:
            # Self-scoring guard (convention): defender may only score C- proposals.
            if not score_item.proposal_id.startswith("C-"):
                logger.warning(
                    "Skipping invalid self-score: Defender (scorer) cannot score "
                    "their own proposal %s (convention guard).",
                    score_item.proposal_id,
                )
                continue

            proposal = proposals_by_id.get(score_item.proposal_id)
            if proposal:
                # Self-scoring guard (schema): defender may only score non-defender proposals.
                if proposal.adversary == "defender":
                    logger.warning(
                        "Skipping invalid self-score: Defender (scorer) cannot score "
                        "their own proposal %s (schema guard).",
                        proposal.id,
                    )
                    continue
                challenger_gain += score_proposal(proposal, score_item.verdict)

    # Challenger's turn scores Defender's proposals -> Defender gets the points
    if round_data.challenger_turn:
        for score_item in round_data.challenger_turn.opponent_scores:
            # Self-scoring guard (convention): challenger may only score D- proposals.
            if not score_item.proposal_id.startswith("D-"):
                logger.warning(
                    "Skipping invalid self-score: Challenger (scorer) cannot score "
                    "their own proposal %s (convention guard).",
                    score_item.proposal_id,
                )
                continue

            proposal = proposals_by_id.get(score_item.proposal_id)
            if proposal:
                # Self-scoring guard (schema): challenger may only score non-challenger proposals.
                if proposal.adversary == "challenger":
                    logger.warning(
                        "Skipping invalid self-score: Challenger (scorer) cannot score "
                        "their own proposal %s (schema guard).",
                        proposal.id,
                    )
                    continue
                defender_gain += score_proposal(proposal, score_item.verdict)

    return {"defender": defender_gain, "challenger": challenger_gain}

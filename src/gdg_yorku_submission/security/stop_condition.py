from typing import List, Tuple, Optional, Dict
from gdg_yorku_submission.security.debate_schema import DebateRound, Proposal
from gdg_yorku_submission.security.debate_scoring import SEVERITY_WEIGHTS
from gdg_yorku_submission.severity import Severity, is_at_or_above_floor

def get_proposal_max_score(p: Proposal) -> float:
    """
    Helper to calculate the maximum potential score of a single proposal.
    Formula: severity_weight * groundedness_multiplier * 1.0 (since max acceptance factor is 1.0)
    """
    severity_val = p.severity
    if isinstance(severity_val, Severity):
        severity = severity_val.value.lower()
    else:
        severity = str(severity_val).lower()
        
    weight = SEVERITY_WEIGHTS.get(severity, 2.0)
    cit = (p.groundednessCitation or "").strip()
    is_grounded = len(cit) >= 3 and cit.upper() != "NONE"
    mult = 1.0 if is_grounded else 0.2
    return weight * mult

def get_proposals_evaluated_in_round(round_num: int, rounds: List[DebateRound]) -> List[Proposal]:
    """
    Returns a list of all proposals evaluated in a given round number.
    In the sequential debate loop:
    - Defender's turn in Round N scores Challenger's proposals proposed in Round N-1.
    - Challenger's turn in Round N scores Defender's proposals proposed in Round N.
    """
    evaluated = []
    # Challenger's proposals proposed in Round N-1 are evaluated in Round N
    if round_num > 1 and len(rounds) >= round_num - 1:
        prev_r = rounds[round_num - 2]
        if prev_r.challenger_turn:
            evaluated.extend(prev_r.challenger_turn.new_proposals)
    # Defender's proposals proposed in Round N are evaluated in Round N
    if len(rounds) >= round_num:
        curr_r = rounds[round_num - 1]
        if curr_r.defender_turn:
            evaluated.extend(curr_r.defender_turn.new_proposals)
    return evaluated

def should_terminate(rounds: List[DebateRound]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates the termination conditions per the spec and returns (should_terminate, reason).
    """
    if not rounds:
        return False, None
        
    # Condition 2: Hard cap of 5 rounds
    if len(rounds) >= 5:
        return True, "Hard cap of 5 rounds reached."
        
    # Get latest round
    r_N = rounds[-1]
    
    # Condition 1: Both adversaries returned empty new proposals in the current round
    if r_N.defender_turn and r_N.challenger_turn:
        def_empty = len(r_N.defender_turn.new_proposals) == 0
        chal_empty = len(r_N.challenger_turn.new_proposals) == 0
        
        if def_empty and chal_empty:
            return True, "Both adversaries returned empty proposals and all previous round disagreements were addressed."

    # Conditions that require at least 2 rounds
    if len(rounds) >= 2:
        r_N_prev = rounds[-2]
        
        # Check delta/score convergence
        props_N = get_proposals_evaluated_in_round(r_N.round_number, rounds)
        props_prev = get_proposals_evaluated_in_round(r_N_prev.round_number, rounds)
        
        t_max_N = sum(get_proposal_max_score(p) for p in props_N)
        t_max_prev = sum(get_proposal_max_score(p) for p in props_prev)
        
        max_possible_delta = max(t_max_N, t_max_prev)
        
        actual_N = sum(r_N.scores_this_round.values())
        actual_prev = sum(r_N_prev.scores_this_round.values())
        actual_delta = abs(actual_N - actual_prev)
        
        is_converged = False
        if max_possible_delta > 0.0 and actual_delta < 0.05 * max_possible_delta:
            is_converged = True
            
        # Check stability: no critical/important (at-or-above-floor) proposals for 2 consecutive rounds
        def has_no_floor_proposals(r: DebateRound) -> bool:
            for turn in [r.defender_turn, r.challenger_turn]:
                if turn:
                    for p in turn.new_proposals:
                        if is_at_or_above_floor(p.severity):
                            return False
            return True
            
        no_new_floor_proposals = has_no_floor_proposals(r_N) and has_no_floor_proposals(r_N_prev)
        
        # Conjunction of score convergence AND stability (no floor proposals)
        if is_converged and no_new_floor_proposals:
            return True, (
                f"Score convergence and stability met: actual delta {actual_delta:.2f} "
                f"is below 5% of max possible delta {max_possible_delta:.2f} AND no critical/high "
                f"proposals generated for 2 consecutive rounds."
            )
            
    return False, None


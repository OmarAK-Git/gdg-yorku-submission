import os
import logging
from typing import List, Tuple, Any, Callable
from gdg_yorku_submission.schemas import ReviewFinding
from gdg_yorku_submission.security.deterministic import make_security_specialist as make_deterministic_specialist

logger = logging.getLogger(__name__)

def make_security_specialist(orch: Any) -> Callable[[], Any]:
    """
    Returns the security specialist Callable.
    Executes the deterministic AST baseline first, seeds the debate loop with those findings,
    runs the LLM debate if enabled, and falls back to the AST baseline on exceptions or lease failures.
    """
    async def security_specialist() -> Tuple[List[ReviewFinding], str, str]:
        # 1. Run deterministic baseline scan first
        baseline_func = make_deterministic_specialist(orch)
        baseline_findings, status, reason = baseline_func()

        # 2. Check if we should upgrade to debate loop
        enable_debate = os.getenv("ENABLE_SECURITY_DEBATE", "false").lower() == "true"
        if not enable_debate:
            return baseline_findings, status, reason

        # Run debate loop inside anyio/asyncio
        from gdg_yorku_submission.security.debate import run_debate_loop
        
        try:
            session = await run_debate_loop(orch, baseline_findings)
            
            # Extract findings from the ledger
            survived = session.ledger.get_survived()
            contested, high_only_notice = session.ledger.get_contested_with_kcap()
            
            # Group all final findings
            final_findings = survived + contested
            
            if high_only_notice:
                notice = "Contested K-cap truncation limit (3) exceeded; below-floor findings omitted."
                reason = f"{reason}; {notice}" if reason else notice
            
            final_status = "complete" if not reason else "complete_limited"
            return final_findings, final_status, reason
            
        except Exception as e:
            # On any failure, degrade gracefully to the baseline AST results (fallback)
            logger.warning(f"Debate loop failed with {type(e).__name__}: {e}. Gracefully falling back to AST baseline.")
            notice = f"Security debate failed: {type(e).__name__}: {e}. Fell back to AST baseline."
            new_reason = f"{reason}; {notice}" if reason else notice
            return baseline_findings, "complete_limited", new_reason

    return security_specialist

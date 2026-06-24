from pydantic import BaseModel, Field
from typing import Literal, Dict, Any

class RunBudget(BaseModel):
    max_total_tokens: int = Field(200000, description="Max total tokens across all LLM calls")
    max_gemini_tokens: int = Field(160000, description="Max tokens for Gemini model calls")
    max_claude_tokens: int = Field(40000, description="Max tokens for Claude model calls")
    max_llm_calls: int = Field(20, description="Max number of LLM calls allowed")
    max_cost_usd: float = Field(4.0, description="Max total cost in USD")
    
    used_total_tokens: int = Field(0, description="Total tokens used so far")
    used_gemini_tokens: int = Field(0, description="Gemini tokens used so far")
    used_claude_tokens: int = Field(0, description="Claude tokens used so far")
    used_llm_calls: int = Field(0, description="Number of LLM calls made so far")
    used_cost_usd: float = Field(0.0, description="Total cost in USD spent so far")

class BudgetLease(BaseModel):
    component: str = Field(..., description="The component requesting the lease (e.g. correctness_agent)")
    estimated_tokens: int = Field(..., description="Estimated tokens for this call")
    provider: Literal["gemini", "claude"] = Field(..., description="The LLM provider")

class BudgetExhaustedError(Exception):
    """Exception raised when an LLM call would exceed the configured budget."""
    pass

def acquire_budget_lease(orch, lease: BudgetLease) -> None:
    """
    Checks if a lease can be acquired under the current budget.
    If allowed, increments the call counter and saves the state.
    Otherwise, raises BudgetExhaustedError.
    """
    state = orch.read_state()
    budget_dict = state.get("budget")
    if not budget_dict:
        budget = RunBudget()
    else:
        budget = RunBudget(**budget_dict)
        
    if lease.provider == "gemini":
        projected_cost = lease.estimated_tokens * 0.30 / 1_000_000
    elif lease.provider == "claude":
        projected_cost = lease.estimated_tokens * 15.00 / 1_000_000
    else:
        projected_cost = 0.0

    # Reservation for coordinator compiler (R7)
    reserve_llm_calls = 1
    reserve_tokens = 4000
    reserve_cost_usd = 0.005

    # Scale down reservations if the configured limits are smaller than the reserve
    if budget.max_llm_calls <= reserve_llm_calls:
        reserve_llm_calls = 0
    if budget.max_total_tokens <= reserve_tokens:
        reserve_tokens = 0
    if budget.max_gemini_tokens <= reserve_tokens:
        reserve_tokens = 0
    if budget.max_cost_usd <= reserve_cost_usd:
        reserve_cost_usd = 0.0

    # Determine projected usage including coordinator reservation if not coordinator
    check_llm_calls = budget.used_llm_calls + 1
    check_total_tokens = budget.used_total_tokens + lease.estimated_tokens
    check_gemini_tokens = budget.used_gemini_tokens + (lease.estimated_tokens if lease.provider == "gemini" else 0)
    check_cost = budget.used_cost_usd + projected_cost

    if lease.component != "coordinator":
        check_llm_calls += reserve_llm_calls
        check_total_tokens += reserve_tokens
        # Coordinator always uses Gemini
        check_gemini_tokens += reserve_tokens
        check_cost += reserve_cost_usd

    if check_cost > budget.max_cost_usd:
        raise BudgetExhaustedError(
            f"Budget exceeded: projected cost would exceed max_cost_usd cap "
            f"({check_cost:.6f} > {budget.max_cost_usd})"
        )

    if check_llm_calls > budget.max_llm_calls:
        raise BudgetExhaustedError(
            f"Budget exceeded: maximum LLM calls cap reached ({check_llm_calls} > {budget.max_llm_calls})"
        )
        
    if check_total_tokens > budget.max_total_tokens:
        raise BudgetExhaustedError(
            f"Budget exceeded: estimated tokens would exceed max_total_tokens cap "
            f"({check_total_tokens} > {budget.max_total_tokens})"
        )
        
    if lease.provider == "gemini" or lease.component != "coordinator":
        if check_gemini_tokens > budget.max_gemini_tokens:
            raise BudgetExhaustedError(
                f"Budget exceeded: estimated tokens would exceed max_gemini_tokens cap "
                f"({check_gemini_tokens} > {budget.max_gemini_tokens})"
            )
    
    if lease.provider == "claude":
        if budget.used_claude_tokens + lease.estimated_tokens > budget.max_claude_tokens:
            raise BudgetExhaustedError(
                f"Budget exceeded: estimated tokens would exceed max_claude_tokens cap "
                f"({budget.used_claude_tokens + lease.estimated_tokens} > {budget.max_claude_tokens})"
            )
            
    budget.used_llm_calls += 1
    
    raw_state = orch._get_state()
    raw_state["budget"] = budget.model_dump()
    if "run_metadata" not in raw_state or raw_state["run_metadata"] is None:
        raw_state["run_metadata"] = {}
    raw_state["run_metadata"]["budget"] = budget.model_dump()
    orch._save_state(raw_state)

def record_llm_usage(orch, provider: str, tokens_used: int, cost_usd: float) -> None:
    """
    Updates the budget usage with actual token count and cost from a completed LLM call.
    """
    raw_state = orch._get_state()
    budget_dict = raw_state.get("budget")
    if not budget_dict:
        budget = RunBudget()
    else:
        budget = RunBudget(**budget_dict)
        
    budget.used_total_tokens += tokens_used
    if provider == "gemini":
        budget.used_gemini_tokens += tokens_used
    elif provider == "claude":
        budget.used_claude_tokens += tokens_used
        
    budget.used_cost_usd += cost_usd
    
    raw_state["budget"] = budget.model_dump()
    if "run_metadata" not in raw_state or raw_state["run_metadata"] is None:
        raw_state["run_metadata"] = {}
    raw_state["run_metadata"]["budget"] = budget.model_dump()
    orch._save_state(raw_state)

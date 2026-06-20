from pydantic import BaseModel, Field
from typing import Literal, Dict, Any

class RunBudget(BaseModel):
    max_total_tokens: int = Field(100000, description="Max total tokens across all LLM calls")
    max_gemini_tokens: int = Field(80000, description="Max tokens for Gemini model calls")
    max_claude_tokens: int = Field(20000, description="Max tokens for Claude model calls")
    max_llm_calls: int = Field(10, description="Max number of LLM calls allowed")
    max_cost_usd: float = Field(2.0, description="Max total cost in USD")
    
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

    if budget.used_cost_usd + projected_cost > budget.max_cost_usd:
        raise BudgetExhaustedError(
            f"Budget exceeded: projected cost would exceed max_cost_usd cap "
            f"({budget.used_cost_usd + projected_cost:.6f} > {budget.max_cost_usd})"
        )

    if budget.used_llm_calls + 1 > budget.max_llm_calls:
        raise BudgetExhaustedError(
            f"Budget exceeded: maximum LLM calls cap reached ({budget.max_llm_calls})"
        )
        
    if budget.used_total_tokens + lease.estimated_tokens > budget.max_total_tokens:
        raise BudgetExhaustedError(
            f"Budget exceeded: estimated tokens would exceed max_total_tokens cap "
            f"({budget.used_total_tokens + lease.estimated_tokens} > {budget.max_total_tokens})"
        )
        
    if lease.provider == "gemini":
        if budget.used_gemini_tokens + lease.estimated_tokens > budget.max_gemini_tokens:
            raise BudgetExhaustedError(
                f"Budget exceeded: estimated tokens would exceed max_gemini_tokens cap "
                f"({budget.used_gemini_tokens + lease.estimated_tokens} > {budget.max_gemini_tokens})"
            )
    elif lease.provider == "claude":
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

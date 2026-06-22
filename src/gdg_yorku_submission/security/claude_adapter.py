import os
import json
import logging
from typing import Any, Optional
from gdg_yorku_submission.budget import BudgetLease, acquire_budget_lease, record_llm_usage

logger = logging.getLogger(__name__)

def clean_json_string(text: str) -> str:
    """Strips markdown code block backticks if present."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text

async def call_claude_adversary(
    orch,
    system_prompt: str,
    user_content: str,
    response_model: Any,
    model: Optional[str] = None
) -> Any:
    """
    Calls the Claude adapter asynchronously.
    Routes every call through acquire_budget_lease + record_llm_usage.
    Enforce budget lease using provider='claude'.
    """
    estimated_input_tokens = len(system_prompt + user_content) // 4 + 1000
    estimated_output_tokens = 1000
    total_estimated = estimated_input_tokens + estimated_output_tokens

    # Acquire budget lease
    lease = BudgetLease(
        component="challenger",
        estimated_tokens=total_estimated,
        provider="claude"
    )
    acquire_budget_lease(orch, lease)

    use_fake = os.getenv("USE_FAKE_LLM", "false").lower() == "true"

    if use_fake:
        # Generate dummy response conforming to the expected model
        if hasattr(response_model, "__name__") and response_model.__name__ == "AdversaryResponse":
            dummy = {
                "proposals": [
                    {
                        "text": "Claude security flaw recommendation",
                        "severity": "high",
                        "groundednessCitation": "src/app.py#20-30",
                        "reasoning": "Standard security SQLi assertion"
                    }
                ],
                "questions_for_human": []
            }
        else:
            dummy = {
                "summary": "Challenger turn summary",
                "opponent_scores": [],
                "new_proposals": [],
                "disagreements": [],
                "questions_for_human": []
            }
        
        # Record usage
        # Claude Sonnet Pricing: Input: $3/1M, Output: $15/1M
        cost = (estimated_input_tokens * 3.0 / 1_000_000) + (estimated_output_tokens * 15.0 / 1_000_000)
        record_llm_usage(orch, "claude", total_estimated, cost)
        return response_model.model_validate(dummy)

    # Real Claude call
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)
    
    if not model:
        model = os.getenv("CRUCIBLE_CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    response = await client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_content}
        ]
    )
    
    content = response.content[0].text
    
    input_tokens = estimated_input_tokens
    output_tokens = estimated_output_tokens
    if response.usage:
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        
    actual_tokens = input_tokens + output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
    record_llm_usage(orch, "claude", actual_tokens, cost)

    cleaned = clean_json_string(content)
    try:
        data = json.loads(cleaned)
        return response_model.model_validate(data)
    except Exception as e:
        logger.error(f"Claude returned malformed response: {content[:500]}")
        raise ValueError(f"Claude returned malformed JSON: {e}")

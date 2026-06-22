import os
import json
import logging
import secrets
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

async def call_gemini_adversary(
    orch,
    system_prompt: str,
    user_content: str,
    response_model: Any,
    model: Optional[str] = None
) -> Any:
    """
    Calls the Gemini adapter asynchronously.
    Routes every call through acquire_budget_lease + record_llm_usage.
    Enforce budget lease using provider='gemini'.
    """
    estimated_input_tokens = len(system_prompt + user_content) // 4 + 1000
    estimated_output_tokens = 1000
    total_estimated = estimated_input_tokens + estimated_output_tokens

    # Acquire budget lease
    lease = BudgetLease(
        component="defender",
        estimated_tokens=total_estimated,
        provider="gemini"
    )
    acquire_budget_lease(orch, lease)

    use_fake = os.getenv("USE_FAKE_LLM", "false").lower() == "true"

    if use_fake:
        # Generate dummy response conforming to the expected model
        if hasattr(response_model, "__name__") and response_model.__name__ == "AdversaryResponse":
            dummy = {
                "proposals": [
                    {
                        "text": "Gemini usability recommendation",
                        "severity": "info",
                        "groundednessCitation": "src/app.py#5-10",
                        "reasoning": "Standard usability layout assertion"
                    }
                ],
                "questions_for_human": []
            }
        else:
            dummy = {
                "summary": "Defender turn summary",
                "opponent_scores": [],
                "new_proposals": [],
                "disagreements": [],
                "questions_for_human": []
            }
        
        # Record usage
        # Input: $0.075/1M, Output: $0.30/1M
        cost = (estimated_input_tokens * 0.075 / 1_000_000) + (estimated_output_tokens * 0.30 / 1_000_000)
        record_llm_usage(orch, "gemini", total_estimated, cost)
        return response_model.model_validate(dummy)

    # Real Gemini call
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    if not model:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Combine system prompt with instructions or set as system instruction
    generation_config = {
        "response_mime_type": "application/json"
    }
    
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
        generation_config=generation_config
    )
    
    # Run the generation in an executor since it's a blocking client call
    import anyio
    
    def sync_generate():
        return gemini_model.generate_content(user_content)
        
    response = await anyio.to_thread.run_sync(sync_generate)
    
    content = response.text
    
    input_tokens = estimated_input_tokens
    output_tokens = estimated_output_tokens
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        
    actual_tokens = input_tokens + output_tokens
    cost = (input_tokens * 0.075 / 1_000_000) + (output_tokens * 0.30 / 1_000_000)
    record_llm_usage(orch, "gemini", actual_tokens, cost)

    cleaned = clean_json_string(content)
    try:
        data = json.loads(cleaned)
        return response_model.model_validate(data)
    except Exception as e:
        logger.error(f"Gemini returned malformed response: {content[:500]}")
        raise ValueError(f"Gemini returned malformed JSON: {e}")

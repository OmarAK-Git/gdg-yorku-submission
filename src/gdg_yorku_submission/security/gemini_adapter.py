import os
import json
import logging
import secrets
from typing import Any, Optional
from gdg_yorku_submission.budget import BudgetLease, acquire_budget_lease, record_llm_usage

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
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
    model_name = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    import anyio
    from google import genai
    from google.genai import types

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    api_key = os.getenv("GEMINI_API_KEY")

    if project:
        client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        logger.info("Using google.genai Client with Vertex AI (ADC).")
    elif api_key:
        client = genai.Client(
            api_key=api_key
        )
        logger.info("Using google.genai Client with API Key.")
    else:
        raise ValueError(
            "Neither GOOGLE_CLOUD_PROJECT (for Vertex AI ADC) nor GEMINI_API_KEY "
            "environment variables were detected."
        )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=response_model
    )

    def sync_call_genai():
        return client.models.generate_content(
            model=model_name,
            contents=user_content,
            config=config
        )

    try:
        response = await anyio.to_thread.run_sync(sync_call_genai)
        content = response.text
    except Exception as e:
        logger.error(f"google.genai adversary call failed. Error: {e}")
        raise ValueError(f"google.genai call failed: {e}")
    finally:
        # Release the (synchronous) genai client so its transport is not reported
        # as an unclosed socket at GC. Only the sync side is exercised here.
        try:
            client.close()
        except Exception:
            pass

    input_tokens = estimated_input_tokens
    output_tokens = estimated_output_tokens
    if response and hasattr(response, "usage_metadata") and response.usage_metadata:
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

import os
import json
import inspect
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
        # Claude Opus 4.8 pricing: input $5/1M, output $25/1M
        cost = (estimated_input_tokens * 5.0 / 1_000_000) + (estimated_output_tokens * 25.0 / 1_000_000)
        record_llm_usage(orch, "claude", total_estimated, cost)
        return response_model.model_validate(dummy)

    # Real Claude call
    model_name = model or os.getenv("CRUCIBLE_CLAUDE_MODEL", "claude-opus-4-8")
    
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    client = None

    # Toggle: force the direct Anthropic API (api.anthropic.com) and bypass Vertex
    # entirely. Use this when the Vertex/GCP plumbing is failing (e.g. 429s) so the
    # demo can run to completion on an ANTHROPIC_API_KEY. Set CLAUDE_USE_ANTHROPIC_API=true.
    force_anthropic_api = os.getenv("CLAUDE_USE_ANTHROPIC_API", "false").lower() == "true"

    using_vertex = False

    # Try Google Cloud Vertex (ADC) first if GOOGLE_CLOUD_PROJECT is set, unless the
    # toggle forces the direct Anthropic API path.
    if project and not force_anthropic_api:
        try:
            from anthropic import AsyncAnthropicVertex
            client = AsyncAnthropicVertex(project_id=project, region=location)
            using_vertex = True
            logger.info("Using AsyncAnthropicVertex client for adversary call.")
        except Exception as e:
            logger.warning(f"Failed to initialize AsyncAnthropicVertex: {e}. Trying fallback AsyncAnthropic...")

    if not client:
        if api_key:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=api_key)
            logger.info("Using standard AsyncAnthropic client for adversary call.")
        else:
            raise ValueError(
                "Neither GOOGLE_CLOUD_PROJECT (for Vertex AI ADC) nor ANTHROPIC_API_KEY "
                "environment variables were detected."
            )

    create_kwargs = {
        "model": model_name,
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "output_config": {
            "effort": os.getenv("CRUCIBLE_CLAUDE_EFFORT", "medium")
        }
    }

    try:
        try:
            response = await client.messages.create(**create_kwargs)
        except Exception as e:
            # Runtime fallback: if the Vertex endpoint is rate-limited (429), retry
            # the call once on the direct Anthropic API so a mid-debate quota error
            # doesn't discard the whole security perspective. Requires ANTHROPIC_API_KEY.
            is_rate_limit = getattr(e, "status_code", None) == 429 or "429" in str(e)
            if using_vertex and is_rate_limit and api_key:
                logger.warning(
                    "Vertex returned 429 (quota exhausted). Falling back to the direct "
                    "Anthropic API for this call."
                )
                old_client = client
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=api_key)
                using_vertex = False
                # Close the rate-limited Vertex client's transport.
                old_closer = getattr(old_client, "close", None)
                if old_closer is not None:
                    try:
                        maybe = old_closer()
                        if inspect.isawaitable(maybe):
                            await maybe
                    except Exception:
                        pass
                response = await client.messages.create(**create_kwargs)
            else:
                raise
        content = response.content[0].text

        input_tokens = estimated_input_tokens
        output_tokens = estimated_output_tokens
        if response.usage:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

        actual_tokens = input_tokens + output_tokens
        cost = (input_tokens * 5.0 / 1_000_000) + (output_tokens * 25.0 / 1_000_000)
        record_llm_usage(orch, "claude", actual_tokens, cost)

        cleaned = clean_json_string(content)
        try:
            data = json.loads(cleaned)
            return response_model.model_validate(data)
        except Exception as e:
            logger.error(f"Claude returned malformed response: {content[:500]}")
            raise ValueError(f"Claude returned malformed JSON: {e}")
    finally:
        # Release the async Anthropic client (AsyncAnthropicVertex talks to the
        # same Vertex endpoint as Gemini), so its transport is not reported as an
        # unclosed socket/transport at GC. close() is a coroutine on the real
        # client but a plain MagicMock in unit tests -- await only if awaitable.
        closer = getattr(client, "close", None)
        if closer is not None:
            try:
                maybe_coro = closer()
                if inspect.isawaitable(maybe_coro):
                    await maybe_coro
            except Exception:
                pass

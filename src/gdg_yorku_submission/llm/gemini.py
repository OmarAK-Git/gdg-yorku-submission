import os
import json
import asyncio
import threading
import logging
from contextlib import aclosing
from typing import Optional, Any, List, Dict
from gdg_yorku_submission.budget import record_llm_usage

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    A wrapper client for Gemini calls.
    Supports a production Vertex AI / Google Generative AI implementation
    and a mock/fake implementation for testing and dry-runs.
    """
    def __init__(
        self,
        use_fake: Optional[bool] = None,
        fake_responses: Optional[List[str]] = None
    ) -> None:
        if use_fake is None:
            # Default to real mode (use_fake = False) in production.
            # If USE_FAKE_LLM is explicitly set, follow that.
            env_use_fake = os.getenv("USE_FAKE_LLM")
            if env_use_fake is not None:
                self.use_fake = env_use_fake.lower() == "true"
            else:
                self.use_fake = False
        else:
            self.use_fake = use_fake

        if not self.use_fake:
            has_creds = (
                os.getenv("GEMINI_API_KEY") or
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or
                os.getenv("GOOGLE_CLOUD_PROJECT")
            )
            if not has_creds:
                raise RuntimeError(
                    "GeminiClient initialized in real/production mode but no credentials "
                    "(GEMINI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, or GOOGLE_CLOUD_PROJECT) "
                    "were detected."
                )

        self.fake_responses = fake_responses or []
        self._fake_index = 0

    def generate_content(
        self,
        orch,
        prompt: str,
        response_schema: Optional[Any] = None,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500,
        component: str = "correctness_agent"
    ) -> str:
        """
        Generates content from the model.
        Acquires/records budget lease information directly.
        """
        # Acquire budget lease before each call/retry (Issue 1 & 8)
        from gdg_yorku_submission.budget import BudgetLease, acquire_budget_lease
        lease = BudgetLease(
            component=component,
            estimated_tokens=estimated_input_tokens + estimated_output_tokens,
            provider="gemini"
        )
        acquire_budget_lease(orch, lease)

        if self.use_fake:
            # Fake/mock execution
            if self.fake_responses:
                idx = min(self._fake_index, len(self.fake_responses) - 1)
                response_text = self.fake_responses[idx]
                self._fake_index += 1
            elif response_schema:
                try:
                    from pydantic import BaseModel
                    if issubclass(response_schema, BaseModel):
                        if response_schema.__name__ == "CoordinatorOutput":
                            dummy = {
                                "merges": [],
                                "omissions": [],
                                "recommended_actions": {}
                            }
                            response_text = json.dumps(dummy)
                        else:
                            instance = response_schema()
                            response_text = instance.model_dump_json()
                    else:
                        response_text = "{}"
                except Exception as e:
                    logger.warning(f"Failed to generate fake response for schema {response_schema}: {e}")
                    response_text = "{}"
            else:
                # Return a default valid correctness finding JSON
                response_text = json.dumps([
                    {
                        "id": "prov-correctness-finding-1",
                        "source_agent": "correctness_agent",
                        "perspective": "correctness",
                        "severity": "high",
                        "location": {
                            "path": "src/app.py",
                            "line_start": 5,
                            "line_end": 10
                        },
                        "claim": "[SYNTHETIC-DEFAULT] Default mock correctness finding.",
                        "evidence_ref": ["file:SPEC.md#12-14"],
                        "status": "active",
                        "metadata": {}
                    }
                ])

            # Record fake usage
            total_tokens = estimated_input_tokens + estimated_output_tokens
            # Input: $0.075/1M, Output: $0.30/1M
            cost = (estimated_input_tokens * 0.075 / 1_000_000) + (estimated_output_tokens * 0.30 / 1_000_000)
            record_llm_usage(orch, "gemini", total_tokens, cost)
            return response_text

        else:
            # If using AdkOrchestrator, route through ADK runtime (LlmAgent + Runner)
            if type(orch).__name__ == "AdkOrchestrator" and hasattr(orch, "_session_service") and not getattr(orch, "_fallback_mode", True):
                try:
                    from google.adk import Runner
                    from google.adk.agents import LlmAgent
                    from google.adk.models.google_llm import Gemini
                    from google.genai import types
                    from functools import cached_property
                    from google.genai import Client

                    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
                    
                    class VertexGemini(Gemini):
                        @cached_property
                        def api_client(self) -> Client:
                            project = os.getenv("GOOGLE_CLOUD_PROJECT")
                            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
                            api_key = os.getenv("GEMINI_API_KEY")
                            if project:
                                return Client(
                                    vertexai=True,
                                    project=project,
                                    location=location
                                )
                            elif api_key:
                                return Client(
                                    api_key=api_key
                                )
                            else:
                                return Client()

                    adk_model = VertexGemini(model=model_name)
                    
                    agent = LlmAgent(
                        name="gemini_client_adk_agent",
                        model=adk_model,
                        instruction="You are a helpful assistant. Respond with content adhering to the output schema if specified.",
                        output_schema=response_schema
                    )
                    
                    runner = Runner(
                        app_name="gdg-yorku-submission",
                        agent=agent,
                        session_service=orch._session_service
                    )
                    
                    new_message = types.Content(parts=[types.Part.from_text(text=prompt)])
                    
                    async def _drive_adk_runner():
                        """Drive the ADK runner and release the async genai client
                        before the event loop is torn down.

                        google.genai.Client.close() only closes the *synchronous*
                        client (per its own docstring); the ADK runner uses the
                        async client, whose transports must be aclose()'d from
                        inside the loop that opened them. Skipping this leaks
                        '_ProactorSocketTransport' objects that asyncio reports as
                        unclosed-transport ResourceWarnings at interpreter GC.
                        """
                        collected = []
                        try:
                            async with aclosing(runner.run_async(
                                user_id="system",
                                session_id=orch.run_id,
                                new_message=new_message
                            )) as agen:
                                async for event in agen:
                                    collected.append(event)
                        finally:
                            # Only touch the client if ADK actually instantiated
                            # it (cached_property stores it in __dict__); reading
                            # the property here would otherwise construct a client
                            # purely in order to close it.
                            cached = adk_model.__dict__.get("api_client")
                            aio = getattr(cached, "aio", None) if cached is not None else None
                            if aio is not None and hasattr(aio, "aclose"):
                                await aio.aclose()
                        return collected

                    # generate_content() runs *inside* an active event loop (the
                    # CLI driver wraps the pipeline in asyncio.run(); the FastAPI
                    # handlers are async). asyncio.run() refuses to nest, so -- like
                    # ADK's own sync Runner.run() -- drive the async generator on a
                    # dedicated thread that owns a fresh loop. Unlike ADK's run(),
                    # we also aclose() the async client above, in the same loop.
                    _runner_result: Dict[str, Any] = {}

                    def _run_adk_in_thread():
                        try:
                            _runner_result["events"] = asyncio.run(_drive_adk_runner())
                        except BaseException as thread_err:  # noqa: BLE001
                            _runner_result["error"] = thread_err

                    _adk_thread = threading.Thread(target=_run_adk_in_thread)
                    _adk_thread.start()
                    _adk_thread.join()

                    if "error" in _runner_result:
                        raise _runner_result["error"]
                    events = _runner_result["events"]

                    # Release the synchronous side of the same client as well,
                    # again only if ADK actually constructed it.
                    cached_client = adk_model.__dict__.get("api_client")
                    if cached_client is not None:
                        try:
                            cached_client.close()
                        except Exception:
                            pass
                    
                    response_text = ""
                    for event in events:
                        if event.output is not None:
                            if isinstance(event.output, str):
                                response_text = event.output
                            elif hasattr(event.output, "model_dump_json"):
                                response_text = event.output.model_dump_json()
                            elif isinstance(event.output, (dict, list)):
                                response_text = json.dumps(event.output)
                            else:
                                response_text = str(event.output)
                            break
                    
                    if not response_text:
                        for event in events:
                            if event.content and event.content.parts:
                                for part in event.content.parts:
                                    if part.text:
                                        response_text += part.text
                                        
                    # Record the LLM usage
                    total_tokens = estimated_input_tokens + estimated_output_tokens
                    cost = (estimated_input_tokens * 0.075 / 1_000_000) + (estimated_output_tokens * 0.30 / 1_000_000)
                    record_llm_usage(orch, "gemini", total_tokens, cost)
                    
                    # Store an execution confirmation in state for verification tests
                    orch.set_run_metadata("adk_runner_executed", True)
                    
                    return response_text
                except Exception as adk_err:
                    logger.warning(
                        f"Real LLM call via ADK Runner failed: {adk_err}. "
                        "Falling back to direct Vertex AI / Generative AI client..."
                    )
                    orch.set_run_metadata(
                        "adk_runner_warning",
                        "ADK Runner failed; fell back to direct Vertex"
                    )


            # Direct Vertex AI / enterprise / local fallback using unified google-genai SDK
            client = None
            try:
                from google import genai
                from google.genai import types

                project = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
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

                model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
                
                config_args = {}
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema
                
                config = types.GenerateContentConfig(**config_args) if config_args else None
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )

                # Track usage
                input_tokens = estimated_input_tokens
                output_tokens = estimated_output_tokens
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens = response.usage_metadata.prompt_token_count
                    output_tokens = response.usage_metadata.candidates_token_count
                    
                total_tokens = input_tokens + output_tokens
                cost = (input_tokens * 0.075 / 1_000_000) + (output_tokens * 0.30 / 1_000_000)
                record_llm_usage(orch, "gemini", total_tokens, cost)
                
                return response.text
            except Exception as e:
                logger.error(f"google.genai call failed. Error: {e}")
                raise RuntimeError(f"google.genai call failed: {e}")
            finally:
                # The direct fallback uses the synchronous client; release its
                # transports so they are not reported as unclosed sockets at GC.
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass

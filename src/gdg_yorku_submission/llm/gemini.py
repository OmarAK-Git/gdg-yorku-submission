import os
import json
import logging
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
            if self._fake_index < len(self.fake_responses):
                response_text = self.fake_responses[self._fake_index]
                self._fake_index += 1
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
            # Real production call using Vertex AI or google.generativeai
            # For robustness, we check for google-generativeai and vertexai setup
            try:
                # 1. Try google.generativeai first
                import google.generativeai as genai
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                    
                    generation_config = {}
                    if response_schema:
                        generation_config["response_mime_type"] = "application/json"
                        generation_config["response_schema"] = response_schema
                        
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    # Track usage from response metadata if available
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
                logger.warning(f"Failed to use google.generativeai client: {e}. Trying vertexai...")

            try:
                # 2. Try vertexai
                import vertexai
                from vertexai.generative_models import GenerativeModel, GenerationConfig
                
                project = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
                vertexai.init(project=project, location=location)
                
                model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                model = GenerativeModel(model_name)
                
                config_args = {}
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema
                    
                generation_config = GenerationConfig(**config_args) if config_args else None
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
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
                logger.error(f"Vertex AI call failed: {e}")
                raise RuntimeError(f"Vertex AI Gemini API call failed: {e}")

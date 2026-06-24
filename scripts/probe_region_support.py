"""One-off probe: which Vertex region serves BOTH our Gemini and Claude models?

Makes minimal (≈1 token) calls so cost is negligible. Reports, per candidate
region, whether each model resolves (OK), 404s (NOT SERVED), or hits some other
error (e.g. 429 quota / 403 perms — meaning the model exists but is gated).

Run:  python scripts/probe_region_support.py
Reads GOOGLE_CLOUD_PROJECT from the environment / .env (ADC must be configured).
"""
import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = "gemini-3.5-flash"
CLAUDE_MODELS = ["claude-opus-4-8", "claude-sonnet-4-6"]
# Regions worth checking. global is the current baseline; us-east5 is the usual
# Claude-on-Vertex home; us-central1/us-east1/europe-west1 are common Gemini regions.
REGIONS = ["global", "us-east5", "us-central1", "us-east1", "europe-west1"]


def classify(exc: Exception) -> str:
    s = str(exc)
    code = getattr(exc, "status_code", None)
    if "404" in s or code == 404:
        return "NOT SERVED (404)"
    if "429" in s or code == 429:
        return "served but QUOTA/429"
    if "403" in s or code == 403:
        return "served but 403 (perms)"
    return f"ERROR: {s[:120]}"


def probe_gemini(region: str) -> str:
    try:
        from google import genai
        client = genai.Client(vertexai=True, project=PROJECT, location=region)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents="hi")
        _ = resp  # noqa: F841
        return "OK"
    except Exception as e:  # noqa: BLE001
        return classify(e)


async def probe_claude(region: str, model: str) -> str:
    try:
        from anthropic import AsyncAnthropicVertex
        client = AsyncAnthropicVertex(project_id=PROJECT, region=region)
        await client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return "OK"
    except Exception as e:  # noqa: BLE001
        return classify(e)


async def main() -> None:
    if not PROJECT:
        print("GOOGLE_CLOUD_PROJECT not set; cannot probe Vertex.")
        sys.exit(1)
    print(f"Project: {PROJECT}\n")
    header = f"{'region':<14} {GEMINI_MODEL:<22} " + " ".join(f"{m:<22}" for m in CLAUDE_MODELS)
    print(header)
    print("-" * len(header))
    for region in REGIONS:
        g = probe_gemini(region)
        claude_results = [await probe_claude(region, m) for m in CLAUDE_MODELS]
        row = f"{region:<14} {g:<22} " + " ".join(f"{r:<22}" for r in claude_results)
        print(row)


if __name__ == "__main__":
    asyncio.run(main())

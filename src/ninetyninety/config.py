"""Model provider selection.

Gemini's free tier needs no credit card; its exact quota is no longer
published, so read the live numbers at aistudio.google.com/rate-limit.
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL_ID = "gemini-2.5-flash"
OPENROUTER_MODEL_ID = "nvidia/nemotron-3-super-120b-a12b:free"  # verified live 2026-09-06; z-ai/glm-5.2:free no longer listed
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# AgentRouter: OpenAI-compatible gateway to Claude. Claude/GPT there draw on a
# daily quota pool (402 "Budget pool quota has been exhausted" when drained),
# so a second provider stays configured as failover.
AGENTROUTER_MODEL_ID = "claude-sonnet-4-5"
AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"


def select_provider(env: dict) -> str | None:
    if env.get("AGENTROUTER_API_KEY"):
        return "agentrouter"
    if env.get("GOOGLE_API_KEY"):
        return "gemini"
    if env.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def build_model(provider: str | None = None):
    provider = provider or select_provider(os.environ)
    if provider == "gemini":
        from strands.models.gemini import GeminiModel
        return GeminiModel(
            client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
            model_id=GEMINI_MODEL_ID,
        )
    if provider == "openrouter":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": os.environ["OPENROUTER_API_KEY"],
                         "base_url": OPENROUTER_BASE_URL},
            model_id=os.environ.get("OPENROUTER_MODEL_ID", OPENROUTER_MODEL_ID),
        )
    if provider == "agentrouter":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": os.environ["AGENTROUTER_API_KEY"],
                         "base_url": AGENTROUTER_BASE_URL},
            model_id=os.environ.get("AGENTROUTER_MODEL_ID", AGENTROUTER_MODEL_ID),
        )
    raise RuntimeError(
        "No model provider configured. Get a free key at "
        "https://aistudio.google.com/apikey and set GOOGLE_API_KEY, "
        "or set AGENTROUTER_API_KEY / OPENROUTER_API_KEY. See .env.example."
    )

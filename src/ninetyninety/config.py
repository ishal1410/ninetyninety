"""Model provider selection.

Gemini's free tier needs no credit card; its exact quota is no longer
published, so read the live numbers at aistudio.google.com/rate-limit.
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL_ID = "gemini-2.5-flash"
OPENROUTER_MODEL_ID = "z-ai/glm-5.2:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def select_provider(env: dict) -> str | None:
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
            model_id=OPENROUTER_MODEL_ID,
        )
    raise RuntimeError(
        "No model provider configured. Get a free key at "
        "https://aistudio.google.com/apikey and set GOOGLE_API_KEY, "
        "or set OPENROUTER_API_KEY. See .env.example."
    )

"""Model provider selection.

Gemini's free tier needs no credit card; its exact quota is no longer
published, so read the live numbers at aistudio.google.com/rate-limit.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Gemini free tier, measured 2026-09-06: 20 requests per DAY per model per
# project. Each model id has its own cap, so the failover list rotates through
# several. gemini-2.5-flash 404s for new users. Override with GEMINI_MODEL_IDS.
GEMINI_MODEL_IDS = [m.strip() for m in os.environ.get(
    "GEMINI_MODEL_IDS", "gemini-3.8-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash-lite"
).split(",") if m.strip()]
GEMINI_MODEL_ID = GEMINI_MODEL_IDS[0]
OPENROUTER_MODEL_ID = "nvidia/nemotron-3-super-120b-a12b:free"  # verified live 2026-09-06; z-ai/glm-5.2:free no longer listed
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def select_provider(env: dict) -> str | None:
    if env.get("GOOGLE_API_KEY"):
        return "gemini"
    if env.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def providers_in_order(env: dict) -> list[str]:
    """Every configured provider, best first. prepare_ledger fails over down
    this list. Gemini appears once per model id ("gemini:<model>") because the
    free tier's daily cap is per model."""
    order = []
    if env.get("GOOGLE_API_KEY"):
        order += [f"gemini:{model}" for model in GEMINI_MODEL_IDS]
    if env.get("OPENROUTER_API_KEY"):
        order.append("openrouter")
    return order


def build_model(provider: str | None = None):
    provider = provider or select_provider(os.environ)
    if provider and provider.startswith("gemini"):
        from strands.models.gemini import GeminiModel
        _, _, model_id = provider.partition(":")
        return GeminiModel(
            client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
            model_id=model_id or GEMINI_MODEL_ID,
        )
    if provider == "openrouter":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": os.environ["OPENROUTER_API_KEY"],
                         "base_url": OPENROUTER_BASE_URL},
            model_id=os.environ.get("OPENROUTER_MODEL_ID", OPENROUTER_MODEL_ID),
        )
    raise RuntimeError(
        "No model provider configured. Get a free key at "
        "https://aistudio.google.com/apikey and set GOOGLE_API_KEY, "
        "or set OPENROUTER_API_KEY. See .env.example."
    )

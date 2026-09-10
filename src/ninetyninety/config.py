"""One model provider: Google Gemini, through Strands' native GeminiModel.

The free tier needs no card. Measured 2026-09-06: 20 requests per DAY per
model per project, so one ledger cannot finish on a single model id and
prepare_ledger rotates through GEMINI_MODEL_IDS when one is exhausted.
GOOGLE_API_KEY is the only required setting.
"""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL_IDS = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash-lite"

# Strands passes `params` straight into Gemini's GenerationConfig, so greedy
# decoding and a fixed seed are all it takes to stop the sampler being a source
# of run-to-run disagreement between the Preparer and the Reviewer.
# ponytail: this narrows variance, it does not remove it -- Gemini batches
# requests server-side and the free tier rotates model ids mid-ledger.
SAMPLING = {"temperature": 0, "top_p": 1, "seed": 990}


def gemini_configured(env: dict) -> bool:
    return bool(env.get("GOOGLE_API_KEY"))


def model_ids(env: dict | None = None) -> list[str]:
    """Model ids to try, in order; each has its own daily cap."""
    env = os.environ if env is None else env
    ids = [m.strip() for m in env.get("GEMINI_MODEL_IDS", DEFAULT_MODEL_IDS).split(",") if m.strip()]
    return ids or DEFAULT_MODEL_IDS.split(",")  # an empty override must not mean "no model"


def build_model(model_id: str | None = None):
    if not gemini_configured(os.environ):
        raise RuntimeError(
            "Gemini is not configured. Get a free key at "
            "https://aistudio.google.com/apikey and set GOOGLE_API_KEY in .env. "
            "See .env.example.")
    from strands.models.gemini import GeminiModel
    return GeminiModel(client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
                       model_id=model_id or model_ids()[0], params=dict(SAMPLING))


def provider_label(model) -> str:
    """What the trace shows for the provider that answered a batch."""
    model_id = getattr(model, "config", {}).get("model_id", "?")
    return f"gemini:{model_id}"
